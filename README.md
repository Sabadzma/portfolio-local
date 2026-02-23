# Framer Site Clone

Static clone of **https://authentic-devices-570724.framer.app/**

## Run locally

```bash
./serve.sh
# or
cd public && python3 -m http.server 8000
```

Open http://localhost:8000

## Deploy on Vercel

### CLI
```bash
npm i -g vercel && vercel
```
Set root directory to `public`.

### GitHub
Push to GitHub, import in Vercel, set root directory to `public`.

## Re-capture

```bash
pip install playwright beautifulsoup4 aiohttp Pillow lxml
playwright install chromium
python3 scripts/clone_framer_site.py https://authentic-devices-570724.framer.app/
```

## Parity

See [PARITY_REPORT.md](PARITY_REPORT.md) and `parity/screenshots/`.
