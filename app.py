import csv
import email.utils
import hashlib
import io
import json
import os
import random
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from urllib.parse import quote_plus

import feedparser
import requests
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
scraper.headers.update({"Referer": "https://www.google.fr/", "Accept": "text/html,application/xhtml+xml"})


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "collection.json"
EBAY_APP_ID = os.environ.get("EBAY_APP_ID", "")

CATEGORIES = [
    "ETB/BUNDLE",
    "COFFRET",
    "TINS",
    "POKEBOX",
    "TRIPACK/DUOPACK",
    "BOOSTER À L'UNITÉ/ARTSET",
]

PLACEHOLDER_IMAGE = "/static/images/pokeball.svg"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

SOURCES_ACTUALITES = [
    {
        "nom": "Pokémon TCG News",
        "url": "https://www.pokemon.com/fr/rss/news",
        "type": "rss",
    },
    {
        "nom": "Pokébip Actualités",
        "url": "https://www.pokebip.com/",
        "type": "scraping",
        "selector": ".news-item, article, .news",
    },
    {
        "nom": "PokéNews",
        "url": "https://www.pokemons.fr/news/",
        "type": "scraping",
        "selector": "article, .post, .news-item",
    },
]

INITIAL_ITEMS = [
    {"categorie": "ETB/BUNDLE", "nom": "ETB Equilibre Parfait (ME03)", "quantite": 1, "prix_achete": 45.00},
    {"categorie": "ETB/BUNDLE", "nom": "ETB Foudre Noire (EV10.5)", "quantite": 1, "prix_achete": 80.00},
    {"categorie": "ETB/BUNDLE", "nom": "ETB Flamme Blanche (EV10.5)", "quantite": 1, "prix_achete": 80.00},
    {"categorie": "ETB/BUNDLE", "nom": "ETB Fable Nébuleuse (EV6.5)", "quantite": 1, "prix_achete": 65.00},
    {"categorie": "ETB/BUNDLE", "nom": "ETB Mascarade Crépusculaire (EV06)", "quantite": 1, "prix_achete": 75.00},
    {"categorie": "ETB/BUNDLE", "nom": "ETB Faille Paradoxe Garde-De-Fer (EV04)", "quantite": 1, "prix_achete": 75.00},
    {"categorie": "ETB/BUNDLE", "nom": "BUNDLE Héros Transcendants", "quantite": 1, "prix_achete": 30.00},
    {"categorie": "COFFRET", "nom": "UPC MEGA DRACAUFEU X (ME02)", "quantite": 1, "prix_achete": 160.00},
    {"categorie": "COFFRET", "nom": "Coffret Dracaufeu Collection Spéciale (EV09)", "quantite": 3, "prix_achete": 35.00},
    {"categorie": "COFFRET", "nom": "Coffret Amphinobi et Hyporoi Collection Spéciale", "quantite": 1, "prix_achete": 50.00},
    {"categorie": "COFFRET", "nom": "Coffret classeur Foudre Noire (EV10.5)", "quantite": 1, "prix_achete": 45.00},
    {"categorie": "COFFRET", "nom": "Coffret classeur Flamme Blanche (EV10.5)", "quantite": 1, "prix_achete": 45.00},
    {"categorie": "COFFRET", "nom": "Coffret Victini Collection Illustration (EV10.5)", "quantite": 1, "prix_achete": 26.00},
    {"categorie": "COFFRET", "nom": "Coffret Collection Poster Unys (EV10.5)", "quantite": 1, "prix_achete": 34.00},
    {"categorie": "COFFRET", "nom": "Coffret Méga-Florizarre Collection-Premium (ME01)", "quantite": 1, "prix_achete": 45.00},
    {"categorie": "COFFRET", "nom": "Coffret Méga-Kangourex (ME01)", "quantite": 1, "prix_achete": 25.00},
    {"categorie": "COFFRET", "nom": "Coffret Collection Journée Pokémon 2026", "quantite": 1, "prix_achete": 20.00},
    {"categorie": "TINS", "nom": "TINS ME2.5", "quantite": 2, "prix_achete": 13.00},
    {"categorie": "TINS", "nom": "TINS EV10.5", "quantite": 2, "prix_achete": 12.00},
    {"categorie": "TINS", "nom": "TINS POUVOIR DE KANTO", "quantite": 9, "prix_achete": 18.00},
    {"categorie": "TINS", "nom": "BIS BALL TIN", "quantite": 1, "prix_achete": 18.00},
    {"categorie": "TINS", "nom": "Valisette de Combat (ME01)", "quantite": 1, "prix_achete": 38.00},
    {"categorie": "POKEBOX", "nom": "POKEBOX MIRAIDON (EV09)", "quantite": 1, "prix_achete": 24.00},
    {"categorie": "POKEBOX", "nom": "POKEBOX ZACIAN (EV09)", "quantite": 1, "prix_achete": 24.00},
    {"categorie": "POKEBOX", "nom": "POKEBOX MEGA-DRACAUFEU X (ME02)", "quantite": 1, "prix_achete": 26.00},
    {"categorie": "TRIPACK/DUOPACK", "nom": "TRIPACK Flamme Blanche", "quantite": 1, "prix_achete": 18.00},
    {"categorie": "TRIPACK/DUOPACK", "nom": "TRIPACK Foudre Noire", "quantite": 1, "prix_achete": 18.00},
    {"categorie": "TRIPACK/DUOPACK", "nom": "TRIPACK Aventures Ensemble", "quantite": 4, "prix_achete": 20.00},
    {"categorie": "TRIPACK/DUOPACK", "nom": "DUOPACK EV06/EV03", "quantite": 1, "prix_achete": 12.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "ARTSET EV09 CARTON", "quantite": 1, "prix_achete": 24.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "ARTSET EV09 PLASTIQUE", "quantite": 1, "prix_achete": 28.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "BOOSTER EV09 PLASTIQUE", "quantite": 2, "prix_achete": 14.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "BOOSTER EV08 PLASTIQUE (Pikachu)", "quantite": 1, "prix_achete": 0.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "ARTSET BOOSTER EV08 (SORTI DISPLAY)", "quantite": 1, "prix_achete": 24.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "BOOSTER EV07 (SORTI DISPLAY)", "quantite": 1, "prix_achete": 0.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "BOOSTER EB12 (SORTI DISPLAY)", "quantite": 2, "prix_achete": 7.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "BOOSTER EB10 (SORTI DISPLAY)", "quantite": 2, "prix_achete": 7.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "ARTSET EV06 (SORTIE DISPLAY)", "quantite": 1, "prix_achete": 24.00},
    {"categorie": "BOOSTER À L'UNITÉ/ARTSET", "nom": "ARTSET EB09 PLASTIQUE", "quantite": 1, "prix_achete": 24.00},
]

app = Flask(__name__)
CORS(app)
progress_queue = Queue()
data_lock = threading.Lock()


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def slugify(text):
    normalized = text.lower()
    normalized = re.sub(r"[àáâäãå]", "a", normalized)
    normalized = re.sub(r"[èéêë]", "e", normalized)
    normalized = re.sub(r"[ìíîï]", "i", normalized)
    normalized = re.sub(r"[òóôöõ]", "o", normalized)
    normalized = re.sub(r"[ùúûü]", "u", normalized)
    normalized = re.sub(r"[ç]", "c", normalized)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:6]
    return f"{normalized}_{digest}" if normalized else digest


def compute_item(item):
    quantity = int(item.get("quantite") or 0)
    paid = float(item.get("prix_achete") or 0)
    market = item.get("prix_marche")
    market = float(market) if market not in (None, "") else None
    item["val_marche_totale"] = round((market or 0) * quantity, 2)
    item["variation_pct"] = round(((market - paid) / paid) * 100, 1) if paid > 0 and market is not None else None
    item.setdefault("image_url", PLACEHOLDER_IMAGE)
    item.setdefault("search_query", item.get("nom", ""))
    item.setdefault("derniere_maj", "")
    item.setdefault("price_status", "pending")
    return item


def normalize_item(raw):
    item = deepcopy(raw)
    item.setdefault("id", slugify(item.get("nom", "")))
    item.setdefault("prix_marche", None)
    item.setdefault("search_query", f"{item.get('nom', '')} pokemon scellé")
    return compute_item(item)


def load_collection():
    if not DATA_FILE.exists():
        items = [normalize_item(item) for item in INITIAL_ITEMS]
        data = {"last_updated": now_iso(), "items": items}
        save_collection(data)
        return data
    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    data.setdefault("last_updated", now_iso())
    data["items"] = [compute_item(item) for item in data.get("items", [])]
    return data


def save_collection(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_collection(data):
    items = data.get("items", [])
    total_units = sum(int(item.get("quantite") or 0) for item in items)
    total_cost = sum(float(item.get("prix_achete") or 0) * int(item.get("quantite") or 0) for item in items)
    total_market = sum(float(item.get("val_marche_totale") or 0) for item in items)
    pnl = total_market - total_cost
    pnl_pct = (pnl / total_cost) * 100 if total_cost else 0
    return {
        "total_items": len(items),
        "total_units": total_units,
        "total_cost": round(total_cost, 2),
        "total_market": round(total_market, 2),
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 1),
    }


def headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def parse_price(text):
    clean = text.replace("\xa0", " ").replace("EUR", "€")
    clean = re.sub(r"\s+", " ", clean)
    match = re.search(r"(\d+(?:[.,]\d{1,2})?)", clean)
    if not match:
        return None
    price = float(match.group(1).replace(",", "."))
    return price if 1 < price < 5000 else None


def get_ebay_market_price(search_query):
    if not EBAY_APP_ID:
        return get_cardmarket_price(search_query)
    query_clean = re.sub(r"pokemon scellé|scellé|neuf", "", search_query, flags=re.IGNORECASE).strip()
    try:
        url = "https://svcs.ebay.com/services/search/FindingService/v1"
        params = {
            "OPERATION-NAME": "findCompletedItems",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": EBAY_APP_ID,
            "RESPONSE-DATA-FORMAT": "JSON",
            "keywords": f"{query_clean} pokemon scellé",
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
            "itemFilter(1).name": "Condition",
            "itemFilter(1).value": "1000",
            "sortOrder": "EndTimeSoonest",
            "paginationInput.entriesPerPage": "15",
            "outputSelector": "SellingStatus",
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        items = data.get("findCompletedItemsResponse", [{}])[0].get("searchResult", [{}])[0].get("item", [])
        prices = []
        for item in items:
            try:
                price = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
                if 1 < price < 5000:
                    prices.append(price)
            except Exception:
                continue
        if len(prices) >= 2:
            return round(statistics.median(prices), 2)
    except Exception as exc:
        app.logger.warning("eBay API failed: %s", exc)
    return get_cardmarket_price(search_query)


def get_cardmarket_price(search_query):
    query_clean = re.sub(r"pokemon scellé|scellé|neuf|pokemon", "", search_query, flags=re.IGNORECASE).strip()
    url = f"https://www.cardmarket.com/fr/Pokemon/Products/Search?searchString={quote_plus(query_clean)}&idCategory=18"
    try:
        response = scraper.get(url, timeout=14)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        prices = []
        for selector in [
            "div.col-price span.font-weight-bold",
            "div.price-container",
            "span.color-primary.small",
            "div.info-list-container dd",
        ]:
            for tag in soup.select(selector):
                price = parse_price(tag.get_text(" ", strip=True))
                if price and 1 < price < 5000:
                    prices.append(price)
            if prices:
                break
        if prices:
            return round(min(prices), 2)
    except Exception as exc:
        app.logger.warning("Cardmarket erreur pour '%s': %s", query_clean, exc)
    return None


def get_product_image(search_query):
    try:
        tcg_url = "https://api.pokemontcg.io/v2/sets"
        response = scraper.get(tcg_url, params={"q": f'name:"{search_query}"'}, timeout=8)
        if response.ok:
            for item in response.json().get("data", []):
                images = item.get("images") or {}
                if images.get("logo"):
                    return images["logo"]
                if images.get("symbol"):
                    return images["symbol"]
    except Exception:
        pass

    try:
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(search_query + ' pokemon scellé')}"
        response = scraper.get(search_url, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")
        image = soup.select_one("img")
        if image and image.get("src"):
            return image["src"]
    except Exception:
        pass
    return PLACEHOLDER_IMAGE


def get_pricecharting_price(search_query):
    query_clean = re.sub(r"pokemon scellé|scellé|neuf", "", search_query, flags=re.IGNORECASE).strip()
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query_clean + ' pokemon')}&type=prices"
    try:
        response = scraper.get(url, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        prices = []
        for selector in ["td.price", ".price", "span.price"]:
            for tag in soup.select(selector):
                price = parse_price(tag.get_text(" ", strip=True))
                if price and 1 < price < 5000:
                    prices.append(price)
            if prices:
                break
        if prices:
            return round(statistics.median(prices[:8]), 2)
    except Exception as exc:
        app.logger.warning("PriceCharting erreur pour '%s': %s", query_clean, exc)
    return None


def update_item_price(item):
    search = item.get("search_query") or item.get("nom", "")
    timestamp = now_iso()
    ancien_prix = item.get("prix_marche")

    # Essai 1 : Cardmarket
    market_price = get_cardmarket_price(search)
    # Essai 2 : PriceCharting
    if market_price is None:
        market_price = get_pricecharting_price(search)
    # Essai 3 : eBay (si clé dispo)
    if market_price is None:
        market_price = get_ebay_market_price(search)

    if market_price is not None:
        item["prix_marche"] = market_price
        item["derniere_maj"] = timestamp
        item["price_status"] = "ok"
    else:
        # IMPORTANT : conserver l'ancien prix au lieu de mettre 0
        if ancien_prix is not None:
            item["prix_marche"] = ancien_prix
            item["price_status"] = "cached"
        else:
            item["price_status"] = "failed"
        item["derniere_maj"] = timestamp

    if not item.get("image_url") or item.get("image_url") == PLACEHOLDER_IMAGE:
        item["image_url"] = get_product_image(search)
    return compute_item(item)


def tag_news(title, summary):
    content = f"{title} {summary}".lower()
    tags = []
    if any(word in content for word in ["leak", "rumeur", "révélé", "revealed"]):
        tags.append("🔥 Leak")
    if any(word in content for word in ["restock", "stock", "réassort", "reassort"]):
        tags.append("📦 Restock")
    if any(word in content for word in ["sortie", "date", "release"]):
        tags.append("📅 Sortie")
    if any(word in content for word in ["prix", "market", "cote"]):
        tags.append("💰 Prix")
    if not tags:
        tags.append("🆕 Annonce")
    return tags


def compact_text(text, limit=520):
    clean = re.sub(r"\s+", " ", BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)).strip()
    return clean[:limit].rsplit(" ", 1)[0] + "..." if len(clean) > limit else clean


def get_article_image(url):
    if not url:
        return ""
    try:
        # Suivre la redirection Google News pour obtenir l'URL réelle
        resp = scraper.get(url, timeout=8, allow_redirects=True)
        final_url = resp.url
        soup = BeautifulSoup(resp.text, "html.parser")
        for attr in [("property", "og:image"), ("name", "twitter:image"), ("property", "og:image:url")]:
            tag = soup.find("meta", {attr[0]: attr[1]})
            if tag and tag.get("content", "").startswith("http"):
                return tag["content"]
    except Exception:
        pass
    return ""


def parse_article_date(date_str):
    if not date_str:
        return None
    try:
        return datetime(*email.utils.parsedate(date_str)[:6], tzinfo=timezone.utc)
    except Exception:
        return None


def fetch_news():
    GOOGLE_NEWS_FEEDS = [
        {"url": "https://news.google.com/rss/search?q=pokemon+TCG+carte+france+restock&hl=fr&gl=FR&ceid=FR:fr", "nom": "Restocks FR"},
        {"url": "https://news.google.com/rss/search?q=pokemon+carte+nouvelle+extension+sortie+2026&hl=fr&gl=FR&ceid=FR:fr", "nom": "Nouvelles extensions"},
        {"url": "https://news.google.com/rss/search?q=pokemon+TCG+leak+reveal+2026&hl=fr&gl=FR&ceid=FR:fr", "nom": "Leaks & Reveals"},
        {"url": "https://news.google.com/rss/search?q=pokemon+card+game+prix+cote+sealed&hl=fr&gl=FR&ceid=FR:fr", "nom": "Prix & Marché"},
    ]
    articles = []
    seen_titles = set()
    for feed_info in GOOGLE_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:4]:
                title = entry.get("title", "").split(" - ")[0].strip()
                if not title or title in seen_titles or len(title) < 10:
                    continue
                seen_titles.add(title)
                summary = compact_text(entry.get("summary", entry.get("description", "")))
                image_url = ""
                content = entry.get("content", [{}])
                if content and isinstance(content, list):
                    img_soup = BeautifulSoup(content[0].get("value", ""), "html.parser")
                    img_tag = img_soup.find("img")
                    if img_tag:
                        image_url = img_tag.get("src", "")
                entry_url = entry.get("link", "")
                articles.append({"title": title, "summary": summary or "Clique sur Lire la suite pour voir l'article.", "source": feed_info["nom"], "date": entry.get("published", ""), "url": entry_url, "image": image_url, "tags": tag_news(title, summary)})
        except Exception as exc:
            app.logger.warning("Google News RSS '%s' échoué : %s", feed_info["nom"], exc)
    if len(articles) < 3:
        try:
            official = feedparser.parse("https://www.pokemon.com/fr/rss/news")
            for entry in official.entries[:4]:
                title = entry.get("title", "")
                summary = compact_text(entry.get("summary", ""))
                if title and title not in seen_titles:
                    entry_url = entry.get("link", "")
                    articles.append({"title": title, "summary": summary, "source": "Pokémon Officiel FR", "date": entry.get("published", ""), "url": entry_url, "image": "", "tags": tag_news(title, summary)})
        except Exception as exc:
            app.logger.warning("RSS Pokémon officiel échoué : %s", exc)
    if not articles:
        articles = [{"title": "Connexion aux sources d'actualité impossible", "summary": "Les flux RSS ne sont pas accessibles. Vérifie ta connexion et clique sur Actualiser.", "source": "Hors ligne", "date": now_iso(), "url": "https://www.pokemon.com/fr/actus-pokemon", "image": "", "tags": ["🆕 Annonce"]}]
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_by_index = {
            executor.submit(get_article_image, article.get("url", "")): index
            for index, article in enumerate(articles)
            if article.get("url")
        }
        for future, index in future_by_index.items():
            try:
                articles[index]["image"] = future.result()
            except Exception:
                pass
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    articles = [a for a in articles if (parse_article_date(a["date"]) or datetime.now(timezone.utc)) > one_year_ago]
    articles.sort(key=lambda a: parse_article_date(a["date"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles[:12]


def find_item(data, item_id):
    return next((item for item in data["items"] if item["id"] == item_id), None)


@app.route("/")
@app.route("/marche")
def index():
    return render_template("index.html", categories=CATEGORIES)


@app.get("/api/collection")
def api_collection():
    with data_lock:
        data = load_collection()
    return jsonify({"collection": data, "summary": summarize_collection(data), "categories": CATEGORIES})


@app.post("/api/collection/add")
def api_add_item():
    payload = request.get_json(force=True)
    with data_lock:
        data = load_collection()
        item = normalize_item(payload)
        existing_ids = {entry["id"] for entry in data["items"]}
        base_id = item["id"]
        index = 2
        while item["id"] in existing_ids:
            item["id"] = f"{base_id}_{index}"
            index += 1
        data["items"].append(item)
        data["last_updated"] = now_iso()
        save_collection(data)
    return jsonify({"item": item, "summary": summarize_collection(data)}), 201


@app.put("/api/collection/<item_id>")
def api_update_item(item_id):
    payload = request.get_json(force=True)
    with data_lock:
        data = load_collection()
        item = find_item(data, item_id)
        if not item:
            return jsonify({"error": "Item introuvable"}), 404
        for key in ["categorie", "nom", "quantite", "prix_achete", "prix_marche", "image_url", "search_query"]:
            if key in payload:
                item[key] = payload[key]
        compute_item(item)
        data["last_updated"] = now_iso()
        save_collection(data)
    return jsonify({"item": item, "summary": summarize_collection(data)})


@app.delete("/api/collection/<item_id>")
def api_delete_item(item_id):
    with data_lock:
        data = load_collection()
        before = len(data["items"])
        data["items"] = [item for item in data["items"] if item["id"] != item_id]
        if len(data["items"]) == before:
            return jsonify({"error": "Item introuvable"}), 404
        data["last_updated"] = now_iso()
        save_collection(data)
    return jsonify({"ok": True, "summary": summarize_collection(data)})


@app.get("/api/price/<item_id>")
@app.get("/api/update_price/<item_id>")
def api_update_price(item_id):
    with data_lock:
        data = load_collection()
        item = find_item(data, item_id)
        if not item:
            return jsonify({"error": "Item introuvable"}), 404
    updated = update_item_price(item)
    with data_lock:
        data = load_collection()
        saved = find_item(data, item_id)
        saved.update(updated)
        data["last_updated"] = now_iso()
        save_collection(data)
    return jsonify({"item": updated, "summary": summarize_collection(data)})


def update_all_worker():
    with data_lock:
        data = load_collection()
        item_ids = [item["id"] for item in data["items"]]
    total = len(item_ids)
    for index, item_id in enumerate(item_ids, start=1):
        with data_lock:
            data = load_collection()
            item = find_item(data, item_id)
            if not item:
                continue
        progress_queue.put({"type": "progress", "current": index, "total": total, "item": item["nom"]})
        updated = update_item_price(item)
        with data_lock:
            data = load_collection()
            saved = find_item(data, item_id)
            if saved:
                saved.update(updated)
                data["last_updated"] = now_iso()
                save_collection(data)
        progress_queue.put({"type": "item_done", "current": index, "total": total, "item": updated})
        if index < total:
            time.sleep(random.uniform(1.0, 2.0))
    progress_queue.put({"type": "complete", "message": "Mise à jour terminée"})


@app.post("/api/price/update_all")
@app.post("/api/update_all_prices")
def api_update_all_prices():
    thread = threading.Thread(target=update_all_worker, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Mise à jour lancée"})


@app.get("/api/price/stream")
def api_price_stream():
    def stream():
        while True:
            message = progress_queue.get()
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            if message.get("type") == "complete":
                break
    return Response(stream(), mimetype="text/event-stream")


@app.get("/api/search_product")
def api_search_product():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    results = []
    try:
        response = scraper.get(
            "https://api.pokemontcg.io/v2/sets",
            params={"q": f'name:"{query}"', "pageSize": 8},
            timeout=8,
        )
        if response.ok:
            for entry in response.json().get("data", [])[:8]:
                images = entry.get("images") or {}
                image = images.get("logo") or images.get("symbol") or PLACEHOLDER_IMAGE
                results.append({
                    "nom": entry.get("name", query),
                    "image_url": image,
                    "search_query": f"{entry.get('name', query)} pokemon scellé",
                    "prix_estime": None,
                })
    except Exception:
        pass
    # Si rien trouvé, recherche large
    if not results:
        try:
            response = scraper.get(
                "https://api.pokemontcg.io/v2/sets",
                params={"q": f'name:{query}*', "pageSize": 6},
                timeout=8,
            )
            if response.ok:
                for entry in response.json().get("data", [])[:6]:
                    images = entry.get("images") or {}
                    image = images.get("logo") or images.get("symbol") or PLACEHOLDER_IMAGE
                    results.append({
                        "nom": entry.get("name", query),
                        "image_url": image,
                        "search_query": f"{entry.get('name', query)} pokemon scellé",
                        "prix_estime": None,
                    })
        except Exception:
            pass
    # Fallback : retourne au moins le terme tapé
    if not results:
        results.append({
            "nom": query,
            "image_url": PLACEHOLDER_IMAGE,
            "search_query": f"{query} pokemon scellé",
            "prix_estime": None,
        })
    return jsonify({"results": results})


@app.get("/api/news")
def api_news():
    with data_lock:
        data = load_collection()
    items = data.get("items", [])
    sorted_up = sorted(
        [item for item in items if item.get("variation_pct") is not None],
        key=lambda item: item.get("variation_pct", 0),
        reverse=True,
    )
    sorted_down = list(reversed(sorted_up))
    return jsonify({
        "articles": fetch_news(),
        "trends": {
            "up": sorted_up[:5],
            "down": sorted_down[:5],
        },
    })


@app.get("/api/export/csv")
def api_export_csv():
    with data_lock:
        data = load_collection()
    output = io.StringIO()
    fieldnames = [
        "id", "categorie", "nom", "quantite", "prix_achete", "prix_marche",
        "val_marche_totale", "variation_pct", "derniere_maj", "image_url",
        "search_query", "price_status",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in data.get("items", []):
        writer.writerow({key: item.get(key, "") for key in fieldnames})
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=pokemon_collection.csv"},
    )


if __name__ == "__main__":
    load_collection()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
