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
POKEWALLET_API_KEY = os.environ.get("POKEWALLET_API_KEY", "")
POKEWALLET_BASE_URL = "https://api.pokewallet.io"
CARDMARKET_API_KEY = (
    os.environ.get("CARDMARKET_API_KEY")
    or os.environ.get("RAPIDAPI_KEY")
    or os.environ.get("POKEWALLET_API_KEY", "")
)
CARDMARKET_API_BASE_URL = "https://cardmarket-api-tcg.p.rapidapi.com"

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
    item.setdefault("price_source", "")
    item.setdefault("price_source_url", "")
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


def parse_euro_prices(text):
    prices = []
    clean = (text or "").replace("\xa0", " ")
    for match in re.finditer(r"(\d+(?:[.,]\d{1,2})?)\s*€", clean):
        price = float(match.group(1).replace(",", "."))
        if 1 < price < 5000:
            prices.append(price)
    return prices


def clean_price_query(search_query, remove_pokemon=False):
    pattern = r"pokemon scellé|scellé|neuf"
    if remove_pokemon:
        pattern = r"pokemon scellé|scellé|neuf|pokemon"
    return re.sub(pattern, "", search_query, flags=re.IGNORECASE).strip()


def ebay_source_url(search_query):
    query_clean = clean_price_query(search_query)
    query = f"{query_clean} pokemon scellé"
    return f"https://www.ebay.fr/sch/i.html?_nkw={quote_plus(query)}&LH_Sold=1&LH_Complete=1&_sop=13"


def cardmarket_source_url(search_query):
    return cardmarket_product_search_url(search_query)


def pricecharting_source_url(search_query):
    query_clean = clean_price_query(search_query)
    return f"https://www.pricecharting.com/search-products?q={quote_plus(query_clean + ' pokemon')}&type=prices"


SET_ALIASES = {
    "equilibre parfait": "Perfect Order",
    "équilibre parfait": "Perfect Order",
    "foudre noire": "Black Bolt",
    "flamme blanche": "White Flare",
    "fable nebuleuse": "Shrouded Fable",
    "fable nébuleuse": "Shrouded Fable",
    "mascarade crepusculaire": "Twilight Masquerade",
    "mascarade crépusculaire": "Twilight Masquerade",
    "faille paradoxe": "Paradox Rift",
    "aventures ensemble": "Journey Together",
    "etincelles deferlantes": "Surging Sparks",
    "étincelles déferlantes": "Surging Sparks",
    "destinees de paldea": "Paldean Fates",
    "destinées de paldea": "Paldean Fates",
    "evolutions prismatiques": "Prismatic Evolutions",
    "évolutions prismatiques": "Prismatic Evolutions",
}


def normalize_search_text(text):
    normalized = (text or "").lower()
    replacements = {
        "à": "a", "á": "a", "â": "a", "ä": "a",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ç": "c",
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def search_tokens(text):
    stopwords = {
        "pokemon", "scelle", "scellee", "neuf", "neuve", "etb", "bundle",
        "coffret", "collection", "speciale", "special", "elite", "trainer",
        "box", "ev", "me", "eb", "carton", "plastique", "sorti", "sortie",
        "display", "booster", "tripack", "duopack", "tin", "tins",
    }
    return {token for token in normalize_search_text(text).split() if len(token) > 2 and token not in stopwords}


def translated_query(search_query):
    normalized = normalize_search_text(search_query)
    for french, english in SET_ALIASES.items():
        if normalize_search_text(french) in normalized:
            return english
    return ""


def cardmarket_product_search_url(search_query):
    query = translated_query(search_query) or clean_price_query(search_query, remove_pokemon=True)
    return f"https://www.cardmarket.com/fr/Pokemon/Products/Search?searchString={quote_plus(query)}"


def exact_cardmarket_product_url(search_query):
    translated = translated_query(search_query)
    if "Perfect Order" in translated and "etb" in normalize_search_text(search_query):
        return "https://www.cardmarket.com/fr/Pokemon/Products/Elite-Trainer-Boxes/Perfect-Order-Elite-Trainer-Box?sellerCountry=12&language=2"
    return cardmarket_product_search_url(search_query)


def build_cardmarket_queries(search_query):
    query_clean = clean_price_query(search_query, remove_pokemon=True)
    normalized = normalize_search_text(search_query)
    queries = []
    translated = translated_query(search_query)
    if translated:
        if "etb" in normalized:
            queries.append(f"{translated} Elite Trainer Box")
        queries.append(translated)
    queries.append(query_clean)
    if "etb" in normalized:
        queries.append(query_clean.replace("ETB", "").replace("etb", "").strip())
        queries.append(f"{query_clean} Elite Trainer Box")
    unique = []
    for query in queries:
        query = re.sub(r"\([^)]*\)", "", query).strip()
        if query and query not in unique:
            unique.append(query)
    return unique


def entry_matches_query(entry, search_query):
    name = entry.get("name") or entry.get("name_numbered") or entry.get("title") or ""
    source_tokens = search_tokens(search_query)
    name_tokens = search_tokens(name)
    translated = translated_query(search_query)
    if translated and normalize_search_text(translated) in normalize_search_text(name):
        return True
    if not source_tokens:
        return True
    return len(source_tokens & name_tokens) >= min(2, len(source_tokens))


def sane_price_for_item(price, item):
    if price is None:
        return False
    paid = float(item.get("prix_achete") or 0)
    if paid > 0 and price > max(paid * 4, paid + 180):
        return False
    return 1 < price < 5000


def get_ebay_market_price(search_query):
    if not EBAY_APP_ID:
        return None
    query_clean = clean_price_query(search_query)
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
    query_clean = clean_price_query(search_query, remove_pokemon=True)
    url = cardmarket_source_url(search_query)
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


def get_cardmarket_url_price(url):
    if not url or "cardmarket.com" not in url or "/Pokemon/" not in url:
        return None
    try:
        response = scraper.get(url, timeout=14)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        prices = []
        for selector in [
            ".table-body",
            ".table-body .col-offer",
            ".table-body .col-price",
            "div.col-offer",
            "div.col-price",
            ".price-container",
            "dt:contains('De') + dd",
            "dt:contains('Tendance des prix') + dd",
        ]:
            for tag in soup.select(selector):
                prices.extend(parse_euro_prices(tag.get_text(" ", strip=True)))
            if prices:
                break
        if prices:
            return round(min(prices[:12]), 2)
    except Exception as exc:
        app.logger.warning("Cardmarket URL erreur pour '%s': %s", url, exc)
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
    query_clean = clean_price_query(search_query)
    url = pricecharting_source_url(search_query)
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


def cardmarket_api_headers():
    if not CARDMARKET_API_KEY:
        return {}
    return {
        "x-rapidapi-key": CARDMARKET_API_KEY,
        "x-rapidapi-host": "cardmarket-api-tcg.p.rapidapi.com",
    }


def cardmarket_api_get(path, params=None):
    if not CARDMARKET_API_KEY:
        return None
    query_params = dict(params or {})
    query_params.setdefault("rapidapi-key", CARDMARKET_API_KEY)
    try:
        response = requests.get(
            f"{CARDMARKET_API_BASE_URL}{path}",
            params=query_params,
            headers=cardmarket_api_headers(),
            timeout=10,
        )
        if not response.ok:
            app.logger.warning("CardMarket API failed %s: %s", path, response.status_code)
            return None
        return response.json()
    except Exception as exc:
        app.logger.warning("CardMarket API erreur %s: %s", path, exc)
        return None


def iter_api_entries(payload):
    if not payload:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ["data", "results", "cards", "products", "items"]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []


def numeric_price(value):
    if isinstance(value, (int, float)) and 1 < value < 5000:
        return float(value)
    if isinstance(value, str):
        return parse_price(value)
    return None


def extract_cardmarket_api_price(entry):
    prices = entry.get("prices") if isinstance(entry, dict) else None
    candidates = []
    if isinstance(prices, dict):
        cardmarket = prices.get("cardmarket")
        if isinstance(cardmarket, dict):
            for key in [
                "market_price", "mid_price", "avg",
                "30d_average", "7d_average",
                "lowest_near_mint", "lowest_near_mint_ES",
                "lowest_near_mint_FR", "lowest_near_mint_IT",
            ]:
                price = numeric_price(cardmarket.get(key))
                if price:
                    candidates.append(price)
        tcgplayer = prices.get("tcg_player") or prices.get("tcgplayer")
        if isinstance(tcgplayer, dict):
            for key in ["market_price", "mid_price", "low_price"]:
                price = numeric_price(tcgplayer.get(key))
                if price:
                    candidates.append(price)
    for key in ["price", "market_price", "mid_price", "avg_price", "average_price"]:
        price = numeric_price(entry.get(key))
        if price:
            candidates.append(price)
    return round(statistics.median(candidates[:6]), 2) if candidates else None


def cardmarket_api_source_url(entry, search_query):
    for key in ["url", "cardmarket_url", "product_url", "link"]:
        value = entry.get(key)
        if isinstance(value, str) and value.startswith("http") and "/Pokemon/" in value:
            return value
    return exact_cardmarket_product_url(search_query)


def cardmarket_api_search_entries(search_query, limit=8):
    results = []
    seen = set()
    for query in build_cardmarket_queries(search_query):
        endpoints = [
            ("/pokemon/products", {"search": query, "sort": "price_lowest"}),
            ("/pokemon/products/search", {"search": query, "sort": "price_lowest"}),
        ]
        for path, params in endpoints:
            payload = cardmarket_api_get(path, params)
            for entry in iter_api_entries(payload):
                if not isinstance(entry, dict) or not entry_matches_query(entry, search_query):
                    continue
                name = entry.get("name") or entry.get("name_numbered") or entry.get("title") or query
                identity = f"{path}:{name}"
                if identity in seen:
                    continue
                seen.add(identity)
                entry["_api_path"] = path
                results.append(entry)
                if len(results) >= limit:
                    return results
    return results


def get_cardmarket_api_price(search_query):
    entries = cardmarket_api_search_entries(search_query, limit=8)
    prices = [extract_cardmarket_api_price(entry) for entry in entries]
    prices = [price for price in prices if price is not None]
    return round(statistics.median(prices[:6]), 2) if prices else None


def pokewallet_headers():
    if not POKEWALLET_API_KEY:
        return {}
    return {"X-API-Key": POKEWALLET_API_KEY}


def extract_pokewallet_price(entry):
    cardmarket = entry.get("cardmarket") or {}
    for price in cardmarket.get("prices", []) or []:
        for key in ["trend", "avg", "avg7", "avg30", "low"]:
            value = price.get(key)
            if isinstance(value, (int, float)) and 1 < value < 5000:
                return round(float(value), 2)
    tcgplayer = entry.get("tcgplayer") or {}
    for price in tcgplayer.get("prices", []) or []:
        for key in ["market_price", "mid_price", "low_price"]:
            value = price.get(key)
            if isinstance(value, (int, float)) and 1 < value < 5000:
                return round(float(value), 2)
    return None


def pokewallet_source_url(entry):
    cardmarket = entry.get("cardmarket") or {}
    if cardmarket.get("product_url"):
        return cardmarket["product_url"]
    tcgplayer = entry.get("tcgplayer") or {}
    return tcgplayer.get("url", "")


def search_pokewallet(query, limit=8):
    if not POKEWALLET_API_KEY:
        return []
    try:
        response = requests.get(
            f"{POKEWALLET_BASE_URL}/search",
            params={"q": query, "limit": limit},
            headers=pokewallet_headers(),
            timeout=8,
        )
        if not response.ok:
            app.logger.warning("PokéWallet search failed: %s", response.status_code)
            return []
        results = []
        for entry in response.json().get("results", [])[:limit]:
            card_info = entry.get("card_info") or {}
            name = card_info.get("name") or card_info.get("clean_name") or query
            card_id = entry.get("id", "")
            image_url = f"/api/pokewallet/image/{quote_plus(card_id)}" if card_id else PLACEHOLDER_IMAGE
            results.append({
                "nom": name,
                "image_url": image_url,
                "search_query": f"{name} pokemon",
                "prix_estime": extract_pokewallet_price(entry),
                "price_source": "PokéWallet",
                "price_source_url": pokewallet_source_url(entry),
            })
        return results
    except Exception as exc:
        app.logger.warning("PokéWallet erreur pour '%s': %s", query, exc)
    return []


def search_cardmarket_api(query, limit=8):
    results = []
    for entry in cardmarket_api_search_entries(query, limit=limit):
        name = entry.get("name") or entry.get("name_numbered") or entry.get("title") or query
        image = entry.get("image") or entry.get("image_url") or entry.get("thumbnail") or PLACEHOLDER_IMAGE
        price = extract_cardmarket_api_price(entry)
        results.append({
            "nom": name,
            "image_url": image,
            "search_query": f"{name} pokemon",
            "prix_estime": price,
            "price_source": "CardMarket API TCG",
            "price_source_url": cardmarket_api_source_url(entry, query),
        })
    return results


def update_item_price(item):
    search = item.get("search_query") or item.get("nom", "")
    timestamp = now_iso()
    ancien_prix = item.get("prix_marche")
    ancienne_source = item.get("price_source", "")
    ancienne_source_url = item.get("price_source_url", "")
    source = ""
    source_url = ""

    # Essai 1 : source Cardmarket choisie manuellement
    if item.get("price_source_url") and "cardmarket.com" in item.get("price_source_url", ""):
        market_price = get_cardmarket_url_price(item["price_source_url"])
        if sane_price_for_item(market_price, item):
            source = item.get("price_source") or "Cardmarket"
            source_url = item["price_source_url"]
        else:
            market_price = None
    else:
        market_price = None

    # Essai 2 : CardMarket API TCG via RapidAPI
    api_entries = cardmarket_api_search_entries(search, limit=8)
    api_prices = [extract_cardmarket_api_price(entry) for entry in api_entries]
    api_prices = [price for price in api_prices if sane_price_for_item(price, item)]
    market_price = market_price if market_price is not None else (round(statistics.median(api_prices[:6]), 2) if api_prices else None)
    if market_price is not None:
        source = source or "CardMarket API TCG"
        source_url = source_url or (cardmarket_api_source_url(api_entries[0], search) if api_entries else cardmarket_source_url(search))
    # Essai 3 : Cardmarket scraping
    if market_price is None:
        market_price = get_cardmarket_price(search)
        if not sane_price_for_item(market_price, item):
            market_price = None
    if market_price is not None:
        source = source or "Cardmarket"
        source_url = source_url or cardmarket_source_url(search)
    # Essai 4 : PriceCharting
    if market_price is None:
        market_price = get_pricecharting_price(search)
        if not sane_price_for_item(market_price, item):
            market_price = None
        if market_price is not None:
            source = "PriceCharting"
            source_url = pricecharting_source_url(search)
    # Essai 5 : eBay (si clé dispo)
    if market_price is None:
        market_price = get_ebay_market_price(search)
        if not sane_price_for_item(market_price, item):
            market_price = None
        if market_price is not None:
            source = "eBay"
            source_url = ebay_source_url(search)

    if market_price is not None:
        item["prix_marche"] = market_price
        item["derniere_maj"] = timestamp
        item["price_status"] = "ok"
        item["price_source"] = source
        item["price_source_url"] = source_url
    else:
        # IMPORTANT : conserver l'ancien prix au lieu de mettre 0
        if sane_price_for_item(ancien_prix, item):
            item["prix_marche"] = ancien_prix
            item["price_status"] = "cached"
            item["price_source"] = ancienne_source
            item["price_source_url"] = ancienne_source_url
        else:
            item["prix_marche"] = None
            item["price_status"] = "failed"
            item["price_source"] = ""
            item["price_source_url"] = ""
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
        for key in [
            "categorie", "nom", "quantite", "prix_achete", "prix_marche",
            "image_url", "search_query", "price_status", "price_source",
            "price_source_url", "derniere_maj",
        ]:
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


@app.get("/api/pokewallet/image/<card_id>")
def api_pokewallet_image(card_id):
    if not POKEWALLET_API_KEY:
        return Response(status=404)
    try:
        response = requests.get(
            f"{POKEWALLET_BASE_URL}/images/{card_id}",
            params={"size": request.args.get("size", "low")},
            headers=pokewallet_headers(),
            timeout=10,
        )
        if not response.ok:
            return Response(status=response.status_code)
        return Response(response.content, mimetype=response.headers.get("Content-Type", "image/jpeg"))
    except Exception as exc:
        app.logger.warning("PokéWallet image erreur '%s': %s", card_id, exc)
        return Response(status=404)


@app.get("/api/search_product")
def api_search_product():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": []})
    results = search_cardmarket_api(query)
    if results:
        return jsonify({"results": results})

    results = search_pokewallet(query)
    if results:
        return jsonify({"results": results})

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
        "search_query", "price_status", "price_source", "price_source_url",
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
