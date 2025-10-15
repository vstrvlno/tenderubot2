# tender_parser.py
import requests
import sqlite3
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from db import DB_PATH
from config import SITES as PLATFORMS  # импортируем площадки

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

# ----------------- Основной fetch -----------------
def fetch_tenders(limit=50):
    all_tenders = []

    for site in PLATFORMS:
        name = site.get("name")
        site_type = site.get("type")
        url = site.get("url")
        selector = site.get("selector")

        if not url:
            continue

        try:
            if site_type == "json":
                data = fetch_json(url)
                if isinstance(data, list):
                    for item in data[:limit]:
                        purchase_number = item.get("id") or item.get("purchase_number")
                        t_name = item.get("title") or item.get("name")
                        customer = item.get("ref_customer_name_ru") or item.get("customer")
                        amount = item.get("amount") or 0
                        publish_date = item.get("date") or item.get("publish_date") or ""
                        all_tenders.append({
                            "purchase_number": purchase_number,
                            "name": t_name,
                            "customer": customer,
                            "amount": amount,
                            "publish_date": publish_date
                        })
            elif site_type == "html":
                html = fetch_html(url)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select(selector or "")
                for el in items[:limit]:
                    t_name = el.get_text(strip=True)
                    purchase_number = el.get("href") or t_name
                    all_tenders.append({
                        "purchase_number": purchase_number,
                        "name": t_name,
                        "customer": "",
                        "amount": 0,
                        "publish_date": ""
                    })
            elif site_type == "xml":
                html = fetch_html(url)
                if not html:
                    continue
                soup = BeautifulSoup(html, "xml")
                for item in soup.find_all("tender")[:limit]:
                    purchase_number = item.find("id").text if item.find("id") else ""
                    t_name = item.find("title").text if item.find("title") else ""
                    customer = item.find("customer").text if item.find("customer") else ""
                    amount = float(item.find("amount").text) if item.find("amount") else 0
                    publish_date = item.find("date").text if item.find("date") else ""
                    all_tenders.append({
                        "purchase_number": purchase_number,
                        "name": t_name,
                        "customer": customer,
                        "amount": amount,
                        "publish_date": publish_date
                    })
            elif site_type == "rss":
                html = fetch_html(url)
                if not html:
                    continue
                soup = BeautifulSoup(html, "xml")
                for item in soup.find_all("item")[:limit]:
                    t_name = item.find("title").text if item.find("title") else ""
                    purchase_number = item.find("link").text if item.find("link") else t_name
                    publish_date = item.find("pubDate").text if item.find("pubDate") else ""
                    all_tenders.append({
                        "purchase_number": purchase_number,
                        "name": t_name,
                        "customer": "",
                        "amount": 0,
                        "publish_date": publish_date
                    })
        except Exception:
            logging.exception(f"Error parsing site: {name}")

    logging.info(f"Fetched {len(all_tenders)} tenders from platforms.")
    return all_tenders
