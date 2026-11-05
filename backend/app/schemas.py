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
    current_qty: float
    current_price: float
    current_total_value: float


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

