import requests
from typing import Optional, Dict, Any
from app.core.config import Config

def send_telegram_message(message: str, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """
    Send formatted notification message to Telegram channel/user using Bot API.
    """
    token = bot_token or Config.TELEGRAM_BOT_TOKEN
    cid = chat_id or Config.TELEGRAM_CHAT_ID

    if not token or not cid:
        print("[Telegram Warning] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True
        else:
            print(f"[Telegram Error] ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"[Telegram Exception]: {e}")
        return False

def notify_buy_executed(stock_name: str, stock_code: str, qty: int, price: float, is_paper: bool = True):
    """
    Send Telegram Alert on Buy Order Execution.
    """
    mode_str = "🧪 모의투자" if is_paper else "💳 실전투자"
    total_amt = int(price * qty)
    msg = (
        f"<b>[🚀 KIS 매수 체결 완료]</b>\n\n"
        f"• <b>종목명</b>: {stock_name} ({stock_code})\n"
        f"• <b>구분</b>: {mode_str}\n"
        f"• <b>체결 수량</b>: {qty:,} 주\n"
        f"• <b>체결 단가</b>: {int(price):,} 원\n"
        f"• <b>총 매수 금액</b>: {total_amt:,} 원\n\n"
        f"💡 <i>자동 매도 스톱 트래킹(손절 -4% / 트레일링 스톱) 가동 중</i>"
    )
    return send_telegram_message(msg)

def notify_trailing_stop_raised(stock_name: str, stock_code: str, gain_pct: float, entry_price: float):
    """
    Send Telegram Alert when Trailing Stop raises stop loss to breakeven.
    """
    msg = (
        f"<b>[🛡️ 본절 방어선 상향 알림]</b>\n\n"
        f"• <b>종목명</b>: {stock_name} ({stock_code})\n"
        f"• <b>현재 수익률</b>: +{gain_pct:.2f}%\n"
        f"• <b>조치</b>: 주가 +3.0% 반등 포착으로 손절가를 <b>본절가({int(entry_price):,}원)</b>로 올렸습니다.\n\n"
        f"🔒 <i>이 종목은 이제 손실 가능성 0% 안전 상태입니다.</i>"
    )
    return send_telegram_message(msg)

def notify_sell_executed(stock_name: str, stock_code: str, qty: int, exit_price: float, return_pct: float, pnl_krw: float, reason: str, is_paper: bool = True):
    """
    Send Telegram Alert on Profit Taking or Stop Loss Execution.
    """
    mode_str = "🧪 모의투자" if is_paper else "💳 실전투자"
    icon = "🎉" if return_pct >= 0 else "🛡️"
    title_str = "트레일링 익절 완료" if return_pct >= 0 else "위험 제어 손절 처리"

    msg = (
        f"<b>[{icon} KIS 매도 체결: {title_str}]</b>\n\n"
        f"• <b>종목명</b>: {stock_name} ({stock_code})\n"
        f"• <b>구분</b>: {mode_str}\n"
        f"• <b>최종 실현 수익률</b>: <b>{return_pct:+.2f}%</b>\n"
        f"• <b>실현 손익금</b>: <b>{int(pnl_krw):+,} 원</b>\n"
        f"• <b>청산 단가</b>: {int(exit_price):,} 원 ({qty:,} 주)\n"
        f"• <b>청산 사유</b>: {reason}\n\n"
        f"💰 <i>매도 금액이 현금 잔고로 환원되었습니다. (다음 주도주 매수 대기)</i>"
    )
    return send_telegram_message(msg)
