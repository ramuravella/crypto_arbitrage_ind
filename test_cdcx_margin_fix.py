"""Try CoinDCX order without margin_currency, and with different variations"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

raw = cdcx._raw_sym('PIPPINUSDT')

# Test 1: No margin_currency_short_name at all
print("=== Test 1: No margin_currency_short_name ===")
order_payload = {
    "order": {
        "side": "buy",
        "pair": raw,
        "order_type": "market_order",
        "total_quantity": 133.0,
        "leverage": 5,
        "notification": "no_notification",
        "time_in_force": "good_till_cancel",
        "hidden": False,
        "post_only": False,
    }
}
try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/create", order_payload)
    if isinstance(resp, list) and resp:
        o = resp[0]
        print(f"  Status: {o.get('status')}, AvgPrice: {o.get('avg_price')}, Remaining: {o.get('remaining_quantity')}, MarginCurr: {o.get('margin_currency_short_name')}")
    else:
        print(f"  Response: {json.dumps(resp, indent=2, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

time.sleep(2)

# Check position
pos_data = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
for p in pos_data:
    if 'PIPPIN' in str(p.get('pair', '')):
        ap = p.get('active_pos', 0)
        print(f"  Position: active_pos={ap}, margin_currency={p.get('margin_currency_short_name')}")
        break

# Test 2: Try changing position margin currency to INR first
print("\n=== Test 2: Update position margin_currency to INR ===")
try:
    resp = cdcx._signed_post(
        "/exchange/v1/derivatives/futures/positions/update_margin_currency",
        {"pair": raw, "margin_currency_short_name": "INR"}
    )
    print(f"  Response: {json.dumps(resp, indent=2, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Try changing margin type
print("\n=== Test 3: Update margin settings ===")
try:
    resp = cdcx._signed_post(
        "/exchange/v1/derivatives/futures/positions/change_margin_type",
        {"pair": raw, "margin_type": "isolated", "margin_currency_short_name": "INR"}
    )
    print(f"  Response: {json.dumps(resp, indent=2, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Clean check of position
time.sleep(1)
pos_data = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
for p in pos_data:
    if 'PIPPIN' in str(p.get('pair', '')):
        print(f"\n  Final Position State: active_pos={p.get('active_pos')}, margin_currency={p.get('margin_currency_short_name')}")

# Test 4: Now try INR order if margin was successfully changed
print("\n=== Test 4: Place INR order after margin change ===")
order_payload2 = {
    "order": {
        "side": "buy",
        "pair": raw,
        "order_type": "market_order",
        "total_quantity": 133.0,
        "leverage": 5,
        "margin_currency_short_name": "INR",
        "notification": "no_notification",
        "time_in_force": "good_till_cancel",
        "hidden": False,
        "post_only": False,
    }
}
try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/create", order_payload2)
    if isinstance(resp, list) and resp:
        o = resp[0]
        print(f"  Status: {o.get('status')}, AvgPrice: {o.get('avg_price')}, Remaining: {o.get('remaining_quantity')}, MarginCurr: {o.get('margin_currency_short_name')}")
    else:
        print(f"  Response: {json.dumps(resp, indent=2, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Check position
print("\n=== Final position check (3 checks, 2s apart) ===")
for i in range(3):
    time.sleep(2)
    pos_data = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
    for p in pos_data:
        if 'PIPPIN' in str(p.get('pair', '')):
            ap = float(p.get('active_pos', 0))
            print(f"  Check {i+1}: active_pos={ap}, avg_price={p.get('avg_price')}, margin_currency={p.get('margin_currency_short_name')}")
            if ap != 0:
                print(f"  FILLED! Full: {json.dumps(p, indent=2, default=str)}")
