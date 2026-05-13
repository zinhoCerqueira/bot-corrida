import os
import re
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configurações
MD_FILE = 'Plano_Treino_2026.md'
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SERVICE_ACCOUNT_ENV = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# ─── Mapas de Cores (RGB para o Google Sheets) ────────────────────────────────
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return {
        "red": int(hex_str[0:2], 16) / 255.0,
        "green": int(hex_str[2:4], 16) / 255.0,
        "blue": int(hex_str[4:6], 16) / 255.0
    }

FASE_COLORS = {
    'Aquecimento':     hex_to_rgb('FFF9C4'),
    'Base Aeróbia':    hex_to_rgb('DDEEFF'),
    'Desenvolvimento': hex_to_rgb('EDE7F6'),
    'Específico':      hex_to_rgb('FFF3E0'),
    'Pico':            hex_to_rgb('FCE4EC'),
    'Taper':           hex_to_rgb('E8F5E9'),
    'Prova':           hex_to_rgb('FF8A80'),
    'Recuperação':     hex_to_rgb('F5F5F5'),
    'Base':            hex_to_rgb('DDEEFF')
}

TIPO_COLORS = {
    'LR':    hex_to_rgb('BBDEFB'),
    'CL':    hex_to_rgb('C8E6C9'),
    'CM':    hex_to_rgb('DCEDC8'),
    'FK':    hex_to_rgb('E1BEE7'),
    'PROG':  hex_to_rgb('B2EBF2'),
    'TM':    hex_to_rgb('FFCCBC'),
    'TC':    hex_to_rgb('FFAB91'),
    'TR':    hex_to_rgb('FFE0B2'),
    'RP':    hex_to_rgb('FFCDD2'),
    'CL+S':  hex_to_rgb('B2DFDB'),
    'PROVA': hex_to_rgb('FF5252'),
    'REC':   hex_to_rgb('EEEEEE'),
}

def pace_to_decimal(pace_str):
    if not pace_str or pace_str == '-': return None
    matches = re.findall(r'(\d+):(\d+)', str(pace_str))
    if not matches: return None
    decimals = [int(m) + int(s)/60.0 for m, s in matches]
    return round(sum(decimals) / len(decimals), 2)

def parse_markdown_to_dataframe(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    fase_pattern = r'## (FASE \d+ — .*?)\n'
    semana_pattern = r'### Semana (\d+)'
    rows = []
    current_fase, current_semana = "Base", 0
    
    lines = content.split('\n')
    for line in lines:
        if line.startswith('## FASE'):
            fase_match = re.search(fase_pattern, line + '\n')
            if fase_match:
                full = fase_match.group(1)
                current_fase = full.split(' — ')[1].strip() if ' — ' in full else full
        if line.startswith('### Semana'):
            semana_match = re.search(semana_pattern, line)
            if semana_match: current_semana = int(semana_match.group(1))

        # Parser robusto para a tabela
        if line.count('|') >= 9 and 'Data' not in line and '---' not in line:
            parts = [p.strip() for p in line.split('|')][1:-1]
            if len(parts) >= 10:
                # Limpeza de caracteres especiais como '~' e 'km'
                dist_raw = parts[3].replace('km', '').replace('~', '').strip()
                
                rows.append([
                    parts[0], # Data
                    parts[1], # Dia
                    f"S{current_semana:02d}", # Semana
                    current_fase, # Fase
                    parts[2], # Tipo
                    dist_raw, # Distância
                    parts[4], # Pace Alvo
                    pace_to_decimal(parts[4]), # Pace Médio
                    parts[5], # Zona
                    parts[6] if parts[6] != '-' else '', # Detalhes (limpo)
                    parts[7], # Pace Real
                    parts[8], # Percepção
                    parts[9] if parts[9] != '-' else ''  # Comentários (limpo)
                ])

    return pd.DataFrame(rows, columns=['Data','Dia','Semana','Fase','Tipo','Distância','PaceAlvo','PaceMédio','Zona','Detalhes','PaceReal','Percepção','Comentários'])

def apply_formatting(service, sheet_id, df):
    requests = []
    
    # Congelar topo
    requests.append({
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 2}},
            "fields": "gridProperties.frozenRowCount"
        }
    })

    for i, row in df.iterrows():
        row_idx = i + 2 
        fase = row['Fase']
        tipo = row['Tipo']
        
        # 1. Cor da Fase para a linha TODA
        bg_color = FASE_COLORS.get(fase, {"red": 1, "green": 1, "blue": 1})
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": 13},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg_color,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "borders": {
                            "top": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "bottom": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "left": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "right": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,borders)"
            }
        })
        
        # 2. Cor específica do Tipo de Treino
        tipo_color = TIPO_COLORS.get(tipo, bg_color)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 4, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": tipo_color,
                        "textFormat": {
                            "bold": True, 
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1} if tipo == 'PROVA' else {"red": 0, "green": 0, "blue": 0}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        })

    # 3. Alinhamento à esquerda para Detalhes e Comentários (após as cores serem aplicadas)
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 2, "startColumnIndex": 9, "endColumnIndex": 10},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 2, "startColumnIndex": 12, "endColumnIndex": 13},
            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT"}},
            "fields": "userEnteredFormat.horizontalAlignment"
        }
    })

    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()

def update_google_sheets(df):
    creds = service_account.Credentials.from_service_account_info(json.loads(SERVICE_ACCOUNT_ENV), scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheet_id = next(s['properties']['sheetId'] for s in spreadsheet['sheets'] if s['properties']['title'] == 'Plano Completo')

    values = [df.columns.values.tolist()] + df.values.tolist()
    # Limpeza extra: transformar '-' em vazio para não poluir o visual
    values = [[(val if (pd.notnull(val) and val != '-') else '') for val in row] for row in values]
    
    print(f"Limpando e enviando {len(values)} linhas...")
    service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range="'Plano Completo'!A2:M400").execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Plano Completo'!A2",
        valueInputOption='USER_ENTERED', body={'values': values}
    ).execute()

    print("Aplicando formatação visual completa...")
    apply_formatting(service, sheet_id, df)
    print("Sucesso!")

if __name__ == '__main__':
    if SPREADSHEET_ID and SERVICE_ACCOUNT_ENV:
        update_google_sheets(parse_markdown_to_dataframe(MD_FILE))
    else:
        print("Erro: Secrets não configurados.")
