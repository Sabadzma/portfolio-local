#!/usr/bin/env python3
"""
Phase 1: Site Reconnaissance and Route Discovery
Analyzes the Framer portfolio site to discover all routes and create initial mapping.
"""

import json
import asyncio
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
import sys

SOURCE_URL = "https://loving-event-914440.framer.app/"

async def discover_routes():
    """Discover all routes from the Framer site"""
    routes = set()
    routes.add("/")  # Always include home

    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Fetch main page
            print(f"Navigating to {SOURCE_URL}...")
            response = await page.goto(SOURCE_URL, wait_until="networkidle", timeout=30000)
            print(f"Response status: {response.status}")

            # Wait for content to render
            await page.wait_for_timeout(3000)

            # Extract all internal links
            print("Extracting internal links...")
            links = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.map(a => ({
                    href: a.href,
                    text: a.textContent.trim(),
                    isInternal: a.href.includes('framer.app')
                }));
            }""")

            # Filter and normalize internal links
            base_domain = urlparse(SOURCE_URL).netloc
            for link in links:
                href = link['href']
                parsed = urlparse(href)

                # Check if it's an internal link
                if parsed.netloc == base_domain or not parsed.netloc:
                    path = parsed.path
                    if path and path != '/':
                        # Normalize path
                        if not path.startswith('/'):
                            path = '/' + path
                        routes.add(path)
                        print(f"  Found route: {path} ('{link['text']}')")

            # Get page title
            title = await page.title()
            print(f"\nPage title: {title}")

            # Try to fetch sitemap
            print("\nChecking for sitemap.xml...")
            sitemap_url = urljoin(SOURCE_URL, '/sitemap.xml')
            try:
                sitemap_page = await context.new_page()
                sitemap_response = await sitemap_page.goto(sitemap_url, timeout=10000)
                if sitemap_response.status == 200:
                    sitemap_content = await sitemap_page.content()
                    print("Sitemap found!")
                    # Parse sitemap URLs
                    import re
                    sitemap_urls = re.findall(r'<loc>(.*?)</loc>', sitemap_content)
                    for url in sitemap_urls:
                        parsed = urlparse(url)
                        if parsed.path and parsed.path != '/':
                            routes.add(parsed.path)
                            print(f"  Sitemap route: {parsed.path}")
                else:
                    print(f"Sitemap not found (status {sitemap_response.status})")
                await sitemap_page.close()
            except Exception as e:
                print(f"Could not fetch sitemap: {e}")

            # Get navigation structure
            print("\nAnalyzing navigation structure...")
            nav_structure = await page.evaluate("""() => {
                const navElements = document.querySelectorAll('nav, [role="navigation"], header');
                return Array.from(navElements).map(nav => ({
                    tag: nav.tagName,
                    links: Array.from(nav.querySelectorAll('a')).map(a => ({
                        text: a.textContent.trim(),
                        href: a.href
                    }))
                }));
            }""")

            print(json.dumps(nav_structure, indent=2))

            # Get page structure
            print("\nAnalyzing page structure...")
            page_info = await page.evaluate("""() => {
                return {
                    title: document.title,
                    metaDescription: document.querySelector('meta[name="description"]')?.content || '',
                    h1Count: document.querySelectorAll('h1').length,
                    h2Count: document.querySelectorAll('h2').length,
                    imageCount: document.querySelectorAll('img').length,
                    videoCount: document.querySelectorAll('video').length,
                    scriptCount: document.querySelectorAll('script').length,
                    stylesheetCount: document.querySelectorAll('link[rel="stylesheet"]').length
                }
            }""")

            print(json.dumps(page_info, indent=2))

        except Exception as e:
            print(f"Error during reconnaissance: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    return sorted(routes), page_info, nav_structure

async def main():
    print("=" * 60)
    print("PHASE 1: Site Reconnaissance")
    print("=" * 60)

    routes, page_info, nav_structure = await discover_routes()

    print("\n" + "=" * 60)
    print("DISCOVERED ROUTES:")
    print("=" * 60)
    for route in routes:
        print(f"  {route}")

    # Save results
    results = {
        'source_url': SOURCE_URL,
        'discovered_routes': routes,
        'page_info': page_info,
        'navigation_structure': nav_structure,
        'total_routes': len(routes)
    }

    with open('scripts/recon_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Found {len(routes)} route(s)")
    print("✓ Results saved to scripts/recon_results.json")

    return results

if __name__ == "__main__":
    asyncio.run(main())
