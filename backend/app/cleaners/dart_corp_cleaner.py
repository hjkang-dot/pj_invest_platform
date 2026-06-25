import pandas as pd

OUTPUT_COLUMNS = [
    "corp_code",
    "corp_name",
    "stock_code",
    "modify_date",
]

def clean_corp_codes(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.copy()

    cleaned = cleaned[
        cleaned["stock_code"].notna()
        & (cleaned["stock_code"].astype(str).str.strip() != "")
    ].copy()

    cleaned["corp_code"] = cleaned["corp_code"].astype(str).str.strip()
    cleaned["corp_name"] = cleaned["corp_name"].astype(str).str.strip()
    cleaned["stock_code"] = cleaned["stock_code"].astype(str).str.zfill(6)
    cleaned["modify_date"] = cleaned["modify_date"].astype(str).str.strip()

    cleaned = cleaned[OUTPUT_COLUMNS].copy()

    return cleaned
