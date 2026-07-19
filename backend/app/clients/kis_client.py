import time
import requests
import json
import os
from typing import Dict, Any, Optional
from app.core.config import Config

class KISClient:
    """
    Korea Investment & Securities (한국투자증권) Open API Client
    Supports both Real Trading (실전투자) and Paper Trading (모의투자).
    """
    _token_cache: Dict[str, Dict[str, Any]] = {}
    _last_request_time: Dict[str, float] = {}

    def __init__(self, is_paper: Optional[bool] = None, cano: Optional[str] = None, acnt_prdt_cd: Optional[str] = None):
        self.is_paper = Config.KIS_IS_PAPER if is_paper is None else is_paper
        
        if self.is_paper:
            self.app_key = Config.KIS_TEST_API_KEY or Config.KIS_API_KEY
            self.app_secret = Config.KIS_TEST_API_SECRET or Config.KIS_API_SECRET
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            self.cano = cano or Config.KIS_TEST_CANO or Config.KIS_CANO
            self.acnt_prdt_cd = acnt_prdt_cd or Config.KIS_TEST_ACNT_PRDT_CD or "01"
        else:
            self.app_key = Config.KIS_API_KEY
            self.app_secret = Config.KIS_API_SECRET
            self.base_url = "https://openapi.koreainvestment.com:9443"
            self.cano = cano or Config.KIS_CANO
            self.acnt_prdt_cd = acnt_prdt_cd or Config.KIS_ACNT_PRDT_CD or "01"

    def _throttle_request(self):
        """
        Throttle paper trading requests to prevent KIS Paper Trading Rate Limit Exceeded error (Max 2 requests/sec).
        """
        if self.is_paper:
            cache_key = "paper"
            now = time.time()
            last_t = KISClient._last_request_time.get(cache_key, 0.0)
            elapsed = now - last_t
            if elapsed < 0.6: # Ensure at least 600ms gap between paper requests
                time.sleep(0.6 - elapsed)
            KISClient._last_request_time[cache_key] = time.time()

    def is_configured(self) -> bool:
        return bool(self.app_key and self.app_secret)

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Fetch or return cached OAuth 2.0 Access Token from KIS (Memory & File persistence).
        """
        if not self.is_configured():
            raise ValueError("한국투자증권 API Key 및 Secret이 설정되지 않았습니다. backend/.env 파일을 확인해주세요.")

        cache_key = "paper" if self.is_paper else "real"
        now = time.time()

        # 1. Check in-memory cache
        cached = KISClient._token_cache.get(cache_key)
        if not force_refresh and cached and cached.get("expires_at", 0) > now + 120:
            return cached["access_token"]

        # 2. Check file persistence cache in data/ directory
        token_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", f"kis_{cache_key}_token.json"))
        if not force_refresh and os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    if file_data.get("expires_at", 0) > now + 120:
                        KISClient._token_cache[cache_key] = file_data
                        return file_data["access_token"]
            except Exception as e:
                print(f"[KIS Token File Warning]: {e}")

        # 3. Request new token via HTTP POST
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json; charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        resp = requests.post(url, headers=headers, json=body, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"KIS Token Issuance Failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 86400))

        if not token:
            raise RuntimeError(f"KIS Token Response Invalid: {data}")

        token_info = {
            "access_token": token,
            "expires_at": now + expires_in
        }
        KISClient._token_cache[cache_key] = token_info

        # Save to file persistence
        try:
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, "w", encoding="utf-8") as f:
                json.dump(token_info, f)
        except Exception as e:
            print(f"[KIS Token Save Warning]: {e}")

        return token

    def get_hashkey(self, payload: Dict[str, Any]) -> str:
        """
        Generate Hashkey required for POST order requests.
        """
        url = f"{self.base_url}/uapi/hashkey"
        headers = {
            "content-type": "application/json; charset=utf-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("HASH", "")
        return ""

    def get_account_balance(self, cano: Optional[str] = None, acnt_prdt_cd: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch domestic stock account balance and active holdings.
        API: /uapi/domestic-stock/v1/trading/inquire-balance
        TR_ID: TTTC8434R (Real) / VTTC8434R (Paper)
        """
        token = self.get_access_token()
        
        # Smart CANO resolution
        if self.is_paper:
            # If specified CANO matches real CANO or is empty, use KIS_TEST_CANO
            if not cano or (Config.KIS_CANO and cano.strip() == Config.KIS_CANO.strip()):
                use_cano = (self.cano or Config.KIS_TEST_CANO).strip()
            else:
                use_cano = cano.strip()
        else:
            use_cano = (cano or self.cano).strip()

        use_acnt_cd = (acnt_prdt_cd or self.acnt_prdt_cd).strip()

        if not use_cano:
            raise ValueError("계좌번호(CANO 8자리)가 지정되지 않았습니다. .env의 KIS_CANO / KIS_TEST_CANO 설정을 확인해주세요.")

        tr_id = "VTTC8434R" if self.is_paper else "TTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

        params = {
            "CANO": use_cano,
            "ACNT_PRDT_CD": use_acnt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FND_TP": "0",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        self._throttle_request()
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        res_json = resp.json()

        if resp.status_code != 200 or res_json.get("rt_cd") != "0":
            msg = res_json.get("msg1", resp.text)
            raise RuntimeError(f"KIS 계좌 조회 실패 [{res_json.get('msg_cd', '')}]: {msg}")

        # Parse Holdings (output1)
        raw_holdings = res_json.get("output1", [])
        holdings = []
        for h in raw_holdings:
            qty = int(h.get("hldg_qty", 0))
            if qty <= 0:
                continue
            
            entry_p = float(h.get("pchs_avg_pric", h.get("pbuy_unpr", 0)))
            curr_p = float(h.get("prpr", 0))
            eval_amt = float(h.get("evlu_amt", qty * curr_p))
            pnl_amt = float(h.get("evlu_pfls_amt", (curr_p - entry_p) * qty))
            pnl_rt = float(h.get("evlu_pfls_rt", 0.0))

            holdings.append({
                "code": h.get("pdno", ""),
                "name": h.get("prdt_name", ""),
                "quantity": qty,
                "sellableQty": int(h.get("pavl_qty", qty)),
                "entryPrice": entry_p,
                "currentPrice": curr_p,
                "valuation": eval_amt,
                "pnlAmount": pnl_amt,
                "pnlPct": round(pnl_rt, 2)
            })

        # Parse Summary (output2)
        raw_summary = res_json.get("output2", [{}])
        summary_item = raw_summary[0] if isinstance(raw_summary, list) and len(raw_summary) > 0 else {}
        
        deposit = float(summary_item.get("dnca_tot_amt", 0))  # 예수금
        tot_eval = float(summary_item.get("tot_evlu_amt", 0))  # 총평가금액
        net_asset = float(summary_item.get("nass_amt", tot_eval + deposit))  # 순자산금액
        total_pnl = float(summary_item.get("evlu_pfls_smttl_amt", 0))  # 평가손익합계금액

        return {
            "isPaper": self.is_paper,
            "cano": use_cano,
            "acntPrdtCd": use_acnt_cd,
            "deposit": deposit,
            "totalValuation": tot_eval,
            "netAsset": net_asset,
            "totalPnl": total_pnl,
            "holdings": holdings
        }

    def order_cash(
        self,
        stock_code: str,
        qty: int,
        price: float = 0,
        side: str = "BUY",
        order_type: str = "00",
        cano: Optional[str] = None,
        acnt_prdt_cd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute Cash Stock Order (Buy or Sell).
        API: /uapi/domestic-stock/v1/trading/order-cash
        TR_ID:
          BUY:  TTTC0802U (Real), VTTC0802U (Paper)
          SELL: TTTC0801U (Real), VTTC0801U (Paper)
        ORDER_TYPE ("ORD_DVSN"): "00" (Limit 지정가), "01" (Market 시장가)
        """
        token = self.get_access_token()
        
        # Smart CANO resolution
        if self.is_paper:
            if not cano or (Config.KIS_CANO and cano.strip() == Config.KIS_CANO.strip()):
                use_cano = (self.cano or Config.KIS_TEST_CANO).strip()
            else:
                use_cano = cano.strip()
        else:
            use_cano = (cano or self.cano).strip()

        use_acnt_cd = (acnt_prdt_cd or self.acnt_prdt_cd).strip()

        if not use_cano:
            raise ValueError("계좌번호(CANO 8자리)가 필요합니다. .env의 KIS_CANO / KIS_TEST_CANO 설정을 확인해주세요.")

        side_upper = side.upper()
        if side_upper not in ("BUY", "SELL"):
            raise ValueError("side는 'BUY' 또는 'SELL'이어야 합니다.")

        if self.is_paper:
            tr_id = "VTTC0802U" if side_upper == "BUY" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side_upper == "BUY" else "TTTC0801U"

        # Format stock code (ensure 6 digits)
        clean_code = stock_code.strip()
        if len(clean_code) < 6 and clean_code.isdigit():
            clean_code = clean_code.zfill(6)

        # Market order requires price="0"
        ord_price = "0" if order_type == "01" else str(int(price))

        payload = {
            "CANO": use_cano,
            "ACNT_PRDT_CD": use_acnt_cd,
            "PDNO": clean_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": ord_price
        }

        hashkey = self.get_hashkey(payload)
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "hashkey": hashkey
        }

        self._throttle_request()
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        res_json = resp.json()

        if resp.status_code != 200 or res_json.get("rt_cd") != "0":
            msg = res_json.get("msg1", resp.text)
            msg_cd = res_json.get("msg_cd", "")
            raise RuntimeError(f"KIS 주식 주문 실패 [{msg_cd}]: {msg}")

        output = res_json.get("output", {})
        return {
            "status": "success",
            "message": res_json.get("msg1", "주문이 접수되었습니다."),
            "orderNo": output.get("ODNO", ""),
            "orderTime": output.get("ORD_TMD", ""),
            "side": side_upper,
            "code": clean_code,
            "quantity": qty,
            "price": price,
            "orderType": order_type,
            "isPaper": self.is_paper
        }
