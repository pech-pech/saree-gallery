# Saree Gallery — project context

Personal, non-commercial gallery of sarees from designer Indian labels. Static site on GitHub Pages
(https://pech-pech.github.io/saree-gallery/), data refreshed daily by GitHub Actions. No backend.

## How it works
- `sources.json` — the shop list. Each entry: key, name, base URL, platform (shopify | woocommerce | auto),
  optional `collections` (Shopify) or `category_slugs` (WooCommerce), `keyword_filter`, `register`
  (handloom | designer).
- `scripts/fetch_catalog.py` — fetches every shop, keeps sarees only, normalises into `data/catalog.json`.
  - Shopify: `{base}{collection}/products.json?limit=250&page=N`. In `auto` mode it guesses
    /collections/sarees|saree|sari|saris, stops at the first hit, else scans /products.json and keyword-filters.
  - WooCommerce: Store API `/wp-json/wc/store/v1/products`, category query merged with a full-store scan
    (needed for Anavila: some saris sit only in collection categories).
  - Caps: MAX_PER_BRAND=1000 kept per shop, MAX_SCAN=3000 raw scanned. Descriptions trimmed to 500 chars, 4 images.
  - One failing shop never fails the run; an empty run keeps the previous catalog.
- `.github/workflows/refresh.yml` — daily 02:30 UTC, manual dispatch, and on pushes touching
  `sources.json` or `scripts/**`. Has a concurrency group and `git pull --rebase` before push.
- `index.html` — single-file gallery (Newsreader serif, indigo accent, paper background).
  Masonry columns, brand + fabric filter strips, search, Saved (localStorage), detail sheet
  (bottom sheet on mobile, side panel ≥900px), "Similar drapes" scored by shared fabric, price band,
  register, cross-brand preference. Renders in batches of 60 via IntersectionObserver.
  Items link out to the brand's product page; nothing is re-hosted.

## Current shops (9)
Anavila (woocommerce, main), House of Masaba (shopify, main), Raw Mango, Ekaya, Akaaro, Suta,
Chidiyaa, Abraham & Thakore, Torani.

Removed and why: Taneira (403 blocks bots), Gaurang Shah (no usable API), Gulaal (gulaal.org doesn't
resolve; brand isn't saree-focused), Payal Khandwala (only 1 saree), Satya Paul / Shivan & Narresh /
Papa Don't Preach (dropped by owner).

## Working rules
- Owner uses the site mainly on an Android phone; check mobile layout first.
- Priorities: content quality and quantity, saree focus, easy browsing.
- After changing the fetcher or sources, trigger the workflow (`gh workflow run refresh.yml`),
  then read the log (`gh run view --log`) and report per-shop counts.
- Keep it static: no server, no accounts, no re-hosting of brand images.
