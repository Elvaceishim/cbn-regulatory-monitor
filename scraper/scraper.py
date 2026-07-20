"""
CBN Circulars & Press Releases Monitor — scraper module.

The CBN site renders its document listings via JavaScript after page load
(confirmed: a plain HTTP fetch of these pages returns an empty shell with
no actual circulars listed). That's exactly the scenario Playwright exists
for — it runs a real browser and waits for JS-rendered content, which a
simple requests+BeautifulSoup scraper would never see.

IMPORTANT — this needs live verification:
I built the item-extraction selector from a pattern I found across several
real CBN document URLs during research (they consistently look like
/Out/2025/CCD/CIRCULAR-NAME.pdf), but I have no way to execute JavaScript
or reach cbn.gov.ng from my own environment, so I could not confirm this
selector against the site's actual rendered DOM. Run this in --debug mode
first — it dumps every link found on the page — so we can see together
whether the primary selector caught the real items or needs adjusting.

Usage:
    python3 scraper.py                 # normal run, checks for new items
    python3 scraper.py --debug         # opens a visible browser, dumps
                                        # ALL links found for calibration
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

# Identifying ourselves honestly rather than spoofing a normal browser —
# good practice regardless of what a site's terms do or don't require.
USER_AGENT = "Mozilla/5.0 (compatible; PersonalRegMonitor/1.0; +https://github.com/Elvaceishim)"

TARGET_PAGES = {
    "Circulars": "https://www.cbn.gov.ng/Documents/circulars.html",
    "Press Releases": "https://www.cbn.gov.ng/Documents/PressReleases.html",
}

# Real CBN document links consistently follow this shape, confirmed across
# several actual examples during research — this is an informed starting
# point, not a guess, but still needs live confirmation (see module docstring).
DOCUMENT_LINK_PATTERN = "/Out/"




# Boilerplate footer links that happen to live under /Out/ but aren't
# actual circulars — confirmed by live testing against the real site.
EXCLUDED_TITLES = {"privacy notice", "privacy & cookie notice"}


def wait_for_stable_content(page, pattern: str, max_wait_seconds: int = 30, stable_checks: int = 6, poll_interval: float = 1.0) -> int:
    """Polls the page until the COUNT of matching links stops changing,
    rather than waiting for a single element to exist.

    stable_checks=6 (6 consecutive seconds of no change) rather than a
    shorter window: testing showed the Press Releases page loads content
    in at least two separate waves with a real pause between them — a
    3-second stable window was fooled by the count plateauing at a
    partial value (4) before a second batch of ~10 more items arrived.
    A longer required stability window trades a few extra seconds of
    wait time for actually catching the full list.
    """
    last_count = -1
    stable_streak = 0
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        current_count = page.eval_on_selector_all(
            f"a[href*='{pattern}']", "elements => elements.length"
        )
        if current_count == last_count:
            stable_streak += 1
            if stable_streak >= stable_checks:
                return current_count
        else:
            stable_streak = 0
        last_count = current_count
        page.wait_for_timeout(int(poll_interval * 1000))
        elapsed += poll_interval
    return last_count


def scrape_page(page, url: str, source_name: str) -> list[dict]:
    """Navigates to a page and waits for the list of matching links to
    actually finish loading, using count-stabilization polling rather
    than a single-element existence check (see wait_for_stable_content
    docstring for why the simpler check was insufficient in practice).
    """
    page.goto(url, wait_until="domcontentloaded", timeout=30000)

    stable_count = wait_for_stable_content(page, DOCUMENT_LINK_PATTERN)
    if stable_count == 0:
        print(f"  Warning: zero matching links found on {source_name} after waiting — page may not have loaded, or genuinely has nothing to show.", file=sys.stderr)

    links = page.eval_on_selector_all(
        "a",
        """(elements) => elements.map(e => ({
            text: e.textContent.trim(),
            href: e.href
        }))"""
    )

    items = []
    for link in links:
        if DOCUMENT_LINK_PATTERN in link["href"] and link["text"]:
            if link["text"].strip().lower() in EXCLUDED_TITLES:
                continue
            items.append({
                "title": link["text"],
                "url": link["href"],
                "source": source_name,
            })
    return items


def run_debug(url: str, source_name: str):
    """Opens a VISIBLE browser and dumps every link on the page, regardless
    of pattern matching — this is how we calibrate the real selector
    together against the live site."""
    print(f"\n=== DEBUG MODE: {source_name} ({url}) ===")
    print("Opening a visible browser window. Watch it load, then check the terminal output below.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        stable_count = wait_for_stable_content(page, DOCUMENT_LINK_PATTERN)
        print(f"Content stabilized at {stable_count} matching links.\n")

        all_links = page.eval_on_selector_all(
            "a",
            """(elements) => elements.map(e => ({
                text: e.textContent.trim(),
                href: e.href
            }))"""
        )

        print(f"Total links found on page: {len(all_links)}\n")
        matching = [l for l in all_links if DOCUMENT_LINK_PATTERN in l["href"]]
        print(f"Links matching '{DOCUMENT_LINK_PATTERN}' pattern: {len(matching)}")
        for l in matching[:15]:
            print(f"  MATCH: {l['text'][:60]!r} -> {l['href']}")

        non_matching_with_text = [l for l in all_links if l["text"] and DOCUMENT_LINK_PATTERN not in l["href"]]
        print(f"\nOther links with text (first 15, for comparison): ")
        for l in non_matching_with_text[:15]:
            print(f"  OTHER: {l['text'][:60]!r} -> {l['href']}")

        print("\nBrowser window will stay open for 30 seconds so you can inspect the page manually.")
        print("Right-click a circular/press release link and 'Inspect' to see its actual href pattern.")
        page.wait_for_timeout(30000)
        browser.close()


def check_for_updates() -> dict:
    """Stateless: scrapes both pages and returns everything currently
    listed, deduped by URL within this run (the same document sometimes
    appears on both Circulars and Press Releases — see dedup comment
    below). Does NOT track what's been seen before; that responsibility
    belongs to Postgres via the n8n pipeline, same pattern as the job
    search and invoice automation projects. A local file doesn't survive
    container rebuilds cleanly and gives no audit trail — Postgres does
    both correctly.
    """
    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        for source_name, url in TARGET_PAGES.items():
            try:
                items = scrape_page(page, url, source_name)
                all_items.extend(items)
                print(f"{source_name}: found {len(items)} document links", file=sys.stderr)
            except Exception as e:
                print(f"Failed to scrape {source_name} ({url}): {e}", file=sys.stderr)

        browser.close()

    # Dedupe by URL across pages — the same document sometimes appears on
    # both Circulars and Press Releases. Reporting it twice would mean two
    # separate alerts for the same PDF later on, which works against the
    # "alert only when something genuinely needs attention" principle this
    # whole project (and the two before it) is built around. Merge sources
    # into a list instead of discarding the cross-listing information entirely.
    deduped_by_url = {}
    for item in all_items:
        if item["url"] in deduped_by_url:
            if item["source"] not in deduped_by_url[item["url"]]["sources"]:
                deduped_by_url[item["url"]]["sources"].append(item["source"])
        else:
            deduped_by_url[item["url"]] = {
                "title": item["title"],
                "url": item["url"],
                "sources": [item["source"]],
            }
    all_items_deduped = list(deduped_by_url.values())

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_found": len(all_items_deduped),
        "items": all_items_deduped,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Open a visible browser and dump all links for selector calibration")
    args = parser.parse_args()

    if args.debug:
        for source_name, url in TARGET_PAGES.items():
            run_debug(url, source_name)
    else:
        result = check_for_updates()
        print(json.dumps(result, indent=2))
