"""
StockEdge Sector Scraper using Playwright.

This module scrapes the complete hierarchy of sectors, subsectors, and stocks
from https://web.stockedge.com/sectors using Playwright for browser automation.

Features:
    - Scrapes dynamic content with shadow DOM support
    - Exports data in JSON and Excel formats
    - Configurable viewport and zoom settings
    - Error handling and logging
    - Production-ready implementation

Usage:
    python scrape_stockedge_sectors.py

Output:
    - output_sectors_stocks.json: Complete hierarchical data
    - output_sectors_stocks.xlsx: Flattened data in Excel format
    - scraper.log: Detailed operation logs
"""

import logging
import time

from playwright.sync_api import sync_playwright
import pandas as pd
import json
from urllib.parse import urljoin

# Configuration - Hardcoded values
BASE_URL = "https://web.stockedge.com"
START_URL = urljoin(BASE_URL, "/sectors")
OUTPUT_JSON = "output_sectors_stocks.json"
OUTPUT_XLSX = "output_sectors_stocks.xlsx"
SHOW_BROWSER = False  # Set to True to see browser window during scraping
PAGE_ZOOM = 0.75  # Zoom factor to show more content
VIEWPORT_WIDTH = 2560
VIEWPORT_HEIGHT = 8000
MAX_RETRIES = 3
RETRY_DELAY = 2

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run():
    """Main scraper function that extracts sectors and their stocks."""
    results = []

    with sync_playwright() as p:
        try:
            logger.info("Launching browser")
            browser = p.chromium.launch(headless=not SHOW_BROWSER)

            context = browser.new_context(
                viewport={"width": VIEWPORT_WIDTH,
                          "height": VIEWPORT_HEIGHT},
                user_agent=USER_AGENT
            )
            page = context.new_page()

            logger.info(
                f"Opening {START_URL} with "
                f"viewport {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} "
                f"and zoom {PAGE_ZOOM}"
            )
            page.goto(START_URL, wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Apply zoom
            page.evaluate(
                f"() => {{ document.documentElement.style.zoom = "
                f"'{PAGE_ZOOM}'; }}"
            )
            page.wait_for_timeout(600)

            # Count sectors
            sector_count = page.evaluate(
                "() => document.querySelectorAll("
                "'ion-item[se-item]').length"
            )
            logger.info(f"Found {sector_count} sectors")

            for i in range(sector_count):
                try:
                    logger.info(f"Processing sector {i + 1}/{sector_count}")

                    sector_name = page.evaluate(
                        """(i) => {
                            const items = document.querySelectorAll(
                                'ion-item[se-item]'
                            );
                            if (!items[i]) return '';
                            const item = items[i];
                            let title = '';
                            const titleEl = item.querySelector('ion-text');
                            if (titleEl) {
                                title = titleEl.innerText.trim();
                            } else {
                                title = (item.innerText || '')
                                    .split('\\n')[0].trim();
                            }
                            items[i].click();
                            return title;
                        }""", i
                    )
                    page.wait_for_timeout(600)

                    sector_info = page.evaluate(
                        """(i) => {
                            const items = document.querySelectorAll(
                                'ion-item[se-item]'
                            );
                            const item = items[i];
                            if (!item) return null;

                            let title = '';
                            const titleEl = item.querySelector('ion-text');
                            if (titleEl) {
                                title = titleEl.innerText.trim();
                            } else {
                                title = (item.innerText || '')
                                    .split('\\n')[0].trim();
                            }

                            const list = document.querySelector('ion-list');
                            const subSectors = [];
                            if (list) {
                                const listItems = list.querySelectorAll(
                                    'ion-item'
                                );
                                listItems.forEach(li => {
                                    let name = null;
                                    let href = null;

                                    const firstShadowRoot = li.shadowRoot;
                                    if (firstShadowRoot) {
                                        const anchor = firstShadowRoot
                                            .querySelector('a.item-native');
                                        if (anchor) {
                                            href = anchor
                                                .getAttribute('href');
                                        }
                                    }

                                    const nameEl = li.querySelector(
                                        'ion-text.normal-font'
                                    );
                                    if (nameEl && nameEl.textContent) {
                                        name = nameEl.textContent.trim();
                                    }

                                    if (name || href) {
                                        subSectors.push({name, href});
                                    }
                                });
                            }
                            items[i].click();
                            return {title, subSectors};
                        }""", i
                    )

                    if not sector_info:
                        logger.warning(
                            f"Could not read sector info for index {i}"
                        )
                        continue

                    subSectors = sector_info.get("subSectors", [])
                    logger.info(
                        f"Sector: {sector_name} | "
                        f"{len(subSectors)} subsectors found"
                    )

                    sector_record = {
                        "sector_title": sector_name,
                        "subindustries": subSectors
                    }

                    subpage = context.new_page()
                    subpage.evaluate(
                        f"() => {{ document.documentElement.style.zoom = "
                        f"'{PAGE_ZOOM}'; }}"
                    )

                    for sub in subSectors:
                        sub_name = sub.get('name', 'Unknown')
                        sub_href = sub.get('href')
                        logger.info(f"   Processing: {sub_name}")

                        try:
                            full_url = urljoin(BASE_URL, sub_href)
                            subpage.goto(
                                full_url,
                                wait_until="networkidle",
                                timeout=20000
                            )
                            subpage.wait_for_timeout(800)

                            stocks = subpage.evaluate(
                                """() => {
                                    const selector = [
                                        'ion-list.background.list-md',
                                        'ion-list.list-md',
                                        'ion-list'
                                    ].join(', ');
                                    const listEl = document.querySelector(
                                        selector
                                    );
                                    if (!listEl) return [];

                                    const out = [];
                                    const selector2 =
                                        'ion-item[role="listitem"]';
                                    const items = listEl.querySelectorAll(
                                        selector2
                                    );

                                    items.forEach((item) => {
                                        const selector3 =
                                            'ion-col.ion-text-left';
                                        const nameCol = item.querySelector(
                                            selector3
                                        );
                                        const name = nameCol
                                            ? nameCol.textContent.trim()
                                                .replace(/\\s+/g, ' ')
                                            : '';

                                        let href = '';
                                        const shadowRoot = item.shadowRoot;
                                        if (shadowRoot) {
                                            const selector4 =
                                                'a.item-native';
                                            const anchor = shadowRoot
                                                .querySelector(selector4);
                                            if (anchor) {
                                                href = anchor
                                                    .getAttribute('href');
                                            }
                                        }

                                        if (name && href) {
                                            out.push({name, href});
                                        }
                                    });

                                    return out;
                                }"""
                            )

                            sub['stocks'] = stocks
                            logger.info(f"      Found {len(stocks)} stocks")

                        except Exception as e:
                            logger.error(
                                f"Error processing subsector "
                                f"{sub_name}: {e}"
                            )
                            sub['stocks'] = []

                    subpage.close()
                    results.append(sector_record)

                except Exception as e:
                    logger.error(f"Error processing sector {i}: {e}")
                    continue

            browser.close()
            logger.info("Browser closed successfully")

        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}", exc_info=True)
            raise

    # Save outputs
    try:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON output to {OUTPUT_JSON}")

        # Create Excel output
        rows = []
        for sec in results:
            s_title = sec.get("sector_title")
            for sub in sec.get("subindustries", []):
                sub_name = sub.get("name")
                sub_href = sub.get("href")
                rows.append({
                    "sector": s_title,
                    "subindustry": sub_name,
                    "sub_href": sub_href,
                })

        df = pd.DataFrame(rows)
        df.to_excel(OUTPUT_XLSX, index=False)
        logger.info(f"Saved Excel output to {OUTPUT_XLSX}")
        logger.info("Scraping completed successfully!")

    except Exception as e:
        logger.error(f"Error saving outputs: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        exit(1)
