#!/usr/bin/env python3
"""
Debug script to trace exact API calls and responses from both exchanges.
"""
import sys
import logging
from src.auth import get_settings
from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector
import json

# Enable DEBUG logging to see all API calls
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Also log request/response bodies
import requests
print("=" * 80)
print("TRACING API CALLS")
print("=" * 80)

# Monkey-patch requests to log bodies
original_post = requests.post
original_get = requests.get

def logged_post(url, **kwargs):
    print(f"\n>>> POST {url}")
    if 'json' in kwargs:
        print(f"    PAYLOAD: {json.dumps(kwargs['json'], indent=2)}")
    resp = original_post(url, **kwargs)
    print(f"    STATUS: {resp.status_code}")
    try:
        body = resp.json()
        print(f"    RESPONSE: {json.dumps(body, indent=2)[:500]}")
    except:
        print(f"    RESPONSE: {resp.text[:200]}")
    return resp

def logged_get(url, **kwargs):
    print(f"\n>>> GET {url}")
    if 'params' in kwargs:
        print(f"    PARAMS: {json.dumps(kwargs['params'], indent=2)}")
    resp = original_get(url, **kwargs)
    print(f"    STATUS: {resp.status_code}")
    try:
        body = resp.json()
        print(f"    RESPONSE: {json.dumps(body, indent=2)[:500]}")
    except:
        print(f"    RESPONSE: {resp.text[:200]}")
    return resp

requests.post = logged_post
requests.get = logged_get

# Load config
import json as json_lib
with open('config.json') as f:
    CONFIG = json_lib.load(f)

# Get user settings
settings = get_settings(1)

# Build config
user_config = {
    'live_mode': True,
    'exchanges': {
        'coindcx': {'enabled': True, 'api_key': settings.get('coindcx_key'), 'api_secret': settings.get('coindcx_secret')},
        'coinswitch': {'enabled': True, 'api_key': settings.get('coinswitch_key'), 'api_secret': settings.get('coinswitch_secret')},
    },
    'strategy': CONFIG.get('strategy', {}),
    'risk': CONFIG.get('risk', {}),
}

print("\n" + "="*80)
print("TESTING COINDCX")
print("="*80)

try:
    dcx = CoinDCXConnector(user_config)
    print("\n[1] Check balance...")
    dcx_bal = dcx.get_balance_usdt()
    print(f"CoinDCX balance: ${dcx_bal:.2f}")
    
    print("\n[2] Check funding rates...")
    rates = dcx.get_funding_rates()
    symbol = 'DRIFTUSDT'
    if symbol in rates:
        rate_info = rates[symbol]
        print(f"DRIFTUSDT on CoinDCX: ${rate_info.price:.6f}, rate {rate_info.rate*100:.4f}%")
    
    print("\n[3] Check existing positions...")
    for sym in ['DRIFTUSDT', 'ETHUSDT', 'BTCUSDT']:
        pos = dcx.get_position(sym)
        if pos:
            qty = pos.get('quantity', pos.get('qty', 0))
            print(f"  {sym}: {qty}")
        else:
            print(f"  {sym}: No position")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TESTING COINSWITCH")
print("="*80)

try:
    cs = CoinSwitchConnector(user_config)
    print("\n[1] Check balance...")
    cs_bal = cs.get_balance_usdt()
    print(f"CoinSwitch balance: ${cs_bal:.2f}")
    
    print("\n[2] Check funding rates...")
    rates = cs.get_funding_rates()
    symbol = 'DRIFTUSDT'
    if symbol in rates:
        rate_info = rates[symbol]
        print(f"DRIFTUSDT on CoinSwitch: ${rate_info.price:.6f}, rate {rate_info.rate*100:.4f}%")
    
    print("\n[3] Check existing positions...")
    for sym in ['DRIFTUSDT', 'ETHUSDT', 'BTCUSDT']:
        pos = cs.get_position(sym)
        if pos:
            qty = pos.get('quantity', pos.get('qty', 0))
            print(f"  {sym}: {qty}")
        else:
            print(f"  {sym}: No position")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("END TRACE")
print("="*80)
