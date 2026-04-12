import sqlite3
import os

# Load .env_keys
keys = {}
if os.path.exists('.env_keys'):
    with open('.env_keys') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            keys[k.strip()] = v.strip().strip('"').strip("'")

DELTA_API_KEY    = keys.get('DHLKiTHWMAnIaFMSm797YQya49ylXs', '')
DELTA_API_SECRET = keys.get('b56WxXwEl2TStRgMmIvAU0u8ftRw46CgXSJppuCpGsHdmvxkskdas66cs7zn', '')

if not DELTA_API_KEY or not DELTA_API_SECRET:
    print('Delta API keys not found in .env_keys')
    exit(1)

DB_PATH = os.environ.get('USERS_DB', 'users.db')

with sqlite3.connect(DB_PATH) as c:
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if not row:
        print('No admin user found.')
        exit(1)
    admin_id = row['id']
    c.execute("UPDATE user_settings SET delta_key=?, delta_secret=? WHERE user_id=?", (DELTA_API_KEY, DELTA_API_SECRET, admin_id))
    print(f"Admin user {admin_id} updated with Delta keys from .env_keys.")
