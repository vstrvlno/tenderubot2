import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(
    filename="parser.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def parse_rss(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "xml")
        items = soup.find_all("item")
        tenders = []
        for item in items[:10]:
            tenders.append({
                "title": item.title.text,
                "link": item.link.text,
                "date": item.pubDate.text
            })
        return tenders
    except Exception as e:
        logging.exception(f"RSS error {url}")
        return []

def parse_html(url, selector):
    if not url or not selector:
        return []
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        elements = soup.select(selector)
        tenders = []
        for el in elements[:10]:
            tenders.append({
                "title": el.get_text(strip=True),
                "link": el.get("href", url)
            })
        return tenders
    except Exception as e:
        logging.exception(f"HTML error {url}")
        return []

def parse_xml(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        tenders = []
        for tender in root.findall(".//tender"):
            tenders.append({
                "title": tender.findtext("title"),
                "link": tender.findtext("url"),
                "date": tender.findtext("date")
            })
        return tenders
    except Exception as e:
        logging.exception(f"XML error {url}")
        return []

def parse_json(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("results") or data.get("data") or data.get("tenders") or []
        tenders = []
        for t in items[:10]:
            tenders.append({
                "purchase_number": t.get("purchase_number") or t.get("id"),
                "name": t.get("name_ru") or t.get("name") or t.get("title"),
                "customer": t.get("ref_customer_name_ru") or t.get("customer"),
                "amount": t.get("amount"),
                "publish_date": t.get("publish_date") or t.get("date")
            })
        return tenders
    except Exception as e:
        logging.exception(f"JSON error {url}")
        return []
