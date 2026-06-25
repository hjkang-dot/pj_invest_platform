from datetime import date
import pandas as pd

OUTPUT_COLUMNS = [
    "stock_code",
    "stock_name",
    "market",
    "close_price",
    "market_cap",
    "net_income",
    "total_equity",
    "debt_ratio",
    "current_ratio",
    "roe",
    "per",
    "pbr",
    "dividend_yield",
    "cash_dividend_per_share",
    "payout_ratio",
    "dividend_years",
    "dividend_decrease_count",
    "revenue_growth",
    "operating_income_growth",
    "eps_growth",
    "financial_stability_score",
    "growth_score",
    "undervaluation_score",
    "shareholder_return_score",
    "market_governance_score",
    "total_score",
    "is_candidate",
]

def screen_undervalued_dividend_stocks(
    financial_statements: pd.DataFrame,
    dividends: pd.DataFrame,
    daily_prices: pd.DataFrame,
    stocks: pd.DataFrame,
    *,
    minimum_total_score: float = 60.0,
    as_of_year: int | None = None,
) -> pd.DataFrame:
    """Score stocks for an undervalued dividend strategy."""
    as_of_year = as_of_year or date.today().year

    # Remove duplicate financial statements (keep consolidate CFS first, latest source report)
    if "fiscal_period" in financial_statements.columns:
        financial_statements = financial_statements.copy()
        financial_statements["fiscal_period_sort"] = pd.to_numeric(
            financial_statements["fiscal_period"].astype(str).str.replace(".", "", regex=False),
            errors="coerce",
        )
        if "fs_div" in financial_statements.columns:
            financial_statements["fs_priority"] = financial_statements["fs_div"].map({"CFS": 1, "OFS": 2}).fillna(3)
            financial_statements = financial_statements.sort_values(
                ["corp_code", "fiscal_period_sort", "fs_priority"],
                ascending=[True, True, True]
            )
        else:
            financial_statements = financial_statements.sort_values(["corp_code", "fiscal_period_sort"])
            
        financial_statements = financial_statements.drop_duplicates(
            subset=["corp_code", "bsns_year"],
            keep="last"
        ).drop(columns=["fiscal_period_sort", "fs_priority"], errors="ignore")

    # Remove duplicate dividend data (prioritize rows with non-NaN eps and cash_dividend_per_share)
    if not dividends.empty:
        dividends = dividends.copy()
        dividends["has_dps"] = pd.to_numeric(dividends["cash_dividend_per_share"], errors="coerce").fillna(0) > 0
        dividends["has_eps"] = pd.to_numeric(dividends["eps"], errors="coerce").fillna(0) > 0
        dividends["fiscal_year_num"] = pd.to_numeric(dividends["fiscal_year"], errors="coerce").fillna(0)
        
        dividends = dividends.sort_values(
            ["corp_code", "fiscal_year_num", "has_dps", "has_eps"],
            ascending=[True, True, False, False]
        )
        dividends = dividends.drop_duplicates(
            subset=["corp_code", "fiscal_year"],
            keep="first"
        ).drop(columns=["has_dps", "has_eps", "fiscal_year_num"], errors="ignore")

    # 1. Get latest financial year for each company (Filter removed)
    latest_financials = _latest_financials(financial_statements).copy()
    
    # 2. Extract previous year financials to calculate growth rates
    prev_fin = financial_statements[["corp_code", "bsns_year", "revenue", "operating_income"]].copy()
    prev_fin = prev_fin.rename(
        columns={
            "bsns_year": "prev_bsns_year",
            "revenue": "prev_revenue",
            "operating_income": "prev_operating_income",
        }
    )
    
    # Extract previous year dividends to calculate EPS growth rate
    if "eps" in dividends.columns:
        prev_div = dividends[["corp_code", "fiscal_year", "eps"]].copy()
        prev_div["prev_bsns_year"] = pd.to_numeric(prev_div["fiscal_year"], errors="coerce")
        prev_div = prev_div.rename(columns={"eps": "prev_eps"}).drop(columns=["fiscal_year"])
    else:
        prev_div = pd.DataFrame(columns=["corp_code", "prev_bsns_year", "prev_eps"])
    
    # Map previous business year (bsns_year - 1)
    latest_financials["prev_bsns_year"] = latest_financials["bsns_year"] - 1
    
    # Merge previous year details
    latest_financials = latest_financials.merge(
        prev_fin,
        on=["corp_code", "prev_bsns_year"],
        how="left"
    ).merge(
        prev_div,
        on=["corp_code", "prev_bsns_year"],
        how="left"
    )
    
    latest_dividends = _latest_dividends(dividends)
    dividend_years = _dividend_years(dividends)
    dividend_decrease_counts = _dividend_decrease_counts(dividends)

    screened = (
        latest_financials.merge(latest_dividends, on="corp_code", how="left")
        .merge(dividend_years, on="corp_code", how="left")
        .merge(dividend_decrease_counts, on="corp_code", how="left")
        .merge(daily_prices, on="stock_code", how="inner", suffixes=("", "_price"))
        .merge(stocks[["stock_code", "listed_date", "sector"]], on="stock_code", how="left")
    )

    screened["stock_name"] = screened["stock_name"].fillna(screened["corp_name"])
    screened["dividend_years"] = screened["dividend_years"].fillna(0).astype("int64")
    screened["dividend_decrease_count"] = (
        screened["dividend_decrease_count"].fillna(0).astype("int64")
    )

    # Calculate metrics
    screened["roe"] = _safe_ratio(screened["net_income"], screened["total_equity"]) * 100
    
    # Calculate current ratio explicitly from assets and liabilities (as current_ratio may be NaN in source)
    calculated_current_ratio = _safe_ratio(screened["current_assets"], screened["current_liabilities"]) * 100
    screened["current_ratio"] = screened["current_ratio"].fillna(calculated_current_ratio)
    
    # Calculate growth metrics
    screened["revenue_growth"] = _safe_ratio(
        screened["revenue"] - screened["prev_revenue"],
        screened["prev_revenue"]
    ) * 100
    screened["operating_income_growth"] = _safe_ratio(
        screened["operating_income"] - screened["prev_operating_income"],
        screened["prev_operating_income"]
    ) * 100
    screened["eps_growth"] = _safe_ratio(
        screened["eps"] - screened["prev_eps"],
        screened["prev_eps"]
    ) * 100

    screened["per"] = _safe_ratio(screened["market_cap"], screened["net_income"])
    screened["pbr"] = _safe_ratio(screened["market_cap"], screened["total_equity"])
    screened["dividend_yield"] = screened["cash_dividend_yield"]
    calculated_yield = _safe_ratio(
        screened["cash_dividend_per_share"],
        screened["close_price"],
    ) * 100
    screened["dividend_yield"] = screened["dividend_yield"].fillna(calculated_yield)
    screened["payout_ratio"] = screened["cash_dividend_payout_ratio"].fillna(
        screened["cash_dividend_per_eps_ratio"],
    )
    screened["listed_years"] = as_of_year - pd.to_numeric(
        screened["listed_date"].astype(str).str[:4],
        errors="coerce",
    )

    # Score applying
    screened["financial_stability_score"] = screened.apply(
        _score_financial_stability,
        axis=1,
    )
    screened["growth_score"] = screened.apply(
        _score_growth,
        axis=1,
    )
    screened["undervaluation_score"] = screened.apply(_score_undervaluation, axis=1)
    screened["shareholder_return_score"] = screened.apply(
        _score_shareholder_return,
        axis=1,
    )
    screened["market_governance_score"] = screened.apply(
        _score_market_governance,
        axis=1,
    )

    screened["total_score"] = (
        screened["financial_stability_score"]
        + screened["growth_score"]
        + screened["undervaluation_score"]
        + screened["shareholder_return_score"]
        + screened["market_governance_score"]
    ).round(2)
    
    screened["is_candidate"] = (
        (screened["total_score"] >= minimum_total_score)
        & (screened["net_income"] > 0)
        & (screened["total_equity"] > 0)
        & (screened["market_cap"] > 0)
        & (screened["cash_dividend_per_share"] > 0)
    )

    return (
        screened[OUTPUT_COLUMNS]
        .sort_values(
            ["is_candidate", "total_score", "dividend_yield", "market_cap"],
            ascending=[False, False, False, False],
        )
        .reset_index(drop=True)
    )

def _latest_financials(financial_statements: pd.DataFrame) -> pd.DataFrame:
    financials = financial_statements.copy()
    financials["fiscal_period_sort"] = pd.to_numeric(
        financials["fiscal_period"].astype(str).str.replace(".", "", regex=False),
        errors="coerce",
    )

    return (
        financials.sort_values(["stock_code", "fiscal_period_sort"])
        .groupby("stock_code", as_index=False)
        .tail(1)
        .drop(columns=["fiscal_period_sort"])
    )

def _latest_dividends(dividends: pd.DataFrame) -> pd.DataFrame:
    if dividends.empty:
        return pd.DataFrame(columns=["corp_code", "cash_dividend_yield", "cash_dividend_per_share", "cash_dividend_payout_ratio", "cash_dividend_per_eps_ratio"])
    dividend_data = dividends.copy()
    dividend_data["fiscal_year"] = pd.to_numeric(
        dividend_data["fiscal_year"],
        errors="coerce",
    )
    if "stock_code" in dividend_data.columns:
        dividend_data = dividend_data.drop(columns=["stock_code"])

    return (
        dividend_data.sort_values(["corp_code", "fiscal_year"])
        .groupby("corp_code", as_index=False)
        .tail(1)
    )

def _dividend_years(dividends: pd.DataFrame) -> pd.DataFrame:
    if dividends.empty:
        return pd.DataFrame(columns=["corp_code", "dividend_years"])
    dividend_data = dividends.copy()
    if "stock_code" in dividend_data.columns:
        dividend_data = dividend_data.drop(columns=["stock_code"])
    dividend_data["has_cash_dividend"] = (
        pd.to_numeric(dividend_data["cash_dividend_per_share"], errors="coerce").fillna(0)
        > 0
    ) | (
        pd.to_numeric(dividend_data["cash_dividend_total"], errors="coerce").fillna(0) > 0
    )

    return (
        dividend_data[dividend_data["has_cash_dividend"]]
        .groupby("corp_code", as_index=False)["fiscal_year"]
        .nunique()
        .rename(columns={"fiscal_year": "dividend_years"})
    )

def _dividend_decrease_counts(dividends: pd.DataFrame) -> pd.DataFrame:
    if dividends.empty:
        return pd.DataFrame(columns=["corp_code", "dividend_decrease_count"])
    dividend_data = dividends.copy()
    if "stock_code" in dividend_data.columns:
        dividend_data = dividend_data.drop(columns=["stock_code"])

    dividend_data["fiscal_year"] = pd.to_numeric(
        dividend_data["fiscal_year"],
        errors="coerce",
    )
    dividend_data["cash_dividend_per_share"] = pd.to_numeric(
        dividend_data["cash_dividend_per_share"],
        errors="coerce",
    ).fillna(0)

    rows = []
    for corp_code, group in dividend_data.groupby("corp_code"):
        dividend_history = group.sort_values("fiscal_year")["cash_dividend_per_share"]
        decrease_count = int((dividend_history.diff().dropna() < 0).sum())
        rows.append(
            {
                "corp_code": corp_code,
                "dividend_decrease_count": decrease_count,
            }
        )

    return pd.DataFrame(rows)

def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    ratio = numerator / denominator

    return ratio.where(denominator.notna() & (denominator > 0))

def _is_financial_sector(row: pd.Series) -> bool:
    # 1. Check sector column
    sector = row.get("sector")
    if not pd.isna(sector):
        s = str(sector)
        if not any(ex in s for ex in ["생명과학", "생명공학", "생명자원"]):
            for kw in ["금융", "은행", "보험", "증권", "카드"]:
                if kw in s:
                    return True

    # 2. Check stock_name / corp_name for financial keywords
    name = row.get("stock_name") or row.get("corp_name") or ""
    if name:
        name_str = str(name)
        if not any(ex in name_str for ex in ["생명과학", "생명공학", "생명자원"]):
            for kw in ["금융지주", "금융", "은행", "생명", "화재", "손해보험", "증권", "카드", "캐피탈"]:
                if kw in name_str:
                    return True

    # 3. Check accounting characteristics
    current_ratio = row.get("current_ratio")
    debt_ratio = row.get("debt_ratio")

    is_current_ratio_na = pd.isna(current_ratio) or current_ratio is None or float(current_ratio) <= 0
    if is_current_ratio_na and not pd.isna(debt_ratio) and debt_ratio is not None:
        try:
            if float(debt_ratio) > 300.0:
                return True
        except (ValueError, TypeError):
            pass

    return False

def _score_financial_stability(row: pd.Series) -> int:
    if _is_financial_sector(row):
        return 12

    score = 0
    score += _inverse_range_score(row["debt_ratio"], [(50, 8), (100, 6), (200, 4), (400, 2)])
    score += _range_score(row["current_ratio"], [(200, 7), (150, 5), (100, 3)], 0)

    return min(score, 15)

def _score_growth(row: pd.Series) -> int:
    score = 0
    score += _range_score(row["revenue_growth"], [(10, 5), (5, 4), (0, 2)], 0)
    score += _range_score(row["operating_income_growth"], [(15, 5), (5, 4), (0, 2)], 0)
    score += _range_score(row["eps_growth"], [(15, 5), (5, 4), (0, 2)], 0)

    return min(score, 15)

def _score_undervaluation(row: pd.Series) -> int:
    score = 0
    score += _inverse_range_score(row["per"], [(6, 15), (10, 12), (15, 8), (25, 4)])
    score += _inverse_range_score(row["pbr"], [(0.6, 15), (1.0, 12), (1.5, 8), (2.5, 4)])

    return min(score, 25)

def _score_shareholder_return(row: pd.Series) -> int:
    score = 0
    score += _payout_score(row["payout_ratio"])
    score += _range_score(row["dividend_years"], [(3, 15), (2, 10), (1, 5)], 0)
    score -= min(int(row["dividend_decrease_count"]) * 5, 15)

    return max(min(score, 25), 0)

def _score_market_governance(row: pd.Series) -> int:
    return 0

def _range_score(value: object, thresholds: list[tuple[float, int]], default: int) -> int:
    numeric_value = _to_float(value)

    if numeric_value is None:
        return default

    for threshold, score in thresholds:
        if numeric_value >= threshold:
            return score

    return default

def _inverse_range_score(value: object, thresholds: list[tuple[float, int]]) -> int:
    numeric_value = _to_float(value)

    if numeric_value is None or numeric_value <= 0:
        return 0

    for threshold, score in thresholds:
        if numeric_value <= threshold:
            return score

    return 0

def _payout_score(value: object) -> int:
    payout_ratio = _to_float(value)

    if payout_ratio is None or payout_ratio <= 0:
        return 0
    if 20 <= payout_ratio <= 60:
        return 15
    if 10 <= payout_ratio <= 80:
        return 10

    return 5

def _to_float(value: object) -> float | None:
    if pd.isna(value):
        return None

    return float(value)
