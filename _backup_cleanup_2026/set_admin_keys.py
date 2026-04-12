# Patch admin API keys for Delta and CoinDCX in users.db
# Usage: python set_admin_keys.py

import sqlite3
import sys

# === EDIT THESE WITH YOUR ACTUAL KEYS ===
COINDCX_KEY = "PUT_YOUR_COINDCX_KEY_HERE"
COINDCX_SECRET = "PUT_YOUR_COINDCX_SECRET_HERE"
DELTA_KEY = "PUT_YOUR_DELTA_KEY_HERE"
DELTA_SECRET = "PUT_YOUR_DELTA_SECRET_HERE"

DB_PATH = "users.db"

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
    # Update user_settings for admin
    c.execute("UPDATE user_settings SET coindcx_key_enc=?, coindcx_secret_enc=?, delta_key_enc=?, delta_secret_enc=? WHERE user_id=?", (
        COINDCX_KEY, COINDCX_SECRET, DELTA_KEY, DELTA_SECRET, admin_id
    ))
    conn.commit()
    print("Admin API keys updated successfully.")

if __name__ == "__main__":
    main()
