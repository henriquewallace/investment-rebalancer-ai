import json
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app.clients.sheets_db import SheetsDbClient
from app.schemas import AssetRule, ResolveBatchResponse, ResolveResult


def normalize_asset_key(raw: str) -> str:
    """Normalize string by removing accents, extra spaces and converting to uppercase."""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKD", str(raw)).encode("ASCII", "ignore").decode("ASCII")
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def _find_config_file(filename: str) -> Optional[str]:
    candidates = [
        os.getenv(f"CONFIG_{filename.upper().replace('.', '_')}"),
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", filename)
        ),
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "config", filename)
        ),
        f"/app/config/{filename}",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def load_seed_rules() -> List[AssetRule]:
    """Load initial seed rules from config/asset_mapping.json and config/alias_map.json."""
    mapping_path = _find_config_file("asset_mapping.json")
    alias_path = _find_config_file("alias_map.json")

    raw_mapping: Dict[str, Any] = {}
    raw_aliases: Dict[str, str] = {}

    if mapping_path:
        with open(mapping_path, "r", encoding="utf-8") as f:
            raw_mapping = json.load(f)

    if alias_path:
        with open(alias_path, "r", encoding="utf-8") as f:
            raw_aliases = json.load(f)

    # Group aliases from alias_map.json by target ticker
    extra_aliases_by_ticker: Dict[str, List[str]] = {}
    for alias_str, target_ticker in raw_aliases.items():
        t_key = target_ticker.strip().upper()
        extra_aliases_by_ticker.setdefault(t_key, []).append(alias_str.strip())

    rules: List[AssetRule] = []
    for ticker_key, data in raw_mapping.items():
        t_clean = ticker_key.strip().upper()
        aliases = list(data.get("aliases", []))
        for extra in extra_aliases_by_ticker.get(t_clean, []):
            if extra.upper() not in {a.upper() for a in aliases}:
                aliases.append(extra)

        is_frac = data.get("is_fractional", data.get("fractional", False))
        a_type = data.get("asset_type", data.get("type", "STOCK"))

        rules.append(
            AssetRule(
                ticker=t_clean,
                name=data.get("name", t_clean),
                category=data.get("category", "Outros"),
                asset_type=str(a_type).upper(),
                is_fractional=bool(is_frac),
                min_order_value=float(data.get("min_order_value", 0.0)),
                lot_step=float(data.get("lot_step", 1.0)),
                price_source=data.get("price_source", "brapi"),
                aliases=aliases,
                active=bool(data.get("active", True)),
            )
        )

    return rules


class AssetResolver:
    """Service to resolve asset names/tickers and retrieve trading constraints."""

    def __init__(
        self,
        sheets_client: Optional[SheetsDbClient] = None,
        use_sheets: bool = True,
    ):
        self.sheets_client = sheets_client or SheetsDbClient()
        self.use_sheets = use_sheets
        self._cached_rules: Optional[List[AssetRule]] = None
        self._cached_source: str = "seed_json"

    def invalidate_cache(self) -> None:
        self._cached_rules = None

    def get_rules(self, force_refresh: bool = False) -> Tuple[str, List[AssetRule]]:
        """Retrieve AssetRule catalog from Google Sheets (auto-seeding if empty) or JSON fallback."""
        if self._cached_rules is not None and not force_refresh:
            return self._cached_source, self._cached_rules

        if (
            self.use_sheets
            and self.sheets_client.is_credentials_present()
            and bool(self.sheets_client.spreadsheet_id)
        ):
            try:
                rows = self.sheets_client.get_asset_mapping_rows()
                if not rows:
                    seed = load_seed_rules()
                    if seed:
                        self.sheets_client.seed_asset_mapping_sheet(seed)
                        rows = self.sheets_client.get_asset_mapping_rows() or seed
                self._cached_rules = rows
                self._cached_source = "sheets"
                return self._cached_source, self._cached_rules
            except Exception:
                pass

        self._cached_rules = load_seed_rules()
        self._cached_source = "seed_json"
        return self._cached_source, self._cached_rules

    def _build_lookup_index(self, rules: List[AssetRule]) -> Dict[str, AssetRule]:
        """Build normalized lookup dictionary mapping ticker, name, and aliases to AssetRule."""
        index: Dict[str, AssetRule] = {}
        for rule in rules:
            if not rule.active:
                continue
            for candidate in [rule.ticker, rule.name] + list(rule.aliases):
                norm_key = normalize_asset_key(candidate)
                if norm_key and norm_key not in index:
                    index[norm_key] = rule
            # Guarantee canonical ticker always takes priority
            t_norm = normalize_asset_key(rule.ticker)
            if t_norm:
                index[t_norm] = rule
        return index

    def resolve(
        self, raw_name: str, rules: Optional[List[AssetRule]] = None
    ) -> ResolveResult:
        """Resolve a single raw asset name or ticker into a canonical AssetRule."""
        if rules is None:
            _, rules = self.get_rules()

        index = self._build_lookup_index(rules)
        norm_query = normalize_asset_key(raw_name)

        if norm_query in index:
            matched_rule = index[norm_query]
            return ResolveResult(
                raw_name=raw_name,
                ticker=matched_rule.ticker,
                mapped=True,
                rule=matched_rule,
            )

        return ResolveResult(
            raw_name=raw_name,
            ticker=None,
            mapped=False,
            rule=None,
        )

    def resolve_batch(
        self, names: List[str], rules: Optional[List[AssetRule]] = None
    ) -> ResolveBatchResponse:
        """Resolve a list of raw names and determine if simulation can proceed."""
        if rules is None:
            _, rules = self.get_rules()

        mapped_list: List[ResolveResult] = []
        unmapped_list: List[str] = []

        for raw in names:
            if not raw or not str(raw).strip():
                continue
            res = self.resolve(raw, rules=rules)
            if res.mapped:
                mapped_list.append(res)
            else:
                if raw.strip() not in unmapped_list:
                    unmapped_list.append(raw.strip())

        return ResolveBatchResponse(
            mapped=mapped_list,
            unmapped=unmapped_list,
            can_simulate=(len(unmapped_list) == 0),
        )

    def upsert_rule(self, rule: AssetRule) -> AssetRule:
        """Save or update an AssetRule in Google Sheets and refresh cache."""
        saved = self.sheets_client.upsert_asset_rule(rule)
        self.invalidate_cache()
        return saved

    def add_alias(self, ticker: str, alias: str) -> AssetRule:
        """Add an alias to an existing ticker in Google Sheets and refresh cache."""
        updated = self.sheets_client.add_asset_alias(ticker, alias)
        self.invalidate_cache()
        return updated

