from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.clients.sheets_db import SheetsDbClient
from app.schemas import (
    AliasAddRequest,
    AssetMappingListResponse,
    AssetRule,
    InitTemplateResponse,
    LatestCustodyResponse,
    ResolveBatchResponse,
    ResolveRequest,
)
from app.services.asset_resolver import AssetResolver, load_seed_rules

app = FastAPI(
    title="Investment Rebalancer AI API",
    version="1.0.0",
    description="Engine determinística de rebalanceamento de carteiras de investimentos",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "ok", "service": "investment-rebalancer-ai"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/sheets/health")
def sheets_health(response: Response):
    """Check connectivity and credentials health for Google Sheets integration."""
    client = SheetsDbClient()
    result = client.test_connection()
    if not result.get("connected", False):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@app.get("/api/v1/sheets/latest-custody", response_model=LatestCustodyResponse)
def get_latest_custody():
    """Retrieve current custody holdings from the latest monthly tab in Google Sheets."""
    client = SheetsDbClient()
    if not client.is_credentials_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Arquivo de credencial Google Sheets não configurado.",
        )
    try:
        data = client.get_latest_monthly_sheet()
        return data
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ler aba mensal recente: {str(e)}",
        )


@app.post("/api/v1/sheets/template/init", response_model=InitTemplateResponse)
def init_sheets_template():
    """Initialize template and master evolution sheets in Google Sheets."""
    client = SheetsDbClient()
    if not client.is_credentials_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Arquivo de credencial Google Sheets não configurado.",
        )
    try:
        res = client.ensure_template_sheet()
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao inicializar templates: {str(e)}",
        )


@app.get("/api/v1/assets/mapping", response_model=AssetMappingListResponse)
def list_asset_mapping(refresh: bool = False):
    """List all mapped assets and trading constraints from 'Mapeamento_Ativos' (or fallback JSON)."""
    resolver = AssetResolver()
    source, rules = resolver.get_rules(force_refresh=refresh)
    return AssetMappingListResponse(
        source=source,
        count=len(rules),
        items=rules,
    )


@app.put("/api/v1/assets/mapping", response_model=AssetRule)
def upsert_asset_mapping(rule: AssetRule):
    """Create or update an asset rule (including minimum order, lot step, aliases) in Google Sheets."""
    client = SheetsDbClient()
    if not client.is_credentials_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Arquivo de credencial Google Sheets não configurado.",
        )
    try:
        resolver = AssetResolver(sheets_client=client)
        return resolver.upsert_rule(rule)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar regra do ativo: {str(e)}",
        )


@app.post("/api/v1/assets/alias", response_model=AssetRule)
def add_asset_alias(req: AliasAddRequest):
    """Add a new alias/synonym to an existing asset in 'Mapeamento_Ativos'."""
    client = SheetsDbClient()
    if not client.is_credentials_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Arquivo de credencial Google Sheets não configurado.",
        )
    try:
        resolver = AssetResolver(sheets_client=client)
        return resolver.add_alias(req.ticker, req.alias)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao vincular alias: {str(e)}",
        )


@app.post("/api/v1/assets/resolve", response_model=ResolveBatchResponse)
def resolve_assets_batch(req: ResolveRequest):
    """Resolve a list of asset names/tickers and check if simulation is unblocked."""
    resolver = AssetResolver()
    return resolver.resolve_batch(req.names)


@app.post("/api/v1/assets/seed")
def seed_assets_mapping():
    """Populate 'Mapeamento_Ativos' tab in Google Sheets with the initial seed catalog."""
    client = SheetsDbClient()
    if not client.is_credentials_present():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Arquivo de credencial Google Sheets não configurado.",
        )
    try:
        seed_rules = load_seed_rules()
        res = client.seed_asset_mapping_sheet(seed_rules)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao popular aba Mapeamento_Ativos: {str(e)}",
        )
