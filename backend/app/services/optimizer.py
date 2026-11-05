from typing import List
from app.schemas import CustodyAsset, RebalanceItem, RebalanceResponse, RecommendedAsset


def optimize_allocation(
    custody: List[CustodyAsset],
    recommended: List[RecommendedAsset],
    total_investment: float,
    allow_partial_sales: bool = False,
) -> RebalanceResponse:
    """Discrete quadratic optimization for portfolio rebalancing."""
    # Implementation in Phase 4
    raise NotImplementedError("optimize_allocation not yet implemented")

