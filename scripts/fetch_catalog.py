#!/usr/bin/env python3
"""
Fetch saree listings from the shops in sources.json and write data/catalog.json.

Supported platforms:
  shopify      -> {base}{collection}/products.json?limit=250&page=N   (public, no auth)
  woocommerce  -> {base}/wp-json/wc/store/v1/products?per_page=100&page=N  (public Store API)
  auto         -> probe Shopify first, then WooCommerce, else skip with a note

Run locally:   python scripts/fetch_catalog.py
Runs in CI via .github/workflows/refresh.yml
"""
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
OUT_FILE = ROOT / "data" / "catalog.json"

UA = "Mozilla/5.0 (personal saree gallery; polite fetcher; contact via repo)"
TIMEOUT = 25
MAX_PER_BRAND = 1000      # sarees kept per shop
MAX_SCAN = 3000           # raw products scanned when a whole store must be filtered
MAX_IMAGES = 4
SAREE_RE = re.compile(r"\b(saree|sarees|sari|saris)\b", re.I)
FABRIC_WORDS = [
    "linen", "khadi", "silk", "cotton", "tussar", "tissue", "organza", "chiffon",
    "georgette", "banarasi", "chanderi", "kanjivaram", "kanjeevaram", "jamdani",
    "mashru", "muslin", "mul", "wool", "zari", "ikat", "ajrakh", "dabu", "bagru",
    "kalamkari", "crepe", "satin", "velvet", "net", "handloom", "handwoven",
]
SHOPIFY_COLLECTION_GUESSES = [
    "/collections/sarees", "/collections/saree", "/collections/sari", "/collections/saris",
]

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "application/json"})


def log(msg):
    print(msg, flush=True)


def get_json(url, params=None):
    """GET url, return parsed JSON or None. One retry on transient failure."""
    for attempt in (1, 2):
        try:
            r = session.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(8)
                continue
            r.raise_for_status()
            ct = r.headers.get("content-type", "")
            if "json" not in ct and not r.text.lstrip().startswith(("{", "[")):
                return None
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if attempt == 2:
                log(f"    ! {url} -> {e}")
                return None
            time.sleep(2)
    return None


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>|</p>|</li>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def fabric_tags(*texts):
    blob = " ".join(t for t in texts if t).lower()
    return sorted({w for w in FABRIC_WORDS if re.search(rf"\b{w}\b", blob)})


def is_saree(*texts):
    return any(SAREE_RE.search(t or "") for t in texts)


# ---------------------------------------------------------------- Shopify ----
def shopify_products(base, collection, cap=MAX_PER_BRAND):
    items, page = [], 1
    while True:
        url = f"{base}{collection}/products.json"
        data = get_json(url, params={"limit": 250, "page": page})
        if not data or not data.get("products"):
            break
        items.extend(data["products"])
        if len(data["products"]) < 250 or len(items) >= cap:
            break
        page += 1
        time.sleep(0.6)
    return items[:cap]


def normalise_shopify(p, src):
    variants = p.get("variants") or []
    price = None
    available = False
    if variants:
        try:
            price = float(variants[0].get("price"))
        except (TypeError, ValueError):
            price = None
        available = any(v.get("available") for v in variants)
    images = [im.get("src") for im in (p.get("images") or []) if im.get("src")][:MAX_IMAGES]
    desc = strip_html(p.get("body_html"))
    tags = p.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return {
        "id": f"{src['key']}:{p.get('id')}",
        "brand": src["key"],
        "title": (p.get("title") or "").strip(),
        "url": f"{src['base']}/products/{p.get('handle')}",
        "price": price,
        "currency": "INR",
        "images": images,
        "available": available,
        "type": p.get("product_type") or "",
        "tags": tags,
        "fabric": fabric_tags(p.get("title"), p.get("product_type"), " ".join(tags), desc),
        "description": desc[:500],
        "published": p.get("published_at") or p.get("created_at"),
    }


# ------------------------------------------------------------ WooCommerce ----
def woo_products(base, category=None, cap=MAX_SCAN):
    items, page = [], 1
    while True:
        params = {"per_page": 100, "page": page}
        if category:
            params["category"] = category
        data = get_json(f"{base}/wp-json/wc/store/v1/products", params=params)
        if not data or not isinstance(data, list):
            break
        items.extend(data)
        if len(data) < 100 or len(items) >= cap:
            break
        page += 1
        time.sleep(0.6)
    return items


def normalise_woo(p, src):
    prices = p.get("prices") or {}
    price = None
    try:
        minor = int(prices.get("currency_minor_unit", 2))
        price = int(prices.get("price")) / (10 ** minor)
    except (TypeError, ValueError):
        pass
    images = [im.get("src") for im in (p.get("images") or []) if im.get("src")][:MAX_IMAGES]
    cats = [c.get("slug", "") for c in (p.get("categories") or [])]
    tags = [t.get("name", "") for t in (p.get("tags") or [])]
    desc = strip_html(p.get("short_description") or p.get("description"))
    return {
        "id": f"{src['key']}:{p.get('id')}",
        "brand": src["key"],
        "title": strip_html(p.get("name")),
        "url": p.get("permalink"),
        "price": price,
        "currency": prices.get("currency_code") or "INR",
        "images": images,
        "available": bool(p.get("is_in_stock", True)),
        "type": ", ".join(cats),
        "tags": tags,
        "fabric": fabric_tags(p.get("name"), " ".join(cats + tags), desc),
        "description": desc[:500],
        "published": None,
        "_cats": cats,
    }


# ------------------------------------------------------------------ driver ----
def fetch_source(src):
    key, base, platform = src["key"], src["base"].rstrip("/"), src.get("platform", "auto")
    log(f"-> {src['name']} ({platform})")
    items, used = [], None

    if platform in ("shopify", "auto"):
        collections = src.get("collections") or SHOPIFY_COLLECTION_GUESSES
        explicit = bool(src.get("collections"))
        for col in collections:
            raw = shopify_products(base, col)
            if raw:
                items.extend(normalise_shopify(p, src) for p in raw)
                used = "shopify"
                log(f"    {col}: {len(raw)}")
                if not explicit:
                    break  # guessed aliases usually point at the same collection
        if not items and platform == "auto":
            # whole store, keyword-filtered later
            raw = shopify_products(base, "", cap=MAX_SCAN)
            if raw:
                items.extend(normalise_shopify(p, src) for p in raw)
                used = "shopify"
                log(f"    /products.json: {len(raw)}")

    if not items and platform in ("woocommerce", "auto"):
        slugs_list = src.get("category_slugs", [])
        raw = []
        for slug in slugs_list:
            raw = woo_products(base, category=slug)
            if raw:
                log(f"    category '{slug}': {len(raw)}")
                break
        if not raw:
            raw = woo_products(base)
        if raw:
            used = "woocommerce"
            slugs = {s.lower() for s in src.get("category_slugs", [])}
            for p in raw:
                n = normalise_woo(p, src)
                if slugs and not (set(n["_cats"]) & slugs) and not is_saree(n["title"], n["type"]):
                    continue
                items.append(n)
            log(f"    store api: {len(raw)} raw, {len(items)} kept")

    if src.get("keyword_filter"):
        items = [i for i in items if is_saree(i["title"], i["type"], " ".join(i["tags"]))]

    # dedupe, clean private keys, require an image
    items = items[:MAX_PER_BRAND * 2]
    seen, clean = set(), []
    for i in items:
        i.pop("_cats", None)
        if i["id"] in seen or not i["images"]:
            continue
        seen.add(i["id"])
        clean.append(i)
    clean = clean[:MAX_PER_BRAND]

    status = f"ok ({used})" if clean else ("no products found" if used else "no supported API")
    log(f"    => {len(clean)} sarees, {status}")
    return clean, {"key": key, "name": src["name"], "base": base, "register": src.get("register", ""),
                   "platform": used, "count": len(clean), "status": status}


def main():
    cfg = json.loads(SOURCES_FILE.read_text())
    all_items, brands = [], []
    for src in cfg["sources"]:
        try:
            items, meta = fetch_source(src)
        except Exception as e:  # never let one shop kill the run
            log(f"    ! unexpected error: {e}")
            items, meta = [], {"key": src["key"], "name": src["name"], "base": src["base"],
                               "register": src.get("register", ""), "platform": None,
                               "count": 0, "status": f"error: {e}"}
        all_items.extend(items)
        brands.append(meta)
        time.sleep(1.0)

    if not all_items and OUT_FILE.exists():
        log("No items fetched at all; keeping previous catalog.json")
        sys.exit(0)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "brands": brands,
        "items": all_items,
    }, ensure_ascii=False, separators=(",", ":")))
    log(f"Wrote {OUT_FILE} — {len(all_items)} items across {sum(1 for b in brands if b['count'])} brands")


if __name__ == "__main__":
    main()
