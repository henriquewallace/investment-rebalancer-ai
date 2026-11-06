import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import gspread
from google.oauth2.service_account import Credentials

from app.schemas import CustodyAsset, EvolutionRecord, RebalanceItem

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

MONTHS_ORDER: Dict[str, int] = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "MAIO": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
}

MONTHLY_TAB_REGEX = re.compile(
    r"^(Jan|Fev|Mar|Abr|Mai|Maio|Jun|Jul|Ago|Set|Out|Nov|Dez)_(\d{2})$",
    re.IGNORECASE,
)


def parse_numeric(val: Any) -> float:
    """Robust conversion of Sheets values (BRL formatted or raw) to float."""
    if val is None or val == "" or val == "-":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = s.replace("R$", "").replace("%", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_template_config(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """Load sheets_template.json configuration with fallback paths and defaults."""
    candidates = [
        custom_path,
        os.getenv("SHEETS_TEMPLATE_PATH"),
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "config",
                "sheets_template.json",
            )
        ),
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "config",
                "sheets_template.json",
            )
        ),
        "/app/config/sheets_template.json",
    ]

    for path in candidates:
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # Built-in fallback template if file is not found
    return {
        "monthly_template": {
            "tab_name": "_TEMPLATE",
            "columns": [
                {"letter": "A", "header": "Categoria", "key": "category"},
                {"letter": "B", "header": "Ticker", "key": "ticker"},
                {"letter": "C", "header": "Nome do Ativo", "key": "asset_name"},
                {"letter": "D", "header": "Qtd Anterior", "key": "current_qty"},
                {"letter": "E", "header": "Preço Unitário (R$)", "key": "unit_price"},
                {"letter": "F", "header": "Valor Anterior (R$)", "key": "current_value"},
                {"letter": "G", "header": "Meta (%)", "key": "target_weight"},
                {"letter": "H", "header": "Qtd Aporte", "key": "target_qty_change"},
                {"letter": "I", "header": "Valor Aporte (R$)", "key": "allocated_value"},
                {"letter": "J", "header": "Qtd Nova", "key": "new_qty"},
                {"letter": "K", "header": "Valor Novo (R$)", "key": "new_value"},
                {"letter": "L", "header": "% Real Novo", "key": "new_weight"},
                {"letter": "M", "header": "Status / Obs", "key": "status"},
            ],
        },
        "evolution_template": {
            "tab_name": "Evolução Patrimonial",
            "columns": [
                {"letter": "A", "header": "Mês/Ano", "key": "month_year"},
                {"letter": "B", "header": "Data Execução", "key": "execution_date"},
                {"letter": "C", "header": "Patrimônio Anterior (R$)", "key": "previous_total"},
                {"letter": "D", "header": "Novo Aporte (R$)", "key": "new_investment"},
                {"letter": "E", "header": "Patrimônio Final (R$)", "key": "new_total"},
                {"letter": "F", "header": "Variação de Mercado (R$)", "key": "market_delta"},
                {"letter": "G", "header": "Rentabilidade Mensal (%)", "key": "monthly_return_pct"},
                {"letter": "H", "header": "Saldo Ações (R$)", "key": "equity_total"},
                {"letter": "I", "header": "Saldo FIIs (R$)", "key": "real_estate_total"},
                {"letter": "J", "header": "Saldo Renda Fixa (R$)", "key": "fixed_income_total"},
                {"letter": "K", "header": "Saldo Alternativos (R$)", "key": "alternatives_total"},
            ],
        },
    }


def parse_tab_sort_key(tab_name: str) -> Optional[Tuple[int, int]]:
    """Convert tab name like 'Mai_26' to sortable tuple (year, month_index)."""
    match = MONTHLY_TAB_REGEX.match(tab_name.strip())
    if not match:
        return None
    month_str = match.group(1).upper()
    year_str = match.group(2)
    month_idx = MONTHS_ORDER.get(month_str, 0)
    year = 2000 + int(year_str)
    return (year, month_idx)


def get_latest_monthly_tab_title(sheet_titles: List[str]) -> Optional[str]:
    """Find the most recent monthly tab from a list of worksheet titles."""
    matched: List[Tuple[Tuple[int, int], str]] = []
    for title in sheet_titles:
        key = parse_tab_sort_key(title)
        if key is not None:
            matched.append((key, title))

    if not matched:
        return None

    matched.sort(key=lambda item: item[0])
    return matched[-1][1]


class SheetsDbClient:
    """Google Sheets integration client using GCP Service Account and gspread."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        template_config_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "/app/credentials/google-service-account.json",
        )
        self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID", "")
        self.template_config = load_template_config(template_config_path)
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

    def ensure_template_sheet(self) -> Dict[str, Any]:
        """Ensure _TEMPLATE and Evolução Patrimonial tabs exist with proper headers."""
        sh = self.get_spreadsheet()
        existing_worksheets = {ws.title: ws for ws in sh.worksheets()}
        created_tabs: List[str] = []

        # 1. Monthly _TEMPLATE
        template_name = self.template_config.get("monthly_template", {}).get(
            "tab_name", "_TEMPLATE"
        )
        if template_name not in existing_worksheets:
            cols = self.template_config.get("monthly_template", {}).get("columns", [])
            headers = [c.get("header", "") for c in cols]
            ws_template = sh.add_worksheet(
                title=template_name, rows=100, cols=max(len(headers), 15)
            )
            ws_template.update(range_name="A1:M1", values=[headers])
            try:
                ws_template.freeze(rows=1)
            except Exception:
                pass
            created_tabs.append(template_name)

        # 2. Evolução Patrimonial
        evo_name = self.template_config.get("evolution_template", {}).get(
            "tab_name", "Evolução Patrimonial"
        )
        if evo_name not in existing_worksheets:
            cols = self.template_config.get("evolution_template", {}).get("columns", [])
            headers = [c.get("header", "") for c in cols]
            ws_evo = sh.add_worksheet(
                title=evo_name, rows=100, cols=max(len(headers), 15)
            )
            ws_evo.update(range_name="A1:K1", values=[headers])
            try:
                ws_evo.freeze(rows=1)
            except Exception:
                pass
            created_tabs.append(evo_name)

        return {
            "initialized": True,
            "created_tabs": created_tabs,
            "existing_tabs": list(existing_worksheets.keys()),
            "message": (
                f"Templates verificados com sucesso. Abas criadas: {created_tabs}"
                if created_tabs
                else "Todas as abas de template já existem."
            ),
        }

    def get_latest_monthly_sheet(self) -> Dict[str, Any]:
        """Locate and load custody rows from the most recent monthly tab."""
        sh = self.get_spreadsheet()
        worksheets = sh.worksheets()
        titles = [ws.title for ws in worksheets]

        latest_title = get_latest_monthly_tab_title(titles)
        if not latest_title:
            raise ValueError(
                "Nenhuma aba mensal no formato 'Mes_AA' (ex.: 'Mai_26') foi encontrada na planilha."
            )

        ws = next(w for w in worksheets if w.title == latest_title)
        all_values = ws.get_all_values()

        if not all_values or len(all_values) <= 1:
            return {
                "tab_name": latest_title,
                "total_value": 0.0,
                "assets_count": 0,
                "assets": [],
            }

        headers = [h.strip() for h in all_values[0]]
        header_map = {name: idx for idx, name in enumerate(headers)}

        assets: List[CustodyAsset] = []
        total_portfolio_value = 0.0

        for row in all_values[1:]:
            if not row or not any(row):
                continue

            ticker = (
                row[header_map["Ticker"]].strip()
                if "Ticker" in header_map and len(row) > header_map["Ticker"]
                else (row[1].strip() if len(row) > 1 else "")
            )

            # Skip header or totals row
            if not ticker or ticker.upper() in ["TOTAL", "TICKER", "SOMA"]:
                continue

            asset_name = (
                row[header_map["Nome do Ativo"]].strip()
                if "Nome do Ativo" in header_map and len(row) > header_map["Nome do Ativo"]
                else (row[2].strip() if len(row) > 2 else ticker)
            )

            category = (
                row[header_map["Categoria"]].strip()
                if "Categoria" in header_map and len(row) > header_map["Categoria"]
                else (row[0].strip() if len(row) > 0 else "Outros")
            )

            # Quantity: prefer Qtd Nova (J), fallback to Qtd Anterior (D)
            new_qty_str = (
                row[header_map["Qtd Nova"]]
                if "Qtd Nova" in header_map and len(row) > header_map["Qtd Nova"]
                else (row[9] if len(row) > 9 else "")
            )
            old_qty_str = (
                row[header_map["Qtd Anterior"]]
                if "Qtd Anterior" in header_map and len(row) > header_map["Qtd Anterior"]
                else (row[3] if len(row) > 3 else "")
            )
            qty = parse_numeric(new_qty_str) if parse_numeric(new_qty_str) > 0 else parse_numeric(old_qty_str)

            # Price: Preço Unitário (E)
            price_str = (
                row[header_map["Preço Unitário (R$)"]]
                if "Preço Unitário (R$)" in header_map and len(row) > header_map["Preço Unitário (R$)"]
                else (row[4] if len(row) > 4 else "")
            )
            unit_price = parse_numeric(price_str)

            # Total value: prefer Valor Novo (K), fallback to Valor Anterior (F)
            new_val_str = (
                row[header_map["Valor Novo (R$)"]]
                if "Valor Novo (R$)" in header_map and len(row) > header_map["Valor Novo (R$)"]
                else (row[10] if len(row) > 10 else "")
            )
            old_val_str = (
                row[header_map["Valor Anterior (R$)"]]
                if "Valor Anterior (R$)" in header_map and len(row) > header_map["Valor Anterior (R$)"]
                else (row[5] if len(row) > 5 else "")
            )
            val = parse_numeric(new_val_str) if parse_numeric(new_val_str) > 0 else parse_numeric(old_val_str)
            if val == 0.0 and qty > 0 and unit_price > 0:
                val = qty * unit_price

            total_portfolio_value += val

            assets.append(
                CustodyAsset(
                    ticker=ticker,
                    asset_name=asset_name or ticker,
                    category=category or "Outros",
                    current_qty=qty,
                    current_price=unit_price,
                    current_total_value=round(val, 2),
                )
            )

        return {
            "tab_name": latest_title,
            "total_value": round(total_portfolio_value, 2),
            "assets_count": len(assets),
            "assets": [a.model_dump() for a in assets],
        }

    def create_monthly_sheet(
        self,
        tab_name: str,
        items: List[RebalanceItem],
        evolution_record: Optional[EvolutionRecord] = None,
    ) -> Dict[str, Any]:
        """Duplicate monthly template, write rebalance items and update evolution sheet."""
        sh = self.get_spreadsheet()
        worksheets = sh.worksheets()
        existing_map = {ws.title: ws for ws in worksheets}

        # 1. Setup target monthly worksheet
        if tab_name in existing_map:
            target_ws = existing_map[tab_name]
            target_ws.clear()
        else:
            template_name = self.template_config.get("monthly_template", {}).get(
                "tab_name", "_TEMPLATE"
            )
            if template_name in existing_map:
                source_id = existing_map[template_name].id
                target_ws = sh.duplicate_sheet(
                    source_sheet_id=source_id, new_sheet_name=tab_name
                )
                try:
                    target_ws.batch_clear(["A2:M1000"])
                except Exception:
                    pass
            else:
                target_ws = sh.add_worksheet(
                    title=tab_name, rows=max(len(items) + 15, 60), cols=15
                )

        # 2. Ensure header row
        cols = self.template_config.get("monthly_template", {}).get("columns", [])
        headers = [c.get("header", "") for c in cols]
        target_ws.update(range_name="A1:M1", values=[headers])

        # 3. Populate rows
        rows: List[List[Any]] = []
        tot_prev_val = 0.0
        tot_alloc_val = 0.0
        tot_new_val = 0.0
        tot_target_wt = 0.0
        tot_new_wt = 0.0

        for item in items:
            cat = getattr(item, "category", "Outros")
            ticker = item.ticker
            name = item.asset_name
            cur_qty = item.current_qty
            price = item.unit_price
            cur_val = item.current_value
            tgt_wt = item.target_weight
            qty_chg = item.target_qty_change
            alloc_val = item.allocated_value
            new_qty = item.new_qty
            new_val = item.new_value
            new_wt = item.new_weight

            status_note = getattr(item, "action", "HOLD")
            if getattr(item, "is_under_review", False):
                status_note += " (Em revisão)"
            if getattr(item, "ceiling_price_exceeded", False):
                status_note += " (Preço Teto Excedido)"

            tot_prev_val += cur_val
            tot_alloc_val += alloc_val
            tot_new_val += new_val
            tot_target_wt += tgt_wt
            tot_new_wt += new_wt

            rows.append(
                [
                    cat,
                    ticker,
                    name,
                    cur_qty,
                    price,
                    cur_val,
                    f"{tgt_wt * 100:.2f}%" if tgt_wt <= 1.0 else f"{tgt_wt:.2f}%",
                    qty_chg,
                    alloc_val,
                    new_qty,
                    new_val,
                    f"{new_wt * 100:.2f}%" if new_wt <= 1.0 else f"{new_wt:.2f}%",
                    status_note,
                ]
            )

        # Row of Totals
        total_row = [
            "TOTAL",
            "",
            "",
            "",
            "",
            round(tot_prev_val, 2),
            "100.00%",
            "",
            round(tot_alloc_val, 2),
            "",
            round(tot_new_val, 2),
            f"{tot_new_wt * 100:.2f}%" if tot_new_wt <= 1.0 else f"{tot_new_wt:.2f}%",
            "",
        ]
        rows.append(total_row)

        end_row = len(rows) + 1
        target_ws.update(range_name=f"A2:M{end_row}", values=rows)

        # 4. Update Evolution sheet if record provided
        if evolution_record is not None:
            self.append_evolution_record(evolution_record)

        return {
            "success": True,
            "tab_name": tab_name,
            "rows_written": len(rows),
            "total_new_value": round(tot_new_val, 2),
            "total_allocated": round(tot_alloc_val, 2),
        }

    def append_evolution_record(self, record: EvolutionRecord) -> bool:
        """Append or update a row in the 'Evolução Patrimonial' sheet."""
        sh = self.get_spreadsheet()
        evo_name = self.template_config.get("evolution_template", {}).get(
            "tab_name", "Evolução Patrimonial"
        )
        worksheets = sh.worksheets()
        ws_evo = next((w for w in worksheets if w.title == evo_name), None)

        if ws_evo is None:
            self.ensure_template_sheet()
            sh = self.get_spreadsheet()
            ws_evo = next((w for w in sh.worksheets() if w.title == evo_name))

        all_values = ws_evo.get_all_values()
        row_data = [
            record.month_year,
            record.execution_date,
            record.previous_total,
            record.new_investment,
            record.new_total,
            record.market_delta,
            f"{record.monthly_return_pct * 100:.2f}%"
            if record.monthly_return_pct <= 1.0
            else f"{record.monthly_return_pct:.2f}%",
            record.equity_total,
            record.real_estate_total,
            record.fixed_income_total,
            record.alternatives_total,
        ]

        # Check if record for month_year already exists
        existing_row_idx = None
        for idx, row in enumerate(all_values[1:], start=2):
            if row and row[0].strip().upper() == record.month_year.strip().upper():
                existing_row_idx = idx
                break

        if existing_row_idx:
            ws_evo.update(range_name=f"A{existing_row_idx}:K{existing_row_idx}", values=[row_data])
        else:
            ws_evo.append_row(row_data)

        return True
