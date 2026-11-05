# Investment Rebalancer AI

Engine determinística para rebalanceamento mensal automatizado de carteiras de investimentos pessoais durante novos aportes.

## Propósito do Sistema

O **investment-rebalancer-ai** elimina o trabalho manual de planilhas, cotações em tempo real e cálculos aritméticos complexos de distribuição por ativos com:
- **Custo operacional zero (Free Tier / Deploy Local)**
- **Máxima privacidade de dados financeiros** (credenciais efêmeras, sem persistência de senhas)
- **Engine determinística** (FastAPI + Otimizador Quadrático Inteiro Discreto)
- **Google Sheets como Single Source of Truth**

---

## Estrutura do Monorepo

```text
investment-rebalancer-ai/
├── docker-compose.yml              # Orquestração local dos serviços
├── .env.example                    # Template de variáveis de ambiente
├── .gitignore                      # Regras de exclusão (ignora credentials/ e .env)
├── credentials/                    # Chaves de Service Account do GCP (ignorado no git)
├── config/
│   ├── asset_mapping.json          # Regras operacionais e aplicação mínima
│   └── alias_map.json              # Mapeamento De-Para e recomendações "OU"
├── backend/
│   ├── Dockerfile                  # Contêiner Python 3.12
│   ├── requirements.txt            # Dependências FastAPI, gspread, scipy, numpy
│   └── app/
│       ├── main.py                 # Ponto de entrada FastAPI e rotas HTTP
│       ├── schemas.py              # Modelos de dados Pydantic
│       ├── clients/
│       │   ├── platform_api.py     # Autenticação transparente e carteiras
│       │   ├── market_data.py      # Cotações B3, CVM, Tesouro e Cripto
│       │   └── sheets_db.py        # Integração Google Sheets via gspread
│       └── services/
│           ├── parser.py           # Parser e sanitização da carteira 50K
│           └── optimizer.py        # Otimização quadrática discreta
└── frontend/
    ├── Dockerfile                  # Contêiner Node 20
    ├── package.json                # Dependências Next.js, React, Tailwind CSS
    └── src/
        ├── components/
        │   ├── LoginForm.tsx       # Autenticação transparente efêmera
        │   ├── Dashboard.tsx       # Controle de aporte e modo de rebalanceamento
        │   └── SimulationTable.tsx # Tabela interativa com prévia de ordens
        └── pages/
            └── index.tsx           # Página principal
```

---

## Como Executar Localmente

### Pré-requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e ativo.

### 1. Clonar o Repositório e Configurar Variáveis
```bash
cp .env.example .env
# Preencher chaves e IDs da planilha no .env
```

### 2. Adicionar Credenciais do Google Cloud
Colocar o arquivo de chave JSON da Service Account em:
`credentials/google-service-account.json`

### 3. Subir os Contêineres
```bash
docker compose up --build
```

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Docs Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

