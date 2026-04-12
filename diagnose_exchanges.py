"""
Diagnostic script: Test both exchanges for entry/exit/position operations.
Identifies exactly what's broken and why.
"""
import json
import time
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

with open("config.json") as f:
    config = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector

dcx = CoinDCXConnector(config)
cs  = CoinSwitchConnector(config)

print("=" * 70)
print("EXCHANGE DIAGNOSTICS")
print("=" * 70)

# ── 1. Test connectivity & balances ──
print("\n[1] BALANCE CHECK")
t0 = time.time()
try:
    dcx_bal = dcx.get_balance_usdt()
    print(f"  CoinDCX  balance: ${dcx_bal:.2f}  ({time.time()-t0:.2f}s)")
except Exception as e:
    print(f"  CoinDCX  balance FAILED: {e}")

t0 = time.time()
try:
    cs_bal = cs.get_balance_usdt()
    print(f"  CoinSwitch balance: ${cs_bal:.2f}  ({time.time()-t0:.2f}s)")
except Exception as e:
    print(f"  CoinSwitch balance FAILED: {e}")

# ── 2. Test funding rate fetch (identify lag) ──
print("\n[2] FUNDING RATE FETCH TIMING")
t0 = time.time()
try:
    dcx_rates = dcx.get_funding_rates()
    print(f"  CoinDCX  rates: {len(dcx_rates)} symbols ({time.time()-t0:.2f}s)")
except Exception as e:
    print(f"  CoinDCX  rates FAILED: {e}")
    dcx_rates = {}

t0 = time.time()
try:
    cs_rates = cs.get_funding_rates()
    print(f"  CoinSwitch rates: {len(cs_rates)} symbols ({time.time()-t0:.2f}s)")
except Exception as e:
    print(f"  CoinSwitch rates FAILED: {e}")
    cs_rates = {}

# ── 3. Check existing positions ──
print("\n[3] EXISTING POSITIONS")
# CoinDCX
try:
    ts = int(time.time() * 1000)
    dcx_positions = dcx._post("/exchange/v1/derivatives/positions", {"timestamp": ts})
    if isinstance(dcx_positions, list):
        open_dcx = [p for p in dcx_positions if float(p.get('quantity', p.get('qty', p.get('size', 0))) or 0) != 0]
    else:
        open_dcx = []
    print(f"  CoinDCX  open positions: {len(open_dcx)}")
    for p in open_dcx:
        sym = p.get('symbol', '?')
        qty = p.get('quantity', p.get('qty', p.get('size', '?')))
        side = p.get('side', '?')
        pnl = p.get('unrealized_pnl', p.get('pnl', '?'))
        print(f"    {sym} | side={side} | qty={qty} | pnl={pnl}")
        print(f"    Raw fields: {list(p.keys())}")
except Exception as e:
    print(f"  CoinDCX  positions FAILED: {e}")
    open_dcx = []

# CoinSwitch
try:
    cs_positions_raw = cs._get("/trade/api/v2/futures/positions",
                               params={"exchange": "EXCHANGE_2"})
    cs_positions = cs_positions_raw.get('data', [])
    if isinstance(cs_positions, dict):
        cs_positions = list(cs_positions.values())
    open_cs = [p for p in cs_positions if float(p.get('size', p.get('quantity', p.get('qty', 0))) or 0) != 0]
    print(f"  CoinSwitch open positions: {len(open_cs)}")
    for p in open_cs:
        sym = p.get('symbol', '?')
        qty = p.get('size', p.get('quantity', p.get('qty', '?')))
        side = p.get('side', '?')
        pnl = p.get('unrealized_pnl', p.get('pnl', '?'))
        print(f"    {sym} | side={side} | qty={qty} | pnl={pnl}")
        print(f"    Raw fields: {list(p.keys())}")
except Exception as e:
    print(f"  CoinSwitch positions FAILED: {e}")
    open_cs = []

# ── 4. Test small order on CoinSwitch (DRY RUN - just test the payload) ──
print("\n[4] COINSWITCH ORDER TEST (tiny qty)")
test_symbol = "BTCUSDT"
test_qty = 0.001  # Minimum BTC

# First check if CoinSwitch symbol info works
try:
    si = cs.get_symbol_info(test_symbol)
    if si:
        print(f"  CoinSwitch symbol_info({test_symbol}): min_qty={si.min_qty}, qty_step={si.qty_step}, price={si.price}")
    else:
        print(f"  CoinSwitch symbol_info({test_symbol}): None")
except Exception as e:
    print(f"  CoinSwitch symbol_info FAILED: {e}")

# Test leverage setting
try:
    t0 = time.time()
    lev_ok = cs._set_leverage(test_symbol, 5)
    print(f"  CoinSwitch set_leverage: {'OK' if lev_ok else 'FAILED'} ({time.time()-t0:.2f}s)")
except Exception as e:
    print(f"  CoinSwitch set_leverage FAILED: {e}")

# ── 5. Test CoinDCX close mechanics ──
print("\n[5] COINDCX CLOSE ORDER MECHANICS")
# Check if reduce_only is supported correctly
print("  CoinDCX order payload for close_short (reduce_only=True):")
raw = dcx._raw_sym(test_symbol)
print(f"  raw_sym: {raw}")
close_order = {
    "side": "buy",
    "pair": raw,
    "order_type": "market_order",
    "total_quantity": 0.001,
    "leverage": 5,
    "margin_currency_short_name": "INR",
    "notification": "no_notification",
    "time_in_force": "good_till_cancel",
    "hidden": False,
    "post_only": False,
    "reduce_only": True,
}
print(f"  Payload: {json.dumps(close_order, indent=2)}")

# Test CoinDCX order endpoint response format
print("\n  Testing CoinDCX order API response format...")
try:
    # Look at recent orders to understand response structure
    ts = int(time.time() * 1000)
    recent = dcx._post("/exchange/v1/derivatives/futures/orders", {"timestamp": ts})
    if isinstance(recent, list):
        print(f"  CoinDCX recent orders: {len(recent)}")
        for o in recent[:3]:
            print(f"    {o.get('symbol','?')} | side={o.get('side','?')} | status={o.get('status','?')} | reduce_only={o.get('reduce_only','?')}")
    elif isinstance(recent, dict):
        orders = recent.get('data', recent.get('orders', []))
        print(f"  CoinDCX recent orders: {len(orders) if isinstance(orders, list) else '?'}")
        if isinstance(orders, list):
            for o in orders[:3]:
                print(f"    {o.get('symbol','?')} | side={o.get('side','?')} | status={o.get('status','?')} | reduce_only={o.get('reduce_only','?')}")
except Exception as e:
    print(f"  CoinDCX orders query FAILED: {e}")

# ── 6. CoinSwitch recent orders ──
print("\n[6] COINSWITCH ORDER HISTORY")
try:
    cs_orders = cs._get("/trade/api/v2/futures/orders",
                        params={"exchange": "EXCHANGE_2"})
    orders_list = cs_orders.get('data', [])
    if isinstance(orders_list, dict):
        orders_list = list(orders_list.values())
    print(f"  CoinSwitch recent orders: {len(orders_list) if isinstance(orders_list, list) else '?'}")
    if isinstance(orders_list, list):
        for o in orders_list[:5]:
            print(f"    {o.get('symbol','?')} | side={o.get('side','?')} | status={o.get('status','?')} | type={o.get('order_type','?')}")
            print(f"    Raw fields: {list(o.keys())}")
except Exception as e:
    print(f"  CoinSwitch orders FAILED: {e}")

# Also try trade history
print("\n  CoinSwitch trade history:")
try:
    cs_trades = cs._get("/trade/api/v2/futures/trades",
                        params={"exchange": "EXCHANGE_2"})
    trades_list = cs_trades.get('data', [])
    if isinstance(trades_list, dict):
        trades_list = list(trades_list.values())
    print(f"  CoinSwitch recent trades: {len(trades_list) if isinstance(trades_list, list) else '?'}")
    if isinstance(trades_list, list):
        for t in trades_list[:5]:
            print(f"    {t.get('symbol','?')} | side={t.get('side','?')} | qty={t.get('quantity', t.get('qty','?'))} | price={t.get('price','?')}")
except Exception as e:
    print(f"  CoinSwitch trades FAILED: {e}")

# ── 7. Timing analysis ──
print("\n[7] API CALL TIMING ANALYSIS")
endpoints = [
    ("CoinDCX balance", lambda: dcx.get_balance_usdt()),
    ("CoinSwitch balance", lambda: cs.get_balance_usdt()),
    ("CoinDCX positions", lambda: dcx._post("/exchange/v1/derivatives/positions", {"timestamp": int(time.time()*1000)})),
    ("CoinSwitch positions", lambda: cs._get("/trade/api/v2/futures/positions", params={"exchange": "EXCHANGE_2"})),
]
for name, fn in endpoints:
    t0 = time.time()
    try:
        fn()
        print(f"  {name}: {time.time()-t0:.3f}s")
    except Exception as e:
        print(f"  {name}: FAILED ({time.time()-t0:.3f}s) — {e}")

print("\n" + "=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
