import requests
import sqlite3
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from db import DB_PATH
from config import SITES as PLATFORMS # импортируем площадки

logging.basicConfig(
    filename="parser.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----------------- База данных -----------------
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
            source TEXT,
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

# ----------------- Подписки -----------------
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
        cur.execute(
            "INSERT OR IGNORE INTO subscriptions (user_id, keyword) VALUES (?, ?)",
            (user_id, keyword.strip().lower())
        )
        conn.commit()
    except Exception:
        logging.exception("Failed to add subscription")
    finally:
        conn.close()

def remove_subscription(user_id: int, keyword: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM subscriptions WHERE user_id=? AND keyword=?",
            (user_id, keyword.strip().lower())
        )
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

# ----------------- Парсеры -----------------
def fetch_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        logging.exception(f"Failed to fetch JSON from {url}")
        return []

def fetch_html(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception:
        logging.exception(f"Failed to fetch HTML from {url}")
        return ""

def save_tender(purchase_number, name, customer, amount, publish_date, source):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO tenders (purchase_number, name, customer, amount, publish_date, source, inserted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(purchase_number), name, customer, amount, publish_date, source, datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    except Exception:
        logging.exception("Error inserting tender")
    finally:
        conn.close()

