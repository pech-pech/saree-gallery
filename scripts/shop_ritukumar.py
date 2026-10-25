"""Ritu Kumar (Fynd platform) saree fetcher.

Sarees live only on the sub-brand store https://ri.ritukumar.com/collection/sarees
(ritukumar.com itself has no saree collection; its footer links to the ri. store).

How it works:
  1. GET the collection page HTML once. It is server-rendered by Fynd and embeds
     `window.APP_DATA = {...}` which holds the storefront's public applicationID /
     applicationToken and the first 12 products.
  2. Page through Fynd's public storefront catalog API with
     `Authorization: Bearer base64(applicationID:applicationToken)` (exactly the
     header the site itself uses, see APP_DATA.gqlClient.authorizationHeader):
       {host}/service/application/catalog/v1.0/collections/sarees/items/?page_no=N&page_size=..
     host = https://ri.ritukumar.com/api (same origin) or https://api.fynd.com.
  The product pages have no prose description (only an attribute table), so the
  description is built from the listing attributes; no per-product requests.
  If the API fails, the 12 server-rendered products from step 1 are returned.
"""
import base64
import json
import re
import time

import requests

UA = "Mozilla/5.0 (personal saree gallery; polite fetcher; contact via repo)"
PAUSE = 0.6
PAGE_SIZE = 50
COLLECTION = "sarees"
MAX_ITEMS = 20000


def _log(msg):
    print(f"[ritukumar] {msg}", flush=True)


def _strip_html(s):
    s = re.sub(r"<(br|/p|/li|/div)[^>]*>", " ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
          .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", s).strip()


def parse_app_data(html):
    """Return the APP_DATA object embedded in a Fynd storefront page (or None)."""
    m = re.search(r"window\.APP_DATA\s*=\s*", html)
    if not m:
        return None
    end = html.find("</script>", m.end())
    js = html[m.end(): end if end > 0 else None]
    # It's a JS literal: only non-JSON token seen is bare `undefined`.
    js = re.sub(r"(?<=[:,\[])\s*undefined(?=\s*[,}\]])", "null", js)
    try:
        obj, _ = json.JSONDecoder().raw_decode(js)
        return obj
    except ValueError:
        return None


def auth_from_html(html):
    """Bearer value for the storefront API, from the page HTML."""
    m = re.search(r'"authorizationHeader"\s*:\s*"Bearer ([A-Za-z0-9+/=]+)"', html)
    if m:
        return m.group(1)
    a = re.search(r'"applicationID"\s*:\s*"([0-9a-f]{24})"', html)
    t = re.search(r'"applicationToken"\s*:\s*"([^"]+)"', html)
    if a and t:
        return base64.b64encode(f"{a.group(1)}:{t.group(1)}".encode()).decode()
    return None


def ssr_collection(app):
    """(items, page) of the server-rendered collection listing."""
    try:
        c = app["reduxData"]["collection"]["collection"]
        return c.get("items") or [], c.get("page") or {}
    except (KeyError, TypeError):
        return [], {}


def _published(item):
    # Fynd listings carry no publish date; custom-attribute-9 holds a YYYYMMDD
    # launch date on this store. Use it only if it looks like one.
    v = (item.get("attributes") or {}).get("custom-attribute-9")
    v = v[0] if isinstance(v, list) and v else v
    if isinstance(v, str) and re.fullmatch(r"20\d{2}[01]\d[0-3]\d", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}T00:00:00Z"
    return None


def normalise(item, base):
    attrs = item.get("attributes") or {}
    price = None
    try:
        eff = (item.get("price") or {}).get("effective") or {}
        price = float(eff.get("min") if eff.get("min") is not None else eff.get("max"))
    except (TypeError, ValueError):
        price = None
    images, seen = [], set()
    for m in (item.get("medias") or item.get("media") or []):
        u = (m or {}).get("url")
        if u and (m.get("type") in (None, "image")) and u not in seen:
            seen.add(u)
            images.append(u if u.startswith("http") else "https:" + u)
    tags = [t for t in (item.get("tags") or []) if isinstance(t, str)]
    for k in ("collection", "color", "primary_material", "technique", "occasion"):
        v = attrs.get(k)
        if isinstance(v, str) and v and v not in tags:
            tags.append(v)
    parts = []
    for label, k in (("Material", "material"), ("Components", "package-content"),
                     ("Technique", "technique"), ("Colour", "color"),
                     ("Occasion", "occasion"), ("Care", "care_instructions")):
        v = attrs.get(k)
        v = ", ".join(v) if isinstance(v, list) else v
        if isinstance(v, str) and v.strip():
            parts.append(f"{label}: {_strip_html(v)}")
    desc = ". ".join(parts)
    return {
        "id": f"ritukumar:{item.get('uid')}",
        "brand": "ritukumar",
        "title": (item.get("name") or "").strip(),
        "url": f"{base}/product/{item.get('slug')}",
        "price": price,
        "currency": "INR",
        "images": images[:20],
        "available": bool(item.get("sellable", True)),
        "type": attrs.get("custom-attribute-3") or attrs.get("custom-attribute-2") or "Sarees",
        "tags": tags,
        "fabric": [],
        "description": desc[:500],
        "published": _published(item),
    }


def fetch_ritukumar(src):
    base = (src.get("base") or "https://ri.ritukumar.com").rstrip("/")
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9"})
    raw, out = {}, []
    try:
        r = s.get(f"{base}/collection/{COLLECTION}", timeout=60)
        r.raise_for_status()
        html = r.text
        for it in ssr_collection(parse_app_data(html) or {})[0]:
            raw[it.get("uid")] = it
        _log(f"listing page: {len(raw)} products server-rendered")
        bearer = auth_from_html(html)
        if not bearer:
            raise RuntimeError("no Fynd application token in page")

        api_headers = {"Authorization": f"Bearer {bearer}", "Accept": "application/json",
                       "x-currency-code": "INR"}
        hosts = [f"{base}/api/service/application", "https://api.fynd.com/service/application"]
        for host in hosts:
            page, total, got = 1, None, {}
            try:
                while len(got) < MAX_ITEMS:
                    time.sleep(PAUSE)
                    resp = s.get(f"{host}/catalog/v1.0/collections/{COLLECTION}/items/",
                                 params={"page_no": page, "page_size": PAGE_SIZE,
                                         "page_type": "number"},
                                 headers=api_headers, timeout=60)
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("items") or []
                    pg = data.get("page") or {}
                    total = pg.get("item_total", total)
                    for it in items:
                        got[it.get("uid")] = it
                    if not items or not pg.get("has_next"):
                        break
                    page += 1
            except Exception as e:  # noqa: BLE001
                _log(f"API via {host} failed on page {page}: {e}")
            if got:
                raw.update(got)
                _log(f"API via {host}: {len(got)} of item_total={total}")
                if len(got) >= (total or 0):
                    break  # complete; otherwise try the next host too

        for uid, it in raw.items():
            if uid is not None:
                out.append(normalise(it, base))
    except Exception as e:  # noqa: BLE001
        _log(f"error: {e}")
        if not out:
            out = [normalise(it, base) for uid, it in raw.items() if uid is not None]
    _log(f"{len(out)} sarees")
    return out


if __name__ == "__main__":
    items = fetch_ritukumar({"key": "ritukumar", "name": "Ritu Kumar",
                             "base": "https://ri.ritukumar.com"})
    print(json.dumps(items[:2], indent=1, ensure_ascii=False))
