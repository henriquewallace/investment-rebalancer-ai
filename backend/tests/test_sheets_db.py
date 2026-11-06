import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.clients.sheets_db import (
    SheetsDbClient,
    get_latest_monthly_tab_title,
    parse_numeric,
    parse_tab_sort_key,
)
from app.main import app
from app.schemas import EvolutionRecord, RebalanceItem


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
    mock_ws1.title = "Mai_26"
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
    assert res["worksheets"] == ["Mai_26", "Evolução Patrimonial"]
    assert res["worksheets_count"] == 2


def test_parse_tab_sort_key_and_latest_title():
    # Valid tabs
    assert parse_tab_sort_key("Jan_26") == (2026, 1)
    assert parse_tab_sort_key("Mai_26") == (2026, 5)
    assert parse_tab_sort_key("Maio_26") == (2026, 5)
    assert parse_tab_sort_key("Dez_25") == (2025, 12)
    assert parse_tab_sort_key("Fev_27") == (2027, 2)

    # Invalid tabs
    assert parse_tab_sort_key("_TEMPLATE") is None
    assert parse_tab_sort_key("Evolução Patrimonial") is None
    assert parse_tab_sort_key("Random_Tab") is None

    # Sorting
    titles = [
        "Evolução Patrimonial",
        "_TEMPLATE",
        "Abr_26",
        "Jan_26",
        "Mai_26",
        "Dez_25",
        "Fev_26",
    ]
    latest = get_latest_monthly_tab_title(titles)
    assert latest == "Mai_26"

    # With future year
    titles_with_future = titles + ["Jan_27"]
    assert get_latest_monthly_tab_title(titles_with_future) == "Jan_27"

    # Empty/no match
    assert get_latest_monthly_tab_title(["_TEMPLATE", "Outros"]) is None


def test_parse_numeric():
    assert parse_numeric(100) == 100.0
    assert parse_numeric(150.75) == 150.75
    assert parse_numeric("R$ 1.500,50") == 1500.50
    assert parse_numeric("65,40") == 65.40
    assert parse_numeric("15.2%") == 15.2
    assert parse_numeric(" 4,5 % ") == 4.5
    assert parse_numeric("-") == 0.0
    assert parse_numeric("") == 0.0
    assert parse_numeric(None) == 0.0
    assert parse_numeric("invalid") == 0.0


def test_ensure_template_sheet(tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="test-id")
    mock_sh = MagicMock()
    mock_ws_existing = MagicMock()
    mock_ws_existing.title = "Outra Aba"
    mock_sh.worksheets.return_value = [mock_ws_existing]

    mock_template_ws = MagicMock()
    mock_evo_ws = MagicMock()
    mock_sh.add_worksheet.side_effect = [mock_template_ws, mock_evo_ws]

    client._spreadsheet = mock_sh
    client._client = MagicMock()

    res = client.ensure_template_sheet()
    assert res["initialized"] is True
    assert "_TEMPLATE" in res["created_tabs"]
    assert "Evolução Patrimonial" in res["created_tabs"]
    assert mock_sh.add_worksheet.call_count == 2


def test_get_latest_monthly_sheet(tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="test-id")
    mock_sh = MagicMock()

    mock_ws_template = MagicMock()
    mock_ws_template.title = "_TEMPLATE"

    mock_ws_abr = MagicMock()
    mock_ws_abr.title = "Abr_26"

    mock_ws_mai = MagicMock()
    mock_ws_mai.title = "Mai_26"
    mock_ws_mai.get_all_values.return_value = [
        [
            "Categoria",
            "Ticker",
            "Nome do Ativo",
            "Qtd Anterior",
            "Preço Unitário (R$)",
            "Valor Anterior (R$)",
            "Meta (%)",
            "Qtd Aporte",
            "Valor Aporte (R$)",
            "Qtd Nova",
            "Valor Novo (R$)",
            "% Real Novo",
            "Status / Obs",
        ],
        [
            "Ações",
            "VALE3",
            "Vale S.A.",
            "100",
            "60,00",
            "6.000,00",
            "5,00%",
            "10",
            "600,00",
            "110",
            "6.600,00",
            "5,10%",
            "BUY",
        ],
        [
            "Renda Fixa",
            "TESOURO SELIC",
            "Tesouro Selic 2029",
            "1",
            "15.000,00",
            "15.000,00",
            "20,00%",
            "0",
            "0,00",
            "1",
            "15.000,00",
            "20,00%",
            "HOLD",
        ],
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            "21.000,00",
            "100,00%",
            "",
            "600,00",
            "",
            "21.600,00",
            "100,00%",
            "",
        ],
    ]

    mock_sh.worksheets.return_value = [mock_ws_template, mock_ws_abr, mock_ws_mai]
    client._spreadsheet = mock_sh
    client._client = MagicMock()

    data = client.get_latest_monthly_sheet()
    assert data["tab_name"] == "Mai_26"
    assert data["assets_count"] == 2
    assert data["total_value"] == 21600.00
    assert data["assets"][0]["ticker"] == "VALE3"
    assert data["assets"][0]["current_qty"] == 110.0
    assert data["assets"][0]["current_total_value"] == 6600.0
    assert data["assets"][1]["ticker"] == "TESOURO SELIC"


def test_create_monthly_sheet_and_append_evolution(tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="test-id")
    mock_sh = MagicMock()

    mock_ws_template = MagicMock()
    mock_ws_template.title = "_TEMPLATE"
    mock_ws_template.id = 12345

    mock_ws_evo = MagicMock()
    mock_ws_evo.title = "Evolução Patrimonial"
    mock_ws_evo.get_all_values.return_value = [
        ["Mês/Ano", "Data Execução", "Patrimônio Anterior (R$)"]
    ]

    mock_target_ws = MagicMock()
    mock_sh.duplicate_sheet.return_value = mock_target_ws
    mock_sh.worksheets.return_value = [mock_ws_template, mock_ws_evo]

    client._spreadsheet = mock_sh
    client._client = MagicMock()

    items = [
        RebalanceItem(
            ticker="VALE3",
            asset_name="Vale S.A.",
            category="Ações",
            current_qty=100.0,
            target_qty_change=10.0,
            new_qty=110.0,
            unit_price=60.0,
            current_value=6000.0,
            allocated_value=600.0,
            new_value=6600.0,
            target_weight=0.05,
            new_weight=0.051,
            action="BUY",
        )
    ]

    evo = EvolutionRecord(
        month_year="Jun_26",
        execution_date="2026-06-10",
        previous_total=6000.0,
        new_investment=600.0,
        new_total=6600.0,
        equity_total=6600.0,
    )

    res = client.create_monthly_sheet("Jun_26", items=items, evolution_record=evo)
    assert res["success"] is True
    assert res["tab_name"] == "Jun_26"
    assert res["total_new_value"] == 6600.0
    assert mock_sh.duplicate_sheet.called
    assert mock_target_ws.update.called
    assert mock_ws_evo.append_row.called


def test_sheets_endpoints_mocked(test_client, tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    with patch.dict(
        os.environ,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": str(cred_file),
            "SPREADSHEET_ID": "test-id",
        },
    ):
        with patch.object(
            SheetsDbClient,
            "get_latest_monthly_sheet",
            return_value={
                "tab_name": "Mai_26",
                "total_value": 50000.0,
                "assets_count": 1,
                "assets": [
                    {
                        "ticker": "VALE3",
                        "asset_name": "Vale S.A.",
                        "category": "Ações",
                        "current_qty": 100.0,
                        "current_price": 50.0,
                        "current_total_value": 5000.0,
                    }
                ],
            },
        ):
            response = test_client.get("/api/v1/sheets/latest-custody")
            assert response.status_code == 200
            data = response.json()
            assert data["tab_name"] == "Mai_26"
            assert data["total_value"] == 50000.0
            assert len(data["assets"]) == 1

        with patch.object(
            SheetsDbClient,
            "ensure_template_sheet",
            return_value={
                "initialized": True,
                "created_tabs": ["_TEMPLATE"],
                "existing_tabs": ["Evolução Patrimonial"],
                "message": "Templates verificados com sucesso.",
            },
        ):
            response = test_client.post("/api/v1/sheets/template/init")
            assert response.status_code == 200
            data = response.json()
            assert data["initialized"] is True
            assert "_TEMPLATE" in data["created_tabs"]
