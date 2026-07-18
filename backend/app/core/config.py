import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Config:
    # ------------------ API Credentials ------------------
    # Coin (Aden Exchange)
    API_KEY = os.getenv("ADEN_API_KEY", "")
    API_SECRET = os.getenv("ADEN_API_SECRET", "")
    BASE_URL = os.getenv("ADEN_BASE_URL", "https://api.aden.io/api/v1")
    
    # Stock (DART & KRX)
    DART_API_KEY = os.getenv("DART_API_KEY", "")
    KRX_API_KEY = os.getenv("KRX_API_KEY", "")
    
    # Korea Investment & Securities (KIS)
    KIS_API_KEY = os.getenv("KIS_API_KEY", "")
    KIS_API_SECRET = os.getenv("KIS_API_SECRET", "")
    KIS_TEST_API_KEY = os.getenv("KIS_TEST_API_KEY", "")
    KIS_TEST_API_SECRET = os.getenv("KIS_TEST_API_SECRET", "")
    KIS_CANO = os.getenv("KIS_CANO", "")
    KIS_ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD", "01")
    KIS_IS_PAPER = os.getenv("KIS_IS_PAPER", "true").lower() in ("true", "1", "yes")
    
    # ------------------ Telegram Notifications ------------------
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    
    # ------------------ Trading Defaults ------------------
    DEFAULT_SETTLE = "usdt"
    DEFAULT_CONTRACT = "BTC_USDT"
    
    # Risk Parameters
    DEFAULT_LEVERAGE = 3
    STOP_LOSS_PCT = 0.02
    TAKE_PROFIT_PCT = 0.05
    MAX_ALLOCATION_PCT = 0.10
