# Chai Chai Chai by Pakhi — look & mood redesign (mockups only, no PR)

Repo: /home/claude/saree-gallery (read CLAUDE.md and index.html first; current design tokens are at the top of index.html).
Personal gallery of 33,790 sarees from 13 Indian designer/handloom labels (Nalli ~80%, Suta, Ekaya, Torani, Raw Mango, Chidiyaa,
Anavila, House of Masaba, Anita Dongre, Ritu Kumar, Akaaro, Neeta Lulla, Abraham & Thakore). Real sample rows: data/index.json
(fields: brand, title, price INR, fabric[], available). Use real titles/prices/brands from that file.

## What the owner (M) chose
- Change LOOK AND MOOD only: colours, type, card style, wordmark styling, icon/button feel, sheet styling.
  Keep the structure: top bar with wordmark + search / Saved (badge) / view toggle + "Material" and "Store" dropdown buttons;
  Feed = one saree per screen as a photo card, brand/title/price, ✕ hide and ♥ save below, photo dots for sideways carousel;
  Grid = masonry tiles; Detail sheet = bottom sheet with photos, title, brand, price, fabrics, "View on <brand>" link, "Similar drapes" row.
- The name "Chai Chai Chai" with "by Pakhi" stays, but YOUR mood may restyle the wordmark (any face/treatment that fits).
- Each mockup shows 3 phone screens: Feed, Grid, Detail sheet (open over the feed or grid).

## Hard constraints
- Android phone first. Render each screen at 412 x 1007 CSS px (22:9) and confirm it also fits 412 x 961 (21:9) with nothing cut off
  (use dvh / safe layout; the feed card must fit the screen without scroll).
- Every saree is kept — no copy implying curation/trimming.
- Brand photos AND Google Fonts are blocked in this cloud workspace. Draw saree photo stand-ins in CSS/SVG: draped-fabric shapes
  with plausible saree colours, a body/pallu/border (zari stripe, butis, ikat or checks motif) — tasteful, not cartoonish; vary per
  saree to match its title colour/fabric. Fonts: system has Inter, DejaVu Serif, Liberation Serif, FreeSerif, Caladea, Charter.
  You may try webfonts from cdn.jsdelivr.net/npm/@fontsource/<font> (download into your folder and use @font-face locally);
  if blocked, fall back to installed faces and say so.
- Use the design-taste-frontend skill (load it with the Skill tool: anthropic-skills:design-taste-frontend). This is an APP SCREEN:
  read its references/app-screens.md and follow that run (draw.mjs --app, inspect.mjs --app), adapted to this brief. Its house
  rules apply (no gradients, no glass, no eyebrow labels, no tracked tiny caps, no emoji, etc.). Don't spend long on the gate;
  the screenshots are what matter.

## Deliverables (in /mnt/project-files/redesign/v2/<your-slug>/)
- index.html — one self-contained mockup page showing the three screens (each a 412x1007 frame), fonts local.
- feed.png, grid.png, detail.png — each 412x1007 at deviceScaleFactor 2 (Playwright: require('playwright'), chromium.launch()).
- ../<slug>.png — one comparison strip: the three screens side by side with small gap, mood name at top, on a neutral ground.
- Look at your own screenshots with the Read tool, fix the top problems, re-shoot (max 2 rounds).
- Return: mood name, 2-line description, palette hex values, fonts used (and whether webfonts loaded), wordmark treatment, any caveats.
Rules for /mnt/project-files: it's a network mount — only write inside your own subfolder plus your one strip PNG; don't search the whole folder.
