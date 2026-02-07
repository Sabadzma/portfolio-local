#!/usr/bin/env python3
"""
Phase 5: Visual Parity Verification
Generates screenshots of source and local sites for comparison.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image, ImageChops, ImageDraw, ImageFont
import math

SOURCE_URL = "https://loving-event-914440.framer.app"
LOCAL_URL = "http://localhost:8000"
PARITY_DIR = Path("parity")
SCREENSHOTS_DIR = PARITY_DIR / "screenshots"
DIFFS_DIR = PARITY_DIR / "diffs"

# Load routes from Phase 1
with open('scripts/recon_results.json', 'r') as f:
    recon_data = json.load(f)
    ROUTES = [r for r in recon_data['discovered_routes'] if '@' not in r]

VIEWPORTS = {
    'desktop': {'width': 1920, 'height': 1080},
    'mobile': {'width': 375, 'height': 667}
}

parity_results = []


def calculate_diff(img1_path, img2_path, output_path):
    """Calculate pixel difference between two images"""
    try:
        img1 = Image.open(img1_path).convert('RGB')
        img2 = Image.open(img2_path).convert('RGB')

        # Ensure same size
        if img1.size != img2.size:
            print(f"    ⚠ Size mismatch: {img1.size} vs {img2.size}")
            # Resize img2 to match img1
            img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)

        # Calculate difference
        diff = ImageChops.difference(img1, img2)

        # Enhance difference for visibility
        diff_enhanced = diff.point(lambda p: p * 10 if p < 25 else 255)

        # Save diff
        diff_enhanced.save(output_path)

        # Calculate similarity score
        diff_pixels = sum(sum(1 for p in row if p > 10) for row in diff.getdata())
        total_pixels = img1.width * img1.height
        similarity = (1 - (diff_pixels / total_pixels)) * 100

        return similarity, diff_pixels, total_pixels

    except Exception as e:
        print(f"    ✗ Diff calculation error: {e}")
        return None, None, None


async def capture_screenshot(page, url, route, viewport_name, output_path):
    """Capture a single screenshot"""
    try:
        full_url = f"{url}{route}"
        print(f"    Capturing {viewport_name}: {full_url}")

        response = await page.goto(full_url, wait_until="networkidle", timeout=60000)

        if response.status != 200:
            print(f"      ✗ HTTP {response.status}")
            return False

        # Wait for rendering
        await page.wait_for_timeout(5000)

        # Scroll to trigger lazy loading
        await page.evaluate("""() => {
            window.scrollTo(0, document.body.scrollHeight / 2);
        }""")
        await page.wait_for_timeout(1000)

        await page.evaluate("() => window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

        # Take screenshot
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output_path), full_page=True)

        print(f"      ✓ Saved to {output_path}")
        return True

    except Exception as e:
        print(f"      ✗ Error: {e}")
        return False


async def compare_route(browser, route):
    """Compare source and local for a single route"""
    print(f"\n{'='*60}")
    print(f"Comparing route: {route}")
    print(f"{'='*60}")

    route_name = route.strip('/').replace('/', '_') or 'home'
    route_results = {
        'route': route,
        'route_name': route_name,
        'viewports': {}
    }

    for viewport_name, viewport_size in VIEWPORTS.items():
        print(f"\n  [{viewport_name.upper()}] {viewport_size['width']}x{viewport_size['height']}")

        # Create contexts for source and local
        source_context = await browser.new_context(viewport=viewport_size)
        local_context = await browser.new_context(viewport=viewport_size)

        source_page = await source_context.new_page()
        local_page = await local_context.new_page()

        # Suppress console logs
        source_page.on("console", lambda msg: None)
        local_page.on("console", lambda msg: None)

        # Screenshot paths
        source_screenshot = SCREENSHOTS_DIR / route_name / viewport_name / "source.png"
        local_screenshot = SCREENSHOTS_DIR / route_name / viewport_name / "local.png"
        diff_screenshot = DIFFS_DIR / route_name / f"{viewport_name}_diff.png"

        # Capture screenshots
        source_ok = await capture_screenshot(source_page, SOURCE_URL, route, viewport_name, source_screenshot)
        local_ok = await capture_screenshot(local_page, LOCAL_URL, route, viewport_name, local_screenshot)

        similarity = None
        if source_ok and local_ok:
            # Calculate diff
            print(f"    Calculating diff...")
            similarity, diff_pixels, total_pixels = calculate_diff(
                source_screenshot,
                local_screenshot,
                diff_screenshot
            )

            if similarity is not None:
                print(f"      Similarity: {similarity:.2f}%")
                print(f"      Different pixels: {diff_pixels}/{total_pixels}")

        route_results['viewports'][viewport_name] = {
            'source_screenshot': str(source_screenshot),
            'local_screenshot': str(local_screenshot),
            'diff_screenshot': str(diff_screenshot) if similarity is not None else None,
            'similarity': similarity,
            'captured_successfully': source_ok and local_ok
        }

        await source_context.close()
        await local_context.close()

    parity_results.append(route_results)
    return route_results


async def main():
    print("=" * 60)
    print("PHASE 5: Visual Parity Verification")
    print("=" * 60)

    # Create directories
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    DIFFS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("\nLaunching browser...")
        browser = await p.chromium.launch(headless=True)

        # Compare each route
        for route in ROUTES:
            await compare_route(browser, route)
            await asyncio.sleep(1)

        await browser.close()

    # Save results
    with open('parity/parity_results.json', 'w') as f:
        json.dump(parity_results, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("PARITY VERIFICATION SUMMARY")
    print("=" * 60)

    total_comparisons = len(ROUTES) * len(VIEWPORTS)
    successful_comparisons = sum(
        1 for r in parity_results
        for v in r['viewports'].values()
        if v['captured_successfully']
    )

    print(f"\nTotal comparisons: {total_comparisons}")
    print(f"Successful: {successful_comparisons}")

    print("\nSimilarity Scores:")
    for result in parity_results:
        print(f"\n  {result['route']}")
        for viewport_name, viewport_data in result['viewports'].items():
            if viewport_data['similarity'] is not None:
                score = viewport_data['similarity']
                status = "✓" if score > 95 else "⚠" if score > 85 else "✗"
                print(f"    {status} {viewport_name}: {score:.2f}%")
            else:
                print(f"    ✗ {viewport_name}: Failed")

    print(f"\n✓ Results saved to parity/parity_results.json")
    print(f"✓ Screenshots saved to {SCREENSHOTS_DIR}")
    print(f"✓ Diffs saved to {DIFFS_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
