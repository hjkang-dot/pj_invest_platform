from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from app.core.config import Config

DART_CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_SINGLE_ACCOUNT_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
DART_DIVIDEND_URL = "https://opendart.fss.or.kr/api/alotMatter.json"

def build_dart_params() -> dict[str, str]:
    if not Config.DART_API_KEY:
        msg = "DART_API_KEY is not configured"
        raise ValueError(msg)
    return {"crtfc_key": Config.DART_API_KEY}

def fetch_corp_codes() -> pd.DataFrame:
    response = requests.get(DART_CORP_CODE_URL, params=build_dart_params(), timeout=30)
    response.raise_for_status()

    with ZipFile(BytesIO(response.content)) as zip_file:
        xml_name = zip_file.namelist()[0]
        xml_content = zip_file.read(xml_name)

    root = ET.fromstring(xml_content)

    rows = []
    for item in root.findall("list"):
        rows.append(
            {
                "corp_code": item.findtext("corp_code", default=""),
                "corp_name": item.findtext("corp_name", default=""),
                "stock_code": item.findtext("stock_code", default=""),
                "modify_date": item.findtext("modify_date", default=""),
            }
        )
    return pd.DataFrame(rows)

def fetch_financial_statement(
    corp_code: str,
    business_year: str,
    report_code: str = "11011",
) -> pd.DataFrame:
    params = {
        **build_dart_params(),
        "corp_code": corp_code,
        "bsns_year": business_year,
        "reprt_code": report_code,
    }

    response = requests.get(DART_SINGLE_ACCOUNT_URL, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    status = payload.get("status")

    if status != "000":
        message = payload.get("message", "Unknown DART API error")
        msg = f"DART financial statement request failed: {status} {message}"
        raise ValueError(msg)

    return pd.DataFrame(payload.get("list", []))

def fetch_dividend_info(
    corp_code: str,
    business_year: str,
    report_code: str = "11011",
) -> pd.DataFrame:
    params = {
        **build_dart_params(),
        "corp_code": corp_code,
        "bsns_year": business_year,
        "reprt_code": report_code,
    }

    response = requests.get(DART_DIVIDEND_URL, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json()
    status = payload.get("status")

    if status != "000":
        message = payload.get("message", "Unknown DART API error")
        msg = f"DART dividend request failed: {status} {message}"
        raise ValueError(msg)

    return pd.DataFrame(payload.get("list", []))
