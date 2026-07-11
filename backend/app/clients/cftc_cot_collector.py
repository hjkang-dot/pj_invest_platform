import urllib.request
import ssl
import zipfile
import io
import csv
import datetime

# Target markets mapping: COT Market Name Substring -> DB contract code
COT_MARKET_MAPPING = {
    "GOLD - COMMODITY EXCHANGE INC.": "XAU_USDT",
    "WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE": "CL_USDT",
    "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE": "NAS100_USDT"
}

class CftcCotCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.ssl_context = ssl._create_unverified_context()

    def fetch_cot_report(self, year: int = None) -> list:
        """
        Downloads CFTC COT annual history zip for the given year,
        parses the CSV content and filters for target contracts.
        Returns a list of tuples:
        (trade_date, contract_code, contract_name, open_interest, noncommercial_long, noncommercial_short, commercial_long, commercial_short)
        """
        if year is None:
            year = datetime.date.today().year

        url = f"https://www.cftc.gov/files/dea/history/deahistfo{year}.zip"
        req = urllib.request.Request(url, headers=self.headers)
        
        print(f"[CftcCotCollector] Downloading COT zip from {url}...")
        
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=30) as response:
                zip_data = response.read()
                
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zfile:
                namelist = zfile.namelist()
                if not namelist:
                    print("[CftcCotCollector] Error: Empty zip archive.")
                    return []
                
                # Usually it contains 'annualof.txt' or 'annual.txt'
                txt_filename = namelist[0]
                print(f"[CftcCotCollector] Extracting and parsing {txt_filename}...")
                
                with zfile.open(txt_filename) as txt_file:
                    wrapper = io.TextIOWrapper(txt_file, encoding='utf-8')
                    reader = csv.reader(wrapper)
                    
                    headers = next(reader)
                    # Clean headers from quotes and whitespace
                    headers = [h.strip().replace('"', '') for h in headers]
                    
                    # Identify column indices
                    try:
                        idx_market = headers.index("Market and Exchange Names")
                        idx_date = headers.index("As of Date in Form YYYY-MM-DD")
                        idx_oi = headers.index("Open Interest (All)")
                        idx_nc_long = headers.index("Noncommercial Positions-Long (All)")
                        idx_nc_short = headers.index("Noncommercial Positions-Short (All)")
                        idx_c_long = headers.index("Commercial Positions-Long (All)")
                        idx_c_short = headers.index("Commercial Positions-Short (All)")
                    except ValueError as e:
                        print(f"[CftcCotCollector] Header parsing failed: {e}")
                        return []
                    
                    parsed_records = []
                    for row in reader:
                        if not row or len(row) <= max(idx_market, idx_date, idx_oi, idx_nc_long, idx_nc_short, idx_c_long, idx_c_short):
                            continue
                        
                        market_raw = row[idx_market].strip()
                        
                        # Match target markets
                        contract_code = None
                        for market_key, code in COT_MARKET_MAPPING.items():
                            if market_key in market_raw:
                                contract_code = code
                                break
                        
                        if not contract_code:
                            continue
                        
                        trade_date = row[idx_date].strip() # Format: YYYY-MM-DD
                        
                        # Try parsing numbers
                        try:
                            oi = int(row[idx_oi].strip()) if row[idx_oi].strip() else 0
                            nc_long = int(row[idx_nc_long].strip()) if row[idx_nc_long].strip() else 0
                            nc_short = int(row[idx_nc_short].strip()) if row[idx_nc_short].strip() else 0
                            c_long = int(row[idx_c_long].strip()) if row[idx_c_long].strip() else 0
                            c_short = int(row[idx_c_short].strip()) if row[idx_c_short].strip() else 0
                        except ValueError as e:
                            print(f"[CftcCotCollector] Number parsing warning for {market_raw} on {trade_date}: {e}")
                            continue
                        
                        # Database row tuple matching cftc_cot table structure
                        parsed_records.append((
                            trade_date,
                            contract_code,
                            market_raw,
                            oi,
                            nc_long,
                            nc_short,
                            c_long,
                            c_short
                        ))
                    
                    print(f"[CftcCotCollector] Parsed {len(parsed_records)} relevant COT records for year {year}")
                    return parsed_records
                    
        except Exception as e:
            print(f"[CftcCotCollector] Failed to fetch or parse COT data: {e}")
            raise e
