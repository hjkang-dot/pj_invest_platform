import pandas as pd

COLUMN_RENAMES = {
    "ISU_SRT_CD": "stock_code",
    "ISU_ABBRV": "stock_name",
    "ISU_NM": "full_stock_name",
    "MKT_TP_NM": "market",
    "SECUGRP_NM": "security_group",
    "SECT_TP_NM": "sector",
    "LIST_DD": "listed_date",
    "LIST_SHRS": "listed_shares",
}

OUTPUT_COLUMNS = [
    "stock_code",
    "stock_name",
    "full_stock_name",
    "market",
    "security_group",
    "sector",
    "listed_date",
    "listed_shares",
]

def clean_listed_stocks(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.rename(columns=COLUMN_RENAMES)

    for col in OUTPUT_COLUMNS:
        if col not in cleaned.columns:
            cleaned[col] = "" if col != "listed_shares" else 0

    cleaned = cleaned[OUTPUT_COLUMNS].copy()

    cleaned["stock_code"] = cleaned["stock_code"].astype(str).str.zfill(6)
    cleaned["stock_name"] = cleaned["stock_name"].astype(str).str.strip()
    cleaned["full_stock_name"] = cleaned["full_stock_name"].astype(str).str.strip()
    cleaned["market"] = cleaned["market"].astype(str).str.strip()
    
    cleaned["listed_shares"] = (
        cleaned["listed_shares"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("None", "0")
        .replace("", "0")
        .replace("nan", "0")
        .astype("int64")
    )

    return cleaned
