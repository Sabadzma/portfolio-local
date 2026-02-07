#!/usr/bin/env python3
"""Download missing Framer JavaScript modules"""

import asyncio
import aiohttp
import ssl
from pathlib import Path
import re

ASSETS_DIR = Path("public/assets")
SCRIPTS_DIR = ASSETS_DIR / "js"

# JavaScript modules to download
JS_MODULES = [
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/PCfld_oAA.BPo8PRGg.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/augiA20Il.CnpEaY-j.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/framer.BHwoO2HT.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/motion.L9gF1kgt.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/pKlcJRcBX.BE66DLKD.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/react.CYRL5wt9.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/rolldown-runtime.CWR5Z7Jy.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/shared-lib.BSe_C3bg.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/tlCjTTYYRZGym0g585DfZEIdn_FQOWglNBPmL-tNLn4.DByOuk-j.mjs",
    "https://framerusercontent.com/sites/3fsUBDASSViKpZLFY74d2i/xvTYe9Qg0.BEi3lrPV.mjs"
]

async def download_js_module(session, url):
    """Download a single JS module"""
    filename = url.split('/')[-1]
    local_path = SCRIPTS_DIR / filename

    if local_path.exists():
        print(f"  ✓ Already exists: {filename}")
        return filename

    try:
        print(f"  Downloading: {filename}...")
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with session.get(url, ssl=ssl_context, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.read()

                with open(local_path, 'wb') as f:
                    f.write(content)

                print(f"    ✓ Saved {len(content)} bytes")
                return filename
            else:
                print(f"    ✗ Failed: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None

async def update_html_files():
    """Update HTML files to use local JS modules"""
    print("\nUpdating HTML files...")

    html_files = list(Path("public").glob("**/*.html"))

    for html_file in html_files:
        print(f"  Processing {html_file}...")

        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace all framerusercontent.com module paths with local ones
        modified = False
        for url in JS_MODULES:
            filename = url.split('/')[-1]
            old_url = re.escape(url)

            # Calculate relative path
            depth = len(html_file.relative_to(Path("public")).parts) - 1
            rel_prefix = "../" * depth if depth > 0 else ""
            new_path = f"{rel_prefix}assets/js/{filename}"

            if re.search(old_url, content):
                content = re.sub(old_url, new_path, content)
                modified = True

        if modified:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    ✓ Updated")

async def main():
    print("=" * 60)
    print("Downloading Missing Framer JavaScript Modules")
    print("=" * 60)

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_js_module(session, url) for url in JS_MODULES]
        results = await asyncio.gather(*tasks)

    successful = [r for r in results if r]
    print(f"\n✓ Downloaded {len(successful)} modules")

    await update_html_files()
    print("\n✓ All HTML files updated")

if __name__ == "__main__":
    asyncio.run(main())
