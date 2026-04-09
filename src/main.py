import sys
from connectors.coindcx import CoinDCXConnector
from connectors.delta import DeltaConnector


def print_balances():
    print("--- CoinDCX Balances ---")
    coindcx = CoinDCXConnector()
    print(coindcx.get_balance())
    print("\n--- Delta Balances ---")
    delta = DeltaConnector()
    print(delta.get_balance())

def print_funding_rates():
    print("--- Delta Funding Rates ---")
    delta = DeltaConnector()
    print(delta.get_funding_rates())
    print("\n--- CoinDCX Funding Rates (not available) ---")
    coindcx = CoinDCXConnector()
    print(coindcx.get_funding_rates())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "funding":
        print_funding_rates()
    else:
        print_balances()
