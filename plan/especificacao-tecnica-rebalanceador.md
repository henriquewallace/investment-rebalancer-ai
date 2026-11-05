# Especificação Técnica e Visão Arquitetural: investment-rebalancer-ai

Documento de Visão Técnica e **Fonte da Verdade (Single Source of Truth)** do repositório `investment-rebalancer-ai`.

---

## 1. Visão Geral e Objetivos do Sistema

### 1.1 Propósito do Projeto
O **`investment-rebalancer-ai`** foi concebido para automatizar o processo de rebalanceamento mensal de carteira de investimentos pessoais durante novos aportes. O objetivo central é eliminar o trabalho manual de atualização de planilhas, busca individual de cotações em tempo real e cálculos aritméticos complexos de distribuição por ativos, operando com **custo operacional zero (Free Tier / Deploy Local)** e **máxima privacidade de dados financeiros**.

### 1.2 Abordagem Híbrida (Código Determinístico + Second Brain)
Para garantir resiliência e precisão matemática, o sistema divide rigidamente a execução técnica em dois ecossistemas complementares:
1. **Engine Determinística (FastAPI + Python + Otimizador Quadrático):** Responsável pela ingestão de APIs, scraping/parsing de carteiras recomendadas, busca de preços públicos de mercado e alocação exata de lotes discretos por otimização quadrática. Evita-se o uso de LLMs para cálculos matemáticos ou manipulação direta de planilhas.
2. **Second Brain Qualitativo (NotebookLM):** Atua como repositório central de inteligência financeira ("Second Brain"), armazenando relatórios mensais em PDF e históricos das teses emitidas pela casa de análise. Permite responder dúvidas qualitativas sobre trocas de ativos, teses de investimento e relatórios conjunturais sem interferir no cálculo exato de rebalanceamento.

---

## 2. Arquitetura do Sistema e Deploy MVP Local

### 2.1 Stack do Sistema (Docker Compose)
O projeto é empacotado através do **Docker Compose** em ambiente local, garantindo fácil reprodução e isolamento total de dependências:
* **Backend:** Python 3.12 com FastAPI, Uvicorn, `httpx`, `gspread`, `numpy`, `scipy`, `yfinance` e Pydantic.
* **Frontend:** Node 20 com Next.js / React, Tailwind CSS e componentes interativos em TypeScript.
* **Orquestração:** `docker-compose.yml` local expondo a aplicação em `http://localhost:3000`.

### 2.2 Google Sheets como Banco de Dados e Fonte da Verdade
Em vez de utilizar bancos de dados relacionais tradicionais, o **Google Sheets** é adotado como a *Single Source of Truth* do sistema.
* **Service Account no GCP:** A autenticação backend é realizada via arquivo de credencial JSON (`credentials/google-service-account.json`) com permissão de escrita via biblioteca `gspread`.
* **Fluxo de Abas Mensais:** Cada mês aprovado gera uma nova aba padronizada (ex.: `Maio_26`), preservando o histórico de aportes e atualizando a aba master de `Evolução Patrimonial`.

---

## 3. Ingestão da Carteira Recomendada e Autenticação (Pass-Through Auth)

### 3.1 Pass-Through Authentication (Autenticação Transparente)
Para evitar o armazenamento de senhas e credenciais de acesso em arquivos de configuração local (`.env`), o sistema implementa a arquitetura de **Autenticação por Repasse**:
1. O usuário informa seu e-mail e senha diretamente na tela de login da interface web.
2. O endpoint `POST /api/v1/auth/login` do FastAPI repassa as credenciais via chamada HTTP (`httpx`) para o endpoint oficial de autenticação da casa de análise.
3. O FastAPI captura o Bearer Token retornado no corpo da resposta (*Response Body*) e o armazena de forma efêmera em sessão (`sessionStorage` do navegador / memória RAM do servidor).
4. As senhas são descartadas imediatamente após a validação, eliminando riscos de vazamento.

### 3.2 Parsing da Carteira Recomendada ("Ativos 50K")
O módulo `parser.py` navega pela estrutura de árvore hierárquica do payload JSON fornecido pela casa de análise (faixa **"Ativos 50K"** composta por 32 ativos principais), transformando nós aninhados em uma lista plana e tipada pelo Pydantic (`RecommendedAsset`). A carteira distribui 100% do patrimônio entre 4 categorias principais:
* **A - Ações (15%):** 8 ativos
* **R - Real Estate / FIIs (15%):** 6 ativos
* **C - Caixa / Renda Fixa (35%):** 6 ativos
* **A - Alternativos / Internacional / Cripto (35%):** 12 ativos

---

## 4. Tratamento dos 5 Casos de Borda (Edge Cases)

O parser e o pipeline de dados tratam nativamente 5 inconsistências comuns em payloads de carteiras recomendadas:

1. **Ativos em Status "Em revisão" (ex.: PSEC11):**
   * *Problema:* O campo de código vem preenchido com a string `"Em revisão"` em vez do ticker oficial.
   * *Solução:* Aplicação de expressão regular (`r"\b([A-Z]{4}\d{1,2})\b"`) no nome completo do fundo para recuperar o ticker original. O otimizador bloqueia compras adicionais (`UB_i = 0`) e gera um alerta visual na UI.
2. **Linhas Filhas de Fundos Espelho / Feeder (`% da Carteira: "-"`):**
   * *Problema:* Fundos como Absolute Vertex, Genoa Capital Radar e Kinea Atlas possuem uma linha mãe com peso oficial (ex.: `4.00%`) e até 7 linhas filhas referentes a fundos espelho em corretoras parceiras (XP, BTG, Inter, Itaú, Ágora) sem peso percentual (`"-"`).
   * *Solução:* O parser mantém o ponteiro do ativo mãe e anexa as linhas filhas como opções de execução (`FeederOption`), contendo CNPJ, corretora, aplicação inicial e regras de aporte adicional.
3. **Recomendações Equivalentes ("OU"):**
   * *Problema:* Linhas com recomendações do tipo `"ETF IRFM11 OU ETF IDKA11"` ou `"CDB DO DAYCOVAL, CDB DO BMG OU TESOURO RESERVA"`.
   * *Solução:* Uso de arquivo de mapeamento `config/alias_map.json` para definir qual ativo específico mantido em custódia pelo usuário deve ser vinculado à regra percentual da recomendação.
4. **Respeito à Trava de Preço Teto:**
   * *Problema:* Presença de preços máximos de compra em Ações e FIIs com formatação numérica heterogênea.
   * *Solução:* Normalização de valores monetários. Se o preço público de mercado for superior ao preço teto informado na recomendação, o otimizador desativa ordens de compra (`UB_i = 0`).
5. **Full Outer Join entre Custódia Real e Carteira Recomendada:**
   * *Problema:* Ativos em custódia que saíram da recomendação ou ativos recomendados que o usuário ainda não possui.
   * *Solução:* O backend realiza a junção completa dos dados:
     * *Ativo na planilha, mas fora da API:* Peso alvo vira `0%` e o ativo é sinalizado para liquidação total.
     * *Ativo na API, mas fora da planilha:* Entra na simulação com saldo atual de `R$ 0,00` e desvio de `100%` do alvo.

---

## 5. Pipeline de Cotações de Mercado

### 5.1 Provedores de Cotação em Tempo Real
O módulo `market_data.py` consolida os preços atualizados através de fontes públicas e gratuitas:
* **Ações e FIIs da B3:** Consultados via API `brapi` e fallback para `yfinance` (adicionando o sufixo `.SA`).
* **Tesouro Direto:** Leitura do arquivo JSON de preços e taxas dos títulos públicos.
* **Fundos de Investimento:** Consulta ao valor da cota diária nos dados abertos da CVM através do CNPJ do fundo.
* **Criptomoedas (Bitcoin):** Consulta de cotação em BRL via API pública do CoinGecko / Binance.

### 5.2 Entradas Manuais Restritas
Manutenção de input manual na UI restrita estritamente a ativos sem cotação pública diária, como títulos de Renda Fixa privada (CDBs pós-fixados).

---

## 6. Motor de Otimização Quadrática Discreta

### 6.1 Formulação Matemática
O problema de alocação de aportes é modelado como um problema de **Programação Inteira Quadrática Discreta (MIQP / Coordinate Descent)**. O objetivo é minimizar a soma dos desvios quadráticos entre o valor final de cada ativo pós-aporte e o seu valor ideal recomendado, respeitando a trava de orçamento disponível ($X$):

$$\min \sum_{i=1}^{N} \left( (\text{Atual}_i + q_i \times P_i) - \text{Recomendado}_i \right)^2$$

**Sujeito a:**
* $\sum_{i=1}^{N} (q_i \times P_i) \le X \quad \text{(Restrição de Orçamento)}$
* $q_i \in \mathbb{Z} \quad \text{(Lotes Inteiros para Ações, FIIs e ETFs)}$
* $q_i \times P_i \ge M_i \quad \text{ou} \quad q_i = 0 \quad \text{(Trava de Aporte Mínimo / Minimum Lot)}$

O uso da função quadrática penaliza desproporcionalmente grandes desvios absolutos, impedindo que aportes pequenos sejam consumidos por um único ativo com aporte mínimo elevado (ex.: CDB de R$ 1.000 ou Fundo de R$ 500).

### 6.2 Modos de Rebalanceamento ("Sabonete" vs. "Cirúrgico")
A interface gráfica permite alternar entre duas políticas de rebalanceamento ajustando os limites inferiores ($LB_i$) das variáveis de decisão $q_i$:

1. **Modo "Sabonete" / Orgânico (`allow_partial_sales = False`):**
   * $LB_i = 0$ para todos os ativos com recomendação ativa ($w_i > 0$).
   * Proíbe vendas parciais em posições valorizadas que ultrapassaram o percentual alvo (ex.: PRIO3 acima do recomendado). O rebalanceamento ocorre exclusivamente via novos aportes, diluindo o peso do ativo organicamente ao longo dos meses e evitando custos de giro/tributação.
   * *Exceção:* Se um ativo foi zerado na recomendação ($w_i = 0$), a venda é integral e compulsória ($LB_i = UB_i = -Q_i^{\text{atual}}$).

2. **Modo "Cirúrgico" / Estrito (`allow_partial_sales = True`):**
   * $LB_i = -Q_i^{\text{atual}}$ for ativos líquidos acima do alvo.
   * Permite a realização de lucros e a venda parcial de cotas em excesso para financiar a compra imediata de ativos defasados, cravando as proporções ideais recomendadas no mês.

---

## 7. Estrutura do Repositório e Fluxo da Interface Web

### 7.1 Estrutura de Diretórios (`investment-rebalancer-ai`)

```text
investment-rebalancer-ai/
├── docker-compose.yml
├── .env
├── credentials/
│   └── google-service-account.json
├── config/
│   ├── asset_mapping.json
│   └── alias_map.json
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── clients/
│       │   ├── platform_api.py
│       │   ├── market_data.py
│       │   └── sheets_db.py
│       ├── services/
│       │   ├── parser.py
│       │   └── optimizer.py
│       └── schemas.py
└── frontend/
    ├── Dockerfile
    └── src/
        ├── components/
        │   ├── LoginForm.tsx
        │   ├── Dashboard.tsx
        │   └── SimulationTable.tsx
        └── pages/
            └── index.tsx
```

### 7.2 Fluxo Operacional da Interface no Dia do Aporte
1. **Login:** O usuário acessa a UI local (`http://localhost:3000`) e efetua login com as credenciais da plataforma para obter o Bearer Token.
2. **Sincronização:** O sistema executa o *Full Outer Join* entre a última aba do Google Sheets, a API de Recomendações e as cotações de mercado da B3/CVM/Cripto.
3. **Parametrização:** O usuário insere o valor do novo aporte ($X$), atualiza saldos de ativos sem cotação pública (CDBs) e seleciona o modo de giro ("Sabonete" ou "Cirúrgico").
4. **Simulação:** O otimizador executa em < 10ms e renderiza a tabela interativa mostrando a quantidade a comprar/vender, o valor alocado por ativo e alertas de preços teto/revisão.
5. **Commit:** O usuário clica em **"Confirmar e Salvar no Google Sheets"**, disparando a escrita da nova aba mensal padronizada e a atualização do saldo consolidado.
