# test_delta_funding.py
import os
from pathlib import Path
from src.connectors.delta import DeltaConnector

# Load .env_keys manually
env_path = Path(__file__).parent / ".env_keys"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().replace('"', '').replace("'", "")
            v = v.strip().strip('"').strip("'")
            os.environ[k] = v

cfg = {"exchanges": {"delta": {"enabled": True}}}
delta = DeltaConnector(cfg)
rates = delta.get_funding_rates()
for symbol, info in rates.items():
    print(f"{symbol}: rate={info.rate}, next_settlement={info.next_settlement}, price={info.price}, vol_24h={info.volume_24h}")
