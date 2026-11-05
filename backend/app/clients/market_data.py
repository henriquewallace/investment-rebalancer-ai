from typing import Dict, List, Optional
import httpx


class MarketDataClient:
    """Consolidated market data provider for B3, CVM, Tesouro and Crypto."""

    async def get_quotes(self, tickers: List[str]) -> Dict[str, Optional[float]]:
        """Fetch quotes for given tickers with fallback."""
        # Implementation in Phase 4
        raise NotImplementedError("MarketDataClient.get_quotes not yet implemented")

