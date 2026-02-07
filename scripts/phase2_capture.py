#!/usr/bin/env python3
"""
Phase 2: Capture Fully Rendered HTML
Captures all discovered routes with complete DOM and inline styles.
"""

import json
import asyncio
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

SOURCE_URL = "https://loving-event-914440.framer.app/"
PUBLIC_DIR = Path("public")

# Load discovered routes from Phase 1
with open('scripts/recon_results.json', 'r') as f:
    recon_data = json.load(f)
    ROUTES = [r for r in recon_data['discovered_routes'] if '@' not in r]  # Exclude email links

print(f"Routes to capture: {ROUTES}")


async def capture_page(page, route):
    """Capture a single page with full rendering"""
    url = urljoin(SOURCE_URL, route)
    print(f"\n{'='*60}")
    print(f"Capturing: {url}")
    print(f"Route: {route}")
    print(f"{'='*60}")

    try:
        # Navigate to page
        response = await page.goto(url, wait_until="networkidle", timeout=60000)
        print(f"  Status: {response.status}")

        if response.status != 200:
            print(f"  ❌ Failed with status {response.status}")
            return None

        # Wait for Framer to fully render
        await page.wait_for_timeout(5000)  # 5s for animations and lazy loading

        # Wait for any lazy-loaded images
        await page.evaluate("""() => {
            return new Promise((resolve) => {
                const images = Array.from(document.querySelectorAll('img'));
                let loaded = 0;
                if (images.length === 0) {
                    resolve();
                    return;
                }
                images.forEach(img => {
                    if (img.complete) {
                        loaded++;
                        if (loaded === images.length) resolve();
                    } else {
                        img.addEventListener('load', () => {
                            loaded++;
                            if (loaded === images.length) resolve();
                        });
                        img.addEventListener('error', () => {
                            loaded++;
                            if (loaded === images.length) resolve();
                        });
                    }
                });
                // Timeout after 10s
                setTimeout(resolve, 10000);
            });
        }""")

        # Get fully rendered HTML
        html_content = await page.content()
        print(f"  ✓ Captured {len(html_content)} bytes")

        # Get page metadata
        metadata = await page.evaluate("""() => ({
            title: document.title,
            meta_description: document.querySelector('meta[name="description"]')?.content || '',
            meta_og_image: document.querySelector('meta[property="og:image"]')?.content || '',
            canonical: document.querySelector('link[rel="canonical"]')?.href || '',
            lang: document.documentElement.lang || 'en'
        })""")

        print(f"  Title: {metadata['title']}")

        # Determine output path
        if route == '/':
            output_path = PUBLIC_DIR / 'index.html'
        else:
            # Create nested directory structure
            route_path = route.lstrip('/')
            output_path = PUBLIC_DIR / route_path / 'index.html'

        # Create directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  ✓ Saved to: {output_path}")

        return {
            'route': route,
            'url': url,
            'output_path': str(output_path),
            'size_bytes': len(html_content),
            'metadata': metadata,
            'status': 'success'
        }

    except Exception as e:
        print(f"  ❌ Error capturing {route}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'route': route,
            'url': url,
            'status': 'failed',
            'error': str(e)
        }


async def capture_all_pages():
    """Capture all pages in the route list"""
    results = []

    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-web-security', '--disable-features=IsolateOrigins,site-per-process']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        # Enable console logging for debugging
        page.on("console", lambda msg: print(f"  [Browser Console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [Browser Error] {err}"))

        # Capture each route
        for route in ROUTES:
            result = await capture_page(page, route)
            if result:
                results.append(result)
            await asyncio.sleep(2)  # Brief pause between pages

        await browser.close()

    return results


def main():
    print("=" * 60)
    print("PHASE 2: Capture Fully Rendered HTML")
    print("=" * 60)

    # Create public directory
    PUBLIC_DIR.mkdir(exist_ok=True)

    # Run capture
    results = asyncio.run(capture_all_pages())

    # Summary
    print("\n" + "=" * 60)
    print("CAPTURE SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') == 'failed']

    print(f"Total routes: {len(ROUTES)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print("\n✓ Successfully captured:")
        for r in successful:
            print(f"  {r['route']} → {r['output_path']}")

    if failed:
        print("\n✗ Failed to capture:")
        for r in failed:
            print(f"  {r['route']}: {r.get('error', 'Unknown error')}")

    # Save results
    with open('scripts/capture_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n✓ Results saved to scripts/capture_results.json")

    # Update directory tree
    print("\n" + "=" * 60)
    print("PUBLIC DIRECTORY STRUCTURE")
    print("=" * 60)
    os.system(f"tree {PUBLIC_DIR} -L 3 || find {PUBLIC_DIR} -type f")


if __name__ == "__main__":
    main()
