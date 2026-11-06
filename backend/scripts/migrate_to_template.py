import os
import re
from typing import Dict, Tuple
from app.clients.sheets_db import SheetsDbClient, parse_numeric

ASSET_CATEGORY_MAP = {
    # Ações
    "GMAT3": ("Ações", "GMAT3", "Grupo Mateus ON"),
    "PRIO3": ("Ações", "PRIO3", "PRIO ON"),
    "WIZC3": ("Ações", "WIZC3", "Wiz Co ON"),
    "WIZC3 ": ("Ações", "WIZC3", "Wiz Co ON"),
    "BRBI11": ("Ações", "BRBI11", "Brasil Bolsa Balcão / BR Partners"),
    "KEPL3": ("Ações", "KEPL3", "Kepler Weber ON"),
    "SLCE3": ("Ações", "SLCE3", "SLC Agrícola ON"),
    "VALE3": ("Ações", "VALE3", "Vale S.A. ON"),
    "VAMO3": ("Ações", "VAMO3", "Grupo Vamos ON"),

    # FIIs
    "CPTI11": ("FIIs", "CPTI11", "Capitânia Infra FIC FI-Infra"),
    "CPTI11 ": ("FIIs", "CPTI11", "Capitânia Infra FIC FI-Infra"),
    "CPTS11": ("FIIs", "CPTS11", "Capitânia Securities II FII"),
    "JURO11": ("FIIs", "JURO11", "Sparta Infra FIC FI-Infra"),
    "KDIF11": ("FIIs", "KDIF11", "Kinea Debêntures Incentivadas"),
    "KDIF11 ": ("FIIs", "KDIF11", "Kinea Debêntures Incentivadas"),
    "PVBI11": ("FIIs", "PVBI11", "VBI Prime Properties FII"),
    "XPML11": ("FIIs", "XPML11", "XP Malls FII"),
    "XPML11 ": ("FIIs", "XPML11", "XP Malls FII"),
    "VILG11": ("FIIs", "VILG11", "Vinci Logística FII"),
    "XPCI11": ("FIIs", "XPCI11", "XP Crédito Imobiliário FII"),
    "PSEC11": ("FIIs", "PSEC11", "Pátria Securities FII"),

    # Renda Fixa
    "CDB DO DAYCOVAL": ("Renda Fixa", "CDB DAYCOVAL", "CDB Banco Daycoval Pós-fixado"),
    "Tesouro IPCA 2050": ("Renda Fixa", "TESOURO IPCA+ 2050", "Tesouro IPCA+ com Juros Semestrais 2050"),
    "IRFM11": ("Renda Fixa", "IRFM11", "ETF Itaú Tesouro IRF-M"),
    "IRFM11 ": ("Renda Fixa", "IRFM11", "ETF Itaú Tesouro IRF-M"),

    # Alternativos / Internacional / Cripto
    "WRLD11": ("Alternativos", "WRLD11", "ETF Investo Vanguard Total World"),
    "USDB11": ("Alternativos", "USDB11", "ETF Investo Dólar BRL"),
    "GOLD11": ("Alternativos", "GOLD11", "ETF Trend Ouro"),
    "ACE CAPITAL": ("Alternativos", "ACE CAPITAL", "Ace Capital FIC FIM"),
    "GENOA CAPITAL RADAR": ("Alternativos", "GENOA CAPITAL", "Genoa Capital Radar FIC FIM"),
    "ABSOLUTE VERTEX": ("Alternativos", "ABSOLUTE VERTEX", "Absolute Vertex FIC FIM"),
    "KINEA ATLAS": ("Alternativos", "KINEA ATLAS", "Kinea Atlas II FIC FIM"),
    "ALUG11": ("Alternativos", "ALUG11", "ETF Trend Imobiliário EUA"),
    "ALUG11 ": ("Alternativos", "ALUG11", "ETF Trend Imobiliário EUA"),
    "BNDX11": ("Alternativos", "BNDX11", "ETF Investo Vanguard Total Bond"),
    "BNDX11 ": ("Alternativos", "BNDX11", "ETF Investo Vanguard Total Bond"),
    "MS GLOBAL OPPORTUNITIES DÓLAR": ("Alternativos", "MS GLOBAL OPP", "Morgan Stanley Global Opportunities"),
    "HTEK11": ("Alternativos", "HTEK11", "ETF Investo Healthcare Innovation"),
    "NUCL11": ("Alternativos", "NUCL11", "ETF Investo Energia Nuclear"),
    "BITCOIN": ("Alternativos", "BITCOIN", "Bitcoin (BTC / Moeda Digital)"),
}


def categorize_asset(raw_name: str) -> Tuple[str, str, str]:
    clean = raw_name.strip()
    if clean in ASSET_CATEGORY_MAP:
        return ASSET_CATEGORY_MAP[clean]
    for key, val in ASSET_CATEGORY_MAP.items():
        if key.strip().upper() == clean.upper():
            return val
    # Fallback
    return ("Outros", clean, clean)


def run_migration():
    client = SheetsDbClient()
    sh = client.get_spreadsheet()
    print(f"Conectado à planilha: '{sh.title}'")

    # 1. Garantir _TEMPLATE e Evolução Patrimonial
    res_tpl = client.ensure_template_sheet()
    print("Templates garantidos:", res_tpl)

    # 2. Ler aba antiga 'Rebalanceamento e aportes - Out/26'
    source_title = "Rebalanceamento e aportes - Out/26"
    ws_source = sh.worksheet(source_title)
    all_rows = ws_source.get_all_values()

    # Identificar linha de totais do topo (R0/R1)
    # R1: ['', 'R$ 6.100,00', 'R$ 50.812,83', 'R$ 56.912,83', '', 'R$ 6.536,33', '', 'R$ 6.536,33']
    aporte_topo = parse_numeric(all_rows[1][1]) if len(all_rows) > 1 and len(all_rows[1]) > 1 else 0.0
    patrimonio_ant = parse_numeric(all_rows[1][2]) if len(all_rows) > 1 and len(all_rows[1]) > 2 else 0.0
    patrimonio_pos = parse_numeric(all_rows[1][3]) if len(all_rows) > 1 and len(all_rows[1]) > 3 else 0.0

    # Localizar cabeçalho da tabela de ativos (linha 4)
    header_idx = None
    for idx, row in enumerate(all_rows[:7]):
        if row and any("Ativos" in str(c) for c in row):
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError("Cabeçalho 'Ativos' não encontrado na aba antiga.")

    data_rows = all_rows[header_idx + 1:]
    new_tab_rows = []

    total_ant = 0.0
    total_aporte = 0.0
    total_novo = 0.0
    total_rec = 0.0

    parsed_items = []

    for r in data_rows:
        if not r or not any(r):
            continue
        raw_name = r[0].strip()
        if not raw_name or raw_name.upper() in ["TOTAL", "SOMA", "ATIVOS"]:
            continue

        cat, ticker, full_name = categorize_asset(raw_name)

        rec_val = parse_numeric(r[1]) if len(r) > 1 else 0.0
        val_ant = parse_numeric(r[2]) if len(r) > 2 else 0.0
        unit_price = parse_numeric(r[4]) if len(r) > 4 else 0.0
        qtd_aporte = parse_numeric(r[5]) if len(r) > 5 else 0.0
        val_aporte = parse_numeric(r[6]) if len(r) > 6 else 0.0

        # Calcular quantidades
        if unit_price > 0:
            qtd_ant = round(val_ant / unit_price, 4)
            qtd_nova = round(qtd_ant + qtd_aporte, 4)
            val_novo = round(qtd_nova * unit_price, 2)
        else:
            qtd_ant = 1.0 if val_ant > 0 else 0.0
            qtd_nova = qtd_ant + (1.0 if val_aporte > 0 else 0.0)
            val_novo = round(val_ant + val_aporte, 2)

        total_ant += val_ant
        total_aporte += val_aporte
        total_novo += val_novo
        total_rec += rec_val

        status = "BUY" if qtd_aporte > 0 or val_aporte > 0 else "HOLD"

        parsed_items.append({
            "category": cat,
            "ticker": ticker,
            "name": full_name,
            "qtd_ant": qtd_ant,
            "price": unit_price,
            "val_ant": val_ant,
            "rec_val": rec_val,
            "qtd_aporte": qtd_aporte,
            "val_aporte": val_aporte,
            "qtd_nova": qtd_nova,
            "val_novo": val_novo,
            "status": status,
        })

    # Calcular percentuais
    for item in parsed_items:
        meta_pct = (item["rec_val"] / total_rec * 100) if total_rec > 0 else 0.0
        real_novo_pct = (item["val_novo"] / total_novo * 100) if total_novo > 0 else 0.0

        new_tab_rows.append([
            item["category"],
            item["ticker"],
            item["name"],
            item["qtd_ant"],
            item["price"],
            item["val_ant"],
            f"{meta_pct:.2f}%",
            item["qtd_aporte"],
            item["val_aporte"],
            item["qtd_nova"],
            item["val_novo"],
            f"{real_novo_pct:.2f}%",
            item["status"],
        ])

    # Ordenar por categoria: Ações, FIIs, Renda Fixa, Alternativos
    cat_order = {"Ações": 1, "FIIs": 2, "Renda Fixa": 3, "Alternativos": 4, "Outros": 5}
    new_tab_rows.sort(key=lambda r: (cat_order.get(r[0], 99), r[1]))

    # Linha de Totais
    total_row = [
        "TOTAL",
        "",
        "",
        "",
        "",
        round(total_ant, 2),
        "100.00%",
        "",
        round(total_aporte, 2),
        "",
        round(total_novo, 2),
        "100.00%",
        "",
    ]
    new_tab_rows.append(total_row)

    # 3. Criar nova aba 'Out_26'
    target_title = "Out_26"
    existing_ws = {w.title: w for w in sh.worksheets()}
    if target_title in existing_ws:
        ws_target = existing_ws[target_title]
        ws_target.clear()
    else:
        template_ws = existing_ws.get("_TEMPLATE")
        if template_ws:
            ws_target = sh.duplicate_sheet(source_sheet_id=template_ws.id, new_sheet_name=target_title)
            try:
                ws_target.batch_clear(["A2:M1000"])
            except Exception:
                pass
        else:
            ws_target = sh.add_worksheet(title=target_title, rows=len(new_tab_rows) + 10, cols=15)

    headers = [col["header"] for col in client.template_config["monthly_template"]["columns"]]
    ws_target.update(range_name="A1:M1", values=[headers])
    ws_target.update(range_name=f"A2:M{len(new_tab_rows) + 1}", values=new_tab_rows)
    print(f"Aba '{target_title}' criada com sucesso! Linhas escritas: {len(new_tab_rows)}")

    # 4. Gravar registro em 'Evolução Patrimonial'
    # Calcular saldos por categoria
    equity = sum(item["val_novo"] for item in parsed_items if item["category"] == "Ações")
    fii = sum(item["val_novo"] for item in parsed_items if item["category"] == "FIIs")
    rf = sum(item["val_novo"] for item in parsed_items if item["category"] == "Renda Fixa")
    alt = sum(item["val_novo"] for item in parsed_items if item["category"] == "Alternativos")

    from app.schemas import EvolutionRecord
    evo_rec = EvolutionRecord(
        month_year="Out_26",
        execution_date="2026-10-31",
        previous_total=round(patrimonio_ant or total_ant, 2),
        new_investment=round(aporte_topo or total_aporte, 2),
        new_total=round(patrimonio_pos or total_novo, 2),
        market_delta=round((patrimonio_pos or total_novo) - ((patrimonio_ant or total_ant) + (aporte_topo or total_aporte)), 2),
        monthly_return_pct=0.0,
        equity_total=round(equity, 2),
        real_estate_total=round(fii, 2),
        fixed_income_total=round(rf, 2),
        alternatives_total=round(alt, 2),
    )
    client.append_evolution_record(evo_rec)
    print("Evolução Patrimonial atualizada com sucesso para 'Out_26'!")


if __name__ == "__main__":
    run_migration()

