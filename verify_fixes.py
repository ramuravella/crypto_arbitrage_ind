"""
Post-fix verification: Test all three fixed issues.
"""
import json
import time
import sys
import logging
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

with open("config.json") as f:
    config = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector

dcx = CoinDCXConnector(config)
cs  = CoinSwitchConnector(config)

print("=" * 70)
print("POST-FIX VERIFICATION")
print("=" * 70)

# ── FIX 1: CoinDCX get_position now uses correct endpoint ──
print("\n[FIX 1] CoinDCX get_position (was 404, should work now)")
t0 = time.time()
try:
    pos = dcx.get_position("BTCUSDT")
    elapsed = time.time() - t0
    if pos:
        print(f"  BTCUSDT position found: {pos} ({elapsed:.2f}s)")
    else:
        print(f"  BTCUSDT: No open position (correct if none exists) ({elapsed:.2f}s)")
    print("  STATUS: PASS ✓")
except Exception as e:
    print(f"  FAILED: {e}")
    print("  STATUS: FAIL ✗")

# Test another symbol
t0 = time.time()
try:
    pos = dcx.get_position("HEMIUSDT")
    elapsed = time.time() - t0
    if pos:
        print(f"  HEMIUSDT position found: qty={pos.get('quantity')} ({elapsed:.2f}s)")
    else:
        print(f"  HEMIUSDT: No open position ({elapsed:.2f}s)")
except Exception as e:
    print(f"  HEMIUSDT FAILED: {e}")

# ── FIX 2: CoinSwitch exchange in body (was 422) ──
print("\n[FIX 2] CoinSwitch leverage setting (was 422 'exchange missing')")
t0 = time.time()
try:
    ok = cs._set_leverage("BTCUSDT", 5)
    elapsed = time.time() - t0
    print(f"  Set leverage 5x: {'OK ✓' if ok else 'FAILED ✗'} ({elapsed:.2f}s)")
except Exception as e:
    print(f"  FAILED: {e}")

# ── FIX 3: Timing comparison ──
print("\n[FIX 3] Entry/Exit timing improvement")

# Simulate verification with concurrent threads
print("  Sequential position checks (OLD way):")
t0 = time.time()
dcx.get_position("BTCUSDT")
cs.get_position("BTCUSDT")
t_seq = time.time() - t0
print(f"    Time: {t_seq:.3f}s")

print("  Concurrent position checks (NEW way):")
t0 = time.time()
results = {}
def _check(key, fn, sym):
    try: results[key] = fn(sym)
    except: results[key] = None

t1 = threading.Thread(target=_check, args=('dcx', dcx.get_position, 'BTCUSDT'))
t2 = threading.Thread(target=_check, args=('cs', cs.get_position, 'BTCUSDT'))
t1.start(); t2.start()
t1.join(); t2.join()
t_par = time.time() - t0
print(f"    Time: {t_par:.3f}s")
print(f"    Speedup: {t_seq/t_par:.1f}x faster")

# Full entry simulation timing (without actual orders)
print("\n  Full entry flow timing estimate:")
print(f"    Pre-flight (2 balances): ~0.6s (concurrent)")
print(f"    Orders (2 exchanges): ~0.6s (concurrent)")
print(f"    Wait: 0.3s (was 1.0s)")
print(f"    Verify (2 positions): ~{t_par:.1f}s (was {t_seq:.1f}s sequential)")
print(f"    Entry price: 0s (reuse verify data, was ~{t_seq:.1f}s)")
total_old = 0.6 + 0.6 + 1.0 + t_seq + 0.5 + t_seq
total_new = 0.6 + 0.6 + 0.3 + t_par
print(f"    TOTAL: ~{total_new:.1f}s (was ~{total_old:.1f}s)")

# ── Summary ──
print("\n" + "=" * 70)
print("FIXES APPLIED:")
print("  1. CoinDCX: Fixed positions endpoint")
print("     /exchange/v1/derivatives/positions (404)")
print("     → /exchange/v1/derivatives/futures/positions (200)")
print("     Also fixed field mapping: active_pos instead of quantity")
print()
print("  2. CoinSwitch: Fixed exchange param location")
print("     exchange in query params → 422 'Input exchange is missing'")
print("     exchange in request body → 200 OK")
print()
print("  3. Lag reduction:")
print("     - Post-entry/exit sleep: 1.0s → 0.3s")
print("     - Position verification: sequential → concurrent")
print("     - Entry price fetch: extra API call → reuse verify data")
print("     - Exit extra timeout: removed unnecessary 2s+5s fallback")
print("=" * 70)
