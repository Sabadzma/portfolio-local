# Parity Report: Framer Site Clone

**Source:** https://authentic-devices-570724.framer.app/
**Approach:** Pure static HTML with localized assets (no framework wrapper)

## Discovered Routes

- `/` (Homepage)
- `/writing/design-tokens-101`
- `/writing/hello-world`
- `/writing/how-ai-is-changing-my-workflow`
- `/writing/how-to-think-like-both-a-designer-engineer`
- `/writing/test-test`
- `/writing/ui-performance`

## Asset Inventory

- **Fonts**: 62 files (woff2 — Inter, Fragment Mono, Geist Mono, etc.)
- **Images**: 89 files (jpg, png, jpeg — responsive srcset variants included)
- **JS Modules**: 19 files (Framer runtime, React, Motion, page modules)
- **Data**: 2 files (search index JSON)

## Visual Parity

| Route | Desktop | Mobile | Notes |
|-------|---------|--------|-------|
| `/` | **99.99%** | **99.88%** | Essentially pixel-perfect |
| `/writing/*` | ~88-89% | ~58-60% | Lower due to Framer CMS hydration (see Known Differences) |

## Known Differences

1. **Homepage clock** — The header displays a live clock (Asia/Tbilisi timezone). Tiny time differences between source and local captures account for the 0.01% desktop gap.

2. **Writing pages — CMS hydration** — The Framer runtime uses CMS collection data (`.framercms` files) to hydrate writing pages client-side. These files return 403 when accessed directly, so the React runtime re-renders with incomplete data. The SSR HTML content is correct; the issue is post-hydration JS. Not a priority per project scope.

3. **Framer editor badge** — The source site shows a small "Made in Framer" badge. The clone includes the badge module.

4. **Animations** — Framer Motion animations (scroll-triggered, hover states) are preserved via the localized JS runtime. Minor timing differences may occur between captures.

## Screenshots

Screenshots stored in:
- `parity/screenshots/<route>/<desktop|mobile>/source.png` — Source site
- `parity/screenshots/<route>/<desktop|mobile>/local.png` — Local clone
- `parity/diffs/<route>/<viewport>_diff.png` — Pixel diff (amplified 10x)
