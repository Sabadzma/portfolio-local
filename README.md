# Saba Chitaishvili — Portfolio (Static Clone)

Static clone of **https://authentic-devices-570724.framer.app/**

This repository contains a pixel-perfect static clone of the Framer-hosted portfolio site, fully self-contained with all assets localized for offline/self-hosted use.

## Run Locally

### Option 1: Simple HTTP server
```bash
cd public && python3 -m http.server 8000
```

### Option 2: Shell script
```bash
./serve.sh
```

Then open http://localhost:8000

## Preview / Build

No build step required — this is a pure static site. All HTML, CSS, JS, fonts, and images are pre-rendered and included in the `public/` directory.

To verify all routes work:
```bash
cd public && python3 -m http.server 8000 &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/                    # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/writing/hello-world/ # 200
```

## Deploy on Vercel

### Via CLI
```bash
npm i -g vercel
vercel
```
When prompted, set the output directory to `public`.

### Via GitHub
1. Push this repo to GitHub
2. Import the repository in [Vercel Dashboard](https://vercel.com/new)
3. Set **Output Directory** to `public`
4. Deploy

The `vercel.json` at the repo root configures clean URLs, proper MIME types for `.mjs` modules, CORS for fonts, and routing for writing pages.

## Project Structure

```
├── public/                     # Static site root (serve this directory)
│   ├── index.html              # Homepage
│   ├── writing/                # Blog/writing pages
│   │   ├── design-tokens-101/
│   │   ├── hello-world/
│   │   ├── how-ai-is-changing-my-workflow/
│   │   ├── how-to-think-like-both-a-designer-engineer/
│   │   ├── test-test/
│   │   └── ui-performance/
│   └── assets/
│       ├── fonts/              # All font files (woff2)
│       ├── images/             # All images (jpg, png, jpeg)
│       ├── js/                 # Framer runtime JS modules
│       └── data/               # Search index JSON files
├── parity/                     # Visual parity verification
│   ├── screenshots/            # Source vs local screenshots
│   └── diffs/                  # Pixel diff images
├── vercel.json                 # Vercel deployment config
├── serve.sh                    # Local development server script
├── PARITY_REPORT.md            # Visual parity analysis
└── clone-framer-site/          # Cloning scripts (for re-capture)
    └── scripts/
        └── clone_framer_site.py
```

## Re-capture from Source

If the source site changes and you want to re-clone:
```bash
pip install playwright beautifulsoup4 aiohttp Pillow lxml
playwright install chromium
python3 clone-framer-site/scripts/clone_framer_site.py https://authentic-devices-570724.framer.app/
```

## Parity

See [PARITY_REPORT.md](PARITY_REPORT.md) for detailed visual parity analysis with screenshots.
