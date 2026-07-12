from typing import Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    date: str
    assetClass: str  # 'STOCK' | 'COIN' | 'FUTURES' | 'GOLD'
    strategyId: str  # 'ud_dividend' | 'op_growth' | 'deep_value_contra' | 'vol_climax' | 'NONE'
    type: str        # 'BUY' | 'SELL'
    symbol: str
    name: str
    price: float
    qty: float
    fee: float
    memo: str
    currency: Optional[str] = "KRW"


class CashUpdate(BaseModel):
    cash: float


class AccountCashUpdate(BaseModel):
    accountType: str  # 'STOCK' | 'FUTURES'
    amount: float
