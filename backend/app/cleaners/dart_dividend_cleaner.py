from datetime import datetime
import pandas as pd

DIVIDEND_COLUMNS = {
    "주당액면가액(원)": "par_value",
    "(연결)당기순이익(백만원)": "consolidated_net_income_million",
    "(별도)당기순이익(백만원)": "separate_net_income_million",
    "(연결)주당순이익(원)": "eps",
    "현금배당금총액(백만원)": "cash_dividend_total_million",
    "주식배당금총액(백만원)": "stock_dividend_total_million",
    "(연결)현금배당성향(%)": "cash_dividend_payout_ratio",
    "현금배당수익률(%)": "cash_dividend_yield",
    "주식배당수익률(%)": "stock_dividend_yield",
    "주당 현금배당금(원)": "cash_dividend_per_share",
    "주당 주식배당(주)": "stock_dividend_per_share",
}

PERIOD_COLUMNS = [
    ("thstrm", 0),
    ("frmtrm", -1),
    ("lwfr", -2),
]

BASE_COLUMNS = [
    "rcept_no",
    "corp_cls",
    "corp_code",
    "corp_name",
    "stock_knd",
    "fiscal_year",
    "settlement_date",
]

OUTPUT_COLUMNS = [
    *BASE_COLUMNS,
    "par_value",
    "consolidated_net_income_million",
    "separate_net_income_million",
    "eps",
    "cash_dividend_total_million",
    "stock_dividend_total_million",
    "cash_dividend_payout_ratio",
    "cash_dividend_yield",
    "stock_dividend_yield",
    "cash_dividend_per_share",
    "stock_dividend_per_share",
    "cash_dividend_total",
    "consolidated_net_income",
    "cash_dividend_per_eps_ratio",
]

def clean_dividends(dataframe: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in dataframe.iterrows():
        metric_name = _to_text(row.get("se", ""))
        output_column = DIVIDEND_COLUMNS.get(metric_name)

        if output_column is None:
            continue

        settlement_date = _to_text(row.get("stlm_dt", ""))
        settlement_year = _extract_year(settlement_date)

        if settlement_year is None:
            continue

        for amount_column, year_offset in PERIOD_COLUMNS:
            fiscal_year = settlement_year + year_offset

            rows.append(
                {
                    "rcept_no": _to_text(row.get("rcept_no", "")),
                    "corp_cls": _to_text(row.get("corp_cls", "")),
                    "corp_code": _to_text(row.get("corp_code", "")),
                    "corp_name": _to_text(row.get("corp_name", "")),
                    "stock_knd": _to_text(row.get("stock_knd", "")),
                    "fiscal_year": fiscal_year,
                    "settlement_date": settlement_date,
                    "metric_column": output_column,
                    "amount": _to_float(row.get(amount_column, "")),
                }
            )

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    long_dataframe = pd.DataFrame(rows)
    wide = (
        long_dataframe.pivot_table(
            index=BASE_COLUMNS,
            columns="metric_column",
            values="amount",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    for column in DIVIDEND_COLUMNS.values():
        if column not in wide.columns:
            wide[column] = pd.NA

    wide["cash_dividend_total"] = wide["cash_dividend_total_million"] * 1_000_000
    wide["consolidated_net_income"] = (
        wide["consolidated_net_income_million"] * 1_000_000
    )
    wide["cash_dividend_per_eps_ratio"] = _safe_ratio_column(
        wide["cash_dividend_per_share"],
        wide["eps"],
    )

    return wide[OUTPUT_COLUMNS].sort_values(["corp_code", "fiscal_year", "stock_knd"])

def _extract_year(value: str) -> int | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").year
    except ValueError:
        return None

def _safe_ratio_column(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    ratio = numerator / denominator * 100
    ratio = ratio.where(denominator.notna() & (denominator != 0))
    return ratio.round(2)

def _to_float(value: object) -> float | pd.NA:
    text = _to_text(value)
    normalized = (
        text.replace(",", "")
        .replace("%", "")
        .replace("(", "-")
        .replace(")", "")
        .replace(" ", "")
    )
    if normalized in {"", "-", "nan"}:
        return pd.NA
    try:
        return float(normalized)
    except ValueError:
        return pd.NA

def _to_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()
