#!/usr/bin/env python3
"""
Debug script to trace entry/exit flow and identify where positions get stuck.
Run this to manually test entry and exit on both exchanges.
"""
import sys
import asyncio
from src.auth import get_settings
from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector
from src.executor import PerpExecutor
from src.scanner import FundingScanner
from src.connectors.base import SpreadOpportunity
from datetime import datetime, timezone, timedelta
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Load config
import json
with open('config.json') as f:
    CONFIG = json.load(f)

# Get user settings
settings = get_settings(1)  # User 1

# Build config dict
user_config = {
    'live_mode': True,
    'exchanges': {
        'coindcx': {'enabled': True, 'api_key': settings.get('coindcx_key'), 'api_secret': settings.get('coindcx_secret')},
        'coinswitch': {'enabled': True, 'api_key': settings.get('coinswitch_key'), 'api_secret': settings.get('coinswitch_secret')},
    },
    'strategy': CONFIG.get('strategy', {}),
    'risk': CONFIG.get('risk', {}),
}

# Create connectors
print("\n" + "="*80)
print("INITIALIZING CONNECTORS")
print("="*80)

try:
    dcx = CoinDCXConnector(user_config)
    print("✓ CoinDCX connector created")
except Exception as e:
    print(f"✗ CoinDCX connector FAILED: {e}")
    sys.exit(1)

try:
    cs = CoinSwitchConnector(user_config)
    print("✓ CoinSwitch connector created")
except Exception as e:
    print(f"✗ CoinSwitch connector FAILED: {e}")
    sys.exit(1)

connectors = {'coindcx': dcx, 'coinswitch': cs}

# Check balances
print("\n" + "="*80)
print("CHECKING BALANCES")
print("="*80)

try:
    dcx_bal = dcx.get_balance_usdt()
    print(f"✓ CoinDCX balance: ${dcx_bal:.2f} USDT")
except Exception as e:
    print(f"✗ CoinDCX balance check FAILED: {e}")

try:
    cs_bal = cs.get_balance_usdt()
    print(f"✓ CoinSwitch balance: ${cs_bal:.2f} USDT")
except Exception as e:
    print(f"✗ CoinSwitch balance check FAILED: {e}")

# Check existing positions
print("\n" + "="*80)
print("CHECKING EXISTING POSITIONS")
print("="*80)

for symbol in ['BTCUSDT', 'ETHUSDT', 'DRIFTUSDT']:
    try:
        dcx_pos = dcx.get_position(symbol)
        if dcx_pos:
            qty = dcx_pos.get('quantity') or dcx_pos.get('qty') or dcx_pos.get('info', {}).get('qty')
            print(f"✓ CoinDCX {symbol}: {qty}")
        else:
            print(f"  CoinDCX {symbol}: No position")
    except Exception as e:
        print(f"✗ CoinDCX {symbol}: ERROR - {e}")
    
    try:
        cs_pos = cs.get_position(symbol)
        if cs_pos:
            qty = cs_pos.get('quantity') or cs_pos.get('qty') or cs_pos.get('info', {}).get('qty')
            print(f"✓ CoinSwitch {symbol}: {qty}")
        else:
            print(f"  CoinSwitch {symbol}: No position")
    except Exception as e:
        print(f"✗ CoinSwitch {symbol}: ERROR - {e}")

# Create executor
executor = PerpExecutor(connectors, user_config)

# Test entry
test_symbol = 'DRIFTUSDT'
test_qty = 1.0
test_leverage = 1

print("\n" + "="*80)
print(f"TESTING ENTRY: {test_symbol} qty={test_qty} lev={test_leverage}")
print("="*80)

# Create dummy opportunity (SHORT on CoinDCX, LONG on CoinSwitch)
now = datetime.now(timezone.utc)
next_settle = now + timedelta(hours=8)

opp = SpreadOpportunity(
    symbol=test_symbol,
    short_exchange='coindcx',
    long_exchange='coinswitch',
    short_rate=0.001,
    long_rate=0.0005,
    spread_pct=0.0005,
    interval_hours=8,
    next_settlement=next_settle,
    minutes_to_settlement=480,
    price=1000.0,
)

success, result = executor.execute_entry(opp, test_qty)

print(f"\nEntry result: {result}")

if success:
    print("\n✓ ENTRY SUCCESSFUL - Checking positions on both exchanges...")
    
    # Check CoinDCX SHORT
    try:
        dcx_pos = dcx.get_position(test_symbol)
        if dcx_pos:
            qty = dcx_pos.get('quantity') or dcx_pos.get('qty') or dcx_pos.get('info', {}).get('qty')
            print(f"  ✓ CoinDCX SHORT {test_symbol}: qty={qty}")
        else:
            print(f"  ✗ CoinDCX SHORT {test_symbol}: NOT FOUND")
    except Exception as e:
        print(f"  ✗ CoinDCX SHORT check: {e}")
    
    # Check CoinSwitch LONG
    try:
        cs_pos = cs.get_position(test_symbol)
        if cs_pos:
            qty = cs_pos.get('quantity') or cs_pos.get('qty') or cs_pos.get('info', {}).get('qty')
            print(f"  ✓ CoinSwitch LONG {test_symbol}: qty={qty}")
        else:
            print(f"  ✗ CoinSwitch LONG {test_symbol}: NOT FOUND")
    except Exception as e:
        print(f"  ✗ CoinSwitch LONG check: {e}")
    
    # Test exit
    print("\n" + "="*80)
    print(f"TESTING EXIT: {test_symbol}")
    print("="*80)
    
    success, result = executor.execute_exit(test_symbol, 'coindcx', 'coinswitch', test_qty)
    print(f"\nExit result: {result}")
    
    if success:
        print("\n✓ EXIT SUCCESSFUL - Checking positions again...")
        
        # Check CoinDCX SHORT closed
        try:
            dcx_pos = dcx.get_position(test_symbol)
            if dcx_pos:
                qty = dcx_pos.get('quantity') or dcx_pos.get('qty') or dcx_pos.get('info', {}).get('qty')
                print(f"  ⚠ CoinDCX SHORT {test_symbol} STILL EXISTS: qty={qty}")
            else:
                print(f"  ✓ CoinDCX SHORT {test_symbol} CLOSED")
        except Exception as e:
            print(f"  (CoinDCX check: {e})")
        
        # Check CoinSwitch LONG closed
        try:
            cs_pos = cs.get_position(test_symbol)
            if cs_pos:
                qty = cs_pos.get('quantity') or cs_pos.get('qty') or cs_pos.get('info', {}).get('qty')
                print(f"  ⚠ CoinSwitch LONG {test_symbol} STILL EXISTS: qty={qty}")
            else:
                print(f"  ✓ CoinSwitch LONG {test_symbol} CLOSED")
        except Exception as e:
            print(f"  (CoinSwitch check: {e})")
    else:
        print("\n✗ EXIT FAILED")
else:
    print("\n✗ ENTRY FAILED")

print("\n" + "="*80)
