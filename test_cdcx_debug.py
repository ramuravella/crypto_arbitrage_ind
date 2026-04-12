"""Debug CoinDCX order execution in detail"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

SYMBOL = 'PIPPINUSDT'
raw = cdcx._raw_sym(SYMBOL)
print(f"Symbol: {SYMBOL} -> Raw: {raw}")

# Step 1: Check balance
bal = cdcx.get_balance_usdt()
print(f"Balance: {bal} USDT")

# Step 2: Check if there's already a position from earlier
print("\n--- Existing Positions (full detail) ---")
positions_raw = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
for p in positions_raw:
    if 'PIPPIN' in str(p.get('pair', '')):
        print(f"PIPPIN position: {json.dumps(p, indent=2, default=str)}")

# Step 3: Set leverage explicitly
print("\n--- Set leverage ---")
try:
    lev_resp = cdcx._signed_post(
        "/exchange/v1/derivatives/futures/positions/update_leverage",
        {"pair": raw, "leverage": 5}
    )
    print(f"Leverage response: {json.dumps(lev_resp, indent=2, default=str)}")
except Exception as e:
    print(f"Leverage ERROR: {e}")

# Step 4: Place a SMALL market BUY (long) order
print("\n--- Place BUY market order ---")
order_payload = {
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
print(f"Payload: {json.dumps(order_payload, indent=2)}")

try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/create", order_payload)
    print(f"\nOrder response: {json.dumps(resp, indent=2, default=str)}")
    
    if isinstance(resp, list) and len(resp) > 0:
        order = resp[0]
        remaining = order.get('remaining_quantity', 0)
        avg_price = order.get('avg_price', 0)
        status = order.get('status', '')
        print(f"\n  Status: {status}")
        print(f"  Avg Price: {avg_price}")
        print(f"  Remaining: {remaining}")
        print(f"  Total: {order.get('total_quantity', 0)}")
        print(f"  Margin: {order.get('ideal_margin', 0)}")
except Exception as e:
    print(f"Order ERROR: {e}")

# Step 5: Wait and check position
print("\n--- Checking position after order ---")
for i in range(10):
    time.sleep(1)
    positions_raw = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
    for p in positions_raw:
        if 'PIPPIN' in str(p.get('pair', '')):
            ap = p.get('active_pos', 0)
            avg = p.get('avg_price', 0)
            margin = p.get('locked_margin', 0)
            print(f"  Check {i+1}: active_pos={ap}, avg_price={avg}, margin={margin}, margin_currency={p.get('margin_currency_short_name')}")
            if float(ap) != 0:
                print(f"  POSITION FOUND! Full: {json.dumps(p, indent=2, default=str)}")
                break
    else:
        continue
    break
else:
    print("  Position never appeared after 10 seconds")

# Step 6: Check order history to see what happened
print("\n--- Recent order history ---")
try:
    history = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/trade_history", 
                                 {"pair": raw, "limit": 5})
    if isinstance(history, list):
        for h in history[:5]:
            print(f"  id={h.get('id','')[:8]} side={h.get('side')} qty={h.get('total_quantity')} filled={h.get('total_quantity',0) - h.get('remaining_quantity',0)} status={h.get('status')} avg_price={h.get('avg_price')}")
    else:
        print(f"  Response: {json.dumps(history, indent=2, default=str)[:500]}")
except Exception as e:
    print(f"  History ERROR: {e}")
