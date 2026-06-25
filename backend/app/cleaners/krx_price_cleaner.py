import pandas as pd

COLUMN_RENAMES = {
    "BAS_DD": "trade_date",
    "ISU_CD": "stock_code",
    "ISU_NM": "stock_name",
    "MKT_NM": "market",
    "SECT_TP_NM": "section",
    "TDD_CLSPRC": "close_price",
    "CMPPREVDD_PRC": "price_change",
    "FLUC_RT": "change_rate",
    "TDD_OPNPRC": "open_price",
    "TDD_HGPRC": "high_price",
    "TDD_LWPRC": "low_price",
    "ACC_TRDVOL": "volume",
    "ACC_TRDVAL": "trading_value",
    "MKTCAP": "market_cap",
    "LIST_SHRS": "listed_shares",
}

OUTPUT_COLUMNS = [
    "trade_date",
    "stock_code",
    "stock_name",
    "market",
    "section",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "price_change",
    "change_rate",
    "volume",
    "trading_value",
    "market_cap",
    "listed_shares",
]

INTEGER_COLUMNS = [
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "price_change",
    "volume",
    "trading_value",
    "market_cap",
    "listed_shares",
]

FLOAT_COLUMNS = [
    "change_rate",
]

def clean_daily_prices(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.rename(columns=COLUMN_RENAMES)
    
    # Ensure all output columns exist in cleaned df (fallback empty/default if not found)
    for col in OUTPUT_COLUMNS:
        if col not in cleaned.columns:
            cleaned[col] = "" if col in ["section"] else 0
            
    cleaned = cleaned[OUTPUT_COLUMNS].copy()

    cleaned["trade_date"] = cleaned["trade_date"].astype(str)
    cleaned["stock_code"] = cleaned["stock_code"].astype(str).str.zfill(6)
    cleaned["stock_name"] = cleaned["stock_name"].astype(str).str.strip()
    cleaned["market"] = cleaned["market"].astype(str).str.strip()
    cleaned["section"] = cleaned["section"].astype(str).str.strip()

    for column in INTEGER_COLUMNS:
        cleaned[column] = (
            cleaned[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("+", "", regex=False)
            .replace("-", "0")
            .replace("None", "0")
            .replace("", "0")
            .astype("int64")
        )

    for column in FLOAT_COLUMNS:
        cleaned[column] = (
            cleaned[column]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("+", "", regex=False)
            .replace("-", "0")
            .replace("None", "0")
            .replace("", "0")
            .astype("float64")
        )

    return cleaned
