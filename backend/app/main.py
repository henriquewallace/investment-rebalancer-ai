from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

