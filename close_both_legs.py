"""Close both legs and verify."""
import json, sys, time, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt='%H:%M:%S')
sys.path.insert(0, '.')
from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector
with open('config.json') as f:
    cfg = json.load(f)
cdcx = CoinDCXConnector(cfg)
cs = CoinSwitchConnector(cfg)
SYMBOL = 'PIPPINUSDT'
QTY = 133

print('=== Close CoinSwitch LONG ===')
try:
    cs_close = cs.close_long(SYMBOL, QTY)
    print(f'  Response: {json.dumps(cs_close, indent=2)[:300]}')
except Exception as e:
    print(f'  FAILED: {e}')

print('=== Close CoinDCX SHORT ===')
try:
    cdcx_close = cdcx.close_short(SYMBOL, QTY)
    rtype = type(cdcx_close).__name__
    print(f'  Response type: {rtype}')
    if isinstance(cdcx_close, list) and cdcx_close:
        r = cdcx_close[0]
        oid = r.get('id')
        side = r.get('side')
        status = r.get('status')
        print(f'  id={oid}, side={side}, status={status}')
except Exception as e:
    print(f'  FAILED: {e}')

print('=== Verify both closed ===')
time.sleep(2)
cdcx_pos = cdcx.get_position(SYMBOL)
cs_pos = cs.get_position(SYMBOL)
cs_state = 'STILL OPEN' if cs_pos else 'CLOSED OK'
cdcx_state = 'STILL OPEN' if cdcx_pos else 'CLOSED OK'
print(f'  CoinDCX:    {cdcx_state}')
print(f'  CoinSwitch: {cs_state}')

cdcx_bal = cdcx.get_balance_usdt()
cs_bal = cs.get_balance_usdt()
print(f'  CoinDCX: ${cdcx_bal:.4f} | CoinSwitch: ${cs_bal:.4f}')
