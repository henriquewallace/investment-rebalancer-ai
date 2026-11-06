# Plano de Implementação: investment-rebalancer-ai (v3)

Este documento orienta o desenvolvimento passo a passo do **`investment-rebalancer-ai`**, dividindo a especificação técnica em tarefas e entregáveis menores para acompanhamento e criação de *issues*.

---

## Fase 1: Setup do Repositório e Infraestrutura Docker (MVP Local)

### Tarefa 1.1: Inicialização do Repositório e Estrutura do Projeto
* **Descrição:** Criar o repositório `investment-rebalancer-ai` no GitHub e organizar a estrutura de pastas separando `backend` (FastAPI), `frontend` (Next.js/React), diretórios de configurações (`config/`) e credenciais (`credentials/`).
* **Critérios de Aceite:**
  - [x] Repositório inicializado no GitHub com README inicial.
  - [x] Estrutura de pastas `backend/`, `frontend/`, `config/` e `credentials/` criada.
  - [x] Arquivo `.gitignore` configurado para ignorar credenciais, `.env` e arquivos temporários.
* **Entregável:** Estrutura de arquivos inicial no repositório.

### Tarefa 1.2: Configuração do Docker Compose e Mapeamento de Variáveis
* **Descrição:** Configurar o arquivo `docker-compose.yml` para orquestrar os contêineres do backend (Python 3.12 + FastAPI) e frontend (Node 20 + Next.js/React), criando o arquivo `.env` para variáveis locais de ambiente.
* **Critérios de Aceite:**
  - [x] `Dockerfile` funcional no backend e no frontend.
  - [x] `docker-compose.yml` orquestrando os serviços e expondo `http://localhost:3000` (frontend) e `http://localhost:8000` (backend).
  - [x] Execução bem-sucedida de `docker compose up`.
* **Entregável:** Ambiente Docker Compose rodando localmente.

---

## Fase 2: Ingestão da Custódia (B3), Conector Google Sheets e Padronização de Dados

### Tarefa 2.1: Autenticação via Service Account do Google Cloud
* **Descrição:** Configurar a credencial da Service Account em JSON (`credentials/google-service-account.json`) com suporte à biblioteca `gspread` no FastAPI para acesso seguro ao Google Sheets.
* **Critérios de Aceite:**
  - [x] Arquivo JSON de credencial carregado de forma segura no backend.
  - [x] Teste de conexão estabelecido com a planilha do Google Sheets via `gspread`.
  - [x] Endpoint de verificação de saúde da conexão com a planilha.
* **Entregável:** Módulo `sheets_db.py` autenticado e conectado à planilha.

### Tarefa 2.2: Template do Google Sheets, Leitura da Última Custódia e Gravação de Nova Aba
* **Descrição:** Definir e manter no projeto o template nativo do Google Sheets (`config/sheets_template.json`), desenvolver as funções para identificar e ler a custódia da aba mensal mais recente no padrão `Mes_AA` (ex.: `Mai_26`), duplicar o template mensal `_TEMPLATE` gravando a nova aba aprovada e consolidar a linha histórica na aba master de `Evolução Patrimonial`.
* **Definição do Template (`config/sheets_template.json`):**
  - **Aba Mensal (`_TEMPLATE` e `Mes_AA`):** Formato tabular contínuo com 13 colunas:
    `Categoria` (A), `Ticker` (B), `Nome do Ativo` (C), `Qtd Anterior` (D), `Preço Unitário (R$)` (E), `Valor Anterior (R$)` (F), `Meta (%)` (G), `Qtd Aporte` (H), `Valor Aporte (R$)` (I), `Qtd Nova` (J), `Valor Novo (R$)` (K), `% Real Novo` (L), `Status / Obs` (M).
  - **Aba Master (`Evolução Patrimonial`):** Registro de consolidação histórica mensal com 11 colunas:
    `Mês/Ano` (A), `Data Execução` (B), `Patrimônio Anterior (R$)` (C), `Novo Aporte (R$)` (D), `Patrimônio Final (R$)` (E), `Variação de Mercado (R$)` (F), `Rentabilidade Mensal (%)` (G), `Saldo Ações (R$)` (H), `Saldo FIIs (R$)` (I), `Saldo Renda Fixa (R$)` (J), `Saldo Alternativos (R$)` (K).
  - **Padrão de Nomenclatura:** Regex `^(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)_(\d{2})$` para ordenação cronológica e seleção automática da custódia mais recente.
* **Critérios de Aceite:**
  - [x] Arquivo de template e schema `config/sheets_template.json` versionado no projeto.
  - [ ] Implementação de `ensure_template_sheet()` para inicializar `_TEMPLATE` e `Evolução Patrimonial` no Google Sheets se inexistentes.
  - [ ] Implementação de `get_latest_monthly_sheet()` ordenando abas cronologicamente e retornando lista tipada de `CustodyAsset`.
  - [ ] Implementação de `create_monthly_sheet()` duplicando `_TEMPLATE`, preenchendo os 13 campos formatados e linha de totais.
  - [ ] Implementação de `append_evolution_record()` inserindo ou atualizando a linha do mês na aba `Evolução Patrimonial`.
  - [ ] Endpoint `GET /api/v1/sheets/latest-custody` retornando a custódia do último mês registrado.
  - [ ] Endpoint `POST /api/v1/sheets/template/init` para bootstrapping da planilha.
  - [ ] Testes unitários com mocks cobrindo ordenação de abas, leitura, escrita e tratamento de erros.
* **Entregável:** Template padronizado versionado no projeto, módulo `sheets_db.py` com leitura/escrita funcional e testes passando.

### Tarefa 2.3: Configuração de Mapeamento de Ativos (`asset_mapping.json` / `alias_map.json`)
* **Descrição:** Criar arquivos JSON de configuração para vincular nomes/tickers da recomendação aos ativos mantidos em custódia (ex.: relacionar opções "OU" e fundos espelho às escolhas reais), além de registrar regras de aplicação e lote mínimo (como CDB Daycoval R$ 1.000 e Genoa R$ 500).
* **Critérios de Aceite:**
  - Mapeamento de sinonímias e regras de de-para para ativos equivalentes.
  - Mapeamento de regras de lote mínimo e restrições de fracionamento.
* **Entregável:** Arquivos de mapeamento criados e integrados ao backend.

### Tarefa 2.4: Parser do Relatório Consolidado B3 (`b3_parser.py`)
* **Descrição:** Implementar o parser para ler o arquivo `.xlsx` do relatório mensal da B3 (Área do Investidor) contendo as abas de Posição (`Ações`, `ETF`, `Fundos`, `Renda Fixa`, `Tesouro Direto`). Extrair automaticamente quantidades de cotas, tickers e saldos de CDBs/Tesouro/Bolsa.
* **Critérios de Aceite:**
  - Leitura via `pandas` (`pd.read_excel`) das abas do relatório mensal `.xlsx` da B3.
  - Extração precisa de quantidades e tickers para Ações, FIIs, ETFs, Tesouro e CDBs.
  - Endpoint `POST /api/v1/portfolio/upload-b3` recebendo o arquivo e retornando o JSON de custódia consolidado.
* **Entregável:** Parser `b3_parser.py` e endpoint de upload de extrato B3 operacionais.

---

## Fase 3: Ingestão da Carteira Recomendada e Autenticação (Pass-Through Auth)

### Tarefa 3.1: Pass-Through Auth (Login Transparente na Plataforma)
* **Descrição:** Criar a rota de autenticação no FastAPI que repassa as credenciais (e-mail e senha) para a API oficial da casa de análise via `httpx`, retornando o Bearer Token para a sessão do usuário sem salvar senhas.
* **Critérios de Aceite:**
  - Endpoint `POST /api/v1/auth/login` recebendo credenciais e repassando via POST HTTP.
  - Captura do Bearer Token no corpo da resposta (*Response Body*).
  - Descarte imediato das senhas em memória após a chamada.
* **Entregável:** Endpoint de autenticação por repasse funcionando.

### Tarefa 3.2: Parser da Carteira Recomendada ("Ativos 50K")
* **Descrição:** Implementar o serviço `parser.py` para ler a estrutura hierárquica do JSON da carteira recomendada (faixa "Ativos 50K" composta por 32 ativos) e transformá-la em uma lista plana de alvos percentuais.
* **Critérios de Aceite:**
  - Navegação na árvore `recommendedBody["Ativos 50K"]`.
  - Transformação das categorias Ações (15%), FIIs (15%), Renda Fixa (35%) e Alternativos (35%) em lista plana.
  - Validação da soma total de alvos em 100%.
* **Entregável:** Função `parse_recommended_portfolio` retornando a lista de 32 ativos estruturada.

### Tarefa 3.3: Tratamento dos 5 Casos de Borda (Edge Cases)
* **Descrição:** Tratar no parser os 5 casos de borda mapeados: ativos com status "Em revisão" (PSEC11), linhas filhas de fundos espelho/feeder (com peso "-"), recomendações equivalentes ("OU"), conversão de preços teto e *Full Outer Join* entre os ativos mantidos em custódia e a recomendação.
* **Critérios de Aceite:**
  - Regex para recuperar ticker de ativos em revisão e trava de compra.
  - Agrupamento de linhas filhas como `FeederOption`.
  - Aplicação de trava de Preço Teto no otimizador.
  - Realização de *Full Outer Join* entre extrato B3/planilha e carteira recomendada.
* **Entregável:** Parser resiliente a inconsistências do payload da API.

---

## Fase 4: Pipeline de Cotações de Mercado e Motor de Otimização

### Tarefa 4.1: Pipeline de Consulta de Cotações de Mercado
* **Descrição:** Criar o módulo `market_data.py` para consultar preços de fechamento atualizados na B3 (`yfinance` / `brapi`), Tesouro Direto, dados abertos da CVM (cotas de fundos) e Cripto (`CoinGecko` / Binance).
* **Critérios de Aceite:**
  - Busca de preços em tempo real via `brapi` com fallback para `yfinance`.
  - Consulta de cotas diárias da CVM via CNPJ para fundos de investimento.
  - Consulta de cotações em BRL para Bitcoin.
* **Entregável:** Serviço unificado de busca de cotações de mercado.

### Tarefa 4.2: Motor de Otimização Quadrática Discreta
* **Descrição:** Codificar o algoritmo de otimização no módulo `optimizer.py` que minimiza o desvio quadrático frente aos pesos alvo, respeitando restrições de orçamento, compra por lotes inteiros de cotas e travas de aporte mínimo.
* **Critérios de Aceite:**
  - Modelagem da função objetivo quadrática $\min \sum ((Atual_i + q_i \times P_i) - Recomendado_i)^2$.
  - Respeito à trava de orçamento $X$.
  - Respeito a lotes inteiros $q_i \in \mathbb{Z}$ e aplicações mínimas $M_i$.
* **Entregável:** Motor de cálculo calculando sugestões de compra/venda por ativo em < 10ms.

### Tarefa 4.3: Implementação dos Modos "Sabonete" vs. "Cirúrgico"
* **Descrição:** Configurar as travas do otimizador para permitir dois comportamentos: Modo "Sabonete" (`allow_partial_sales = False`), que rebalanceia apenas via novos aportes mantendo posições valorizadas, e Modo "Cirúrgico" (`allow_partial_sales = True`), que vende excessos para zerar desvios. Incluir a regra de venda total compulsória para ativos excluídos da carteira.
* **Critérios de Aceite:**
  - Trava de limites inferiores $LB_i = 0$ no modo "Sabonete".
  - Liberação de vendas parciais $LB_i = -Q_i^{\text{atual}}$ no modo "Cirúrgico".
  - Venda compulsória total para ativos zerados na recomendação ($w_i = 0\%$).
* **Entregável:** Suporte às duas políticas de rebalanceamento.

---

## Fase 5: Interface Gráfica (Frontend) e Integração Fim a Fim

### Tarefa 5.1: Interface de Login e Sessão Efêmera
* **Descrição:** Construir a tela inicial em React/Next.js para o usuário informar suas credenciais, autenticando via FastAPI e armazenando o token Bearer em sessão efêmera.
* **Critérios de Aceite:**
  - Formulário de login responsivo.
  - Integração com `POST /api/v1/auth/login`.
  - Armazenamento do Bearer Token em `sessionStorage`.
* **Entregável:** Tela de autenticação funcional no frontend.

### Tarefa 5.2: Dashboard de Upload B3 e Tabela Interativa de Simulação
* **Descrição:** Desenvolver o painel principal com componente de upload `.xlsx` do extrato B3, campo para digitar o valor do aporte ($X$), seletor de política de giro ("Sabonete" vs "Cirúrgico"), exibição de alertas (preço teto / revisão) e tabela de simulação detalhada.
* **Critérios de Aceite:**
  - Componente drag-and-drop `B3Upload.tsx` integrado com o backend.
  - Tabela de simulação mostrando Atual vs Recomendado vs Qtd a Comprar/Vender.
  - Alertas visuais destacados na tabela.
* **Entregável:** Interface gráfica responsiva para simulação do rebalanceamento.

### Tarefa 5.3: Fluxo de Confirmação, Gravação no Sheets e Second Brain
* **Descrição:** Integrar o botão "Confirmar e Salvar no Google Sheets" (`POST /api/v1/portfolio/commit`) para efetivar a nova aba do mês e documentar o processo de adição dos relatórios mensais em PDF no NotebookLM como *Second Brain*.
* **Critérios de Aceite:**
  - Persistência da nova aba mensal no Google Sheets via `gspread`.
  - Atualização do resumo master de evolução patrimonial.
  - Documentação do fluxo de uso do NotebookLM para acompanhamento qualitativo das teses.
* **Entregável:** Sistema MVP local testado e integrado ponta a ponta.
