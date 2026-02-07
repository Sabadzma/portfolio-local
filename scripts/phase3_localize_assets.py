#!/usr/bin/env python3
"""
Phase 3: Asset Localization
Downloads all external assets and rewrites HTML to use local paths.
"""

import re
import os
import json
import hashlib
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import ssl

PUBLIC_DIR = Path("public")
ASSETS_DIR = PUBLIC_DIR / "assets"

# Asset categories
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"
SCRIPTS_DIR = ASSETS_DIR / "js"
STYLES_DIR = ASSETS_DIR / "css"

# Track downloaded assets to avoid duplicates
downloaded_assets = {}
asset_inventory = {
    'fonts': [],
    'images': [],
    'scripts': [],
    'styles': [],
    'other': []
}


def get_asset_hash(url):
    """Generate a short hash for asset filename"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def get_local_path(url, asset_type):
    """Determine local path for an asset"""
    parsed = urlparse(url)
    path_parts = parsed.path.split('/')
    filename = path_parts[-1] if path_parts else 'asset'

    # If no extension, try to infer from URL or use hash
    if '.' not in filename or len(filename) > 100:
        ext_map = {
            'fonts': '.woff2',
            'images': '.png',
            'scripts': '.js',
            'styles': '.css'
        }
        asset_hash = get_asset_hash(url)
        filename = f"{asset_hash}{ext_map.get(asset_type, '')}"

    # Create subdirectory based on asset type
    type_dir = {
        'fonts': FONTS_DIR,
        'images': IMAGES_DIR,
        'scripts': SCRIPTS_DIR,
        'styles': STYLES_DIR
    }.get(asset_type, ASSETS_DIR / 'other')

    return type_dir / filename


async def download_asset(session, url, local_path, asset_type):
    """Download a single asset"""
    if url in downloaded_assets:
        return downloaded_assets[url]

    try:
        print(f"  Downloading {asset_type}: {url[:80]}...")

        # Create directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download with SSL verification disabled for development
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with session.get(url, ssl=ssl_context, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.read()

                # Write to file
                with open(local_path, 'wb') as f:
                    f.write(content)

                downloaded_assets[url] = str(local_path)
                asset_inventory[asset_type].append({
                    'url': url,
                    'local_path': str(local_path),
                    'size': len(content)
                })

                print(f"    ✓ Saved to {local_path} ({len(content)} bytes)")
                return str(local_path)
            else:
                print(f"    ✗ Failed: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None


def extract_urls_from_css(css_content, base_url):
    """Extract URLs from CSS content"""
    # Match url(...) patterns
    url_pattern = r'url\(["\']?([^"\')]+)["\']?\)'
    urls = re.findall(url_pattern, css_content)

    absolute_urls = []
    for url in urls:
        url = url.strip()
        if url.startswith(('http://', 'https://')):
            absolute_urls.append(url)
        elif url.startswith('//'):
            absolute_urls.append('https:' + url)
        elif not url.startswith('data:'):
            absolute_urls.append(urljoin(base_url, url))

    return absolute_urls


async def process_html_file(html_path, session):
    """Process a single HTML file to localize assets"""
    print(f"\n{'='*60}")
    print(f"Processing: {html_path}")
    print(f"{'='*60}")

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'lxml')
    base_url = "https://loving-event-914440.framer.app/"

    modifications = []

    # 1. Extract and download fonts from @font-face rules
    print("\n[1] Processing fonts...")
    style_tags = soup.find_all('style')
    for style in style_tags:
        if style.string:
            css_content = style.string

            # Find all font URLs
            font_urls = re.findall(r'url\(([^)]+)\)', css_content)
            for font_url in font_urls:
                font_url = font_url.strip('"\'')
                if font_url.startswith('http'):
                    local_path = get_local_path(font_url, 'fonts')
                    downloaded_path = await download_asset(session, font_url, local_path, 'fonts')

                    if downloaded_path:
                        # Calculate relative path from HTML file to asset
                        rel_path = os.path.relpath(downloaded_path, html_path.parent)
                        modifications.append(('css', font_url, rel_path))

    # 2. Download images
    print("\n[2] Processing images...")
    img_tags = soup.find_all('img')
    for img in img_tags:
        if img.get('src'):
            img_url = img['src']
            if img_url.startswith('http'):
                local_path = get_local_path(img_url, 'images')
                downloaded_path = await download_asset(session, img_url, local_path, 'images')

                if downloaded_path:
                    rel_path = os.path.relpath(downloaded_path, html_path.parent)
                    modifications.append(('attr', img_url, rel_path))

    # 3. Download meta images (favicons, og:image)
    print("\n[3] Processing meta images...")
    for tag in soup.find_all(['link', 'meta']):
        for attr in ['href', 'content']:
            url = tag.get(attr, '')
            if url.startswith('http') and any(ext in url for ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico']):
                local_path = get_local_path(url, 'images')
                downloaded_path = await download_asset(session, url, local_path, 'images')

                if downloaded_path:
                    rel_path = os.path.relpath(downloaded_path, html_path.parent)
                    modifications.append(('attr', url, rel_path))

    # 4. Download JavaScript files
    print("\n[4] Processing JavaScript files...")
    script_tags = soup.find_all('script', src=True)
    for script in script_tags:
        script_url = script['src']
        if script_url.startswith('http'):
            local_path = get_local_path(script_url, 'scripts')
            downloaded_path = await download_asset(session, script_url, local_path, 'scripts')

            if downloaded_path:
                rel_path = os.path.relpath(downloaded_path, html_path.parent)
                modifications.append(('attr', script_url, rel_path))

    # 5. Download CSS files
    print("\n[5] Processing CSS files...")
    link_tags = soup.find_all('link', rel='stylesheet')
    for link in link_tags:
        if link.get('href'):
            css_url = link['href']
            if css_url.startswith('http'):
                local_path = get_local_path(css_url, 'styles')
                downloaded_path = await download_asset(session, css_url, local_path, 'styles')

                if downloaded_path:
                    rel_path = os.path.relpath(downloaded_path, html_path.parent)
                    modifications.append(('attr', css_url, rel_path))

    # Apply all modifications to the HTML content
    print(f"\n[6] Applying {len(modifications)} modifications...")
    modified_content = content
    for mod_type, old_url, new_path in modifications:
        # Escape special regex characters in URL
        old_url_escaped = re.escape(old_url)
        modified_content = re.sub(old_url_escaped, new_path, modified_content)

    # Write modified HTML
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)

    print(f"✓ Updated {html_path}")

    return len(modifications)


async def main():
    print("=" * 60)
    print("PHASE 3: Asset Localization")
    print("=" * 60)

    # Create asset directories
    for dir_path in [FONTS_DIR, IMAGES_DIR, SCRIPTS_DIR, STYLES_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Find all HTML files
    html_files = list(PUBLIC_DIR.glob('**/*.html'))
    print(f"\nFound {len(html_files)} HTML files to process")

    # Create aiohttp session
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        total_modifications = 0

        for html_file in html_files:
            mods = await process_html_file(html_file, session)
            total_modifications += mods
            await asyncio.sleep(0.5)  # Brief pause between files

    # Save inventory
    print("\n" + "=" * 60)
    print("ASSET INVENTORY SUMMARY")
    print("=" * 60)

    for category, items in asset_inventory.items():
        if items:
            total_size = sum(item['size'] for item in items)
            print(f"\n{category.upper()}: {len(items)} files ({total_size / 1024 / 1024:.2f} MB)")
            for item in items[:3]:  # Show first 3
                print(f"  - {Path(item['local_path']).name} ({item['size'] / 1024:.1f} KB)")
            if len(items) > 3:
                print(f"  ... and {len(items) - 3} more")

    # Save detailed inventory
    with open('scripts/asset_inventory.json', 'w') as f:
        json.dump(asset_inventory, f, indent=2)

    print(f"\n✓ Total modifications applied: {total_modifications}")
    print("✓ Asset inventory saved to scripts/asset_inventory.json")

    # Show directory tree
    print("\n" + "=" * 60)
    print("ASSET DIRECTORY STRUCTURE")
    print("=" * 60)
    os.system(f"find {ASSETS_DIR} -type f | head -20")


if __name__ == "__main__":
    asyncio.run(main())
