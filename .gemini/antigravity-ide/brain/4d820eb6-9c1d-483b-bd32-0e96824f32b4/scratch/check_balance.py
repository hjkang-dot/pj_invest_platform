import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.clients.kis_client import KISClient
from app.core.config import Config

print(f"Config KIS_IS_PAPER: {Config.KIS_IS_PAPER}")
print(f"Real CANO: {Config.KIS_CANO}")
print(f"Paper CANO: {Config.KIS_TEST_CANO}")

# Try Real Balance if Real CANO is configured
if Config.KIS_CANO and Config.KIS_API_KEY:
    try:
        print("\n--- [실전 계좌 잔고 조회 중] ---")
        real_client = KISClient(is_paper=False)
        real_bal = real_client.get_account_balance()
        print(f"실전 계좌번호: {real_bal.get('cano')}")
        print(f"예수금(현금): {real_bal.get('deposit', 0):,} 원")
        print(f"총 평가금액: {real_bal.get('totalValuation', 0):,} 원")
        print(f"순자산금액: {real_bal.get('netAsset', 0):,} 원")
        print(f"보유 종목 수: {len(real_bal.get('holdings', []))} 개")
        for h in real_bal.get('holdings', []):
            print(f"  - {h['name']}({h['code']}): {h['quantity']}주, 평가손익: {h['pnlAmount']:,}원 ({h['pnlPct']}%)")
    except Exception as e:
        print(f"실전 계좌 조회 중 오류 발생: {e}")

# Try Paper Balance if Paper CANO is configured
if Config.KIS_TEST_CANO or Config.KIS_TEST_API_KEY:
    try:
        print("\n--- [모의 계좌 잔고 조회 중] ---")
        paper_client = KISClient(is_paper=True)
        paper_bal = paper_client.get_account_balance()
        print(f"모의 계좌번호: {paper_bal.get('cano')}")
        print(f"예수금(현금): {paper_bal.get('deposit', 0):,} 원")
        print(f"총 평가금액: {paper_bal.get('totalValuation', 0):,} 원")
        print(f"순자산금액: {paper_bal.get('netAsset', 0):,} 원")
        print(f"보유 종목 수: {len(paper_bal.get('holdings', []))} 개")
        for h in paper_bal.get('holdings', []):
            print(f"  - {h['name']}({h['code']}): {h['quantity']}주, 평가손익: {h['pnlAmount']:,}원 ({h['pnlPct']}%)")
    except Exception as e:
        print(f"모의 계좌 조회 중 오류 발생: {e}")
