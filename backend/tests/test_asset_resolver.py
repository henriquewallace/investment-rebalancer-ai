import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.clients.sheets_db import SheetsDbClient
from app.main import app
from app.schemas import AssetRule
from app.services.asset_resolver import (
    AssetResolver,
    load_seed_rules,
    normalize_asset_key,
)


@pytest.fixture
def test_client():
    return TestClient(app)


def test_normalize_asset_key():
    assert normalize_asset_key("  irfm11  ") == "IRFM11"
    assert normalize_asset_key("Tesouro IPCA+ 2050") == "TESOURO IPCA+ 2050"
    assert (
        normalize_asset_key("MS Global Opportunities Dólar")
        == "MS GLOBAL OPPORTUNITIES DOLAR"
    )
    assert normalize_asset_key("") == ""


def test_load_seed_rules_catalog():
    rules = load_seed_rules()
    assert len(rules) >= 33
    by_ticker = {r.ticker: r for r in rules}

    # Check CDB Daycoval constraints and "OU" alias
    assert "CDB DAYCOVAL" in by_ticker
    cdb = by_ticker["CDB DAYCOVAL"]
    assert cdb.min_order_value == 1000.0
    assert cdb.category == "Renda Fixa"
    assert "CDB DO DAYCOVAL, CDB DO BMG OU TESOURO RESERVA" in [
        a.upper() for a in cdb.aliases
    ]

    # Check IRFM11 "OU" alias
    assert "IRFM11" in by_ticker
    irfm = by_ticker["IRFM11"]
    assert "ETF IRFM11 OU ETF IDKA11" in [a.upper() for a in irfm.aliases]

    # Check Funds min order R$ 500
    for fund_ticker in ["GENOA CAPITAL", "ABSOLUTE VERTEX", "KINEA ATLAS", "MS GLOBAL OPP", "ACE CAPITAL"]:
        assert fund_ticker in by_ticker
        assert by_ticker[fund_ticker].min_order_value == 500.0
        assert by_ticker[fund_ticker].is_fractional is True

    # Check Stocks are integer lots
    assert by_ticker["VALE3"].is_fractional is False
    assert by_ticker["VALE3"].lot_step == 1.0


def test_resolver_resolve_and_batch():
    resolver = AssetResolver(use_sheets=False)

    # Resolve direct ticker
    r1 = resolver.resolve("  vale3 ")
    assert r1.mapped is True
    assert r1.ticker == "VALE3"

    # Resolve "OU" expressions
    r2 = resolver.resolve("ETF IRFM11 OU ETF IDKA11")
    assert r2.mapped is True
    assert r2.ticker == "IRFM11"

    r3 = resolver.resolve("CDB DO DAYCOVAL, CDB DO BMG OU TESOURO RESERVA")
    assert r3.mapped is True
    assert r3.ticker == "CDB DAYCOVAL"

    # Resolve unknown asset
    r4 = resolver.resolve("ATIVO_DESCONHECIDO_99")
    assert r4.mapped is False
    assert r4.ticker is None

    # Batch with unmapped blocks simulation
    batch_blocked = resolver.resolve_batch(["VALE3", "IRFM11", "NOVO_FUNDO_XYZ"])
    assert batch_blocked.can_simulate is False
    assert batch_blocked.unmapped == ["NOVO_FUNDO_XYZ"]
    assert len(batch_blocked.mapped) == 2

    # Batch with all mapped unlocks simulation
    batch_ok = resolver.resolve_batch(["VALE3", "CDB DO DAYCOVAL", "GENOA CAPITAL RADAR"])
    assert batch_ok.can_simulate is True
    assert batch_ok.unmapped == []
    assert len(batch_ok.mapped) == 3


def test_sheets_db_mapping_crud(tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    client = SheetsDbClient(credentials_path=str(cred_file), spreadsheet_id="test-id")
    mock_sh = MagicMock()
    mock_ws_map = MagicMock()
    mock_ws_map.title = "Mapeamento_Ativos"
    mock_ws_map.get_all_values.return_value = [
        [
            "Ticker",
            "Nome",
            "Categoria",
            "Tipo",
            "Fracionável",
            "Aporte Mínimo (R$)",
            "Passo Lote",
            "Fonte Preço",
            "Aliases",
            "Ativo",
        ],
        [
            "VALE3",
            "Vale S.A. ON",
            "Ações",
            "STOCK",
            "FALSE",
            "0",
            "1",
            "brapi",
            "VALE3|VALE",
            "TRUE",
        ],
    ]
    mock_sh.worksheets.return_value = [mock_ws_map]
    client._spreadsheet = mock_sh
    client._client = MagicMock()

    # 1. Read rows
    rows = client.get_asset_mapping_rows()
    assert len(rows) == 1
    assert rows[0].ticker == "VALE3"
    assert rows[0].aliases == ["VALE3", "VALE"]

    # 2. Add alias
    updated = client.add_asset_alias("VALE3", "VALE ON NM")
    assert "VALE ON NM" in updated.aliases
    assert mock_ws_map.update.called

    # 3. Upsert existing rule (e.g. changing min_order_value)
    updated.min_order_value = 100.0
    saved = client.upsert_asset_rule(updated)
    assert saved.min_order_value == 100.0

    # 4. Upsert new rule
    new_rule = AssetRule(
        ticker="XYZW11",
        name="Fundo Teste",
        category="FIIs",
        asset_type="FII",
        is_fractional=False,
        min_order_value=0.0,
        lot_step=1.0,
        price_source="brapi",
        aliases=["XYZW11"],
    )
    client.upsert_asset_rule(new_rule)
    assert mock_ws_map.append_row.called


def test_asset_endpoints(test_client, tmp_path):
    cred_file = tmp_path / "creds.json"
    cred_file.write_text("{}")

    with patch.dict(
        os.environ,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": "/non/existent/creds.json",
            "SPREADSHEET_ID": "",
        },
    ):
        # Fallback to seed_json when credentials are not active
        res = test_client.get("/api/v1/assets/mapping")
        assert res.status_code == 200
        data = res.json()
        assert data["source"] == "seed_json"
        assert data["count"] >= 33

        # Resolve endpoint
        res_resolve = test_client.post(
            "/api/v1/assets/resolve",
            json={"names": ["ETF IRFM11 OU ETF IDKA11", "ATIVO_NAO_MAPEADO"]},
        )
        assert res_resolve.status_code == 200
        r_data = res_resolve.json()
        assert r_data["can_simulate"] is False
        assert r_data["unmapped"] == ["ATIVO_NAO_MAPEADO"]
        assert r_data["mapped"][0]["ticker"] == "IRFM11"

