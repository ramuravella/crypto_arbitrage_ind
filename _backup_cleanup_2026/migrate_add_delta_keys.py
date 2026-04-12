import sqlite3
import os

DB_PATH = os.environ.get("USERS_DB", "users.db")

def migrate():
    with sqlite3.connect(DB_PATH) as c:
        # Add delta columns if missing
        try:
            c.execute("ALTER TABLE user_settings ADD COLUMN delta_key TEXT DEFAULT ''")
        except Exception as e:
            if "duplicate" not in str(e).lower():
                print("delta_key:", e)
        try:
            c.execute("ALTER TABLE user_settings ADD COLUMN delta_secret TEXT DEFAULT ''")
        except Exception as e:
            if "duplicate" not in str(e).lower():
                print("delta_secret:", e)
        try:
            c.execute("ALTER TABLE user_settings ADD COLUMN delta_key_enc TEXT DEFAULT ''")
        except Exception as e:
            if "duplicate" not in str(e).lower():
                print("delta_key_enc:", e)
        try:
            c.execute("ALTER TABLE user_settings ADD COLUMN delta_secret_enc TEXT DEFAULT ''")
        except Exception as e:
            if "duplicate" not in str(e).lower():
                print("delta_secret_enc:", e)
        print("Migration complete. Delta columns ensured.")

if __name__ == "__main__":
    migrate()
