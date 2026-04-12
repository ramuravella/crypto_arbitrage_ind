# set_admin_delta_keys_encrypted.py
# Usage: python set_admin_delta_keys_encrypted.py
# This script will encrypt and set the admin Delta API keys using your project's Fernet logic.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src import auth
import sqlite3

# === EDIT THESE WITH YOUR ACTUAL DELTA KEYS ===
DELTA_API_KEY = "DHLKiTHWMAnIaFMSm797YQya49ylXs"
DELTA_API_SECRET = "b56WxXwEl2TStRgMmIvAU0u8ftRw46CgXSJppuCpGsHdmvxkskdas66cs7zn"

DB_PATH = os.environ.get('USERS_DB', 'users.db')

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Find admin user
    c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    row = c.fetchone()
    if not row:
        print("No admin user found. Please register an admin user first.")
        sys.exit(1)
    admin_id = row[0]
    # Encrypt keys using project Fernet logic
    delta_key_enc = auth._encrypt(DELTA_API_KEY)
    delta_secret_enc = auth._encrypt(DELTA_API_SECRET)
    # Update user_settings for admin
    c.execute("UPDATE user_settings SET delta_key_enc=?, delta_secret_enc=? WHERE user_id=?", (
        delta_key_enc, delta_secret_enc, admin_id
    ))
    conn.commit()
    print("Admin Delta API keys (encrypted) updated successfully.")

if __name__ == "__main__":
    main()
