import requests
import sqlite3
import logging

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    filename="parser.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# === НАСТРОЙКИ ===
DB_PATH = "database.db"
LIMIT = 20
BASE_URL = "https://ows.goszakup.gov.kz/v3/public/orders"

# === СОЗДАНИЕ ТАБЛИЦ ===
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY,
            purchase_number TEXT UNIQUE,
            name TEXT,
            customer TEXT,
            amount REAL,
            publish_date TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            keyword TEXT,
            PRIMARY KEY(user_id, keyword)
        )
    """)
    conn.commit()
    conn.close()

# === ПОЛУЧЕНИЕ ТЕНДЕРОВ ===
def fetch_tenders():
    params = {"limit": LIMIT, "sort_by": "-publish_date"}
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Получено {len(data)} тендеров")
        return data
    except Exception as e:
        logging.error(f"Ошибка при запросе API: {e}")
        return []

# === СОХРАНЕНИЕ НОВЫХ ТЕНДЕРОВ ===
def save_tenders(tenders):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    new_count = 0
    for t in tenders:
        purchase_number = t.get("purchase_number")
        name = t.get("name_ru", "")
        customer = t.get("ref_customer_name_ru", "")
        amount = t.get("amount", 0)
        publish_date = t.get("publish_date", "")
        try:
            cur.execute("""
                INSERT INTO tenders (purchase_number, name, customer, amount, publish_date)
                VALUES (?, ?, ?, ?, ?)
            """, (purchase_number, name, customer, amount, publish_date))
            new_count += 1
        except sqlite3.IntegrityError:
            continue
    conn.commit()
    conn.close()
    logging.info(f"Добавлено {new_count} новых тендеров")
    return new_count

# === ПОЛУЧЕНИЕ ТЕНДЕРОВ ПО КЛЮЧЕВОМУ СЛОВУ ===
def get_tenders_by_keyword(keyword):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT name, customer, amount, publish_date, purchase_number
        FROM tenders
        WHERE LOWER(name) LIKE ?
        ORDER BY publish_date DESC
        LIMIT 10
    """, (f"%{keyword.lower()}%",))
    rows = cur.fetchall()
    conn.close()
    return rows

# === ПОЛУЧЕНИЕ ВСЕХ ПОДПИСЧИКОВ ===
def get_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT user_id FROM subscriptions")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

# === ПОЛУЧЕНИЕ КЛЮЧЕВЫХ СЛОВ ПОЛЬЗОВАТЕЛЯ ===
def get_user_keywords(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT keyword FROM subscriptions WHERE user_id=?", (user_id,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

# === ДОБАВЛЕНИЕ/УДАЛЕНИЕ ПОДПИСОК ===
def add_subscription(user_id, keyword):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO subscriptions(user_id, keyword) VALUES(?, ?)", (user_id, keyword))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def remove_subscription(user_id, keyword):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM subscriptions WHERE user_id=? AND keyword=?", (user_id, keyword))
    conn.commit()
    conn.close()
