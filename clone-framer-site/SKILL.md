---
name: clone-framer-site
description: Clone any published Framer site into a local, Vercel-deployable static site with pixel-perfect fidelity. Use when the user wants to replicate, clone, mirror, or self-host a Framer website (.framer.app domain or custom domain powered by Framer). Triggers on requests like "clone my Framer site", "make a local copy of my portfolio", "self-host my Framer site", "replicate this Framer page", or "deploy my Framer site to Vercel without Framer hosting".
---

# Clone Framer Site

Clone any published Framer site into a static, Vercel-deployable directory with near pixel-perfect visual parity. All assets (fonts, images, JS) are downloaded and localized.

## Prerequisites

```bash
pip install playwright beautifulsoup4 aiohttp Pillow lxml
playwright install chromium
```

## Usage

Run the bundled script with the Framer site URL:

```bash
python3 scripts/clone_framer_site.py <FRAMER_URL> [--output-dir <DIR>] [--port <PORT>] [--skip-screenshots]
```

**Examples:**

```bash
# Clone into current directory
python3 scripts/clone_framer_site.py https://my-site.framer.app/

# Clone into a specific directory
python3 scripts/clone_framer_site.py https://my-site.framer.app/ --output-dir ./my-clone

# Skip the screenshot comparison phase (faster)
python3 scripts/clone_framer_site.py https://my-site.framer.app/ --skip-screenshots
```

## What the Script Does (5 Phases)

### Phase 1 — Reconnaissance
- Navigate to the site with Playwright headless Chromium
- Scrape all internal `<a>` links from the rendered DOM
- Parse `/sitemap.xml` for additional routes
- Exclude non-page links (e.g. `mailto:`)

### Phase 2 — HTML Capture
- Visit each discovered route
- Wait for network idle + 5 seconds for animations/lazy-loading
- Extract fully rendered DOM via `page.content()`
- Save as clean `index.html` files: `/` → `public/index.html`, `/about` → `public/about/index.html`

### Phase 3 — Asset Localization
- Parse each HTML file with BeautifulSoup
- Download all external assets: fonts (`.woff2`), images, JS modules (`.mjs`), CSS
- Store under `public/assets/{fonts,images,js,css}/`
- Rewrite every URL in HTML to use relative local paths

### Phase 4 — Vercel Configuration
- Write `vercel.json` with clean URLs, asset caching headers, and `.mjs` MIME types
- Write `serve.sh` for local preview

### Phase 5 — Visual Parity Verification (optional)
- Start a local HTTP server
- Capture full-page screenshots of both source and local for each route
- Desktop (1920x1080) and mobile (375x667)
- Generate pixel-diff images and similarity scores
- Write `PARITY_REPORT.md` with results

## Output Structure

```
<output-dir>/
├── public/                # Deploy this directory
│   ├── index.html
│   ├── assets/
│   │   ├── fonts/
│   │   ├── images/
│   │   └── js/
│   └── <route>/index.html
├── parity/                # Screenshot comparisons
│   ├── screenshots/
│   └── diffs/
├── vercel.json
├── serve.sh
├── README.md
└── PARITY_REPORT.md
```

## Deployment

### Local preview
```bash
./serve.sh
```

### Vercel CLI
```bash
vercel
```
Set root directory to `public` when prompted.

### Vercel via GitHub
Push repo, import in Vercel, set root directory to `public`.

## Known Limitations

- **Static snapshot**: Content is frozen at capture time (no CMS sync)
- **React hydration warnings**: Cosmetic console warnings from Framer runtime (do not affect rendering)
- **Dynamic features**: Any server-dependent interactivity (forms, auth) will not function
- **Framer editor badge**: Removed from clone (expected behavior)

## Troubleshooting

- **Blank pages**: Ensure all JS modules downloaded. Re-run the script.
- **Missing fonts**: Check `public/assets/fonts/` — re-run if empty.
- **404 on routes**: Verify `vercel.json` has `cleanUrls: true`. Locally, use trailing `/` (e.g. `/about/`).
- **CORS errors**: The local `python3 -m http.server` doesn't set CORS headers; use a Vercel preview deployment for full testing.
