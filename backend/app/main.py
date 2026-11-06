from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.clients.sheets_db import SheetsDbClient
from app.schemas import InitTemplateResponse, LatestCustodyResponse

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
