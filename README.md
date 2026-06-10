# 🏃 Bot de Corrida Inteligente (Strava + OpenRouter + Sheets)

Sistema automatizado de gestão de treinos focado na preparação para a **Meia Maratona 2026**. O projeto utiliza uma arquitetura "Markdown-as-Database" integrada com APIs de performance e inteligência artificial para eliminar o trabalho manual de registro.

## 🔄 O Ecossistema de Automação

O projeto funciona como uma engrenagem automática com dois fluxos distintos:
1.  **Fluxo de Inteligência (Semanal):** O GitHub Actions busca dados no Strava, processa com o OpenRouter AI e consolida no Markdown e no Sheets.
2.  **Fluxo de Visualização (Reativo):** Qualquer edição manual que você fizer no `Plano_Treino_2026.md` é refletida no Google Sheets instantaneamente via push, sem acionar a IA ou o Strava.

## 🚀 Funcionalidades Principais

-   **Fluxo Híbrido de Sincronismo:** Separação entre inteligência e visualização para otimização de custos e agilidade nas edições manuais.
-   **Sync Strava Inteligente:** Busca treinos automaticamente com janela de tolerância de +/- 1 dia (para compensações de treinos adiados/antecipados).
-   **Sincronismo Incremental:** Utiliza um marco temporal (`last_sync.json`) para buscar apenas atividades novas, otimizando o consumo de APIs e tempo de execução.
-   **Análise Técnica Realista:** O OpenRouter gera feedbacks de até 30 palavras focados em métricas, sem clichês motivacionais (usando modelos gratuitos).
-   **Consolidação de Atividades:** Soma múltiplas corridas no mesmo dia (ex: aquecimento + treino principal).
-   **Proteção de Integridade:** Nunca sobrescreve dados que você preencheu manualmente.
-   **Execução On-Demand:** Botão "Run Workflow" no GitHub para sincronizar no momento que você desejar.

## 📁 Estrutura do Repositório

*   `Plano_Treino_2026.md`: O diário de bordo e banco de dados principal.
*   `scripts/strava_sync.py`: O "cérebro" da integração Strava + OpenRouter.
*   `scripts/last_sync.json`: Arquivo de controle que armazena o marco do último sincronismo.
*   `scripts/sync_to_sheets.py`: Sincronizador para o ecossistema Google.
*   `.github/workflows/weekly_sync.yml`: Orquestrador semanal completo com Strava + OpenRouter.
*   `.github/workflows/manual_md_to_sheets.yml`: Sincronizador reativo (MD -> Sheets).
*   `GEMINI.md`: O protocolo de comportamento da IA local.

## 🛠️ Configuração e Segurança

O sistema utiliza **GitHub Secrets** para manter suas chaves protegidas:

| Secret | Descrição |
| :--- | :--- |
| `STRAVA_CLIENT_ID` | ID do seu App no Strava API |
| `STRAVA_CLIENT_SECRET` | Secret do seu App no Strava API |
| `STRAVA_REFRESH_TOKEN` | Token persistente para autorização |
| `OPENROUTER_API_KEY` | Chave da API do OpenRouter (Free Tier) |
| `GOOGLE_SHEETS_CREDENTIALS` | JSON da Service Account do Google |
| `SPREADSHEET_ID` | ID da planilha de destino |

## 📈 Objetivo e Metodologia
O plano está calibrado para um objetivo **Sub-2h00** na Meia Maratona (27/12/2026), utilizando zonas de treino baseadas no protocolo VDOT.

---
*Desenvolvido para transformar dados brutos em insights técnicos, mantendo o foco onde ele deve estar: no asfalto.*
