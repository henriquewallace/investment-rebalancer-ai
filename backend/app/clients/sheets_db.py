import os
from typing import Any, Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsDbClient:
    """Google Sheets integration client using GCP Service Account and gspread."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "/app/credentials/google-service-account.json",
        )
        self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID", "")
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    def is_credentials_present(self) -> bool:
        """Check if credential JSON file exists on disk."""
        return bool(self.credentials_path and os.path.isfile(self.credentials_path))

    def authenticate(self) -> gspread.Client:
        """Authenticate using Service Account JSON credentials."""
        if not self.is_credentials_present():
            raise FileNotFoundError(
                f"Arquivo de credenciais não encontrado no caminho: '{self.credentials_path}'. "
                "Adicione o arquivo 'google-service-account.json' na pasta credentials/."
            )

        credentials = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=SCOPES,
        )
        self._client = gspread.authorize(credentials)
        return self._client

    def get_spreadsheet(self) -> gspread.Spreadsheet:
        """Open and cache the target spreadsheet instance."""
        if self._spreadsheet is not None:
            return self._spreadsheet

        if not self.spreadsheet_id:
            raise ValueError(
                "Variável SPREADSHEET_ID não informada. Configure no arquivo .env."
            )

        if self._client is None:
            self.authenticate()

        self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    def test_connection(self) -> Dict[str, Any]:
        """Test authentication and connectivity to the Google Sheets spreadsheet."""
        if not self.is_credentials_present():
            return {
                "connected": False,
                "status": "credentials_missing",
                "message": (
                    f"Arquivo de credencial não encontrado em '{self.credentials_path}'. "
                    "Coloque a chave da Service Account em credentials/google-service-account.json"
                ),
                "credentials_path": self.credentials_path,
            }

        if not self.spreadsheet_id or not self.spreadsheet_id.strip():
            return {
                "connected": False,
                "status": "spreadsheet_id_missing",
                "message": "Variável SPREADSHEET_ID vazia ou não configurada.",
            }

        try:
            sh = self.get_spreadsheet()
            worksheets = [ws.title for ws in sh.worksheets()]
            return {
                "connected": True,
                "status": "connected",
                "spreadsheet_title": sh.title,
                "spreadsheet_id": self.spreadsheet_id,
                "worksheets_count": len(worksheets),
                "worksheets": worksheets,
                "message": f"Conectado com sucesso à planilha '{sh.title}'.",
            }
        except Exception as e:
            return {
                "connected": False,
                "status": "connection_error",
                "error": str(e),
                "message": f"Falha na comunicação com o Google Sheets: {str(e)}",
            }

    def get_latest_monthly_sheet(self) -> List[Dict[str, Any]]:
        """Locate and load custody rows from most recent monthly tab."""
        # Detailed row parsing in Task 2.2
        raise NotImplementedError("SheetsDbClient.get_latest_monthly_sheet implementado na Tarefa 2.2")

    def create_monthly_sheet(self, tab_name: str, records: List[Dict[str, Any]]) -> bool:
        """Duplicate monthly template and write new custody snapshot."""
        # Tab duplication in Task 2.2
        raise NotImplementedError("SheetsDbClient.create_monthly_sheet implementado na Tarefa 2.2")
