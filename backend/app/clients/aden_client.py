import time
import hashlib
import hmac
import requests
import json
from app.core.config import Config

class AdenClient:
    def __init__(self):
        self.api_key = Config.API_KEY
        self.api_secret = Config.API_SECRET
        self.base_url = Config.BASE_URL
        self.empty_payload_hash = hashlib.sha512(b"").hexdigest()
        
    def _generate_signature(self, method, path, query_string, payload_str, timestamp):
        method = method.upper()
        if payload_str:
            payload_hash = hashlib.sha512(payload_str.encode('utf-8')).hexdigest()
        else:
            payload_hash = self.empty_payload_hash
            
        signature_string = f"{method}\n{path}\n{query_string}\n{payload_hash}\n{timestamp}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return signature

    def _request(self, method, endpoint, params=None, data=None, signed=True):
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        full_path = f"/api/v1{endpoint}"
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        query_string = ""
        if params:
            parts = []
            for k, v in sorted(params.items()):
                parts.append(f"{k}={v}")
            query_string = "&".join(parts)

        payload_str = ""
        if data:
            payload_str = json.dumps(data)
            
        if signed:
            if not self.api_key or not self.api_secret:
                raise ValueError("API credentials (KEY/SECRET) are missing or invalid.")
                
            timestamp = str(int(time.time()))
            signature = self._generate_signature(method, full_path, query_string, payload_str, timestamp)
            
            headers.update({
                "KEY": self.api_key,
                "Timestamp": timestamp,
                "SIGN": signature
            })
            
        response = None
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, params=params, json=data, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response is not None:
                try:
                    err_info = response.json()
                    print(f"[API Error] Status: {response.status_code} | Label: {err_info.get('label')} | Message: {err_info.get('message')}")
                    return err_info
                except Exception:
                    pass
            print(f"[HTTP Error] {e}")
            raise e
        except Exception as e:
            print(f"[Connection Error] {e}")
            raise e

    # ==================== PUBLIC ENDPOINTS ====================

    def get_tickers(self, settle=Config.DEFAULT_SETTLE, contract=None):
        endpoint = f"/dex_futures/{settle}/tickers"
        params = {}
        if contract:
            params['contract'] = contract
        return self._request("GET", endpoint, params=params, signed=False)

    def get_candlesticks(self, contract, interval="1m", limit=100, to=None, settle=Config.DEFAULT_SETTLE):
        endpoint = f"/dex_futures/{settle}/candlesticks"
        params = {
            "contract": contract,
            "interval": interval,
            "limit": limit
        }
        if to is not None:
            params['to'] = to
        return self._request("GET", endpoint, params=params, signed=False)

    # ==================== PRIVATE ENDPOINTS ====================

    def get_positions(self, settle=Config.DEFAULT_SETTLE, holding=True):
        endpoint = f"/dex_futures/{settle}/positions"
        params = {
            "holding": "true" if holding else "false"
        }
        return self._request("GET", endpoint, params=params, signed=True)

    def place_order(self, contract, size, price, reduce_only=False, tif="gtc", settle=Config.DEFAULT_SETTLE):
        endpoint = f"/dex_futures/{settle}/orders"
        data = {
            "contract": contract,
            "size": str(size),
            "price": str(price),
            "tif": tif,
            "reduce_only": reduce_only
        }
        return self._request("POST", endpoint, data=data, signed=True)

    def update_leverage(self, contract, leverage, settle=Config.DEFAULT_SETTLE):
        endpoint = f"/dex_futures/{settle}/positions/{contract}/leverage"
        params = {
            "leverage": str(leverage)
        }
        return self._request("POST", endpoint, params=params, signed=True)

    def cancel_all_orders(self, settle=Config.DEFAULT_SETTLE):
        pass

    def get_candlesticks_cached(self, contract, interval="1m", limit=1000, settle=Config.DEFAULT_SETTLE):
        import time
        from app.db.db import save_candlesticks, get_stored_candlesticks, get_last_timestamp
        
        interval_secs = 60
        if interval.endswith("m"):
            interval_secs = int(interval[:-1]) * 60
        elif interval.endswith("h"):
            interval_secs = int(interval[:-1]) * 3600
        elif interval.endswith("d"):
            interval_secs = int(interval[:-1]) * 86400
            
        last_t = get_last_timestamp(contract, interval)
        current_time = int(time.time())
        
        fetch_limit = limit
        if last_t > 0:
            diff_secs = current_time - last_t
            needed_candles = int(diff_secs / interval_secs) + 5
            if needed_candles > 0:
                fetch_limit = min(needed_candles, 2000)
            else:
                fetch_limit = 0
                
        if fetch_limit > 0:
            try:
                raw_candles = self.get_candlesticks(contract=contract, interval=interval, limit=fetch_limit, settle=settle)
                if isinstance(raw_candles, list) and len(raw_candles) > 0:
                    save_candlesticks(raw_candles, contract, interval)
            except Exception as e:
                print(f"[Cache Warning] Failed to fetch updates from exchange: {e}")

        stored_candles = get_stored_candlesticks(contract, interval, limit)
        if len(stored_candles) < limit:
            batch_size = 1000
            current_stored = len(stored_candles)
            max_batches = 5
            
            for _ in range(max_batches):
                if current_stored >= limit:
                    break
                needed = min(limit - current_stored, batch_size)
                if needed <= 0:
                    break
                    
                temp_stored = get_stored_candlesticks(contract, interval, limit)
                to_timestamp = None
                if len(temp_stored) > 0:
                    to_timestamp = int(temp_stored[0]['t'])
                else:
                    to_timestamp = current_time

                try:
                    raw_candles = self.get_candlesticks(contract=contract, interval=interval, limit=needed, to=to_timestamp, settle=settle)
                    if isinstance(raw_candles, list) and len(raw_candles) > 0:
                        save_candlesticks(raw_candles, contract, interval)
                        current_stored += len(raw_candles)
                        if len(raw_candles) < needed:
                            break
                    else:
                        break
                except Exception as e:
                    print(f"[Cache Warning] Failed to backfill batch of historical daily candles: {e}")
                    break
                
        return get_stored_candlesticks(contract, interval, limit)

    def get_account(self, settle=Config.DEFAULT_SETTLE):
        endpoint = f"/dex_futures/{settle}/accounts"
        return self._request("GET", endpoint, signed=True)
