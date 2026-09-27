# Saree Gallery

A personal, static gallery of sarees from designer Indian labels (Anavila, House of Masaba and others), refreshed daily by GitHub Actions and served on GitHub Pages.

## Setup (once)

1. Create a new **public** repo and push these files to `main`.
2. Repo → Settings → Pages → Source: **Deploy from a branch** → `main` / `/ (root)` → Save.
3. Repo → Actions → **Refresh saree catalog** → Run workflow. The first run fetches every shop in `sources.json` and commits `data/catalog.json`; Pages redeploys automatically.
4. Open `https://<your-user>.github.io/<repo>/`.

The run log shows, per brand, which API worked and how many sarees were kept.

## Adding or removing shops

Edit `sources.json`. Each entry:

```json
{ "key": "slug", "name": "Display name", "base": "https://shop.example",
  "platform": "shopify | woocommerce | auto",
  "collections": ["/collections/sarees"],        // shopify only, optional
  "category_slugs": ["sari"],                    // woocommerce only, optional
  "keyword_filter": true,                        // keep only titles mentioning saree/sari
  "register": "handloom | designer" }
```

Pushing a change to `sources.json` triggers a refresh.

## Local run

```
pip install requests
python scripts/fetch_catalog.py
python -m http.server 8000   # then open http://localhost:8000
```

## Notes

- Nothing is re-hosted: images load from the brands' own CDNs and every item links out to the brand's product page.
- Shops on platforms other than Shopify/WooCommerce are skipped with a note in the run log.
- Saved items live in your browser's local storage only.
