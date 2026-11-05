# Plano de Implementação Detalhado: investment-rebalancer-ai

Este documento apresenta a quebra refinada em tarefas e entregáveis do projeto **`investment-rebalancer-ai`**, com base nas especificações arquiteturais e decisões de produto registradas na Especificação Técnica.

---

## Estrutura do Plano de Implementação

```text
Fase 1: Setup da Infraestrutura, Repositório e Contêineres Docker
├── Tarefa 1.1: Inicialização do Repositório Git e Estrutura do Projeto
└── Tarefa 1.2: Configuração do Docker Compose e Variáveis de Ambiente

Fase 2: Conector Google Sheets, Schema de Custódia e Mapeamento de Ativos
├── Tarefa 2.1: Autenticação Service Account GCP e Módulo sheets_db.py
├── Tarefa 2.2: Leitura de Histórico, Duplicação de Abas e Atualização Patrimonial
└── Tarefa 2.3: Mapeamento de De-Para de Ativos (alias_map.json e asset_mapping.json)

Fase 3: Autenticação Transparente (Pass-Through Auth) e Parser da Carteira Recomendada
├── Tarefa 3.1: Endpoint de Pass-Through Auth (POST /api/v1/auth/login)
├── Tarefa 3.2: Parser Hierárquico da Carteira "Ativos 50K" (parser.py)
└── Tarefa 3.3: Tratamento de Casos de Borda (Edge Cases) e Sanitização

Fase 4: Pipeline de Cotações de Mercado e Motor de Otimização Quadrática
├── Tarefa 4.1: Módulo Unificado de Cotações (market_data.py)
├── Tarefa 4.2: Motor de Otimização Quadrática Discreta (optimizer.py)
└── Tarefa 4.3: Implementação dos Modos "Sabonete" vs. "Cirúrgico"

Fase 5: Interface Gráfica (Frontend Next.js/React) e Fluxo Fim a Fim
├── Tarefa 5.1: Tela de Autenticação e Sessão Efêmera
├── Tarefa 5.2: Dashboard de Simulação e Tabela Interativa
└── Tarefa 5.3: Fluxo de Confirm/Commit no Sheets e Integração Second Brain
```

---

## Fase 1: Setup da Infraestrutura, Repositório e Contêineres Docker

### Tarefa 1.1: Inicialização do Repositório Git e Estrutura do Projeto
* **Descrição:** Criar o repositório privado `investment-rebalancer-ai` no GitHub e organizar o esqueleto de diretórios conforme o padrão de monorepo desacoplado backend/frontend.
* **Arquivos Afetados:** `.gitignore`, `README.md`, diretórios `backend/`, `frontend/`, `config/`, `credentials/`.
* **Entregável:** Árvore de diretórios no repositório com `.gitignore` configurado para ignorar credenciais em JSON e variáveis `.env`.
* **Pontos de Decisão & Critérios de Aceite:**
  * [x] O diretório `credentials/` deve estar explicitamente ignorado no `.gitignore`.
  * [x] A estrutura de subpastas do FastAPI (`backend/app/clients`, `backend/app/services`, `backend/app/schemas`) deve estar inicializada.
  * [x] O frontend em Next.js com TypeScript e Tailwind CSS deve compilar sem erros.

---

### Tarefa 1.2: Configuração do Docker Compose e Variáveis de Ambiente
* **Descrição:** Criar os arquivos `Dockerfile` para backend (Python 3.12) e frontend (Node 20), orquestrados via `docker-compose.yml` para rodar localmente com um único comando (`docker compose up`).
* **Arquivos Afetados:** `docker-compose.yml`, `.env.example`, `backend/Dockerfile`, `frontend/Dockerfile`.
* **Entregável:** Ambiente Docker rodando localmente exposto em `http://localhost:3000` (Frontend) e `http://localhost:8000` (FastAPI).
* **Pontos de Decisão & Critérios de Aceite:**
  * [x] `docker compose up` deve subir ambos os serviços sem necessidade de dependências instaladas no SO hospedeiro.
  * [x] Hot-reload ativado tanto no FastAPI (`--reload`) quanto no Next.js para agilidade no desenvolvimento.
  * [x] O arquivo `.env.example` deve listar as chaves públicas necessárias (URLs de API, IDs da Planilha).

---

## Fase 2: Conector Google Sheets, Schema de Custódia e Mapeamento de Ativos

### Tarefa 2.1: Autenticação Service Account GCP e Módulo `sheets_db.py`
* **Descrição:** Implementar a integração backend com a API do Google Sheets via biblioteca `gspread`, utilizando autenticação por Service Account do Google Cloud.
* **Arquivos Afetados:** `backend/app/clients/sheets_db.py`, `credentials/google-service-account.json`.
* **Entregável:** Cliente `sheets_db.py` capaz de conectar, autenticar e ler os dados brutos da planilha Google Sheets configurada.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] O arquivo JSON da Service Account é lido com segurança pelo backend.
  * [ ] Caso o arquivo de credencial esteja ausente, o sistema deve emitir um erro claro durante o bootstrap.
  * [ ] Função `get_latest_monthly_sheet()` localiza e carrega os dados da aba mais recente.

---

### Tarefa 2.2: Leitura de Histórico, Duplicação de Abas e Atualização Patrimonial
* **Descrição:** Desenvolver as funções para ler a custódia atual da aba mais recente, duplicar o modelo de aba mensal para o novo mês de aporte e atualizar o resumo consolidado na aba `Evolução Patrimonial`.
* **Arquivos Afetados:** `backend/app/clients/sheets_db.py`.
* **Entregável:** Fluxo completo de leitura e gravação de abas mensais via API do Sheets.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Leitura da custódia converte valores formatados em R$ para float numérico com precisão decimal.
  * [ ] Criação da nova aba (ex.: `Maio_26`) preserva estilos, fórmulas e cabeçalhos do template mensal.
  * [ ] Atualização automática da aba `Evolução Patrimonial` adicionando o total investido pós-aporte.

---

### Tarefa 2.3: Mapeamento de De-Para de Ativos (`alias_map.json` e `asset_mapping.json`)
* **Descrição:** Criar os arquivos de configuração JSON para vincular nomes da carteira recomendada aos tickers mantidos em custódia pelo usuário e registrar regras operacionais por ativo.
* **Arquivos Afetados:** `config/alias_map.json`, `config/asset_mapping.json`.
* **Entregável:** Arquivos JSON de mapeamento populados e consumidos pelo backend.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] `alias_map.json` resolve opções equivalentes "OU" (ex.: "ETF IRFM11 OU ETF IDKA11" -> "FIXA11").
  * [ ] `asset_mapping.json` especifica aplicação mínima e regras de compra por lote/fracionário por ativo.
  * [ ] Suporte a múltiplos aliases por recomendação genérica da casa de análise.

---

## Fase 3: Autenticação Transparente (Pass-Through Auth) e Parser da Carteira Recomendada

### Tarefa 3.1: Endpoint de Pass-Through Auth (`POST /api/v1/auth/login`)
* **Descrição:** Implementar a rota no FastAPI que recebe e-mail e senha informados pelo usuário na UI, repassa para a API oficial da casa de análise via `httpx` e devolve o Bearer Token obtido.
* **Arquivos Afetados:** `backend/app/main.py`, `backend/app/clients/platform_api.py`, `backend/app/schemas.py`.
* **Entregável:** Endpoint `/api/v1/auth/login` operacional fornecendo o token JWT sem armazenar senhas em disco.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Senhas trafegam apenas em memória e são descartadas imediatamente após a requisição.
  * [ ] Retorno `401 Unauthorized` tratado amigavelmente em caso de erro de credenciais.
  * [ ] O Bearer Token retornado possui suporte para armazenamento em `sessionStorage` no frontend.

---

### Tarefa 3.2: Parser Hierárquico da Carteira "Ativos 50K" (`parser.py`)
* **Descrição:** Construir o serviço `parser.py` para navegar na árvore JSON da recomendação ("Ativos 50K", 32 ativos) e nivelá-la em uma lista tipada de objetos `RecommendedAsset`.
* **Arquivos Afetados:** `backend/app/services/parser.py`, `backend/app/schemas.py`.
* **Entregável:** Função `parse_recommended_portfolio()` retornando os 32 ativos com seus respectivos pesos percentuais e metadados.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Mapeamento exato das 4 categorias: Ações (15%), FIIs (15%), Caixa/RF (35%), Alternativos (35%).
  * [ ] A soma de todos os pesos alvos convertidos deve totalizar exatamente 100.0%.
  * [ ] Extração nativa de preços teto informados no payload.

---

### Tarefa 3.3: Tratamento de Casos de Borda (*Edge Cases*) e Sanitização
* **Descrição:** Tratar nativamente os 5 casos de borda especificados: ativos "Em revisão", linhas filhas de fundos espelho (`% da Carteira: "-"`), recomendações "OU", trava de preço teto e *Full Outer Join* entre custódia e recomendação.
* **Arquivos Afetados:** `backend/app/services/parser.py`.
* **Entregável:** Parser resiliente a inconsistências de payload, sem falhas de exceção de código.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Regex `r"\b([A-Z]{4}\d{1,2})\b"` extrai tickers quando o código indica "Em revisão" (ex.: PSEC11).
  * [ ] Linhas com peso `"-"` são vinculadas como `FeederOption` contendo CNPJ e aplicação mínima.
  * [ ] *Full Outer Join* atribui peso `0%` a ativos que saíram da carteira recomendada.

---

## Fase 4: Pipeline de Cotações de Mercado e Motor de Otimização Quadrática

### Tarefa 4.1: Módulo Unificado de Cotações (`market_data.py`)
* **Descrição:** Criar o serviço de busca de preços atualizados em tempo real integrando B3 (`brapi`/`yfinance`), Tesouro Direto, dados abertos da CVM (cotas de fundos) e Cripto (`CoinGecko`/Binance).
* **Arquivos Afetados:** `backend/app/clients/market_data.py`.
* **Entregável:** Módulo `market_data.py` retornando preços atualizados de fechamento por ativo.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Fallback automático entre `brapi` e `yfinance` para ações e FIIs da B3.
  * [ ] Leitura de cotas diárias da CVM via CNPJ para fundos de investimento.
  * [ ] Tratamento de timeout ou indisponibilidade de APIs públicas sem derrubar a aplicação.

---

### Tarefa 4.2: Motor de Otimização Quadrática Discreta (`optimizer.py`)
* **Descrição:** Implementar a otimização por minimização de desvio quadrático com restrição de orçamento, suporte a compras em lotes inteiros de cotas e travas de aplicação mínima.
* **Arquivos Afetados:** `backend/app/services/optimizer.py`.
* **Entregável:** Algoritmo de otimização em Python gerando sugestões numéricas exatas de compra e venda.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Formulação da função objetivo: $\min \sum ((\text{Atual}_i + q_i \times P_i) - \text{Recomendado}_i)^2$.
  * [ ] Restrição estrita de orçamento total disponível para o aporte ($X$).
  * [ ] Execução em menos de 10 milissegundos para os 32 ativos.

---

### Tarefa 4.3: Implementação dos Modos "Sabonete" vs. "Cirúrgico"
* **Descrição:** Configurar as restrições operacionais do otimizador para suportar o Modo "Sabonete" (`allow_partial_sales = False`) e o Modo "Cirúrgico" (`allow_partial_sales = True`), com venda compulsória de ativos excluídos.
* **Arquivos Afetados:** `backend/app/services/optimizer.py`.
* **Entregável:** Otimizador suportando alternância de política de giro via parâmetro na chamada.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Modo "Sabonete" trava $LB_i = 0$ para ativos com recomendação ativa ($w_i > 0$), proibindo vendas parciais.
  * [ ] Modo "Cirúrgico" permite vendas parciais em posições acima do alvo para financiar ativos defasados.
  * [ ] Ativos com peso $w_i = 0\%$ sofrem liquidação total compulsória em ambos os modos.

---

## Fase 5: Interface Gráfica (Frontend Next.js/React) e Fluxo Fim a Fim

### Tarefa 5.1: Tela de Autenticação e Sessão Efêmera
* **Descrição:** Desenvolver a tela de Login em Next.js para o usuário informar e-mail e senha da plataforma de recomendações e armazenar o Bearer Token retornado em `sessionStorage`.
* **Arquivos Afetados:** `frontend/src/components/LoginForm.tsx`, `frontend/src/pages/index.tsx`.
* **Entregável:** Interface de login funcional e responsiva integrada à rota `/api/v1/auth/login`.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Feedback visual claro durante o estado de carregamento do login.
  * [ ] O token Bearer é mantido em `sessionStorage` e limpo ao fechar a aba.
  * [ ] Redirecionamento automático para o Dashboard após login bem-sucedido.

---

### Tarefa 5.2: Dashboard de Simulação e Tabela Interativa
* **Descrição:** Construir o painel principal em React contendo o input do valor do aporte ($X$), atualização manual de saldos sem cotação pública (CDBs), seletor de política de giro ("Sabonete" vs. "Cirúrgico") e a tabela de simulação.
* **Arquivos Afetados:** `frontend/src/components/Dashboard.tsx`, `frontend/src/components/SimulationTable.tsx`.
* **Entregável:** Painel de simulação interativo exibindo dados comparativos e sugestões de rebalanceamento.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Tabela destaca visualmente ativos em revisão ou que ultrapassaram o Preço Teto.
  * [ ] Alternância entre modo "Sabonete" e "Cirúrgico" reexecuta a simulação instantaneamente.
  * [ ] Exibição do valor total alocado e do caixa remanescente pós-otimização.

---

### Tarefa 5.3: Fluxo de Confirm/Commit no Sheets e Integração Second Brain
* **Descrição:** Integrar o botão "Confirmar e Salvar no Google Sheets" (`POST /api/v1/portfolio/commit`) para efetivar a nova aba do mês e registrar o procedimento de upload dos relatórios PDF no NotebookLM como *Second Brain*.
* **Arquivos Afetados:** `frontend/src/components/Dashboard.tsx`, `README.md`.
* **Entregável:** Fluxo MVP local concluído e testado ponta a ponta com gravação na planilha.
* **Pontos de Decisão & Critérios de Aceite:**
  * [ ] Mensagem de sucesso e confirmação gráfica ao persistir os dados no Google Sheets.
  * [ ] A aba criada no Google Sheets contém os valores exatos da simulação aprovada pelo usuário.
  * [ ] Documentação no `README.md` detalhando o passo a passo de inicialização do Docker e uso do Second Brain no NotebookLM.
