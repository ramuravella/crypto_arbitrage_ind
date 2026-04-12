"""Test CoinDCX order with USDT margin (matching position margin type)"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

raw = cdcx._raw_sym('PIPPINUSDT')
print(f"Raw symbol: {raw}")

# Check ALL positions and their margin currencies
print("\n--- All positions with margin currencies ---")
positions_raw = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
for p in positions_raw:
    pair = p.get('pair', '')
    mcurr = p.get('margin_currency_short_name', '?')
    active = p.get('active_pos', 0)
    print(f"  {pair}: margin={mcurr}, active={active}")

# Try order with USDT margin
print("\n--- Place BUY with USDT margin ---")
order_payload = {
    "order": {
        "side": "buy",
        "pair": raw,
        "order_type": "market_order",
        "total_quantity": 133.0,
        "leverage": 5,
        "margin_currency_short_name": "USDT",
        "notification": "no_notification",
        "time_in_force": "good_till_cancel",
        "hidden": False,
        "post_only": False,
    }
}

try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/create", order_payload)
    if isinstance(resp, list) and resp:
        order = resp[0]
        print(f"  Status: {order.get('status')}")
        print(f"  Avg Price: {order.get('avg_price')}")
        print(f"  Remaining: {order.get('remaining_quantity')}")
        print(f"  Margin: {order.get('ideal_margin')}")
        print(f"  Margin Currency: {order.get('margin_currency_short_name')}")
    else:
        print(f"  Response: {json.dumps(resp, indent=2, default=str)}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()

# Check position
print("\n--- Checking position ---")
for i in range(6):
    time.sleep(1)
    for p in cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {}):
        if 'PIPPIN' in str(p.get('pair', '')):
            ap = p.get('active_pos', 0)
            avg = p.get('avg_price', 0)
            mcurr = p.get('margin_currency_short_name', '?')
            print(f"  Check {i+1}: active_pos={ap}, avg_price={avg}, margin_currency={mcurr}")
            if float(ap) != 0:
                print(f"  FOUND! {json.dumps(p, indent=2, default=str)}")
                # Now try to CLOSE it
                print("\n--- Closing position ---")
                close_payload = {
                    "order": {
                        "side": "sell",
                        "pair": raw,
                        "order_type": "market_order",
                        "total_quantity": abs(float(ap)),
                        "leverage": 5,
                        "margin_currency_short_name": mcurr,
                        "reduce_only": True,
                        "notification": "no_notification",
                        "time_in_force": "good_till_cancel",
                        "hidden": False,
                        "post_only": False,
                    }
                }
                try:
                    close_resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/create", close_payload)
                    if isinstance(close_resp, list) and close_resp:
                        cr = close_resp[0]
                        print(f"  Close Status: {cr.get('status')}")
                        print(f"  Close Remaining: {cr.get('remaining_quantity')}")
                    else:
                        print(f"  Close Response: {json.dumps(close_resp, indent=2, default=str)}")
                except Exception as e:
                    print(f"  Close ERROR: {e}")
                break
    else:
        continue
    break
else:
    print("  Position never appeared after 6 seconds")
    # Cancel any pending orders
    print("\n  Trying to cancel unfilled orders...")
    # Check if there are pending orders
