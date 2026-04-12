"""Quick test: Check CoinDCX and Delta BTCUSDT order placement and info"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.delta import DeltaConnector

cdcx = CoinDCXConnector(cfg)
delta = DeltaConnector(cfg)

# 1. Check if BTCUSDT exists in funding rates
print("=== CoinDCX Funding Rates for BTCUSDT ===")
rates = cdcx.get_funding_rates()
btc = rates.get('BTCUSDT')
if btc:
    print(f"  Found: price={btc.price}, rate={btc.rate}, interval={btc.interval_hours}h")
    print(f"  settlement_only={btc.settlement_only}")
else:
    print("  NOT FOUND in funding rates!")
    matches = [k for k in rates if 'BTC' in k]
    print(f"  Similar: {matches}")

# 2. Check symbol info
print("\n=== CoinDCX Symbol Info ===")
try:
    info = cdcx.get_symbol_info('BTCUSDT')
    if info:
        print(f"  min_qty={info.min_qty}, max_qty={info.max_qty}, qty_step={info.qty_step}")
    else:
        print("  get_symbol_info returned None")
except Exception as e:
    print(f"  Error: {e}")

# 3. Check balance
print("\n=== CoinDCX Balance ===")
bal = cdcx.get_balance_usdt()
print(f"  USDT: {bal}")

# 4. Delta funding rates and symbol info
print("\n=== Delta Funding Rates for BTCUSDT ===")
rates = delta.get_funding_rates()
btc = rates.get('BTCUSDT')
if btc:
    print(f"  Found: price={btc.price}, rate={btc.rate}, interval={btc.interval_hours}h")
    print(f"  settlement_only={btc.settlement_only}")
else:
    print("  NOT FOUND in funding rates!")
    matches = [k for k in rates if 'BTC' in k]
    print(f"  Similar: {matches}")

print("\n=== Delta Symbol Info ===")
try:
    info = delta.get_symbol_info('BTCUSDT')
    if info:
        print(f"  min_qty={info.get('min_qty')}, max_qty={info.get('max_qty')}, qty_step={info.get('qty_step')}")
    else:
        print("  get_symbol_info returned None")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== Delta Balance ===")
bal = delta.get_balance_usdt()
print(f"  USDT: {bal}")

# 4. Try set leverage
print("\n=== Set Leverage 5x ===")
try:
    ok = cs._set_leverage('PIPPINUSDT', 5)
    print(f"  Result: {ok}")
except Exception as e:
    print(f"  Error: {e}")

# 5. Try placing order (dry — just see what happens)
print("\n=== Try place_order BUY (LONG) qty=133 ===")
try:
    result = cs._place_order('PIPPINUSDT', 'BUY', 133, reduce_only=False, leverage=5)
    print(f"  Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"  Error: {e}")

# 6. Check if we have a position now (to clean up)
print("\n=== Check Position ===")
try:
    pos = cs.get_position('PIPPINUSDT')
    if pos:
        print(f"  POSITION EXISTS: {pos}")
        print("  Closing it...")
        qty = float(pos.get('size', pos.get('quantity', pos.get('qty', 133))) or 133)
        try:
            close = cs.close_long('PIPPINUSDT', qty)
            print(f"  Close result: {close}")
        except Exception as e:
            print(f"  Close error: {e}")
    else:
        print("  No position found")
except Exception as e:
    print(f"  Error: {e}")
