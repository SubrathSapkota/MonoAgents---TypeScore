"""
extractor/extractor.py — Browser-based computed style extraction.

Ported from extractor.js. Loads pages in headless Chromium and reads the
COMPUTED font styles of every visible text element. This reveals what actually
renders (after cascade, inheritance, @font-face resolution, and fallbacks)
rather than what the CSS source declares.

Returns "page fingerprints" consumed by the brand consistency scorer.
"""

from __future__ import annotations

from .crawler import crawl


# JavaScript function executed INSIDE the browser page.
# Must be self-contained — no Python closures.
COLLECT_IN_PAGE_JS = """
() => {
    const HEADING_TAGS = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6']);
    const BODY_TAGS = new Set([
        'P', 'SPAN', 'LI', 'A', 'TD', 'TH', 'BLOCKQUOTE', 'FIGCAPTION',
        'LABEL', 'DD', 'DT', 'EM', 'STRONG', 'SMALL', 'CAPTION',
    ]);

    const stripQuotes = (s) => s.replace(/^["']|["']$/g, '').trim();
    const firstFamily = (stack) => stripQuotes((stack || '').split(',')[0] || '').trim();

    const hasOwnText = (el) => {
        for (const node of el.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) return true;
        }
        return false;
    };

    const isVisible = (el) => {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };

    const result = {
        elementsAnalyzed: 0,
        primaryFamilies: {},
        weights: {},
        sizes: {},
        roleFamilies: { heading: {}, body: {} },
        fallbackStacks: {},
        inlineOverrides: 0,
        importantFontRules: 0,
    };

    const bump = (obj, key) => { obj[key] = (obj[key] || 0) + 1; };

    const all = document.querySelectorAll('body *');
    for (const el of all) {
        if (!hasOwnText(el) || !isVisible(el)) continue;

        const cs = getComputedStyle(el);
        const stack = cs.fontFamily || '';
        const primary = firstFamily(stack);
        if (!primary) continue;

        result.elementsAnalyzed++;
        bump(result.primaryFamilies, primary);
        bump(result.weights, String(cs.fontWeight));
        bump(result.sizes, String(Math.round(parseFloat(cs.fontSize))));

        const tag = el.tagName;
        if (HEADING_TAGS.has(tag)) bump(result.roleFamilies.heading, primary);
        else if (BODY_TAGS.has(tag)) bump(result.roleFamilies.body, primary);

        if (!result.fallbackStacks[primary]) result.fallbackStacks[primary] = [];
        const stackStr = stack.trim();
        if (!result.fallbackStacks[primary].includes(stackStr)) {
            result.fallbackStacks[primary].push(stackStr);
        }

        // Inline font override detection
        const inline = el.getAttribute('style') || '';
        if (/font(-family|-weight|-size|\\s*:)/i.test(inline)) result.inlineOverrides++;
        if (
            el.style.getPropertyPriority('font-family') === 'important' ||
            el.style.getPropertyPriority('font-size') === 'important' ||
            el.style.getPropertyPriority('font-weight') === 'important'
        ) {
            result.importantFontRules++;
        }
    }

    // Scan same-origin stylesheets for !important font rules
    try {
        for (const sheet of document.styleSheets) {
            let rules;
            try { rules = sheet.cssRules; } catch { continue; }
            if (!rules) continue;
            for (const rule of rules) {
                const t = rule.cssText || '';
                if (/font[^;{}]*!important/i.test(t)) result.importantFontRules++;
            }
        }
    } catch {}

    return result;
}
"""


async def extract_page(page, url: str, *, timeout: int = 30000) -> dict:
    """
    Extract computed font styles from a single page.

    Parameters
    ----------
    page    : Playwright page instance
    url     : URL to analyze
    timeout : Navigation timeout in ms

    Returns
    -------
    PageFingerprint dict:
    {
        "url": str,
        "elementsAnalyzed": int,
        "primaryFamilies": { family: count },
        "weights": { weight: count },
        "sizes": { sizePx: count },
        "roleFamilies": { "heading": {...}, "body": {...} },
        "fallbackStacks": { family: [stack_strings] },
        "inlineOverrides": int,
        "importantFontRules": int,
    }
    """
    await page.goto(url, wait_until="networkidle", timeout=timeout)

    # Wait for web fonts to finish loading
    try:
        await page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
    except Exception:  # noqa: BLE001
        pass

    data = await page.evaluate(COLLECT_IN_PAGE_JS)
    return {"url": url, **data}


async def extract_site(
    url: str,
    *,
    max_pages: int = 5,
    max_depth: int = 1,
    headless: bool = True,
    timeout: int = 30000,
) -> list[dict]:
    """
    Full extraction pipeline: crawl pages + extract fingerprints.

    Parameters
    ----------
    url        : Starting URL
    max_pages  : Max pages to crawl and analyze
    max_depth  : Crawl link depth
    headless   : Run browser in headless mode
    timeout    : Per-page navigation timeout

    Returns
    -------
    List of PageFingerprint dicts (one per successfully analyzed page)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ImportError(
            "Playwright is required for browser-based extraction. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    fingerprints: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            print(f"[extractor] Discovering pages from {url} …")
            urls = await crawl(browser, url, max_pages=max_pages, max_depth=max_depth)
            print(f"[extractor] Found {len(urls)} pages")

            page = await browser.new_page()
            await page.set_viewport_size({"width": 1366, "height": 900})

            for page_url in urls:
                try:
                    print(f"[extractor] Extracting: {page_url} …")
                    fp = await extract_page(page, page_url, timeout=timeout)
                    fingerprints.append(fp)
                    print(f"[extractor]   → {fp['elementsAnalyzed']} elements analyzed")
                except Exception as e:  # noqa: BLE001
                    print(f"[extractor]   → skipped ({e})")

            await page.close()
        finally:
            await browser.close()

    return fingerprints
