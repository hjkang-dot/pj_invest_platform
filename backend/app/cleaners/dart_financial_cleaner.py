import re
import pandas as pd

ACCOUNT_COLUMNS = {
    "유동자산": "current_assets",
    "비유동자산": "non_current_assets",
    "자산총계": "total_assets",
    "유동부채": "current_liabilities",
    "비유동부채": "non_current_liabilities",
    "부채총계": "total_liabilities",
    "자본총계": "total_equity",
    "매출액": "revenue",
    "수익(매출액)": "revenue",
    "영업수익": "revenue",
    "영업이익": "operating_income",
    "영업이익(손실)": "operating_income",
    "당기순이익": "net_income",
    "당기순이익(손실)": "net_income",
    "반기순이익": "net_income",
    "반기순이익(손실)": "net_income",
    "분기순이익": "net_income",
    "분기순이익(손실)": "net_income",
    "당기순이익(손실)(지배지분)": "net_income",
    "당기순이익(지배지분)": "net_income",
    "이자수익": "interest_income",
}

PERIOD_COLUMNS = [
    ("thstrm_dt", "thstrm_amount"),
    ("frmtrm_dt", "frmtrm_amount"),
    ("bfefrmtrm_dt", "bfefrmtrm_amount"),
]

BASE_COLUMNS = [
    "rcept_no",
    "reprt_code",
    "bsns_year",
    "corp_code",
    "stock_code",
    "fs_div",
    "fs_nm",
    "currency",
    "fiscal_period",
]

OUTPUT_COLUMNS = [
    *BASE_COLUMNS,
    "current_assets",
    "non_current_assets",
    "total_assets",
    "current_liabilities",
    "non_current_liabilities",
    "total_liabilities",
    "total_equity",
    "revenue",
    "operating_income",
    "net_income",
    "debt_ratio",
    "current_ratio",
    "equity_ratio",
    "operating_margin",
    "net_margin",
]

def clean_financial_statement(dataframe: pd.DataFrame) -> pd.DataFrame:
    # Filter for Consolidated Financial Statements (CFS)
    cfs = dataframe[dataframe["fs_div"].astype(str).str.strip() == "CFS"].copy()
    
    # Fallback to Separate Financial Statements (OFS) if CFS is empty
    if cfs.empty:
        cfs = dataframe[dataframe["fs_div"].astype(str).str.strip() == "OFS"].copy()
        
    rows = []

    for _, row in cfs.iterrows():
        account_name = _to_text(row.get("account_nm", ""))
        output_column = ACCOUNT_COLUMNS.get(account_name)

        if output_column is None:
            continue

        for date_column, amount_column in PERIOD_COLUMNS:
            fiscal_period = _format_fiscal_period(row.get(date_column, ""))

            if not fiscal_period:
                continue

            rows.append(
                {
                    "rcept_no": _to_text(row.get("rcept_no", "")),
                    "reprt_code": _to_text(row.get("reprt_code", "")),
                    "bsns_year": _to_text(row.get("bsns_year", "")),
                    "corp_code": _to_text(row.get("corp_code", "")).zfill(8),
                    "stock_code": _to_text(row.get("stock_code", "")).zfill(6),
                    "fs_div": _to_text(row.get("fs_div", "")),
                    "fs_nm": _to_text(row.get("fs_nm", "")),
                    "currency": _to_text(row.get("currency", "")),
                    "fiscal_period": fiscal_period,
                    "account_column": output_column,
                    "amount": _to_int(row.get(amount_column, "")),
                }
            )

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    long_dataframe = pd.DataFrame(rows)
    wide = (
        long_dataframe.pivot_table(
            index=BASE_COLUMNS,
            columns="account_column",
            values="amount",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    for column in ACCOUNT_COLUMNS.values():
        if column not in wide.columns:
            wide[column] = pd.NA

    # Financial / Holding sectors fallback for revenue
    if "revenue" in wide.columns and "interest_income" in wide.columns:
        wide["revenue"] = wide["revenue"].fillna(wide["interest_income"])

    wide["debt_ratio"] = _safe_ratio_column(
        wide["total_liabilities"],
        wide["total_equity"],
    )
    wide["current_ratio"] = _safe_ratio_column(
        wide["current_assets"],
        wide["current_liabilities"],
    )
    wide["equity_ratio"] = _safe_ratio_column(
        wide["total_equity"],
        wide["total_assets"],
    )
    wide["operating_margin"] = _safe_ratio_column(
        wide["operating_income"],
        wide["revenue"],
    )
    wide["net_margin"] = _safe_ratio_column(
        wide["net_income"],
        wide["revenue"],
    )

    return wide[OUTPUT_COLUMNS].sort_values(["stock_code", "fiscal_period"])

def _format_fiscal_period(value: object) -> str:
    matches = re.findall(r"\d{4}\.\d{2}", str(value))
    if not matches:
        return ""
    return matches[-1]

def _safe_ratio_column(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    ratio = numerator / denominator * 100
    ratio = ratio.where(denominator.notna() & (denominator != 0))
    return ratio.round(2)

def _to_int(value: object) -> int | None:
    text = _to_text(value)
    normalized = (
        text.replace(",", "")
        .replace("(", "-")
        .replace(")", "")
        .replace(" ", "")
    )
    if normalized in {"", "-"}:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None

def _to_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()
