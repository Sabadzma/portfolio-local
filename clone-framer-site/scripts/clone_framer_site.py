#!/usr/bin/env python3
"""
Framer Site Cloner — Full Pipeline
Clones any Framer site into a local, Vercel-deployable static site.

Usage:
    python3 clone_framer_site.py <framer_url> [--output-dir <dir>] [--port <port>]

Example:
    python3 clone_framer_site.py https://my-site.framer.app/
    python3 clone_framer_site.py https://my-site.framer.app/ --output-dir ./my-clone --port 9000
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
REQUIRED = ["playwright", "bs4", "aiohttp", "PIL", "lxml"]

def check_deps():
    missing = []
    for mod in REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        pip_names = {
            "bs4": "beautifulsoup4",
            "PIL": "Pillow",
        }
        print("Missing dependencies. Install with:")
        pkgs = " ".join(pip_names.get(m, m) for m in missing)
        print(f"  pip install {pkgs}")
        print("Then run:  playwright install chromium")
        sys.exit(1)

check_deps()

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from PIL import Image, ImageChops

# ---------------------------------------------------------------------------
# Globals filled at runtime
# ---------------------------------------------------------------------------
downloaded_assets: dict[str, str] = {}
asset_inventory: dict[str, list] = {
    "fonts": [], "images": [], "scripts": [], "styles": [], "other": []
}

# ---------------------------------------------------------------------------
# Phase 1 — Recon
# ---------------------------------------------------------------------------
async def discover_routes(source_url: str) -> tuple[list[str], dict, list]:
    """Return (sorted_routes, page_info, nav_structure)."""
    routes: set[str] = {"/"}
    base_domain = urlparse(source_url).netloc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()

        print(f"  Navigating to {source_url} ...")
        resp = await page.goto(source_url, wait_until="networkidle", timeout=30_000)
        print(f"  HTTP {resp.status}")
        await page.wait_for_timeout(3000)

        # Scrape <a> links
        links = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                href: a.href, text: a.textContent.trim()
            }));
        }""")
        for link in links:
            parsed = urlparse(link["href"])
            if parsed.netloc == base_domain or not parsed.netloc:
                path = parsed.path or "/"
                if not path.startswith("/"):
                    path = "/" + path
                if "@" not in path and path != "/":
                    routes.add(path)

        # Try sitemap.xml
        try:
            sm_page = await ctx.new_page()
            sm_resp = await sm_page.goto(urljoin(source_url, "/sitemap.xml"), timeout=10_000)
            if sm_resp.status == 200:
                sm_html = await sm_page.content()
                for loc in re.findall(r"<loc>(.*?)</loc>", sm_html):
                    p2 = urlparse(loc).path
                    if p2 and p2 != "/":
                        routes.add(p2)
            await sm_page.close()
        except Exception:
            pass

        page_info = await page.evaluate("""() => ({
            title: document.title,
            imageCount: document.querySelectorAll('img').length,
            scriptCount: document.querySelectorAll('script').length,
        })""")

        nav_structure = await page.evaluate("""() =>
            Array.from(document.querySelectorAll('nav, [role="navigation"], header'))
                .map(n => ({
                    tag: n.tagName,
                    links: Array.from(n.querySelectorAll('a')).map(a => ({
                        text: a.textContent.trim(), href: a.href
                    }))
                }))
        """)

        await browser.close()

    clean = sorted(r for r in routes if "@" not in r)
    return clean, page_info, nav_structure

# ---------------------------------------------------------------------------
# Phase 2 — Capture
# ---------------------------------------------------------------------------
async def capture_pages(source_url: str, routes: list[str], public_dir: Path):
    """Render each route and save the full DOM."""
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        )
        page = await ctx.new_page()

        for route in routes:
            url = urljoin(source_url, route)
            print(f"  Capturing {url} ...")
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=60_000)
                if resp.status != 200:
                    print(f"    SKIP (HTTP {resp.status})")
                    continue
                await page.wait_for_timeout(5000)

                # Wait for images
                await page.evaluate("""() => new Promise(resolve => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    let n = 0;
                    if (!imgs.length) return resolve();
                    imgs.forEach(i => {
                        if (i.complete) { n++; if (n===imgs.length) resolve(); }
                        else {
                            i.onload = i.onerror = () => { n++; if (n===imgs.length) resolve(); };
                        }
                    });
                    setTimeout(resolve, 10000);
                })""")

                html = await page.content()
                out = public_dir / (route.strip("/") + "/index.html" if route != "/" else "index.html")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(html, encoding="utf-8")
                print(f"    Saved {out} ({len(html)} bytes)")
                results.append({"route": route, "path": str(out), "size": len(html)})
            except Exception as e:
                print(f"    ERROR: {e}")
            await asyncio.sleep(1)

        await browser.close()
    return results

# ---------------------------------------------------------------------------
# Phase 3 — Asset localization helpers
# ---------------------------------------------------------------------------
def _local_path(url: str, atype: str, assets_dir: Path) -> Path:
    parts = urlparse(url).path.split("/")
    fname = parts[-1] if parts else "asset"
    if "." not in fname or len(fname) > 100:
        ext = {
            "fonts": ".woff2", "images": ".png", "scripts": ".js", "styles": ".css"
        }.get(atype, "")
        fname = hashlib.md5(url.encode()).hexdigest()[:12] + ext
    subdir = {"fonts": "fonts", "images": "images", "scripts": "js", "styles": "css"}.get(atype, "other")
    return assets_dir / subdir / fname


async def _download(session, url, local_path, atype):
    if url in downloaded_assets:
        return downloaded_assets[url]
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        async with session.get(url, ssl=ssl_ctx, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status == 200:
                data = await r.read()
                local_path.write_bytes(data)
                downloaded_assets[url] = str(local_path)
                asset_inventory[atype].append({"url": url, "local": str(local_path), "size": len(data)})
                return str(local_path)
    except Exception:
        pass
    return None


async def localize_html(html_path: Path, assets_dir: Path, session):
    """Download external assets referenced in *html_path* and rewrite paths."""
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "lxml")
    mods: list[tuple[str, str]] = []

    # Fonts in <style> tags
    for style in soup.find_all("style"):
        if not style.string:
            continue
        for furl in re.findall(r'url\(([^)]+)\)', style.string):
            furl = furl.strip("\"'")
            if furl.startswith("http"):
                lp = _local_path(furl, "fonts", assets_dir)
                dp = await _download(session, furl, lp, "fonts")
                if dp:
                    mods.append((furl, os.path.relpath(dp, html_path.parent)))

    # <img src>
    for img in soup.find_all("img", src=True):
        u = img["src"]
        if u.startswith("http"):
            lp = _local_path(u, "images", assets_dir)
            dp = await _download(session, u, lp, "images")
            if dp:
                mods.append((u, os.path.relpath(dp, html_path.parent)))

    # Meta images (og:image, favicon, etc.)
    for tag in soup.find_all(["link", "meta"]):
        for attr in ("href", "content"):
            u = tag.get(attr, "")
            if u.startswith("http") and any(e in u for e in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico")):
                lp = _local_path(u, "images", assets_dir)
                dp = await _download(session, u, lp, "images")
                if dp:
                    mods.append((u, os.path.relpath(dp, html_path.parent)))

    # <script src>
    for sc in soup.find_all("script", src=True):
        u = sc["src"]
        if u.startswith("http"):
            lp = _local_path(u, "scripts", assets_dir)
            dp = await _download(session, u, lp, "scripts")
            if dp:
                mods.append((u, os.path.relpath(dp, html_path.parent)))

    # <link rel="stylesheet">
    for lnk in soup.find_all("link", rel="stylesheet"):
        u = lnk.get("href", "")
        if u.startswith("http"):
            lp = _local_path(u, "styles", assets_dir)
            dp = await _download(session, u, lp, "styles")
            if dp:
                mods.append((u, os.path.relpath(dp, html_path.parent)))

    # Apply replacements
    for old, new in mods:
        content = content.replace(old, new)
    html_path.write_text(content, encoding="utf-8")
    return len(mods)


async def download_extra_js(public_dir: Path, assets_dir: Path):
    """Find Framer .mjs module references and download them too."""
    js_dir = assets_dir / "js"
    js_dir.mkdir(parents=True, exist_ok=True)

    # Collect unique module URLs across all HTML files
    module_urls: set[str] = set()
    for html_file in public_dir.glob("**/*.html"):
        text = html_file.read_text(encoding="utf-8")
        module_urls.update(re.findall(r'https://framerusercontent\.com/sites/[^"\']+\.mjs', text))

    if not module_urls:
        return

    print(f"  Found {len(module_urls)} additional JS modules to download")

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for url in module_urls:
            fname = url.split("/")[-1]
            lp = js_dir / fname
            if lp.exists():
                continue
            try:
                async with session.get(url, ssl=ssl_ctx, timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status == 200:
                        lp.write_bytes(await r.read())
                        print(f"    Downloaded {fname}")
            except Exception:
                pass

    # Rewrite references in HTML
    for html_file in public_dir.glob("**/*.html"):
        text = html_file.read_text(encoding="utf-8")
        changed = False
        for url in module_urls:
            fname = url.split("/")[-1]
            depth = len(html_file.relative_to(public_dir).parts) - 1
            rel = ("../" * depth if depth else "") + f"assets/js/{fname}"
            if url in text:
                text = text.replace(url, rel)
                changed = True
        if changed:
            html_file.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Phase 4 — Config files
# ---------------------------------------------------------------------------
def write_vercel_json(root: Path):
    cfg = {
        "version": 2,
        "public": True,
        "cleanUrls": True,
        "trailingSlash": False,
        "headers": [
            {
                "source": "/assets/(.*)",
                "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}],
            },
            {
                "source": "/(.*).mjs",
                "headers": [{"key": "Content-Type", "value": "application/javascript"}],
            },
        ],
    }
    (root / "vercel.json").write_text(json.dumps(cfg, indent=2))


def write_serve_sh(root: Path, port: int):
    script = f"""#!/bin/bash
cd "$(dirname "$0")/public"
echo "Site running at http://localhost:{port}"
python3 -m http.server {port}
"""
    p = root / "serve.sh"
    p.write_text(script)
    p.chmod(0o755)

# ---------------------------------------------------------------------------
# Phase 5 — Screenshots & parity
# ---------------------------------------------------------------------------
async def take_screenshots(source_url: str, routes: list[str], root: Path, port: int):
    """Capture source + local screenshots for each route / viewport."""
    local_url = f"http://localhost:{port}"
    ss_dir = root / "parity" / "screenshots"
    diff_dir = root / "parity" / "diffs"
    ss_dir.mkdir(parents=True, exist_ok=True)
    diff_dir.mkdir(parents=True, exist_ok=True)

    viewports = {"desktop": {"width": 1920, "height": 1080}, "mobile": {"width": 375, "height": 667}}
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for route in routes:
            rname = route.strip("/").replace("/", "_") or "home"
            route_result = {"route": route, "viewports": {}}

            for vp_name, vp_size in viewports.items():
                src_ctx = await browser.new_context(viewport=vp_size)
                loc_ctx = await browser.new_context(viewport=vp_size)
                src_page = await src_ctx.new_page()
                loc_page = await loc_ctx.new_page()
                src_page.on("console", lambda m: None)
                loc_page.on("console", lambda m: None)

                src_path = ss_dir / rname / vp_name / "source.png"
                loc_path = ss_dir / rname / vp_name / "local.png"
                dif_path = diff_dir / rname / f"{vp_name}_diff.png"
                src_path.parent.mkdir(parents=True, exist_ok=True)
                dif_path.parent.mkdir(parents=True, exist_ok=True)

                src_ok = loc_ok = False
                for label, pg, url, out in [
                    ("source", src_page, source_url, src_path),
                    ("local", loc_page, local_url, loc_path),
                ]:
                    try:
                        await pg.goto(f"{url}{route}", wait_until="networkidle", timeout=60_000)
                        await pg.wait_for_timeout(5000)
                        await pg.screenshot(path=str(out), full_page=True)
                        if label == "source":
                            src_ok = True
                        else:
                            loc_ok = True
                    except Exception:
                        pass

                similarity = None
                if src_ok and loc_ok:
                    try:
                        im1 = Image.open(src_path).convert("RGB")
                        im2 = Image.open(loc_path).convert("RGB")
                        if im1.size != im2.size:
                            im2 = im2.resize(im1.size, Image.Resampling.LANCZOS)
                        diff = ImageChops.difference(im1, im2)
                        diff.point(lambda px: min(px * 10, 255)).save(dif_path)
                        total = im1.width * im1.height
                        diff_px = sum(1 for px in diff.getdata() if sum(px) > 30)
                        similarity = round((1 - diff_px / total) * 100, 2)
                    except Exception:
                        pass

                route_result["viewports"][vp_name] = {
                    "similarity": similarity, "captured": src_ok and loc_ok
                }
                print(f"  {route} [{vp_name}] — similarity: {similarity}%")

                await src_ctx.close()
                await loc_ctx.close()

            results.append(route_result)

        await browser.close()

    (root / "parity" / "parity_results.json").write_text(json.dumps(results, indent=2))
    return results

# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------
def write_parity_report(root: Path, source_url: str, routes: list[str],
                        page_info: dict, parity_results: list):
    lines = [
        "# Parity Report: Framer Site Clone\n",
        f"**Source:** {source_url}  ",
        "**Approach:** Pure static HTML with localized assets\n",
        "## Discovered Routes\n",
    ]
    for r in routes:
        lines.append(f"- `{r}`")
    lines.append("")
    lines.append("## Asset Inventory\n")
    for cat, items in asset_inventory.items():
        if items:
            total = sum(i["size"] for i in items)
            lines.append(f"- **{cat}**: {len(items)} files ({total/1024/1024:.2f} MB)")
    lines.append("")
    lines.append("## Visual Parity\n")
    lines.append("| Route | Desktop | Mobile |")
    lines.append("|-------|---------|--------|")
    for pr in parity_results:
        d = pr["viewports"].get("desktop", {}).get("similarity")
        m = pr["viewports"].get("mobile", {}).get("similarity")
        lines.append(f"| `{pr['route']}` | {d}% | {m}% |")
    lines.append("")
    lines.append("## Known Differences\n")
    lines.append("1. Framer editor badge not present in clone (expected)")
    lines.append("2. Minor page-height variations due to rendering timing")
    lines.append("3. React hydration console warnings (cosmetic only)")
    (root / "PARITY_REPORT.md").write_text("\n".join(lines))


def write_readme(root: Path, source_url: str, port: int):
    text = f"""# Framer Site Clone

Static clone of **{source_url}**

## Run locally

```bash
./serve.sh
# or
cd public && python3 -m http.server {port}
```

Open http://localhost:{port}

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
python3 scripts/clone_framer_site.py {source_url}
```

## Parity

See [PARITY_REPORT.md](PARITY_REPORT.md) and `parity/screenshots/`.
"""
    (root / "README.md").write_text(text)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run(source_url: str, output_dir: str, port: int, skip_screenshots: bool):
    root = Path(output_dir).resolve()
    public_dir = root / "public"
    assets_dir = public_dir / "assets"
    root.mkdir(parents=True, exist_ok=True)

    # --- Phase 1 ---
    print("\n=== PHASE 1: Reconnaissance ===")
    routes, page_info, nav = await discover_routes(source_url)
    print(f"  Discovered {len(routes)} routes: {routes}")

    # --- Phase 2 ---
    print("\n=== PHASE 2: HTML Capture ===")
    await capture_pages(source_url, routes, public_dir)

    # --- Phase 3 ---
    print("\n=== PHASE 3: Asset Localization ===")
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        for hf in sorted(public_dir.glob("**/*.html")):
            n = await localize_html(hf, assets_dir, session)
            print(f"  {hf}: {n} replacements")

    print("  Downloading extra JS modules ...")
    await download_extra_js(public_dir, assets_dir)

    # --- Phase 4 ---
    print("\n=== PHASE 4: Vercel Configuration ===")
    write_vercel_json(root)
    write_serve_sh(root, port)
    print("  vercel.json and serve.sh written")

    # --- Phase 5 ---
    parity_results = []
    if not skip_screenshots:
        print("\n=== PHASE 5: Visual Parity Verification ===")
        print(f"  Starting local server on port {port} ...")
        import subprocess, signal
        srv = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port)],
            cwd=str(public_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        await asyncio.sleep(2)
        try:
            parity_results = await take_screenshots(source_url, routes, root, port)
        finally:
            srv.send_signal(signal.SIGTERM)
            srv.wait()
    else:
        print("\n=== PHASE 5: Skipped (--skip-screenshots) ===")

    # --- Reports ---
    print("\n=== Writing Reports ===")
    write_parity_report(root, source_url, routes, page_info, parity_results)
    write_readme(root, source_url, port)
    print("  PARITY_REPORT.md and README.md written")

    # Summary
    fc = sum(len(v) for v in asset_inventory.values())
    print(f"\n{'='*50}")
    print(f"  DONE — {len(routes)} routes, {fc} assets")
    print(f"  Output: {root}")
    print(f"  Run:    cd {root} && ./serve.sh")
    print(f"{'='*50}")


def main():
    ap = argparse.ArgumentParser(description="Clone a Framer site into a static, Vercel-deployable directory.")
    ap.add_argument("url", help="Framer site URL (e.g. https://my-site.framer.app/)")
    ap.add_argument("--output-dir", default=".", help="Output directory (default: current dir)")
    ap.add_argument("--port", type=int, default=8000, help="Local preview port (default: 8000)")
    ap.add_argument("--skip-screenshots", action="store_true", help="Skip Phase 5 screenshot comparison")
    args = ap.parse_args()

    url = args.url.rstrip("/") + "/"
    asyncio.run(run(url, args.output_dir, args.port, args.skip_screenshots))


if __name__ == "__main__":
    main()
