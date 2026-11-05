from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.clients.sheets_db import SheetsDbClient

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
