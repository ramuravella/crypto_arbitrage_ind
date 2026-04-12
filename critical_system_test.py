#!/usr/bin/env python3
"""
CRITICAL TEST: Verify if EITHER exchange can actually execute trades
Test both CoinSwitch and CoinDCX with minimal parameters
"""
import json
import sys
sys.path.insert(0, '.')

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector

with open('config.json') as f:
    config = json.load(f)

cdx = CoinDCXConnector(config)
cs = CoinSwitchConnector(config)

print("=" * 80)
print("SYSTEM FUNCTIONALITY TEST: Can we execute trades on either exchange?")
print("=" * 80)

symbol = "HEMIUSDT"
test_qty = 1  # Minimal qty

print(f"\nTesting with: {symbol}, qty={test_qty}, leverage=1x")
print("-" * 80)

# Test 1: CoinDCX
print("\n[TEST 1] CoinDCX - open_long")
print(f"  API Key configured: {bool(cdx.api_key)}")
print(f"  Balance: ${cdx.get_balance_usdt():.2f}")
try:
    result = cdx.open_long(symbol, test_qty, 1)
    print(f"  ✓ SUCCESS: {result}")
    system_status_cdx = "WORKING"
except Exception as e:
    error_msg = str(e)
    print(f"  ✗ FAILED: {error_msg}")
    if "Insufficient funds" in error_msg:
        system_status_cdx = "ACCOUNT_ISSUE (insufficient funds)"
    elif "404" in error_msg or "not found" in error_msg.lower():
        system_status_cdx = "API_MISMATCH (404 endpoints)"
    else:
        system_status_cdx = "UNKNOWN_ERROR"

# Test 2: CoinSwitch
print("\n[TEST 2] CoinSwitch - open_long")
print(f"  API Key configured: {bool(cs.api_key)}")
print(f"  Balance: ${cs.get_balance_usdt():.2f}")
try:
    result = cs.open_long(symbol, test_qty, 1)
    print(f"  ✓ SUCCESS: {result}")
    system_status_cs = "WORKING"
except Exception as e:
    error_msg = str(e)
    print(f"  ✗ FAILED: {error_msg[:200]}")
    if "Insufficient funds" in error_msg or "insufficient" in error_msg.lower():
        system_status_cs = "ACCOUNT_ISSUE (insufficient funds)"
    elif "404" in error_msg or "not found" in error_msg.lower():
        system_status_cs = "API_MISMATCH (404 endpoints)"
    elif "balance" in error_msg.lower():
        system_status_cs = "BALANCE_ISSUE"
    else:
        system_status_cs = "UNKNOWN_ERROR"

print("\n" + "=" * 80)
print("SYSTEM STATUS REPORT")
print("=" * 80)
print(f"\nCoinDCX:     {system_status_cdx}")
print(f"CoinSwitch:  {system_status_cs}")

if system_status_cdx == "WORKING" and system_status_cs == "WORKING":
    print("\n✓ SYSTEM IS FUNCTIONAL - Both exchanges working")
elif system_status_cdx == "WORKING" or system_status_cs == "WORKING":
    print("\n⚠️  SYSTEM IS PARTIALLY FUNCTIONAL - One exchange works")
    working_ex = "CoinDCX" if system_status_cdx == "WORKING" else "CoinSwitch"
    print(f"   Can trade on {working_ex} only (arbitrage requires both)")
else:
    print("\n✗ SYSTEM IS NOT FUNCTIONAL - Both exchanges blocked")
    print(f"   CoinDCX issue: {system_status_cdx}")
    print(f"   CoinSwitch issue: {system_status_cs}")
    print("\n⚠️  CRITICAL: System cannot execute any trades in current state")

print("\n" + "=" * 80)
