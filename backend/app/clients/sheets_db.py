from typing import Any, Dict, List
import gspread


class SheetsDbClient:
    """Google Sheets integration client using GCP Service Account."""

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id

    def get_latest_monthly_sheet(self) -> List[Dict[str, Any]]:
        """Locate and load custody rows from most recent monthly tab."""
        # Implementation in Phase 2
        raise NotImplementedError("SheetsDbClient.get_latest_monthly_sheet not yet implemented")

    def create_monthly_sheet(self, tab_name: str, records: List[Dict[str, Any]]) -> bool:
        """Duplicate monthly template and write new custody snapshot."""
        # Implementation in Phase 2
        raise NotImplementedError("SheetsDbClient.create_monthly_sheet not yet implemented")

