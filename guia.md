# Plano de Automação: Sync MD para Google Sheets (Preservando Gráficos)

Este documento detalha a estratégia para rodar um script semanal via **GitHub Actions** que extrai dados de um ficheiro `.md` e os "injeta" diretamente numa folha de cálculo existente no Google Sheets, preservando abas manuais, fórmulas e gráficos criados pelo utilizador.

## 1. Arquitetura da Solução (Opção A)
*   **Trigger:** GitHub Actions (Cronjob semanal ou manual).
*   **Linguagem:** Python 3.x.
*   **Bibliotecas Principais:** `pandas` (parsing do Markdown), `google-api-python-client` e `google-auth`.
*   **Mecanismo de Sync:** O script identifica o ID da planilha e utiliza a **Google Sheets API** para sobrescrever apenas os intervalos de dados (ex: Aba "Plano Completo"), sem apagar o arquivo ou outras abas.
*   **Autenticação:** Conta de Serviço (Service Account) do Google Cloud.

## 2. Setup Inicial Manual (Obrigatório)
Antes de ativar a automação, deve realizar os seguintes passos uma única vez:
- [ ] **Gerar o Excel Base:** Executar o script `gerar_plano.py` localmente para criar o ficheiro `.xlsx` com a estrutura de 11 colunas (incluindo *Pace Real*, *Percepção* e *Comentários*).
- [ ] **Upload para o Google Drive:** Fazer o upload manual deste ficheiro para a sua pasta do Drive.
- [ ] **Configurar Dashboards:** Criar as suas tabelas e gráficos manuais no Google Sheets. A automação irá atualizar apenas os dados brutos, preservando as suas criações.
- [ ] **Obter o ID:** Copiar o ID da planilha (presente no URL: `docs.google.com/spreadsheets/d/ID_AQUI/edit`) para usar nos Secrets do GitHub.

## 3. Pré-requisitos (Setup Google Cloud)
1. [ ] **Criar Projeto:** No [Google Cloud Console](https://console.cloud.google.com/).
2. [ ] **Ativar APIs:** Pesquisar e ativar:
    * **Google Drive API** (para localizar o ficheiro).
    * **Google Sheets API** (para editar as células).
3. [ ] **Conta de Serviço:**
    * [ ] Ir a "Credenciais" > "Criar Credenciais" > "Conta de Serviço".
    * [ ] Gerar uma chave **JSON** e descarregar (será guardada nos Secrets do GitHub como `GOOGLE_SERVICE_ACCOUNT_JSON`).
4. [ ] **Permissão na Planilha:**
    * [ ] Copiar o e-mail da Conta de Serviço (ex: `bot@projeto.iam.gserviceaccount.com`).
    * [ ] Na sua Google Sheet (no navegador), clicar em **Partilhar** e adicionar esse e-mail como **Editor**.

## 3. Estrutura do Projeto
```text
/
├── .github/workflows/
│   └── weekly_sync.yml    # Configuração do GitHub Actions
├── Plano_Treino_2026.md   # A sua fonte de verdade (Markdown)
├── scripts/
│   └── sync_to_sheets.py  # Script que lê o MD e faz o "Update" na API
└── requirements.txt       # Dependências (pandas, google-api-python-client, google-auth)
```

## 4. Funcionamento do Script
O script `sync_to_sheets.py` deve:
1.  Ler o ficheiro `.md` e converter as tabelas em DataFrames (Pandas).
2.  Conectar-se à planilha via ID (presente no URL da folha de cálculo).
3.  Limpar o conteúdo das abas automáticas (ex: "Dados Treino").
4.  Inserir os novos dados.
5.  **Não tocar** em abas que contenham "Dashboard" ou nomes personalizados, permitindo que os seus gráficos se mantenham ligados aos dados atualizados.
