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

def screen_opportunity_growth_stocks(
    financial_statements: pd.DataFrame,
    dividends: pd.DataFrame,
    daily_prices: pd.DataFrame,
    stocks: pd.DataFrame,
    *,
    minimum_total_score: float = 60.0,
    as_of_year: int | None = None,
) -> pd.DataFrame:
    """Score stocks for an opportunity growth strategy (GARP/PEG & high ROE focus)."""
    as_of_year = as_of_year or date.today().year

    # Remove duplicate financial statements
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

    # Remove duplicate dividends
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

    # 1. Get latest financials
    latest_financials = _latest_financials(financial_statements).copy()
    
    # 2. Extract previous year financials for growth calculation
    prev_fin = financial_statements[["corp_code", "bsns_year", "revenue", "operating_income"]].copy()
    prev_fin = prev_fin.rename(
        columns={
            "bsns_year": "prev_bsns_year",
            "revenue": "prev_revenue",
            "operating_income": "prev_operating_income",
        }
    )
    
    if "eps" in dividends.columns:
        prev_div = dividends[["corp_code", "fiscal_year", "eps"]].copy()
        prev_div["prev_bsns_year"] = pd.to_numeric(prev_div["fiscal_year"], errors="coerce")
        prev_div = prev_div.rename(columns={"eps": "prev_eps"}).drop(columns=["fiscal_year"])
    else:
        prev_div = pd.DataFrame(columns=["corp_code", "prev_bsns_year", "prev_eps"])
    
    latest_financials["prev_bsns_year"] = latest_financials["bsns_year"] - 1
    
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

    if screened.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    screened["stock_name"] = screened["stock_name"].fillna(screened["corp_name"])
    screened["dividend_years"] = screened["dividend_years"].fillna(0).astype("int64")
    screened["dividend_decrease_count"] = (
        screened["dividend_decrease_count"].fillna(0).astype("int64")
    )

    # Calculate metrics
    screened["roe"] = _safe_ratio(screened["net_income"], screened["total_equity"]) * 100
    calculated_current_ratio = _safe_ratio(screened["current_assets"], screened["current_liabilities"]) * 100
    screened["current_ratio"] = screened["current_ratio"].fillna(calculated_current_ratio)
    
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

    # Apply Growth Strategy Scores
    screened["financial_stability_score"] = screened.apply(_score_financial_stability, axis=1) # Max 15
    screened["growth_score"] = screened.apply(_score_growth, axis=1)                          # Max 35
    screened["undervaluation_score"] = screened.apply(_score_efficiency, axis=1)              # Max 25 (Efficiency ROE/OM)
    screened["shareholder_return_score"] = screened.apply(_score_reinvestment, axis=1)        # Max 15 (Growth Reinvestment)
    screened["market_governance_score"] = screened.apply(_score_valuation_peg, axis=1)        # Max 10 (GARP PEG ratio)

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
        & (screened["revenue_growth"] > 5.0)
        & (screened["roe"] >= 8.0)
        & (screened["per"] > 0)
        & (screened["per"] <= 30.0)
    )

    return (
        screened[OUTPUT_COLUMNS]
        .sort_values(
            ["is_candidate", "total_score", "revenue_growth", "market_cap"],
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

def _score_financial_stability(row: pd.Series) -> int:
    score = 0
    debt = row.get("debt_ratio")
    curr = row.get("current_ratio")
    
    # Debt ratio (Max 8)
    if pd.isna(debt):
        pass
    elif debt <= 100.0:
        score += 8
    elif debt <= 150.0:
        score += 5
    elif debt <= 250.0:
        score += 2
        
    # Current ratio (Max 7)
    if pd.isna(curr):
        pass
    elif curr >= 150.0:
        score += 7
    elif curr >= 100.0:
        score += 4
    elif curr >= 70.0:
        score += 2

    return min(score, 15)

def _score_growth(row: pd.Series) -> int:
    score = 0
    rev = row.get("revenue_growth")
    op = row.get("operating_income_growth")
    eps = row.get("eps_growth")

    # Revenue growth (Max 15)
    if pd.isna(rev):
        pass
    elif rev >= 30.0:
        score += 15
    elif rev >= 15.0:
        score += 10
    elif rev >= 5.0:
        score += 5
    elif rev >= 0.0:
        score += 2
        
    # Operating Income growth (Max 10)
    if pd.isna(op):
        pass
    elif op >= 40.0:
        score += 10
    elif op >= 20.0:
        score += 7
    elif op >= 5.0:
        score += 4
    elif op >= 0.0:
        score += 2

    # EPS growth (Max 10)
    if pd.isna(eps):
        pass
    elif eps >= 40.0:
        score += 10
    elif eps >= 20.0:
        score += 7
    elif eps >= 5.0:
        score += 4
    elif eps >= 0.0:
        score += 2

    return min(score, 35)

def _score_efficiency(row: pd.Series) -> int:
    score = 0
    roe = row.get("roe")
    
    # Calculate Operating Margin
    net_inc = pd.to_numeric(row.get("net_income"), errors="coerce")
    rev = pd.to_numeric(row.get("revenue"), errors="coerce")
    op_margin = (net_inc / rev * 100) if (rev and rev > 0 and net_inc) else 0

    # ROE (Max 15)
    if pd.isna(roe):
        pass
    elif roe >= 25.0:
        score += 15
    elif roe >= 15.0:
        score += 12
    elif roe >= 10.0:
        score += 8
    elif roe >= 5.0:
        score += 4

    # Operating Margin (Max 10)
    if op_margin >= 20.0:
        score += 10
    elif op_margin >= 10.0:
        score += 7
    elif op_margin >= 5.0:
        score += 4
    elif op_margin >= 2.0:
        score += 2

    return min(score, 25)

def _score_reinvestment(row: pd.Series) -> int:
    score = 0
    payout = row.get("payout_ratio")
    
    # We want lower payout ratio for high-growth reinvestment (Max 10)
    if pd.isna(payout) or payout <= 0:
        score += 10 # assumed full reinvestment
    elif payout <= 30.0:
        score += 10
    elif payout <= 50.0:
        score += 5
    elif payout <= 80.0:
        score += 2

    # Positive net income (Max 5)
    net_inc = row.get("net_income")
    if not pd.isna(net_inc) and net_inc > 0:
        score += 5

    return min(score, 15)

def _score_valuation_peg(row: pd.Series) -> int:
    score = 0
    per = row.get("per")
    eps_g = row.get("eps_growth")

    if pd.isna(per) or pd.isna(eps_g) or eps_g <= 0 or per <= 0:
        return 1

    peg = per / eps_g

    # PEG Ratio (Max 10)
    if peg <= 1.0:
        score += 10
    elif peg <= 1.5:
        score += 7
    elif peg <= 2.5:
        score += 4
    else:
        score += 1

    return min(score, 10)
