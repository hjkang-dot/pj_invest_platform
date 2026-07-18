import pandas as pd
import requests
import re
import time
from datetime import date
from app.strategies.opportunity_growth_strategy import screen_opportunity_growth_stocks, OUTPUT_COLUMNS

# Cache sectors in memory to avoid redundant web scraping requests during backtest/multiple months
_sector_cache = {}

def get_naver_sector_with_cache(stock_code: str) -> str:
    if stock_code in _sector_cache:
        return _sector_cache[stock_code]
        
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            match = re.search(r'type=upjong&no=\d+">([^<]+)</a>', res.text)
            if match:
                sector = match.group(1).strip()
                _sector_cache[stock_code] = sector
                # Short delay to prevent Naver IP ban
                time.sleep(0.03)
                return sector
    except Exception:
        pass
    _sector_cache[stock_code] = "기타"
    return "기타"

def _build_db_sector_map(stocks: pd.DataFrame) -> dict:
    """Build a sector lookup from the stocks DataFrame (DB sector column)."""
    sector_map = {}
    if "sector" in stocks.columns:
        for _, row in stocks.iterrows():
            code = str(row.get("stock_code", ""))
            sector = str(row.get("sector", "")).strip()
            if code and sector and sector not in ("", "nan", "None"):
                sector_map[code] = sector
    return sector_map

def get_sector(stock_code: str, db_sector_map: dict) -> str:
    """Get sector from DB first, fall back to Naver scraping if missing."""
    if stock_code in db_sector_map:
        sector = db_sector_map[stock_code]
        _sector_cache[stock_code] = sector
        return sector
    return get_naver_sector_with_cache(stock_code)

def screen_sector_diversified_growth_stocks(
    financial_statements: pd.DataFrame,
    dividends: pd.DataFrame,
    daily_prices: pd.DataFrame,
    stocks: pd.DataFrame,
    *,
    minimum_total_score: float = 60.0,
    as_of_year: int | None = None,
) -> pd.DataFrame:
    """Screen growth stocks ensuring each selected stock is from a unique industry sector."""
    # 1. Run the base opportunity growth screening
    base_df = screen_opportunity_growth_stocks(
        financial_statements=financial_statements,
        dividends=dividends,
        daily_prices=daily_prices,
        stocks=stocks,
        minimum_total_score=minimum_total_score,
        as_of_year=as_of_year
    )
    
    if base_df.empty:
        return base_df
        
    # 2. Get candidates sorted by score
    candidates = base_df[base_df["is_candidate"] == True].copy()
    if candidates.empty:
        base_df["is_candidate"] = False
        return base_df
        
    candidates = candidates.sort_values(
        by=["total_score", "revenue_growth", "market_cap"],
        ascending=[False, False, False]
    ).reset_index(drop=True)
    
    # 3. Build DB sector map to avoid unnecessary HTTP requests
    db_sector_map = _build_db_sector_map(stocks)
    
    # 4. Select at most 5 unique-sector stocks with score >= minimum_total_score
    selected_codes = []
    selected_sectors = set()
    
    # Process up to top 25 candidates to save on HTTP requests
    for _, row in candidates.head(25).iterrows():
        if len(selected_codes) >= 5:
            break
            
        code = row["stock_code"]
        score = row["total_score"]
        
        if score < minimum_total_score:
            break
            
        sector = get_sector(code, db_sector_map)
        if sector not in selected_sectors:
            selected_codes.append(code)
            selected_sectors.add(sector)
            
    # 5. Set is_candidate for only the selected codes
    base_df["is_candidate"] = base_df["stock_code"].isin(selected_codes)
    
    return (
        base_df
        .sort_values(
            ["is_candidate", "total_score", "revenue_growth", "market_cap"],
            ascending=[False, False, False, False],
        )
        .reset_index(drop=True)
    )

