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

def load_data(contract: str, interval: str) -> pd.DataFrame:
    """Loads candlesticks from SQLite database into a pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT t, o, h, l, c, v FROM candlesticks
        WHERE contract = ? AND interval = ?
        ORDER BY t ASC
    """
    df = pd.read_sql_query(query, conn, params=(contract, interval))
    conn.close()
    return df

def run_backtest(contract: str, interval: str, initial_balance=10000.0,
                 long_p=120, short_p=20, rsi_p=14, rsi_ob=60,
                 stop_mult=2.0, take_mult=3.0):
    
    print(f"=== Backtest Started ===")
    print(f"Contract: {contract} | Interval: {interval}")
    print(f"Params: Long MA={long_p}, Short MA={short_p}, RSI OB={rsi_ob}")
    print(f"TP/SL: ATR SL Mult={stop_mult}, ATR TP Mult={take_mult}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    
    df = load_data(contract, interval)
    if df.empty:
        print(f"[Error] No data found for {contract} with interval {interval} in database.")
        return
    
    print(f"Loaded {len(df)} candles.")
    
    # Initialize strategy
    strategy = DeadCatShortStrategy(
        long_period=long_p,
        short_period=short_p,
        rsi_period=rsi_p,
        rsi_overbought=rsi_ob,
        stop_atr_mult=stop_mult,
        take_atr_mult=take_mult
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
        
        # Prepare historical slice up to current index i for signal check
        df_slice = df.iloc[:i+1]
        
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
            # Check for entry signal
            signal = strategy.check_signal(df_slice)
            if signal == "SHORT":
                # Enter SHORT
                entry_price = c
                # Bet 100% of balance (simple backtest assumption)
                position_size = balance / entry_price
                
                # Apply entry fee
                fee = balance * fee_rate
                balance -= fee
                position_size = balance / entry_price
                
                stop_loss = strategy.get_stop_loss_price(df_slice, entry_price, "SHORT")
                take_profit = strategy.get_take_profit_price(df_slice, entry_price, "SHORT")
                
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
            else:
                # Check manual EXIT signal from RSI or indicators
                signal = strategy.check_signal(df_slice)
                if signal == "EXIT":
                    exit_price = c
                    exit_reason = "STRATEGY_EXIT"
            
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
    parser = argparse.ArgumentParser(description="Backtest Dead Cat Short Strategy.")
    parser.add_argument("--contract", type=str, default="BTC_USDT", help="Contract code (e.g. BTC_USDT)")
    parser.add_argument("--interval", type=str, default="1d", help="Candle interval (e.g. 1d, 1h)")
    parser.add_argument("--long-p", type=int, default=120, help="Long MA period")
    parser.add_argument("--short-p", type=int, default=20, help="Short MA period")
    parser.add_argument("--rsi-ob", type=int, default=60, help="RSI Overbought boundary")
    parser.add_argument("--stop-mult", type=float, default=2.0, help="ATR Stop Loss multiplier")
    parser.add_argument("--take-mult", type=float, default=3.0, help="ATR Take Profit multiplier")
    parser.add_argument("--list-available", action="store_true", help="List available contracts in DB")
    
    args = parser.parse_args()
    
    if args.list_available:
        show_available_contracts()
    else:
        run_backtest(
            contract=args.contract,
            interval=args.interval,
            long_p=args.long_p,
            short_p=args.short_p,
            rsi_ob=args.rsi_ob,
            stop_mult=args.stop_mult,
            take_mult=args.take_mult
        )
