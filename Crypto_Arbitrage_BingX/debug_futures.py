import asyncio
import logging
import math
from src.exchange_connector import BingXConnector

logging.basicConfig(level=logging.ERROR)

async def check_minimum_lot_size():
    import json
    print("Loading config...")
    with open('config.json', 'r') as f:
        conf = json.load(f)
        
    conn = BingXConnector('config.json')
    try:
        print("\nLoading Exchange Properties...")
        conn.spot.load_markets()
        conn.perp.load_markets()
        
        symbol = "NTRN-USDT"
        test_capital = 15.00  # Updated to $15 as requested
        spot_ask = 0.35 # Rough current price
        
        print(f"\n===============================")
        print(f"TESTING SIZING LOGIC FOR: {symbol}")
        print(f"Simulated Capital: ${test_capital}")
        print(f"Simulated Ask Price: ${spot_ask}")
        
        # 1. Calculate raw affordable quantity
        raw_quantity = test_capital / spot_ask
        print(f"\nRaw Affordable Quantity: {raw_quantity:.4f} {symbol.split('-')[0]}")
        
        # 2. Format to CCXT precision rules
        spot_qty_str = conn.spot.amount_to_precision(symbol, raw_quantity)
        perp_qty_str = conn.perp.amount_to_precision(symbol, raw_quantity)
        formatted_qty = min(float(spot_qty_str), float(perp_qty_str))
        
        print(f"Exchange Precision Output: {formatted_qty}")
        
        # 3. Pull structural minimums using safe market() method
        spot_limit = conn.spot.market(symbol)['limits']['amount']['min']
        spot_min_qty = float(spot_limit) if spot_limit is not None else 0.0
        
        # BingX Perp symbols must be translated (e.g. NTRN-USDT -> NTRN-USDT:USDT)
        perp_symbol_ccxt = f"{symbol}:USDT" if ":" not in symbol else symbol
        try:
            perp_limit = conn.perp.market(perp_symbol_ccxt)['limits']['amount']['min']
            perp_min_qty = float(perp_limit) if perp_limit is not None else 0.0
        except Exception:
            perp_limit = conn.perp.market(symbol)['limits']['amount']['min']
            perp_min_qty = float(perp_limit) if perp_limit is not None else 0.0
        
        print(f"\nExchange Structural Minimums:")
        print(f"  Spot Market Min: {spot_min_qty}")
        print(f"  Perp Market Min: {perp_min_qty}")
        
        required_min_qty = max(spot_min_qty, perp_min_qty)
        print(f"\n--> SAFEST REQUIRED FLOOR: {required_min_qty} coins")
        
        # 4. Compare
        if required_min_qty > 0 and formatted_qty < required_min_qty:
            print(f"\n[REJECTION TEST SUCCESS] Order safely aborted!")
            print(f"Your affordable quantity ({formatted_qty}) is LESS than BingX's minimum requirement ({required_min_qty}).")
            print("The bot will now successfully skip this coin instead of triggering a Panic Recovery.")
        else:
            print(f"\n[APPROVAL TEST SUCCESS] Capital is sufficient (or Exchange doesn't require a strict minimum qty).")
            print("The order will proceed to execution.")
            
        print("===============================\n")

    except Exception as e:
        print("\nAPI ERROR: ", e)

if __name__ == "__main__":
    asyncio.run(check_minimum_lot_size())
