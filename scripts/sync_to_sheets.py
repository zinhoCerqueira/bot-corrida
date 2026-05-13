import os
import re
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configurações
MD_FILE = 'Plano_Treino_2026.md'
# O ID e as Credenciais virão do ambiente (GitHub Secrets)
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SERVICE_ACCOUNT_ENV = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def pace_to_decimal(pace_str):
    """Converte pace string (ex: '6:30', '6:30–6:45') em minutos decimais."""
    if not pace_str or pace_str == '-':
        return None
    # Encontra todos os padrões MM:SS
    matches = re.findall(r'(\d+):(\d+)', str(pace_str))
    if not matches:
        return None
    # Converte cada par para decimal e calcula a média
    decimals = [int(m) + int(s)/60.0 for m, s in matches]
    return round(sum(decimals) / len(decimals), 2)

def parse_markdown_to_dataframe(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo {file_path} não encontrado.")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex para capturar fases e semanas
    fase_pattern = r'## (FASE \d+ — .*?)\n'
    semana_pattern = r'### Semana (\d+)'
    
    rows = []
    current_fase = "Base"
    current_semana = 0
    
    lines = content.split('\n')
    for line in lines:
        # Detectar Fase (ex: ## FASE 1 — BASE AERÓBIA)
        if line.startswith('## FASE'):
            fase_match = re.search(fase_pattern, line + '\n')
            if fase_match:
                full_fase = fase_match.group(1)
                current_fase = full_fase.split(' — ')[1].strip() if ' — ' in full_fase else full_fase
        
        # Detectar Semana (ex: ### Semana 1 (03–07/mai))
        if line.startswith('### Semana'):
            semana_match = re.search(semana_pattern, line)
            if semana_match:
                current_semana = int(semana_match.group(1))

        # Detectar Linha de Tabela de Treino
        # Esperado: | Data | Dia | Treino | Distância | Pace Alvo | Zona | Detalhes | Pace Real | Percepção | Comentários |
        if line.count('|') >= 9 and 'Data' not in line and '---' not in line:
            parts = [p.strip() for p in line.split('|')][1:-1]
            if len(parts) >= 10:
                data_val = parts[0]
                dia_val = parts[1]
                tipo_val = parts[2]
                dist_val = parts[3].replace('km', '').strip()
                pace_alvo = parts[4]
                zona_val = parts[5]
                detalhes_val = parts[6]
                pace_real = parts[7]
                percepcao = parts[8]
                comentarios = parts[9]
                
                # Calcular Pace Médio Decimal
                pace_medio = pace_to_decimal(pace_alvo)
                
                rows.append([
                    data_val, dia_val, f"S{current_semana:02d}", current_fase,
                    tipo_val, dist_val, pace_alvo, pace_medio, zona_val,
                    detalhes_val, pace_real, percepcao, comentarios
                ])

    columns = [
        'Data', 'Dia', 'Semana', 'Fase', 'Tipo', 'Distância (km)', 
        'Pace Alvo', 'Pace Alvo Médio', 'Zona', 'Detalhes', 
        'Pace Real', 'Percepção (0-10)', 'Comentários'
    ]
    return pd.DataFrame(rows, columns=columns)

def update_google_sheets(df):
    try:
        service_account_info = json.loads(SERVICE_ACCOUNT_ENV)
    except Exception as e:
        print(f"Erro ao carregar JSON da conta de serviço: {e}")
        return

    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    # Preparar dados para o Google Sheets (lista de listas)
    # Não incluímos o cabeçalho porque ele já está na planilha base (linha 2)
    values = df.values.tolist()
    
    # Substituir valores nulos/NaN por '-' para a API não dar erro
    values = [[val if (pd.notnull(val) and val != '') else '-' for val in row] for row in values]

    body = {'values': values}
    
    # Diagnóstico: Listar abas antes de tentar o update
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
    print(f"DEBUG: Abas encontradas na planilha: {sheets}")

    range_name = "'Plano Completo'!A3" 
    if "Plano Completo" not in sheets:
        print(f"AVISO: Aba 'Plano Completo' não encontrada. Tentando usar a primeira aba: '{sheets[0]}'")
        range_name = f"'{sheets[0]}'!A3"

    print(f"DEBUG: Enviando {len(values)} linhas. Primeira linha: {values[0]}")
    
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        print(f"Sincronização concluída com sucesso na aba {range_name}!")
    except Exception as api_error:
        print(f"ERRO CRÍTICO NA API: {api_error}")
        raise api_error

if __name__ == '__main__':
    if not SPREADSHEET_ID or not SERVICE_ACCOUNT_ENV:
        print("Erro: SPREADSHEET_ID ou GOOGLE_SERVICE_ACCOUNT_JSON não configurados nos Secrets do GitHub.")
    else:
        try:
            dataframe = parse_markdown_to_dataframe(MD_FILE)
            update_google_sheets(dataframe)
        except Exception as e:
            print(f"Erro durante a execução: {e}")
