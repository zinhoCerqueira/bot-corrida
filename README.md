# 🏃 Automação de Treino — Meia Maratona 2026

Este repositório contém um sistema inteligente de gestão e acompanhamento de treinos focado na preparação para uma Meia Maratona em dezembro de 2026. O projeto utiliza uma abordagem "Markdown-as-Database", onde o plano de treino é a fonte de verdade, sincronizado automaticamente com o Google Sheets para visualização de dashboards.

## 🚀 Como Funciona

1.  **Registro Inteligente:** Os treinos são relatados via linguagem natural para o **Gemini CLI**.
2.  **Processamento:** A IA interpreta os dados (pace, distância, percepção de esforço), calcula médias e gera uma avaliação técnica.
3.  **Atualização Automática:** O arquivo `Plano_Treino_2026.md` é atualizado seguindo regras rigorosas de integridade.
4.  **Sync para Google Sheets:** Através do GitHub Actions, os dados são enviados para uma planilha no Google Sheets, alimentando gráficos e dashboards automáticos.

## 📁 Estrutura do Projeto

*   `Plano_Treino_2026.md`: O plano mestre e diário de bordo. Contém zonas de treino, fases (Base, Desenvolvimento, etc.) e o log de cada sessão.
*   `scripts/sync_to_sheets.py`: Script Python que converte as tabelas Markdown em dados para a API do Google Sheets, aplicando formatação condicional (cores por fase/tipo de treino).
*   `INSTRUCTIONS_TREINO.md`: Guia de diretrizes para a IA, garantindo que o planejamento original (colunas A-J) nunca seja alterado.
*   `GEMINI.md`: Protocolo de operação do Gemini CLI para este repositório.
*   `.github/workflows/`: Automação CI/CD para sincronização semanal ou sob demanda.

## 🛠️ Tecnologias

*   **Python 3.x**: Processamento de dados e integração com APIs.
*   **Pandas**: Parsing de tabelas Markdown e manipulação de DataFrames.
*   **Google Sheets API**: Sincronização e formatação remota.
*   **GitHub Actions**: Automação de tarefas.
*   **Gemini CLI**: Interface de IA para gestão do repositório.

## ⚙️ Configuração

Para replicar o ambiente de sincronização:

1.  Configure os **GitHub Secrets**:
    *   `SPREADSHEET_ID`: O ID da sua planilha Google.
    *   `GOOGLE_SERVICE_ACCOUNT_JSON`: A chave JSON da sua Service Account do Google Cloud.
3.  Instale as dependências locais: `pip install -r requirements.txt`.

## 📈 Objetivo
O plano está calibrado para um objetivo **Sub-2h00** na Meia Maratona (27/12/2026), com zonas de treino baseadas no protocolo VDOT de Jack Daniels.

---
*Este projeto é um exemplo de como utilizar IA e automação para potencializar o rendimento esportivo e a disciplina no registro de dados.*
