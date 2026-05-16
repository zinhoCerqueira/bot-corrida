import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import re

# --- CONFIGURAÇÕES ---
START_DATE = datetime(2026, 5, 17)  # Data de corte para o sync
TOLERANCE_DAYS = 1
PLAN_PATH = "Plano_Treino_2026.md"

def get_strava_activities(access_token):
    """Busca atividades de corrida no Strava após a START_DATE."""
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"after": int(START_DATE.timestamp()), "per_page": 50}
    
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
    return res.json().get("access_token")

def analyze_with_gemini(planned, real):
    """Usa o Gemini para gerar uma análise técnica do treino."""
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Como um treinador de corrida de elite, analise este treino:
    PLANEJADO: {planned}
    REALIZADO: Distância: {real['distance']:.2f}km, Pace Médio: {real['pace']}, Tempo: {real['time']}
    
    Regras:
    1. Seja breve (máximo 15 palavras).
    2. Compare Pace Real vs Alvo e Distância.
    3. Use um tom técnico e motivador.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Erro na análise da IA."

def format_pace(seconds_per_km):
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}"

def sync():
    access_token = get_access_token()
    activities = get_strava_activities(access_token)
    
    if not activities:
        print("Nenhuma atividade nova encontrada no Strava.")
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
            # Regex para capturar a data na coluna 1 (ex: | 18/05/2026 |)
            match = re.search(r'\|\s*(\d{2}/\d{2}/\d{4})\s*\|', line)
            if match:
                plan_date = datetime.strptime(match.group(1), "%d/%m/%Y")
                
                # Se estiver dentro da janela e a coluna 'Pace Real' (coluna 11) estiver vazia
                if abs((plan_date - act_date).days) <= TOLERANCE_DAYS:
                    cols = [c.strip() for c in line.split("|")]
                    
                    # Coluna 11 é o Pace Real, Coluna 14 é Avaliação
                    # Se Pace Real estiver vazio (ou apenas espaços)
                    if len(cols) > 11 and not cols[11]:
                        print(f"Sincronizando treino de {date_str} com plano de {match.group(1)}...")
                        
                        planned_info = f"Distância: {cols[5]}, Pace Alvo: {cols[6]}, Tipo: {cols[3]}"
                        real_info = {"distance": stats['dist'], "pace": pace_real, "time": format_pace(stats['time'])}
                        
                        avaliacao = analyze_with_gemini(planned_info, real_info)
                        
                        # Atualiza as colunas (índices 11 e 14)
                        cols[11] = pace_real
                        cols[14] = avaliacao
                        
                        lines[i] = " | ".join(cols) + "\n"
                        updated = True
                        break

    if updated:
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("Plano de treino atualizado com sucesso!")
    else:
        print("Nenhum registro novo para atualizar no Markdown.")

if __name__ == "__main__":
    sync()
