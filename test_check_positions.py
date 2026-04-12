"""Check CoinDCX and Delta position and clean up"""
import json, sys, time
sys.path.insert(0, '.')
with open('config.json') as f:
    cfg = json.load(f)
from src.connectors.coindcx import CoinDCXConnector
from src.connectors.delta import DeltaConnector

cdcx = CoinDCXConnector(cfg)
delta = DeltaConnector(cfg)

print('Checking CoinDCX position...')
pos = cdcx.get_position('BTCUSDT')
if pos:
    print(f'COINDCX POSITION: {json.dumps(pos, indent=2, default=str)}')
    qty = float(pos.get('size', pos.get('quantity', pos.get('qty', 1))) or 1)
    print(f'Closing qty={abs(qty)}...')
    try:
        r = cdcx.close_long('BTCUSDT', abs(qty))
        print(f'Close result: {json.dumps(r, indent=2)}')
    except Exception as e:
        print(f'Close error: {e}')
else:
    print('No position found on CoinDCX')

print('\nChecking Delta position...')
if hasattr(delta, 'get_position'):
    pos2 = delta.get_position('BTCUSDT')
    if pos2:
        print(f'DELTA POSITION: {json.dumps(pos2, indent=2, default=str)}')
        qty2 = float(pos2.get('size', pos2.get('quantity', pos2.get('qty', 1))) or 1)
        print(f'Closing qty={abs(qty2)}...')
        if hasattr(delta, 'close_long'):
            try:
                r = delta.close_long('BTCUSDT', abs(qty2))
                print(f'Close result: {json.dumps(r, indent=2)}')
            except Exception as e:
                print(f'Close error: {e}')
        else:
            print('DeltaConnector does not implement close_long().')
    else:
        print('No position found on Delta')
else:
    print('DeltaConnector does not implement get_position().')
else:
    print('No position found on CoinDCX')
