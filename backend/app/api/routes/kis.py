from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.clients.kis_client import KISClient
from app.core.config import Config

router = APIRouter()

class KisOrderRequest(BaseModel):
    code: str = Field(..., description="Stock code (e.g. 005930)")
    qty: int = Field(..., gt=0, description="Order quantity")
    price: float = Field(0, ge=0, description="Order price (0 for Market order)")
    side: str = Field("BUY", description="BUY or SELL")
    orderType: str = Field("00", description="00: 지정가 (Limit), 01: 시장가 (Market)")
    isPaper: Optional[bool] = Field(None, description="True for Paper trading, False for Real trading")
    cano: Optional[str] = Field(None, description="8-digit account number override")
    acntPrdtCd: Optional[str] = Field(None, description="2-digit product code override")

@router.get("/api/kis/status")
def get_kis_status():
    """
    Check if KIS API credentials and account details are configured.
    """
    try:
        real_client = KISClient(is_paper=False)
        paper_client = KISClient(is_paper=True)

        has_real = real_client.is_configured()
        has_paper = paper_client.is_configured()

        return {
            "configured": has_real or has_paper,
            "hasRealCredentials": has_real,
            "hasPaperCredentials": has_paper,
            "defaultModeIsPaper": Config.KIS_IS_PAPER,
            "defaultCano": Config.KIS_CANO or "",
            "defaultAcntPrdtCd": Config.KIS_ACNT_PRDT_CD or "01"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/kis/account")
def get_kis_account(
    isPaper: Optional[bool] = Query(None),
    cano: Optional[str] = Query(None),
    acntPrdtCd: Optional[str] = Query(None)
):
    """
    Fetch real-time stock balance and holdings from Korea Investment & Securities.
    """
    try:
        client = KISClient(is_paper=isPaper, cano=cano, acnt_prdt_cd=acntPrdtCd)
        if not client.is_configured():
            raise HTTPException(
                status_code=400,
                detail="한국투자증권 API Key가 설정되지 않았습니다. .env 파일을 확인해주세요."
            )

        balance = client.get_account_balance(cano=cano, acnt_prdt_cd=acntPrdtCd)
        return balance
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"계좌 조회 실패: {str(e)}")

@router.post("/api/kis/order")
def execute_kis_order(req: KisOrderRequest):
    """
    Execute Cash Stock Buy or Sell order via Korea Investment & Securities API.
    """
    try:
        client = KISClient(is_paper=req.isPaper, cano=req.cano, acnt_prdt_cd=req.acntPrdtCd)
        if not client.is_configured():
            raise HTTPException(
                status_code=400,
                detail="한국투자증권 API Key가 설정되지 않았습니다. .env 파일을 확인해주세요."
            )

        result = client.order_cash(
            stock_code=req.code,
            qty=req.qty,
            price=req.price,
            side=req.side,
            order_type=req.orderType,
            cano=req.cano,
            acnt_prdt_cd=req.acntPrdtCd
        )

        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주문 실행 중 오류 발생: {str(e)}")
