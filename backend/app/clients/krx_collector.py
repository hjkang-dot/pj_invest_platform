from typing import Literal
from datetime import date
import requests
import pandas as pd
from app.core.config import Config

Market = Literal["KOSPI", "KOSDAQ"]

SUPPORTED_MARKETS: set[str] = {"KOSPI", "KOSDAQ"}
KRX_BASE_URL = "http://data-dbg.krx.co.kr"

MARKET_API_IDS: dict[str, str] = {
    "KOSPI": "stk_isu_base_info",
    "KOSDAQ": "ksq_isu_base_info",
}

MARKET_DAILY_PRICE_API_IDS: dict[str, str] = {
    "KOSPI": "stk_bydd_trd",
    "KOSDAQ": "ksq_bydd_trd",
}

KRX_STOCK_API_PATH_PREFIX = "/svc/apis/sto"

def validate_market(market: str) -> Market:
    normalized_market = market.upper()
    if normalized_market not in SUPPORTED_MARKETS:
        msg = f"Unsupported market: {market}"
        raise ValueError(msg)
    return normalized_market  # type: ignore[return-value]

def format_base_date(base_date: date | str) -> str:
    if isinstance(base_date, date):
        return base_date.strftime("%Y%m%d")
    return base_date

def build_auth_headers() -> dict[str, str]:
    if not Config.KRX_API_KEY:
        msg = "KRX_API_KEY is not configured"
        raise ValueError(msg)
    return {"AUTH_KEY": Config.KRX_API_KEY}

def build_listed_stocks_url(market: str) -> str:
    validated_market = validate_market(market)
    api_id = MARKET_API_IDS[validated_market]
    return f"{KRX_BASE_URL}{KRX_STOCK_API_PATH_PREFIX}/{api_id}"

def fetch_listed_stocks(market: Market, base_date: date | str) -> pd.DataFrame:
    validated_market = validate_market(market)
    url = build_listed_stocks_url(validated_market)
    headers = build_auth_headers()
    params = {"basDd": format_base_date(base_date)}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    payload = response.json()
    rows = payload.get("OutBlock_1", [])
    return pd.DataFrame(rows)

def build_daily_prices_url(market: str) -> str:
    validated_market = validate_market(market)
    api_id = MARKET_DAILY_PRICE_API_IDS[validated_market]
    return f"{KRX_BASE_URL}{KRX_STOCK_API_PATH_PREFIX}/{api_id}"

def fetch_daily_prices(market: Market, base_date: date | str) -> pd.DataFrame:
    validated_market = validate_market(market)
    url = build_daily_prices_url(validated_market)
    headers = build_auth_headers()
    params = {"basDd": format_base_date(base_date)}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    payload = response.json()
    rows = payload.get("OutBlock_1", [])
    return pd.DataFrame(rows)
