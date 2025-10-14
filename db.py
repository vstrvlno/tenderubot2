import sqlite3
from datetime import datetime
import logging

DB_PATH = "database.db"

logging.basicConfig(
    filename="parser.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def get_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def create_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_number TEXT UNIQUE,
            name TEXT,
            customer TEXT,
            amount REAL,
            publish_date TEXT,
            inserted_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            keyword TEXT,
            UNIQUE(user_id, keyword)
        )
    """)
    conn.commit()
    conn.close()
    logging.info("DB tables ensured.")

def save_new_tenders(tenders):
    conn = get_conn()
    cur = conn.cursor()
    added = []
    for t in tenders:
        name = t.get("name") or t.get("title") or ""
        purchase_number = t.get("purchase_number") or t.get("id") or ""
        customer = t.get("customer") or t.get("ref_customer_name_ru") or ""
        amount = t.get("amount") or 0
        publish_date = t.get("publish_date") or t.get("date") or ""
        if not purchase_number:
            continue
        try:
            cur.execute("""
                INSERT INTO tenders (purchase_number, name, customer, amount, publish_date, inserted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(purchase_number), name, customer, amount, publish_date, datetime.utcnow().isoformat()))
            conn.commit()
            added.append({
                "purchase_number": purchase_number,
                "name": name,
                "customer": customer,
                "amount": amount,
                "publish_date": publish_date
            })
        except sqlite3.IntegrityError:
            continue
        except Exception:
            logging.exception("Error inserting tender")
    conn.close()
    logging.info(f"Added {len(added)} new tenders.")
    return added

def get_subscriptions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, keyword FROM subscriptions")
    rows = cur.fetchall()
    conn.close()
    subs = {}
    for user_id, keyword in rows:
        subs.setdefault(keyword.lower(), set()).add(user_id)
    return subs

def add_subscription(user_id: int, keyword: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO subscriptions (user_id, keyword) VALUES (?, ?)", (user_id, keyword.strip().lower()))
        conn.commit()
    except Exception:
        logging.exception("Failed to add subscription")
    finally:
        conn.close()

def remove_subscription(user_id: int, keyword: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM subscriptions WHERE user_id=? AND keyword=?", (user_id, keyword.strip().lower()))
        conn.commit()
    except Exception:
        logging.exception("Failed to remove subscription")
    finally:
        conn.close()

def list_user_keywords(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT keyword FROM subscriptions WHERE user_id=?", (user_id,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows
