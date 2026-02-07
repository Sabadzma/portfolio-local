# Portfolio Local Clone

A pixel-perfect static clone of the Framer portfolio site at https://loving-event-914440.framer.app/, optimized for deployment on Vercel.

## 🎯 Project Overview

This repository contains a **1:1 visual reproduction** of the source Framer site, achieved through:
- Fully rendered HTML capture using Playwright
- Complete asset localization (fonts, images, JavaScript)
- Static site structure with clean URLs
- 99%+ visual parity verified through screenshot comparison

**Source Site**: https://loving-event-914440.framer.app/
**Approach**: Pure static HTML (no framework wrapper required)

---

## 📁 Repository Structure

```
portfolio-local/
├── public/                          # Static site root (deploy this directory)
│   ├── index.html                   # Home page
│   ├── assets/                      # Localized assets
│   │   ├── fonts/                   # 63 font files (Inter, Fragment Mono, Geist Mono)
│   │   ├── images/                  # 7 images (hero images, icons, favicons)
│   │   └── js/                      # 12 JavaScript modules (React, Framer runtime)
│   └── writing/                     # Blog posts
│       ├── design-tokens-101/
│       ├── hello-world/
│       ├── how-ai-is-changing-my-workflow/
│       ├── how-to-think-like-both-a-designer-engineer/
│       ├── test-test/
│       └── ui-performance/
├── parity/                          # Visual verification artifacts
│   ├── screenshots/                 # Source vs local comparisons
│   └── parity_results.json          # Automated comparison results
├── scripts/                         # Build and capture scripts
│   ├── phase1_recon.py             # Site reconnaissance
│   ├── phase2_capture.py           # HTML capture
│   ├── phase3_localize_assets.py   # Asset downloading
│   └── phase5_screenshots.py       # Screenshot generation
├── vercel.json                      # Vercel deployment configuration
├── serve.sh                         # Local development server
├── PARITY_REPORT.md                # Detailed parity analysis
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+ (for local development)
- Node.js 18+ (optional, for Vercel CLI)

### Run Locally

1. **Start the development server:**
   ```bash
   ./serve.sh
   ```

   Or manually:
   ```bash
   cd public
   python3 -m http.server 8000
   ```

2. **Open in browser:**
   ```
   http://localhost:8000
   ```

3. **Navigate to any route:**
   - Home: `http://localhost:8000/`
   - Blog posts: `http://localhost:8000/writing/design-tokens-101`

---

## 📦 Deploy to Vercel

### Option 1: Vercel CLI (Recommended)

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy:**
   ```bash
   vercel
   ```

3. **Follow prompts:**
   - Set root directory: `./public`
   - Use existing `vercel.json`: Yes

### Option 2: Vercel Dashboard

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Portfolio clone ready for deployment"
   git push origin main
   ```

2. **Import to Vercel:**
   - Go to https://vercel.com/new
   - Import your repository
   - Set **Root Directory**: `public`
   - Deploy

### Option 3: Deploy from Local Filesystem

1. **Go to Vercel Dashboard**
2. **Click "Add New Project"**
3. **Select "Browse" and choose the `public/` directory**
4. **Click "Deploy"**

---

## ⚙️ Configuration

### Vercel Settings

The included [`vercel.json`](vercel.json) configures:

- **Clean URLs**: `/writing/post` instead of `/writing/post/index.html`
- **Asset Caching**: 1-year cache for fonts, images, and scripts
- **MIME Types**: Correct `Content-Type` for `.mjs` modules
- **Rewrites**: Routes all requests to `/public/` directory

### Custom Domain

After deployment, add a custom domain in Vercel:

1. Go to **Project Settings → Domains**
2. Add your domain (e.g., `yourname.com`)
3. Update DNS records as instructed

---

## 🔍 Parity Verification

Visual parity has been verified through automated screenshot comparison:

- **Desktop viewport**: 1920×1080
- **Mobile viewport**: 375×667 (iPhone SE)
- **Routes tested**: 7 (home + 6 blog posts)
- **Result**: 99%+ visual accuracy

### View Comparison

Screenshots are available in [`parity/screenshots/`](parity/screenshots/):

```
parity/screenshots/
├── home/
│   ├── desktop/
│   │   ├── source.png    # Original Framer site
│   │   └── local.png     # This clone
│   └── mobile/
│       ├── source.png
│       └── local.png
└── writing_{post-name}/
    └── ...
```

### Known Differences

See [PARITY_REPORT.md](PARITY_REPORT.md) for detailed analysis. Key points:

- ✓ Typography: Identical (all fonts localized)
- ✓ Layout: Pixel-perfect match
- ✓ Colors: Exact match
- ✓ Images: All images load correctly
- ⚠ Minor: Framer editor badge removed (expected)
- ⚠ Minor: Console warnings from React hydration (cosmetic only)

---

## 🛠️ Development

### Re-capture Site (if source updates)

If the source Framer site is updated and you need to refresh the clone:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Run capture pipeline:**
   ```bash
   # Phase 1: Discover routes
   python3 scripts/phase1_recon.py

   # Phase 2: Capture HTML
   python3 scripts/phase2_capture.py

   # Phase 3: Download and localize assets
   python3 scripts/phase3_localize_assets.py
   python3 scripts/download_missing_js.py

   # Phase 5: Verify parity
   ./serve.sh &  # Start local server
   python3 scripts/phase5_screenshots.py
   ```

### Build Pipeline

This is a **static site** with no build step required. The capture scripts act as the "build process":

1. Playwright renders pages in headless browser
2. Full DOM captured after JavaScript execution
3. Assets downloaded and paths rewritten
4. Output ready for deployment

---

## 📊 Performance

### Asset Inventory

- **Fonts**: 63 files, 1.03 MB
- **Images**: 7 files, 3.39 MB
- **JavaScript**: 12 modules, ~1.3 MB
- **Total**: ~5.7 MB (uncompressed)

### Optimization

Assets are served with optimal caching:
- Fonts: 1-year cache (immutable)
- Images: 1-year cache (immutable)
- HTML: No cache (always fresh)

Vercel automatically compresses assets (Brotli/gzip).

---

## 🚨 Troubleshooting

### Routes show 404
- **Cause**: `vercel.json` not being read
- **Fix**: Ensure `vercel.json` is in repository root and `cleanUrls: true` is set

### Fonts not loading
- **Cause**: Incorrect relative paths
- **Fix**: Check browser console for 404s. Paths should be `assets/fonts/{filename}`

### JavaScript not executing
- **Cause**: Missing `.mjs` MIME type
- **Fix**: Verify `vercel.json` headers include `application/javascript` for `.mjs`

### Blank page
- **Cause**: React hydration error
- **Check**: Browser console for errors. May need to re-capture source HTML

### Local server not starting
- **Cause**: Port 8000 already in use
- **Fix**: Kill existing process or use different port:
  ```bash
  cd public && python3 -m http.server 9000
  ```

---

## 📝 Technical Details

### Rendering Approach

This clone uses **static HTML with client-side hydration**:

1. HTML is pre-rendered by Framer's SSR
2. JavaScript modules handle interactivity
3. React hydrates the DOM on page load

This preserves:
- ✓ SEO (HTML is fully rendered)
- ✓ Fast initial paint
- ✓ Smooth client-side navigation
- ✓ Animations and interactions

### Why Static vs. Framework?

**Static HTML** was chosen over framework wrappers (Next.js, Astro) because:

1. **Maximum fidelity**: Uses actual Framer-rendered HTML
2. **Simplicity**: No build step, no framework version conflicts
3. **Performance**: Instant page loads, optimal caching
4. **Vercel-ready**: Zero configuration needed

---

## 📄 License

This is a personal portfolio clone for deployment purposes. Original design and content are property of the source site owner.

---

## 🙋 Support

- **Parity issues**: Check [PARITY_REPORT.md](PARITY_REPORT.md)
- **Deployment issues**: See Vercel troubleshooting above
- **Re-capture needed**: Run scripts in `scripts/` directory

---

**Built with**: Playwright, Python, BeautifulSoup, Pillow
**Deployed on**: Vercel
**Source**: https://loving-event-914440.framer.app/
