from app.clients.sheets_db import SheetsDbClient
from app.services.asset_resolver import load_seed_rules


def run_seed():
    client = SheetsDbClient()
    sh = client.get_spreadsheet()
    print(f"Conectado à planilha: '{sh.title}'")

    # Garantir que aba Mapeamento_Ativos existe
    tpl_res = client.ensure_template_sheet()
    print("Status das abas de template:", tpl_res)

    # Carregar catálogo seed e popular aba
    seed_rules = load_seed_rules()
    seed_res = client.seed_asset_mapping_sheet(seed_rules)
    print(f"Aba 'Mapeamento_Ativos' populada com sucesso: {seed_res}")


if __name__ == "__main__":
    run_seed()

