# Chai Chai Chai by Pakhi (saree gallery) — project context

Personal, non-commercial gallery of sarees from designer Indian labels. Static site on GitHub Pages
(https://pech-pech.github.io/saree-gallery/), data refreshed daily by GitHub Actions. No backend.

## How it works
- `sources.json` — the shop list. Each entry: key, name, base URL, platform (shopify | woocommerce | auto),
  optional `collections` (Shopify) or `category_slugs` (WooCommerce), `keyword_filter`, `register`
  (handloom | designer).
- `scripts/fetch_catalog.py` — fetches every shop, keeps sarees only, normalises, then writes
  `data/index.json` (grid fields only) and `data/details/<shop>.json` (images, description, tags, keyed by id; one file per shop, split into
  `<shop>.<n>.json` every 5,000 sarees, with `dc: n` on those index rows).
  - Shopify: `{base}{collection}/products.json?limit=250&page=N`. In `auto` mode it guesses
    /collections/sarees|saree|sari|saris, stops at the first hit, else scans /products.json and keyword-filters. If deep pages error (Nalli fails
    around page 90), it walks /collections.json collection by collection to reach the rest (30 min cap).
  - WooCommerce: Store API `/wp-json/wc/store/v1/products`, category query merged with a full-store scan
    (needed for Anavila: some saris sit only in collection categories).
  - Caps are safety ceilings only (MAX_PER_BRAND=100000, MAX_SCAN=100000): every saree is kept (owner wants all). Descriptions trimmed to 500 chars, up to 20 images.
  - Custom fetchers (`platform: custom`, `scripts/shop_<name>.py`): Anita Dongre (Salesforce Commerce Cloud:
    Search-UpdateGrid listing + one Product-Variation JSON request per saree), Ritu Kumar (Fynd, sarees on
    ri.ritukumar.com: reads the public storefront token from the collection page, then pages the catalog API;
    falls back to the 12 server-rendered items if the API fails).
  - One failing shop never fails the run; an empty run keeps the previous catalog.
- Installable app (PWA): `manifest.webmanifest`, `icons/`, `sw.js`. The service worker serves the page and
  `data/index.json` network-first (offline fallback) and `data/details/<shop>.json?v=` cache-first; it never caches brand
  photos. Bump `CACHE` in sw.js if the cached file list changes.
- Feed photos use `object-fit: contain` inside the card, switching to cover only when that crops <12%, so
  20:9–22:9 phones show the whole photo.
- `.github/workflows/refresh.yml` — daily 02:30 UTC, manual dispatch, and on pushes touching
  `sources.json` or `scripts/**`. Has a concurrency group and `git pull --rebase` before push.
- Two looks, switched by the half-moon icon in the header and remembered in localStorage `saree.skin`:
  **Editorial** (light only: centred uppercase Bodoni Moda masthead, Inter UI, square corners, oxblood #a3161d on Save /
  Open; fonts self-hosted in `fonts/`, styles scoped under `[data-skin="editorial"]`) and **Classic** (the design below,
  following the phone's light/dark). First visit: light phone opens Editorial, dark phone opens Classic.
- `index.html` — single-file gallery (Classic = design "A: clean card", chosen by the owner). Header: "Chai Chai Chai" in
  Parisienne (Google Fonts, `text=Chai` subset) over a small-caps "BY PAKHI" byline; search /
  Saved (badge) / view-toggle icons, then two dropdown buttons, **Material** and **Store**, that open a panel with a
  2-column grid of options + live counts and a "Show N sarees" button (multi-select; OR within a facet, AND across).
  Order: daily seeded shuffle that deals one saree per shop per round (`shuffleSeeded`), so small shops sit up
  front and Nalli (~80% of the catalog) fills the tail; every saree is kept. Labels use normal case at 13-14px;
  chips and buttons are solid tints (`--chip`), no 1px outlines; tertiary text `--ink-3` passes 4.5:1.
  Two views, remembered in localStorage `saree.mode` (default Feed):
  Feed = one saree per screen as a rounded photo card with brand/title/price and ✕ (hide) / ♥ (save) below it;
  swipe up for the next, sideways through all photos (loops); double-tap saves; title opens the detail sheet.
  Grid = masonry tiles in batches of 60. Detail sheet (bottom on mobile, side ≥900px) has "Similar drapes".
  Loads index.json first (revalidated with `cache: 'no-cache'`), then details/<shop>.json?v=<generated_at>:
  shops with ≤1,500 sarees in the background, bigger ones (Nalli, Suta) only when one of their sarees is on screen
  or opened. Search picks up a shop's tags once its file arrives. Shopify images are requested resized via the CDN's
  `width=` param; WooCommerce tiles use the Store API thumbnail. Items link out; nothing is re-hosted.

## Current shops (13)
Anavila (woocommerce, main), House of Masaba (shopify, main), Raw Mango, Ekaya, Akaaro, Suta,
Chidiyaa, Abraham & Thakore, Torani, Neeta Lulla (shopify, /collections/sarees), Nalli (auto), Anita Dongre (custom), Ritu Kumar (custom).

Removed and why: Taneira (403 blocks bots), Gaurang Shah (no usable API), Gulaal (gulaal.org doesn't
resolve; brand isn't saree-focused), Payal Khandwala (only 1 saree), Satya Paul / Shivan & Narresh /
Papa Don't Preach (dropped by owner).
Not addable (checked 2026-10-25): Sabyasachi (Shopify but products.json is hidden/empty),
Adeshwari Gadwals (no official online store found).

## Working rules
- Owner uses the site mainly on an Android phone; check mobile layout first.
- Priorities: content quality and quantity, saree focus, easy browsing.
- After changing the fetcher or sources, trigger the workflow (`gh workflow run refresh.yml`),
  then read the log (`gh run view --log`) and report per-shop counts.
- Keep it static: no server, no accounts, no re-hosting of brand images.

## Working with M (owner)
- Moved here from a claude.ai Projects workspace on 2026-11-02; this file is now the single source of context.
- M uses an Android phone: keep replies short, one step at a time. M merges PRs from the phone.
- Every layout must fit 21:9 and 22:9 screens (test at 412x961 and 412x1007 CSS px).
- Keep every saree. Make things faster by restructuring (split files, lazy loads), never by trimming content.
- Before building a UI change, show 2-4 mockups and let M pick one. Past picks are in `design/mockups/README.md`.
- Shortcuts M uses:
  - `vrf`: restate the task and ask multiple-choice questions before doing anything.
  - `/mcq`: one multiple-choice question at a time (max 6), then proceed.
  - `saiyan`: work fast with parallel agents on multi-step tasks.
- Prices: M wants them shown in BDT (taka), at the xe.com INR→BDT rate plus 1.5% (asked 2026-10-27). Not built yet.

## Project history
- PR #1: Anavila full-store WooCommerce scan, CLAUDE.md added, Payal Khandwala removed (3,166 sarees, 9 shops).
- PR #2: split data into a small grid index plus detail files loaded later; resized CDN images; caching.
- PR #3: Reels-style Feed as default (M picked it over a swipe deck); photo cap 4 → 20.
- PR #4: installable PWA, design "A: clean card" with Material/Store dropdown filters, tall-screen fit.
- PR #5: "Chai Chai Chai by Pakhi" wordmark (Parisienne, title over small-caps "BY PAKHI").
- PR #7: Nalli, Anita Dongre, Ritu Kumar, Neeta Lulla added; per-shop cap removed; details split per shop
  (33,850 sarees, 13 shops; daily refresh ~30 min).
- PR #8: even shop mix in the feed, larger readable labels, tinted chips instead of outlines.
- PR #9: Editorial light look (M picked "Editorial luxe" from the 2026-10-27 mood mockups) with a look switch;
  the old design stays as Classic.

## Open items (as of 2026-11-02)
- Show prices in taka (BDT, xe.com rate + 1.5%) on the live site: agreed, not built. Needs a rate source the
  static site or the daily workflow can read.
- Sabyasachi: blocked, its Shopify store hides products.json.
- Adeshwari Gadwals: waiting on M for a store link.
- The app icon still shows the old italic "S", not the new wordmark.
