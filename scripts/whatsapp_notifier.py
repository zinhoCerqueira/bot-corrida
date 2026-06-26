import os
import re
import urllib.parse
import requests
from datetime import datetime, timedelta
from openai import OpenAI
import random

# Configurações
PLAN_PATH = "Plano_Treino_2026.md"
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GREETINGS = [
    "🏃‍♂️ *BORA ATLETA! Seu Treino de Hoje:*",
    "🔥 *PRA CIMA! Veja o que temos para hoje:*",
    "👟 *AJUSTA O TÊNIS! O plano de hoje é:*",
    "🎯 *FOCO NO OBJETIVO! Seu treino do dia:*",
    "🌟 *MAIS UM DIA DE EVOLUÇÃO! Confira seu treino:*",
    "🚀 *VAI QUE É TUA! O desafio de hoje:*",
    "💪 *DISCIPLINA É TUDO! Hoje tem:*",
    "⚡ *ENERGIA LÁ NO ALTO! Seu compromisso de hoje:*"
]

def clean_md(text):
    if not text: return ""
    return text.replace('**', '').replace('~', '').strip()

def get_training_for_date(target_date):
    """Busca os dados do treino no Markdown para uma data específica."""
    with open(PLAN_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    current_fase, current_semana = "Desconhecida", "0"
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Detecta Fase
        if '## FASE' in line.upper():
            fase_match = re.search(r'## (FASE \d+ — .*?)(?:\n|$)', line)
            if fase_match:
                full = fase_match.group(1)
                current_fase = full.split(' — ')[1].strip() if ' — ' in full else full
        
        # Detecta Semana
        if '### Semana' in line:
            semana_match = re.search(r'### Semana (\d+)', line)
            if semana_match: current_semana = semana_match.group(1)

        # Parser da tabela
        if line.count('|') >= 9 and 'Data' not in line and '---' not in line:
            parts = [clean_md(p) for p in line.strip().split('|')][1:-1]
            if len(parts) >= 1:
                data_val = parts[0]
                if data_val == target_date.strftime("%d/%m"):
                    return {
                        "fase": current_fase,
                        "semana": current_semana,
                        "tipo": parts[2],
                        "dist": parts[3],
                        "pace": parts[4],
                        "zona": parts[5],
                        "detalhes": parts[6]
                    }
    return None

def get_ai_coaching_tip(training, feedback_anterior=None):
    """Usa o OpenRouter para gerar uma dica técnica personalizada baseada no tipo de treino."""
    if not OPENROUTER_API_KEY:
        return None
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    
    feedback_text = feedback_anterior["aval"] if feedback_anterior else "Nenhum feedback recente"
    
    prompt = f"""
    Você é um treinador de corrida de elite. Dê uma dica técnica e focada para o treino de HOJE.

    CONTEXTO DO ATLETA:
    - Fase do plano: {training['fase']}
    - Semana: {training['semana']}
    - Treino de hoje: {training['tipo']} - {training['dist']}
    - Instruções: {training['detalhes']}
    - Último feedback: {feedback_text}

    Regras:
    1. Máximo 60 palavras.
    2. A dica deve ser específica para o tipo de treino de hoje:
       - LR: estratégia de ritmo, hidratação, percepção de esforço ao longo do tempo
       - TIROS/TM/TC: postura, cadência, controle nas repetições
       - CL/CM: relaxamento, zona de conforto, economia de movimento
       - PROG: transição de ritmo, paciência no começo
       - PROVA: pacing, estratégia de largada, mental
    3. Se houver feedback do treino anterior, faça uma conexão breve (ex: "seguindo o que vimos no último treino...")
    4. Seja direto e inspirador, mas com conteúdo técnico — nada de "você consegue" vazio.
    """
    try:
        response = client.chat.completions.create(
            model='openrouter/free',
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro AI Notifier: {e}")
        return None

def get_previous_training_feedback():
    """Busca a última avaliação (IA) preenchida no Markdown."""
    with open(PLAN_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    # Percorre de trás para frente para achar o último treino avaliado
    for line in reversed(lines):
        if line.count('|') >= 11:
            parts = [clean_md(p) for p in line.strip().split('|')][1:-1]
            # parts[10] é a coluna "Avaliação"
            if len(parts) >= 11 and parts[10] and 'Avaliação' not in parts[10] and '---' not in parts[10]:
                return {
                    "data": parts[0],
                    "tipo": parts[2],
                    "aval": parts[10]
                }
    return None

def format_message(training, date_obj, is_preview=False):
    """Formata a mensagem no estilo Entusiasta & Visual com saudação aleatória e dica de IA."""
    date_str = date_obj.strftime("%d/%m (%A)")
    
    if not training or not training['tipo']:
        return f"✨ *Descanso Merecido!* 🧘‍♂️\n\nHoje, {date_str}, não há treino planejado. Aproveite para recuperar as energias!"

    greeting = random.choice(GREETINGS)
    msg = f"{greeting} {date_str}\n\n"
    
    # Feedback do treino anterior
    prev_feedback = get_previous_training_feedback()
    if prev_feedback:
        msg += f"⏮️ *Último Treino ({prev_feedback['data']}):*\n_{prev_feedback['aval']}_\n\n"
        msg += "---" * 3 + "\n\n"

    msg += "🏃 *TREINO DE HOJE:*\n"
    msg += f"📍 *{training['fase']}* | Semana {training['semana']}\n"
    msg += f"🎯 *{training['tipo']} - {training['dist']}*\n\n"
    msg += f"⏱️ *Pace Alvo:* {training['pace']}\n"
    msg += f"💓 *Zona:* {training['zona']}\n"
    msg += f"📝 *Instruções:* {training['detalhes']}\n\n"
    
    # Busca dica da IA
    ai_tip = get_ai_coaching_tip(training, prev_feedback)
    if ai_tip:
        msg += f"🧠 *Dica do Treinador:* {ai_tip}\n\n"
    
    msg += "Foco total na execução! 🚀🔥"
    return msg

def get_weekly_preview(start_date):
    """Gera um resumo dos próximos 3 treinos."""
    preview = "📅 *Preview da Semana:*\n"
    found = 0
    for i in range(1, 8):
        future_date = start_date + timedelta(days=i)
        train = get_training_for_date(future_date)
        if train and train['tipo']:
            preview += f"• {future_date.strftime('%d/%m')}: {train['tipo']} ({train['dist']})\n"
            found += 1
            if found >= 3: break
    return preview if found > 0 else ""

def send_whatsapp(message):
    """Envia a mensagem via CallMeBot."""
    if not WHATSAPP_PHONE or not WHATSAPP_API_KEY:
        print("Erro: Variáveis de ambiente WHATSAPP não configuradas.")
        return

    msg_encoded = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_PHONE}&text={msg_encoded}&apikey={WHATSAPP_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        print("Mensagem enviada com sucesso!")
    else:
        print(f"Erro ao enviar: {response.text}")

def main():
    # Ajuste de fuso horário para Brasil (UTC-3)
    today = datetime(2026, 6, 28, 6, 0, 0)  # TESTE: domingo 06:00 BRT forçado
    
    # Lógica para Domingo à Noite (Apenas Preview)
    if today.weekday() == 6 and today.hour >= 18:
        preview = get_weekly_preview(today)
        if preview:
            message = f"📝 *PREPARA O CORAÇÃO!* 📝\nConfira o que vem por aí na sua semana de treinos:\n\n{preview}\nBons treinos e boa semana! 🚀"
            send_whatsapp(message)
        return

    # Lógica normal para treinos do dia
    training = get_training_for_date(today)
    message = format_message(training, today)
    
    send_whatsapp(message)

if __name__ == "__main__":
    main()
