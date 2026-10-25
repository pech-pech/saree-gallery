"""Anita Dongre (Salesforce Commerce Cloud / SFRA, site Sites-AD-INDIA-Site) saree fetcher.

Listing: the SFRA AJAX grid  /on/demandware.store/Sites-AD-INDIA-Site/default/Search-UpdateGrid
returns plain product-tile HTML (no page chrome). It honours sz= up to at least 500, so each query
is one request. Tiles carry pid, title, url, sale price (INR) and the first 2 photos.
Details: Product-Variation?pid=<pid> returns SFRA product JSON: all photos, longDescription,
composition, availability. One request per saree (~180), 0.6 s apart -> ~2-3 min.

Search results list some styles twice (a barcode-id variant like 8909300160594 or a *_Celeb copy next
to the canonical F25K9_BEIG tile); those are collapsed by normalised title.
"""
import html
import json
import re
import time

import requests

AD_BASE = "https://www.anitadongre.com"
AD_SITE = "/on/demandware.store/Sites-AD-INDIA-Site/default"
# (kind, value): site search for both spellings + the two saree categories (main + Grassroot)
AD_QUERIES = [("q", "saree"), ("q", "sari"), ("cgid", "wc-sarees-blouses"), ("cgid", "gr-sarees-blouses")]
AD_PAGE = 500            # sz per grid request; loop continues with start= if a page comes back full
AD_MAX_PAGES = 10
AD_DELAY = 0.6
AD_DETAILS = True        # one Product-Variation request per saree for all photos/description/stock
AD_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
AD_SAREE_RE = re.compile(r"\b(saree|sarees|sari|saris)\b", re.I)
AD_IMG_W = "?sw=1000&sh=1500&sm=fit"

_TILE_SPLIT = re.compile(r'(?=<div class="product-tile[ "])')


def _clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _abs(u):
    u = html.unescape(u or "").strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return AD_BASE + u
    return u


def _img(u):
    """Normalise a /dw/image/v2/ URL to one fixed size (the CDN resizes on ?sw=)."""
    u = _abs(u)
    return u.split("?", 1)[0] + AD_IMG_W if "/dw/image/" in u else u


def parse_grid(text):
    """Parse Search-UpdateGrid HTML into tile dicts (raw, before saree filtering)."""
    out = []
    for chunk in _TILE_SPLIT.split(text)[1:]:
        m = re.search(r'data-pid="([^"]+)"', chunk)
        if not m:
            continue
        pid = html.unescape(m.group(1))
        name = re.search(r'itemprop="name">\s*<span>(.*?)</span>', chunk, re.S)
        title = _clean(name.group(1)) if name else ""
        if not title:
            alt = re.search(r'<img[^>]*\balt="([^"]*)"', chunk)
            title = _clean(alt.group(1)) if alt else ""
        href = (re.search(r'class="product-tile__anchor swimlaneproduct-name"\s+href="([^"]+)"', chunk)
                or re.search(r'class="product-tile__anchor[^"]*"\s+href="([^"]+)"', chunk))
        price = None
        pm = (re.search(r'price__sales.*?itemprop="(?:price|lowprice)"\s+content="([\d.]+)"', chunk, re.S)
              or re.search(r'itemprop="(?:price|lowprice)"\s+content="([\d.]+)"', chunk))
        if pm:
            try:
                price = float(pm.group(1))
            except ValueError:
                pass
        imgs = []
        for im in re.finditer(r'<img[^>]*class="product-tile__image[^"]*"[^>]*?(?:data-src|src)="([^"]+)"', chunk):
            u = _img(im.group(1))
            if u not in imgs:
                imgs.append(u)
        brand = re.search(r'class="plp-short-desc">\s*(.*?)\s*</div>', chunk, re.S)
        out.append({
            "pid": pid, "title": title, "url": _abs(href.group(1)) if href else "",
            "price": price, "images": imgs,
            "label": _clean(brand.group(1)) if brand else "",
            "rts": "ready-to-ship__container" in chunk,
        })
    return out


def parse_variation(data):
    """Pull what we need from a Product-Variation JSON response."""
    p = (data or {}).get("product") or {}
    imgs = []
    for im in ((p.get("images") or {}).get("large") or []):
        u = _img(im.get("absURL") or im.get("url") or "")
        if u and u not in imgs:
            imgs.append(u)
    spec = p.get("adSpecification") or {}
    desc = " ".join(x for x in (_clean(p.get("longDescription")), _clean(p.get("shortDescription")),
                                _clean(p.get("extraProductDetails")),
                                ("Fabric: " + _clean(spec.get("content"))) if spec.get("content") else "") if x)
    price = None
    try:
        price = float(((p.get("price") or {}).get("sales") or {}).get("value"))
    except (TypeError, ValueError):
        pass
    available = bool(p.get("available", True)) and p.get("online", True) is not False \
        and not p.get("comingSoonProduct") and not p.get("notifyMeProduct") \
        and p.get("variationGroupAvailability", True) is not False
    return {"images": imgs, "description": desc, "price": price, "available": available,
            "brand_label": p.get("brand") or "", "composition": _clean(spec.get("content")),
            "ready_to_ship": bool(p.get("readyToShip")),
            "celeb": bool(p.get("isCelebClosetProduct")),
            "mto": "made to order" in (p.get("dispatchLeadTime") or "").lower()}


def _norm_title(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _pid_rank(pid):
    # prefer canonical style ids (F25K9_BEIG) over barcode variants (8909...) and *_Celeb copies
    return (pid.isdigit(), "celeb" in pid.lower(), len(pid))


def fetch_anitadongre(src):
    base = (src.get("base") or AD_BASE).rstrip("/")
    key = src.get("key", "anitadongre")
    s = requests.Session()
    s.headers.update({"User-Agent": AD_UA, "Accept-Language": "en-IN,en;q=0.9"})
    items = []

    def get(url, params, accept):
        time.sleep(AD_DELAY)
        r = s.get(url, params=params, timeout=30, headers={"Accept": accept})
        r.raise_for_status()
        return r

    try:
        # 1. listing
        tiles = {}
        for kind, val in AD_QUERIES:
            start = 0
            for _ in range(AD_MAX_PAGES):
                try:
                    r = get(f"{base}{AD_SITE}/Search-UpdateGrid",
                            {kind: val, "start": start, "sz": AD_PAGE}, "text/html,*/*")
                except Exception as e:
                    print(f"[anitadongre] grid {kind}={val} start={start}: {e}")
                    break
                page = parse_grid(r.text)
                for t in page:
                    tiles.setdefault(t["pid"], t)
                if len(page) < AD_PAGE:
                    break
                start += AD_PAGE

        # 2. sarees only, collapse duplicate listings of one style
        best = {}
        for t in tiles.values():
            if not t["title"] or not AD_SAREE_RE.search(t["title"]):
                continue
            k = _norm_title(t["title"])
            if k not in best or _pid_rank(t["pid"]) < _pid_rank(best[k]["pid"]):
                best[k] = t
        print(f"[anitadongre] tiles={len(tiles)} sarees={len(best)}")

        # 3. build items (details per product, falling back to tile data)
        for t in best.values():
            d = None
            if AD_DETAILS:
                try:
                    r = get(f"{base}{AD_SITE}/Product-Variation", {"pid": t["pid"], "quantity": 1},
                            "application/json")
                    d = parse_variation(r.json())
                except Exception as e:
                    print(f"[anitadongre] detail {t['pid']}: {e}")
            tags = []
            label = (d and d["brand_label"]) or t["label"]
            if label:
                tags.append(label)
            if (d and d["ready_to_ship"]) or t["rts"]:
                tags.append("Ready to ship")
            if (d and d["celeb"]) or "celeb" in t["pid"].lower():
                tags.append("Celebrity closet")
            if d and d["mto"]:
                tags.append("Made to order")
            if d and d["composition"]:
                tags.append(d["composition"])
            imgs = (d and d["images"]) or t["images"]
            items.append({
                "id": f"{key}:{t['pid']}",
                "brand": key,
                "title": t["title"],
                "url": t["url"] or f"{base}/{t['pid']}.html",
                "price": t["price"] if t["price"] is not None else (d and d["price"]),
                "currency": "INR",
                "images": imgs[:20],
                "available": d["available"] if d else True,
                "type": "Saree",
                "tags": tags,
                "fabric": [],
                "description": ((d and d["description"]) or "")[:500],
                "published": None,
            })
    except Exception as e:  # never fail the run
        print(f"[anitadongre] error: {e}")
    return items


if __name__ == "__main__":  # offline self-test against saved samples: python anitadongre.py <dir>
    import sys
    from pathlib import Path
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "html")
    for f in ("grid_wc_200.txt", "grid_q_saree.txt", "plp_grassroot_sz2.txt"):
        tl = parse_grid((d / f).read_text())
        sar = [t for t in tl if AD_SAREE_RE.search(t["title"])]
        uniq = {_norm_title(t["title"]) for t in sar}
        print(f, "tiles", len(tl), "sarees", len(sar), "unique", len(uniq),
              "no-price", sum(t["price"] is None for t in tl), "no-url", sum(not t["url"] for t in tl),
              "imgs/tile", sorted({len(t["images"]) for t in tl}))
        print("  e.g.", json.dumps(sar[0], ensure_ascii=False)[:400])
    for f in ("pv_F26AP52_GREN.json", "pv_8909300160594.json"):
        v = parse_variation(json.loads((d / f).read_text()))
        print(f, len(v["images"]), "imgs", v["available"], v["price"], v["composition"], "|", v["description"][:160])
