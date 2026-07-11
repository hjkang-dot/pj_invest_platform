import urllib.request
import json
import datetime
import ssl

class YahooCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Bypass SSL verification on Windows if needed
        self.ssl_context = ssl._create_unverified_context()

    def fetch_daily_prices(self, ticker: str, range_str: str = "180d") -> list:
        """
        Fetches daily price data from Yahoo Finance for a given ticker.
        Returns a list of dictionaries with daily OHLCV data.
        """
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_str}&interval=1d"
        req = urllib.request.Request(url, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                results = res_data.get("chart", {}).get("result", [])
                if not results:
                    return []
                
                chart_data = results[0]
                timestamps = chart_data.get("timestamp", [])
                quotes = chart_data.get("indicators", {}).get("quote", [{}])[0]
                
                opens = quotes.get("open", [])
                highs = quotes.get("high", [])
                lows = quotes.get("low", [])
                closes = quotes.get("close", [])
                volumes = quotes.get("volume", [])
                
                candles = []
                for idx in range(len(timestamps)):
                    t = timestamps[idx]
                    o = opens[idx]
                    h = highs[idx]
                    l = lows[idx]
                    c = closes[idx]
                    v = volumes[idx] if idx < len(volumes) and volumes[idx] is not None else 0
                    
                    if o is None or h is None or l is None or c is None:
                        continue
                        
                    # Convert to KST datetime (YYYYMMDD)
                    dt = datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=9)))
                    trade_date = dt.strftime("%Y%m%d")
                    
                    candles.append({
                        "trade_date": trade_date,
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                        "volume": int(v)
                    })
                return candles
        except Exception as e:
            print(f"[YahooCollector] Error fetching data for {ticker}: {e}")
            raise e
