import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.clients.sheets_db import SheetsDbClient
from app.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


def test_credentials_missing():
    client = SheetsDbClient(credentials_path="/non/existent/path.json", spreadsheet_id="test-id")
    assert not client.is_credentials_present()
    res = client.test_connection()
    assert not res["connected"]
    assert res["status"] == "credentials_missing"


def test_spreadsheet_id_missing(tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")
    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="")
    assert client.is_credentials_present()
    res = client.test_connection()
    assert not res["connected"]
    assert res["status"] == "spreadsheet_id_missing"


@patch("app.clients.sheets_db.Credentials.from_service_account_file")
@patch("app.clients.sheets_db.gspread.authorize")
def test_connection_successful(mock_authorize, mock_creds, tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    mock_client = MagicMock()
    mock_sh = MagicMock()
    mock_sh.title = "Minha Planilha Financeira"
    mock_ws1 = MagicMock()
    mock_ws1.title = "Maio_26"
    mock_ws2 = MagicMock()
    mock_ws2.title = "Evolução Patrimonial"
    mock_sh.worksheets.return_value = [mock_ws1, mock_ws2]

    mock_client.open_by_key.return_value = mock_sh
    mock_authorize.return_value = mock_client

    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="valid-sheet-id")
    res = client.test_connection()

    assert res["connected"] is True
    assert res["status"] == "connected"
    assert res["spreadsheet_title"] == "Minha Planilha Financeira"
    assert res["worksheets"] == ["Maio_26", "Evolução Patrimonial"]
    assert res["worksheets_count"] == 2


def test_sheets_health_endpoint_missing_creds(test_client):
    with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/non/existent/creds.json"}):
        response = test_client.get("/api/v1/sheets/health")
        assert response.status_code == 503
        data = response.json()
        assert data["connected"] is False
        assert data["status"] == "credentials_missing"

