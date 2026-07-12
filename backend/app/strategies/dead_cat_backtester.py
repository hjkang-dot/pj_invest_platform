import sys
import os
import argparse
import sqlite3
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.strategies.dead_cat_short import DeadCatShortStrategy
from app.db.db import DB_PATH
from app.clients.aden_client import AdenClient

def load_data(contract: str, interval: str, limit=1200) -> pd.DataFrame:
    """Loads candlesticks from SQLite database into a pandas DataFrame. If empty, fetches via AdenClient."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT t, o, h, l, c, v FROM candlesticks
        WHERE contract = ? AND interval = ?
        ORDER BY t ASC
    """
    df = pd.read_sql_query(query, conn, params=(contract, interval))
    conn.close()
    
    if df.empty or len(df) < 100:
        print(f"[Loader] Database cache low/empty for {contract} ({interval}). Fetching from exchange...")
        try:
            client = AdenClient()
            # This helper will fetch from exchange, save to SQLite
            client.get_candlesticks_cached(contract, interval, limit=limit)
            
            # Re-fetch from DB after saving
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(query, conn, params=(contract, interval))
            conn.close()
        except Exception as e:
            print(f"[Loader Error] Failed to fetch historical data from exchange: {e}")
            
    return df

def run_backtest(contract: str, interval: str, initial_balance=10000.0,
                 long_p=120, atr_mult=3.0, stop_loss_pct=0.08,
                 take_profit_pct=0.30, risk_pct=0.02):
    
    print(f"=== Backtest Started ===")
    print(f"Contract: {contract} | Interval: {interval}")
    print(f"Params: Long MA={long_p}, ATR Mult={atr_mult}x")
    print(f"TP/SL: Stop Loss={stop_loss_pct * 100}%, Take Profit={take_profit_pct * 100}%")
    print(f"Risk Target: {risk_pct * 100}% of balance per trade")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    
    df = load_data(contract, interval)
    if df.empty:
        print(f"[Error] No data found for {contract} with interval {interval} in database.")
        return
    
    # Load BTC data for market regime filter (limit = 1200)
    btc_df = load_data("BTC_USDT", interval, limit=1200)
    if not btc_df.empty:
        btc_df = btc_df.rename(columns={'c': 'btc_c'})
        btc_df['btc_ma_long'] = btc_df['btc_c'].rolling(window=120).mean()
        df = pd.merge(df, btc_df[['t', 'btc_c', 'btc_ma_long']], on='t', how='left')
        print("Successfully merged BTC Market Regime Filter data.")
    else:
        print("[Warning] BTC_USDT data not found. Regime filter will be bypassed.")
        df['btc_c'] = 0.0
        df['btc_ma_long'] = 1.0 # Bypassed
        
    print(f"Loaded {len(df)} candles.")
    
    # Initialize strategy
    strategy = DeadCatShortStrategy(
        long_period=long_p,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct
    )
    
    # Calculate indicators
    df = strategy.calculate_indicators(df)
    
    # Simulation variables
    balance = initial_balance
    in_position = False
    entry_price = 0.0
    position_size = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    trades = []
    equity_curve = [initial_balance]
    peak_balance = initial_balance
    max_drawdown = 0.0
    
    # Slippage and Fee model (e.g. 0.05% taker fee per execution)
    fee_rate = 0.0005 
    
    min_bars = strategy.min_required_bars
    
    for i in range(min_bars, len(df)):
        current_row = df.iloc[i]
        c = current_row['c']
        h = current_row['h']
        l = current_row['l']
        t = current_row['t']
        
        # Prepare historical slice up to current index i-1 for signal check
        df_slice = df.iloc[:i]
        
        # Track Equity Curve
        current_equity = balance
        if in_position:
            # PnL for SHORT position: (Entry - Current) * Size
            current_equity += (entry_price - c) * position_size
        
        equity_curve.append(current_equity)
        if current_equity > peak_balance:
            peak_balance = current_equity
        
        drawdown = (peak_balance - current_equity) / peak_balance if peak_balance > 0 else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            
        if not in_position:
            # Calculate short limit order price based on historical data (before this bar)
            limit_price = strategy.get_limit_order_price(df_slice, atr_mult=atr_mult)
            
            # Apply BTC Market Regime Filter: only place limit order when BTC is in downtrend
            is_btc_downtrend = True
            if 'btc_c' in current_row and 'btc_ma_long' in current_row:
                if pd.notna(current_row['btc_c']) and pd.notna(current_row['btc_ma_long']):
                    is_btc_downtrend = current_row['btc_c'] < current_row['btc_ma_long']

            if limit_price > 0.0 and h >= limit_price and is_btc_downtrend:
                # Enter SHORT at limit_price (caught the wick!)
                entry_price = limit_price
                stop_loss = strategy.get_stop_loss_price(df_slice, entry_price, "SHORT")
                take_profit = strategy.get_take_profit_price(df_slice, entry_price, "SHORT")
                
                # ATR-based position sizing (Risk target based on risk_pct)
                risk_amount = balance * risk_pct
                loss_per_coin = abs(stop_loss - entry_price)
                
                if loss_per_coin > 0:
                    position_size = risk_amount / loss_per_coin
                else:
                    position_size = balance / entry_price
                
                # Limit maximum leverage to 3x of current balance to avoid extreme liquidation risk
                max_pos_size = (balance * 3.0) / entry_price
                position_size = min(position_size, max_pos_size)
                
                # Apply entry fee based on actual position size
                fee = (position_size * entry_price) * fee_rate
                balance -= fee
                
                in_position = True
                entry_time = pd.to_datetime(t, unit='s')
                
                trades.append({
                    "type": "SHORT",
                    "entry_time": entry_time,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "size": position_size,
                    "fee": fee
                })
        else:
            # In position: Check Stop Loss, Take Profit, and EXIT signal
            exit_reason = None
            exit_price = c
            
            # SL check (for SHORT, price went UP to SL)
            if h >= stop_loss:
                exit_price = stop_loss
                exit_reason = "STOP_LOSS"
            # TP check (for SHORT, price went DOWN to TP)
            elif l <= take_profit:
                exit_price = take_profit
                exit_reason = "TAKE_PROFIT"
            
            if exit_reason:
                # Close Position
                pnl = (entry_price - exit_price) * position_size
                exit_fee = (exit_price * position_size) * fee_rate
                
                balance += pnl - exit_fee
                in_position = False
                
                exit_time = pd.to_datetime(t, unit='s')
                
                trades[-1].update({
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl": pnl,
                    "pnl_pct": (pnl / (entry_price * position_size)) * 100,
                    "exit_fee": exit_fee,
                    "final_balance": balance
                })
                
    # End of data: Force close if in position
    if in_position:
        last_row = df.iloc[-1]
        exit_price = last_row['c']
        pnl = (entry_price - exit_price) * position_size
        exit_fee = (exit_price * position_size) * fee_rate
        balance += pnl - exit_fee
        exit_time = pd.to_datetime(last_row['t'], unit='s')
        
        trades[-1].update({
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_reason": "FORCE_CLOSE",
            "pnl": pnl,
            "pnl_pct": (pnl / (entry_price * position_size)) * 100,
            "exit_fee": exit_fee,
            "final_balance": balance
        })
        
    # Analyze results
    total_trades = len(trades)
    if total_trades == 0:
        print("\n[Result] No trades executed during backtest period.")
        return
        
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
    
    win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
    total_return = ((balance - initial_balance) / initial_balance) * 100
    
    print("\n" + "="*30)
    print("           BACKTEST RESULTS           ")
    print("="*30)
    print(f"Total Return:       {total_return:.2f}%")
    print(f"Final Balance:      ${balance:,.2f}")
    print(f"Max Drawdown:       {max_drawdown*100:.2f}%")
    print(f"Total Trades:       {total_trades}")
    print(f"Win Rate:           {win_rate:.2f}% ({len(winning_trades)} wins, {len(losing_trades)} losses)")
    
    if winning_trades:
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades])
        print(f"Average Win:        +{avg_win:.2f}%")
    if losing_trades:
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades])
        print(f"Average Loss:       {avg_loss:.2f}%")
        
    print("\n--- Recent 10 Trades ---")
    for idx, t in enumerate(trades[-10:]):
        print(f"[{idx+1}] Entry: {t['entry_time'].strftime('%Y-%m-%d')} @ {t['entry_price']:.2f} | "
              f"Exit: {t['exit_time'].strftime('%Y-%m-%d')} @ {t['exit_price']:.2f} ({t['exit_reason']}) | "
              f"PnL: {t['pnl_pct']:.2f}% (${t['pnl']:.2f})")

def show_available_contracts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT contract, interval, COUNT(*) FROM candlesticks GROUP BY contract, interval")
    rows = cursor.fetchall()
    conn.close()
    
    print("Available coins & intervals in database:")
    for r in rows:
        print(f" - Contract: {r[0]} | Interval: {r[1]} | Candles Count: {r[2]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest Wick Fading Limit Short Strategy.")
    parser.add_argument("--contract", type=str, default="BTC_USDT", help="Contract code (e.g. BTC_USDT)")
    parser.add_argument("--interval", type=str, default="1d", help="Candle interval (e.g. 1d, 1h, 15m)")
    parser.add_argument("--long-p", type=int, default=120, help="Long MA period for downtrend filter")
    parser.add_argument("--atr-mult", type=float, default=3.0, help="ATR multiplier for upper wick fading (default: 3.0)")
    parser.add_argument("--stop-loss", type=float, default=0.08, help="Stop loss percentage above entry (default: 0.08)")
    parser.add_argument("--take-profit", type=float, default=0.30, help="Take profit percentage below entry (default: 0.30)")
    parser.add_argument("--risk-pct", type=float, default=0.02, help="Risk target percentage of balance per trade (default: 0.02)")
    parser.add_argument("--list-available", action="store_true", help="List available contracts in DB")
    
    args = parser.parse_args()
    
    if args.list_available:
        show_available_contracts()
    else:
        run_backtest(
            contract=args.contract,
            interval=args.interval,
            long_p=args.long_p,
            atr_mult=args.atr_mult,
            stop_loss_pct=args.stop_loss,
            take_profit_pct=args.take_profit,
            risk_pct=args.risk_pct
        )
