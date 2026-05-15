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
    'BASE AERÓBIA':    hex_to_rgb('DDEEFF'), # Azul claro
    'DESENVOLVIMENTO': hex_to_rgb('EDE7F6'), # Roxo claro
    'ESPECÍFICO':      hex_to_rgb('FFF8E1'), # Amarelo
    'PICO':            hex_to_rgb('FCE4EC'), # Vermelho claro
    'TAPER':           hex_to_rgb('E8F5E9'), # Verde claro
    'PROVA':           hex_to_rgb('FFCDD2'), # Vermelho suave
    'RECUPERAÇÃO':     hex_to_rgb('F5F5F5'), # Cinza claro
    'AQUECIMENTO':     hex_to_rgb('FFF9C4'), # Amarelo vivo
    'HISTÓRICO':       hex_to_rgb('EFEBE9'), # Cinza amarronzado muito claro
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
    'HIST':  hex_to_rgb('D7CCC8'), # Cinza amarronzado
    'PROVA': hex_to_rgb('FF5252'), # Vermelho forte
    'REC':   hex_to_rgb('EEEEEE'), # Cinza forte
}

def pace_to_decimal(pace_str):
    if not pace_str or pace_str in ('-', ''): return None
    matches = re.findall(r'(\d+):(\d+)', str(pace_str))
    if not matches: return None
    decimals = [int(m) + int(s)/60.0 for m, s in matches]
    return round(sum(decimals) / len(decimals), 2)

def clean_md(text):
    if not text: return ""
    return text.replace('**', '').replace('~', '').strip()

def parse_markdown_to_dataframe(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    rows = []
    current_fase, current_semana = "BASE AERÓBIA", 0
    is_recovery_week = False
    
    lines = content.split('\n')
    for line in lines:
        upper_line = line.upper()
        # ORDEM IMPORTANTE: 'RECUPERAÇÃO' contém 'PROVA' no título 'Recuperação Pós-Prova'
        # Por isso checamos Recuperação primeiro.
        if '## RECUPERAÇÃO' in upper_line:
            current_fase = 'RECUPERAÇÃO'
        elif '## AQUECIMENTO' in upper_line:
            current_fase = 'AQUECIMENTO'
        elif '## PROVA' in upper_line:
            current_fase = 'PROVA'
        elif '## FASE' in upper_line:
            fase_match = re.search(r'## (FASE \d+ — .*?)(?:\n|$)', line)
            if fase_match:
                full = fase_match.group(1)
                current_fase = full.split(' — ')[1].strip().upper() if ' — ' in full else full.upper()
        
        if '### Semana' in line:
            semana_match = re.search(r'### Semana (\d+)', line)
            if semana_match: current_semana = int(semana_match.group(1))
            is_recovery_week = '⚡' in line or 'RECUPERAÇÃO' in line.upper()

        # Parser da tabela (mínimo 9 pipes e primeiro campo deve parecer data)
        if line.count('|') >= 9 and 'Data' not in line and '---' not in line:
            parts = [clean_md(p) for p in line.split('|')][1:-1]
            if len(parts) >= 10:
                data_val = parts[0]
                # Validação extra para garantir que é uma linha de treino (Data no formato DD/MM)
                if not re.search(r'\d+/\d+', data_val):
                    continue
                
                # Simplificação da Fase para treinos históricos
                fase_final = current_fase
                if parts[2] == 'HIST':
                    fase_final = 'HISTÓRICO'

                rows.append([
                    data_val, parts[1], f"S{current_semana:02d}", fase_final,
                    parts[2], parts[3].replace('km', '').strip(), parts[4], 
                    pace_to_decimal(parts[4]), parts[5], parts[6], parts[7], 
                    parts[8], parts[9], is_recovery_week
                ])

    return pd.DataFrame(rows, columns=['Data','Dia','Semana','Fase','Tipo','Distância','PaceAlvo','PaceMédio','Zona','Detalhes','PaceReal','Percepção','Comentários', 'IsRecovery'])

def apply_formatting(service, sheet_id, df):
    requests = []
    
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
        is_rec = row['IsRecovery']
        
        # Cor de fundo padrão da Fase
        bg_color = FASE_COLORS.get(fase.upper(), {"red": 1, "green": 1, "blue": 1})
        if is_rec: bg_color = hex_to_rgb('FFF8E1') # Amarelo para semanas ⚡

        # CASO ESPECIAL: Se o tipo for PROVA, a linha TODA fica vermelha forte
        if tipo == 'PROVA':
            bg_color = hex_to_rgb('FF5252')
            text_color = {"red": 1, "green": 1, "blue": 1} # Branco
            bold = True
        else:
            text_color = {"red": 0, "green": 0, "blue": 0} # Preto
            bold = False

        # 1. Aplicar Cor na linha TODA
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": 13},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg_color,
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "textFormat": {"foregroundColor": text_color, "bold": bold},
                        "borders": {
                            "top": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "bottom": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "left": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                            "right": {"style": "SOLID", "color": {"red": 0.8, "green": 0.8, "blue": 0.8}}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat,borders)"
            }
        })
        
        # 2. Se não for a linha da PROVA (que já é toda vermelha), destaca a célula do Tipo
        if tipo != 'PROVA':
            tipo_base = tipo.split(' ')[0]
            tipo_color = TIPO_COLORS.get(tipo, TIPO_COLORS.get(tipo_base, bg_color))
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 4, "endColumnIndex": 5},
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": tipo_color,
                            "textFormat": {"bold": True}
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            })

    # 3. Alinhamento à esquerda
    for col_idx in [9, 12]:
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 2, "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
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

    df_to_send = df.drop(columns=['IsRecovery'])
    values = [df_to_send.columns.values.tolist()] + df_to_send.values.tolist()
    values = [[(val if pd.notnull(val) else '') for val in row] for row in values]
    
    service.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range="'Plano Completo'!A2:M500").execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Plano Completo'!A2",
        valueInputOption='USER_ENTERED', body={'values': values}
    ).execute()
    apply_formatting(service, sheet_id, df)
    print("Sucesso!")

if __name__ == '__main__':
    if SPREADSHEET_ID and SERVICE_ACCOUNT_ENV:
        update_google_sheets(parse_markdown_to_dataframe(MD_FILE))
    else:
        print("Erro: Secrets não configurados.")
