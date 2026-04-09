# crypto_arbitrage_ind

A clean Python project for crypto arbitrage between Delta and CoinDCX only.

## Features
- Modular connectors for Delta and CoinDCX
- .env-based API key management
- Simple CLI for balance and funding rate checks

## Setup
1. Copy `.env.example` to `.env` and fill in your API keys.
2. Install dependencies:
   ```
pip install -r requirements.txt
   ```
3. Run the main script:
   ```
python main.py
   ```

## Usage
- The system will fetch balances and funding rates from both exchanges.
- Extend with your own trading logic as needed.

## Notes
- No legacy or unused code included.
- Only Delta and CoinDCX are supported.
