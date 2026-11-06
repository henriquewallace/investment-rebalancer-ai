from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FeederOption(BaseModel):
    broker: str
    cnpj: Optional[str] = None
    min_initial_investment: float = 0.0
    min_additional_investment: float = 0.0


class RecommendedAsset(BaseModel):
    asset_name: str
    ticker: str
    category: str
    target_weight: float
    ceiling_price: Optional[float] = None
    is_under_review: bool = False
    feeder_options: List[FeederOption] = Field(default_factory=list)


class CustodyAsset(BaseModel):
    ticker: str
    asset_name: str
    category: str = "Outros"
    current_qty: float
    current_price: float
    current_total_value: float


class MonthlySheetRow(BaseModel):
    category: str
    ticker: str
    asset_name: str
    current_qty: float
    unit_price: float
    current_value: float
    target_weight: float
    target_qty_change: float
    allocated_value: float
    new_qty: float
    new_value: float
    new_weight: float
    status: str = "HOLD"


class EvolutionRecord(BaseModel):
    month_year: str
    execution_date: str
    previous_total: float
    new_investment: float
    new_total: float
    market_delta: float = 0.0
    monthly_return_pct: float = 0.0
    equity_total: float = 0.0
    real_estate_total: float = 0.0
    fixed_income_total: float = 0.0
    alternatives_total: float = 0.0


class LatestCustodyResponse(BaseModel):
    tab_name: str
    total_value: float
    assets_count: int
    assets: List[CustodyAsset]


class InitTemplateResponse(BaseModel):
    initialized: bool
    created_tabs: List[str]
    existing_tabs: List[str]
    message: str


class RebalanceRequest(BaseModel):
    total_investment: float = Field(..., ge=0.0, description="Novo aporte em R$")
    allow_partial_sales: bool = Field(False, description="Modo Sabonete (False) vs Cirúrgico (True)")
    manual_prices: Dict[str, float] = Field(default_factory=dict, description="Preços manuais para ativos sem cotação pública")


class RebalanceItem(BaseModel):
    ticker: str
    asset_name: str
    category: str
    current_qty: float
    target_qty_change: float
    new_qty: float
    unit_price: float
    current_value: float
    allocated_value: float
    new_value: float
    target_weight: float
    new_weight: float
    action: str  # BUY, SELL, HOLD
    is_under_review: bool = False
    ceiling_price_exceeded: bool = False


class RebalanceResponse(BaseModel):
    mode: str
    total_budget: float
    allocated_total: float
    remaining_cash: float
    items: List[RebalanceItem]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

