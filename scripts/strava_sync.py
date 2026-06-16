import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI
import re

# --- CONFIGURAÇÕES ---
SYNC_FILE = "scripts/last_sync.json"
DEFAULT_START_DATE = datetime(2026, 5, 16)
TOLERANCE_DAYS = 1
PLAN_PATH = "Plano_Treino_2026.md"

def load_start_date():
    """Carrega a data do último sincronismo ou usa a padrão."""
    if os.path.exists(SYNC_FILE):
        try:
            with open(SYNC_FILE, 'r') as f:
                data = json.load(f)
                return datetime.fromtimestamp(data['last_sync_timestamp'])
        except Exception:
            pass
    return DEFAULT_START_DATE

def save_start_date(dt):
    """Salva o timestamp do sincronismo atual."""
    with open(SYNC_FILE, 'w') as f:
        json.dump({
            'last_sync_timestamp': int(dt.timestamp()), 
            'last_sync_human': dt.strftime("%Y-%m-%d %H:%M:%S")
        }, f, indent=4)

def get_strava_activities(access_token, start_dt):
    """Busca atividades de corrida no Strava após a data informada."""
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"after": int(start_dt.timestamp()), "per_page": 50}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Erro Strava: {response.json()}")
        return []
    
    # Filtra apenas corridas
    return [a for a in response.json() if a['type'] == 'Run']

def get_access_token():
    """Troca o refresh_token por um access_token válido."""
    res = requests.post(
        "https://www.strava.com/api/v3/oauth/token",
        data={
            "client_id": os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        },
    )
    if res.status_code != 200:
        print(f"Erro na Autenticação Strava (Status {res.status_code}):")
        print(f"Resposta: {res.text}")
        return None
    
    try:
        return res.json().get("access_token")
    except Exception as e:
        print(f"Erro ao processar JSON de autenticação: {e}")
        return None

def analyze_with_ai(planned, real):
    """Usa o OpenRouter para gerar uma análise técnica do treino."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    
    prompt = f"""
    Como um treinador de corrida de elite, analise este treino de forma realista e técnica:
    PLANEJADO: {planned}
    REALIZADO: Distância: {real['distance']:.2f}km, Pace Médio: {real['pace']}, Tempo: {real['time']}
    
    Regras:
    1. Seja direto e realista (máximo 40 palavras).
    2. Compare objetivamente o Pace Real vs Alvo e a Distância realizada.
    3. Foco em fatos e métricas, sem frases motivacionais genéricas.
    """
    try:
        response = client.chat.completions.create(
            model='openrouter/free',
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro AI: {e}")
        return "Erro na análise da IA."

def format_pace(seconds_per_km):
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}"

def sync():
    access_token = get_access_token()
    if not access_token:
        print("Erro: Não foi possível obter o access_token do Strava.")
        return

    start_dt = load_start_date()
    print(f"Buscando atividades desde: {start_dt.strftime('%d/%m/%Y %H:%M:%S')}")
    
    activities = get_strava_activities(access_token, start_dt)
    
    if not activities:
        print("Nenhuma atividade nova encontrada no Strava.")
        save_start_date(datetime.now())
        return

    # Agrupa atividades por data (Consolidação)
    daily_stats = {}
    for act in activities:
        date_str = act['start_date_local'][:10]
        if date_str not in daily_stats:
            daily_stats[date_str] = {"dist": 0, "time": 0}
        daily_stats[date_str]["dist"] += act['distance'] / 1000 # km
        daily_stats[date_str]["time"] += act['moving_time'] # segundos

    # Lendo o Plano Markdown
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated = False
    for date_str, stats in daily_stats.items():
        act_date = datetime.strptime(date_str, "%Y-%m-%d")
        pace_real = format_pace(stats['time'] / stats['dist'])
        
        # Procura a linha correspondente no MD com janela de tolerância
        for i, line in enumerate(lines):
            match = re.search(r'\|\s*(\d{2}/\d{2}(?:/\d{4})?)\s*\|', line)
            if match:
                plan_date_str = match.group(1)
                if len(plan_date_str) == 5: # Formato DD/MM
                    plan_date_str += "/2026"
                plan_date = datetime.strptime(plan_date_str, "%d/%m/%Y")
                
                if plan_date == act_date:
                    cols = [c.strip() for c in line.split("|")]
                    
                    if len(cols) > 11 and (not cols[8] or "Erro" in cols[11]):
                        print(f"Sincronizando treino de {date_str} com plano de {plan_date_str}...")
                        
                        planned_info = f"Distância: {cols[4]}, Pace Alvo: {cols[5]}, Tipo: {cols[3]}"
                        real_info = {"distance": stats['dist'], "pace": pace_real, "time": format_pace(stats['time'])}
                        
                        avaliacao = analyze_with_ai(planned_info, real_info)
                        
                        cols[8] = pace_real
                        cols[11] = avaliacao
                        
                        lines[i] = " | ".join(cols) + "\n"
                        updated = True
                        break

    if updated:
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("Plano de treino atualizado com sucesso!")
    
    save_start_date(datetime.now())
    print(f"Novo marco de sincronismo salvo.")

if __name__ == "__main__":
    sync()
