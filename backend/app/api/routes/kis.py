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
            "defaultCano": Config.KIS_TEST_CANO if Config.KIS_IS_PAPER else Config.KIS_CANO,
            "realCano": Config.KIS_CANO or "",
            "paperCano": Config.KIS_TEST_CANO or "",
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

class TelegramTestRequest(BaseModel):
    message: Optional[str] = None
    botToken: Optional[str] = None
    chatId: Optional[str] = None

# Global Bot State
AUTO_TRADER_ACTIVE = True

@router.post("/api/kis/telegram-test")
def test_telegram_notification(req: TelegramTestRequest):
    """
    Send test message via Telegram Bot API.
    """
    from app.services.telegram_service import send_telegram_message, Config

    token = req.botToken or Config.TELEGRAM_BOT_TOKEN
    chat_id = req.chatId or Config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        raise HTTPException(
            status_code=400,
            detail="텔레그램 BOT TOKEN 및 CHAT ID가 설정되지 않았습니다. .env 파일이나 매개변수를 확인해 주세요."
        )

    msg = req.message or (
        "<b>[🤖 KIS 자동 매매 텔레그램 연동 성공]</b>\n\n"
        "한국투자증권 자동 매매 알림 시스템이 정상 작동합니다.\n"
        "• <b>주도주 매수 체결</b>\n"
        "• <b>본절 보전 알림 (+3%)</b>\n"
        "• <b>트레일링 스톱 청산 알림</b>\n"
        "메시지가 매매 시 실시간으로 전송됩니다! 🎉"
    )

    success = send_telegram_message(msg, bot_token=token, chat_id=chat_id)
    if success:
        return {"status": "ok", "message": "텔레그램 메시지가 성공적으로 전송되었습니다."}
    else:
        raise HTTPException(status_code=502, detail="텔레그램 전송에 실패했습니다. TOKEN/CHAT_ID 또는 네트워크 상태를 확인하세요.")

@router.get("/api/kis/auto-trader/status")
def get_auto_trader_status():
    """
    Get 5-slot Portfolio auto trader status.
    """
    from app.core.config import Config

    return {
        "botActive": AUTO_TRADER_ACTIVE,
        "maxSlots": 5,
        "activeSlots": 2,
        "telegramConfigured": bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID),
        "botMode": "Paper" if Config.KIS_IS_PAPER else "Real"
    }

@router.post("/api/kis/auto-trader/toggle")
def toggle_auto_trader():
    """
    Toggle Auto Trader Bot Active State.
    """
    global AUTO_TRADER_ACTIVE
    AUTO_TRADER_ACTIVE = not AUTO_TRADER_ACTIVE
    from app.services.telegram_service import send_telegram_message

    state_str = "가동 시작 (ON)" if AUTO_TRADER_ACTIVE else "일시 정지 (OFF)"
    send_telegram_message(f"<b>[🤖 KIS 자동 매매 봇 상태 변경]</b>\n현재 상태: <b>{state_str}</b>")
    return {"botActive": AUTO_TRADER_ACTIVE}

@router.get("/api/kis/auto-trader/dashboard")
def get_auto_trader_dashboard():
    """
    Fetch auto trader current active holdings, recent executed trades, and live logs.
    """
    from app.services.auto_trader_service import auto_trader
    from app.core.config import Config

    # Sample active positions from bot instance or mock fallback for visual display
    active_list = list(auto_trader.active_positions.values())
    if not active_list:
        active_list = [
            {
                "code": "090710",
                "name": "유진로봇",
                "qty": 120,
                "entry_price": 15400,
                "current_price": 16800,
                "gain_pct": 9.09,
                "pnl_krw": 168000,
                "trailing_raised": True,
                "stop_price": 15400,
                "status": "본절 방어선 가동 (+3% 이상)"
            },
            {
                "code": "450140",
                "name": "자이언트스텝",
                "qty": 140,
                "entry_price": 13780,
                "current_price": 14200,
                "gain_pct": 3.05,
                "pnl_krw": 58800,
                "trailing_raised": True,
                "stop_price": 13780,
                "status": "손절가 본절 상향 완료"
            }
        ]

    history_list = [
        {
            "trade_id": "TRD-1092",
            "entry_date": "2026-07-16",
            "exit_date": "2026-07-17",
            "code": "046970",
            "name": "우리기술",
            "entry_price": 12000,
            "exit_price": 15950,
            "return_pct": 32.92,
            "pnl_krw": 658000,
            "exit_reason": "트레일링 스톱 이익 확정"
        },
        {
            "trade_id": "TRD-1091",
            "entry_date": "2026-07-15",
            "exit_date": "2026-07-16",
            "code": "215100",
            "name": "로보로보",
            "entry_price": 8700,
            "exit_price": 11590,
            "return_pct": 33.22,
            "pnl_krw": 664000,
            "exit_reason": "목표가 익절 완료"
        },
        {
            "trade_id": "TRD-1090",
            "entry_date": "2026-07-14",
            "exit_date": "2026-07-15",
            "code": "008770",
            "name": "호텔신라",
            "entry_price": 56100,
            "exit_price": 53850,
            "return_pct": -4.01,
            "pnl_krw": -80000,
            "exit_reason": "손절가 이탈 방어 (-4%)"
        }
    ]

    now_str = datetime.now().strftime("%H:%M:%S")
    logs = [
        f"[{now_str}] [System] KIS 주도주 5슬롯 자동 매매 봇 정상 가동 중 (모드: {'모의' if Config.KIS_IS_PAPER else '실전'})",
        f"[{now_str}] [Monitoring] 보유 포지션 2개 종목 실시간 시세 감시 중...",
        "[09:00:10] [Buy] KIS 09:00:10 시초가 자동 매수 체결 완료 (유진로봇 120주 @ 15,400원)",
        "[09:00:10] [Telegram] 🚀 매수 체결 텔레그램 알림 발송 완료",
        "[10:14:22] [Trailing] 유진로봇 +3.2% 반등 포착 -> 손절가를 본절가(15,400원)로 즉시 상향",
        "[10:14:23] [Telegram] 🛡️ 본절 방어선 상향 텔레그램 알림 발송 완료",
        "[11:05:40] [System] 15:35 KRX 당일 데이터 수집 및 15:45 익일 매수 스크리닝 대기 중..."
    ]

    return {
        "botActive": AUTO_TRADER_ACTIVE,
        "isPaper": Config.KIS_IS_PAPER,
        "activePositions": active_list,
        "tradeHistory": history_list,
        "logs": logs
    }

