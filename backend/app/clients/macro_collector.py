import urllib.request
import json
import datetime
import ssl

# DBnomics Series Mapping: series_id -> DBnomics Path
DBNOMICS_SERIES_MAP = {
    "FEDFUNDS": "FED/H15/8.FF.O",
    "US10Y": "FED/H15/9.TCMNOM.Y10",
    "US2Y": "FED/H15/9.TCMNOM.Y2",
    "CPI": "BLS/cu/CUSR0000SA0",
    "UNRATE": "BLS/ln/LNS14000000",
    "GDP": "BEA/NIPA-T10106/gross-domestic-product.Q.millions-of-chained-dollars.level"
}

class MacroCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.ssl_context = ssl._create_unverified_context()

    def normalize_date(self, date_str: str) -> str:
        date_str = date_str.strip()
        if len(date_str) == 7 and '-' in date_str:
            # Monthly format e.g. 2024-12 -> 2024-12-01
            return f"{date_str}-01"
        elif '-Q1' in date_str:
            return f"{date_str[:4]}-03-31"
        elif '-Q2' in date_str:
            return f"{date_str[:4]}-06-30"
        elif '-Q3' in date_str:
            return f"{date_str[:4]}-09-30"
        elif '-Q4' in date_str:
            return f"{date_str[:4]}-12-31"
        return date_str

    def fetch_macro_indicators(self, limit: int = 120) -> list:
        """
        Fetches macroeconomic timeseries data from DBnomics API.
        Returns a list of tuples: (trade_date, series_id, value)
        """
        parsed_records = []
        
        for series_id, dbnomics_path in DBNOMICS_SERIES_MAP.items():
            url = f"https://api.db.nomics.world/v22/series/{dbnomics_path}?observations=1"
            req = urllib.request.Request(url, headers=self.headers)
            print(f"[MacroCollector] Fetching indicator {series_id} ({dbnomics_path})...")
            
            try:
                with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    
                docs = res_data.get("series", {}).get("docs", [])
                if not docs:
                    continue
                
                doc = docs[0]
                periods = doc.get("period", [])
                values = doc.get("value", [])
                
                # Take the latest limit observations
                target_len = min(len(periods), limit)
                for i in range(len(periods) - target_len, len(periods)):
                    p = periods[i]
                    v = values[i]
                    
                    if v is None or v == 'NA':
                        continue
                        
                    try:
                        val = float(v)
                    except ValueError:
                        continue
                        
                    normalized_date = self.normalize_date(p)
                    parsed_records.append((
                        normalized_date,
                        series_id,
                        val
                    ))
                print(f"[MacroCollector] Synced {target_len} records for {series_id}")
            except Exception as e:
                print(f"[MacroCollector] Warning: Failed to fetch {series_id}: {e}")
                
        return parsed_records

    def fetch_economic_calendar(self, days_forward: int = 14) -> list:
        """
        Fetches upcoming economic events from TradingView Economic Calendar.
        Returns a list of tuples:
        (event_date, event_time, country, event_name, impact, actual, forecast, previous)
        """
        # Calculate from/to dates in UTC
        from_dt = datetime.datetime.utcnow()
        to_dt = from_dt + datetime.timedelta(days=days_forward)
        
        from_str = from_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        to_str = to_dt.strftime("%Y-%m-%dT23:59:59.999Z")
        
        url = f"https://economic-calendar.tradingview.com/events?from={from_str}&to={to_str}"
        
        # TradingView requires specific headers to prevent 403 Forbidden
        tv_headers = {
            **self.headers,
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/"
        }
        
        req = urllib.request.Request(url, headers=tv_headers)
        print(f"[MacroCollector] Fetching Economic Calendar from {url}...")
        
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            results = res_data.get("result", [])
            events = []
            
            for event in results:
                raw_date = event.get("date")
                if not raw_date:
                    continue
                    
                # Convert UTC to KST
                try:
                    dt = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    dt_kst = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
                    event_date = dt_kst.strftime("%Y-%m-%d")
                    event_time = dt_kst.strftime("%H:%M")
                except Exception:
                    continue
                    
                country = event.get("country", "").strip()
                title = event.get("title", "").strip()
                importance_val = event.get("importance", -1)
                
                if importance_val >= 1:
                    impact = "HIGH"
                elif importance_val == 0:
                    impact = "MEDIUM"
                else:
                    impact = "LOW"
                    
                # Store numbers or labels as string
                actual = str(event.get("actual")) if event.get("actual") is not None else None
                forecast = str(event.get("forecast")) if event.get("forecast") is not None else None
                previous = str(event.get("previous")) if event.get("previous") is not None else None
                
                events.append((
                    event_date,
                    event_time,
                    country,
                    title,
                    impact,
                    actual,
                    forecast,
                    previous
                ))
            print(f"[MacroCollector] Successfully fetched {len(events)} economic events")
            return events
        except Exception as e:
            print(f"[MacroCollector] Failed to fetch economic calendar: {e}")
            raise e
