"""
Complete StockEdge Scraper - Unified Solution.

This script scrapes the complete hierarchy of sectors, subsectors, stocks,
and their exchange codes in a single pass from https://web.stockedge.com/sectors.

Features:
    - Single-script solution (no intermediate files needed)
    - Scrapes sectors → subsectors → stocks → exchange codes
    - Uses back navigation to efficiently traverse stock lists
    - Handles Shadow DOM and dynamic content
    - Exports complete data with codes in JSON format

Usage:
    python scrap_stockedge_sectors.py

Output:
    - sector_data.json: Full hierarchical data with stock codes
    - scraper_complete.log: Detailed operation logs
"""

import logging
import os
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://web.stockedge.com"
START_URL = urljoin(BASE_URL, "/sectors")
OUTPUT_JSON = "sector_data.json"
SHOW_BROWSER = False  # Set to True to see browser window during scraping
PAGE_ZOOM = 0.50  # Zoom factor to show more content
VIEWPORT_WIDTH = 2560
VIEWPORT_HEIGHT = 8000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_complete.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set console handler to INFO, file handler keeps DEBUG
console_handler = None
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        console_handler = handler
        console_handler.setLevel(logging.INFO)  # Console shows INFO and above
        break

# ============================================================================
# JavaScript Code Snippets for Browser Evaluation
# ============================================================================

# Extract exchange code (NSE/BSE) and symbol from stock detail page
JS_EXTRACT_CODE = r"""
() => {
  const isVisible = (el) => {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style && style.visibility !== 'hidden' &&
           style.display !== 'none';
  };

  const allTexts = Array.from(
    document.querySelectorAll('ion-text')
  );
  const exchangeEl = allTexts.find((el) => {
    const txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
    return isVisible(el) && /\b(NSE|BSE)\b/i.test(txt);
  });

  if (!exchangeEl) return null;

  const exchange = (exchangeEl.textContent || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase()
    .match(/\b(NSE|BSE)\b/)[0];

  const container =
    exchangeEl.closest(
      'div, ion-item, ion-row, ion-toolbar, ion-header'
    ) || exchangeEl.parentElement;

  let symbol = null;

  if (container) {
    const texts = Array.from(
      container.querySelectorAll('ion-text')
    )
      .map((el) => (el.textContent || '')
        .replace(/\s+/g, ' ').trim())
      .filter(Boolean);

    symbol = texts.find(
      (t) => t.toUpperCase() !== exchange
    ) || null;
  }

  if (!symbol) {
    let sib = exchangeEl.nextElementSibling;
    while (sib) {
      if (sib.tagName &&
          sib.tagName.toLowerCase() === 'ion-text') {
        const t = (sib.textContent || '')
          .replace(/\s+/g, ' ').trim();
        if (t) { symbol = t; break; }
      }
      sib = sib.nextElementSibling;
    }
  }

  if (!symbol) return null;

  return `${exchange}:${symbol}`;
}
"""

# Count all sector accordion items on main page
JS_COUNT_SECTORS = """
() => document.querySelectorAll('ion-item[se-item]').length
"""

# Click sector accordion and extract title
JS_CLICK_SECTOR_GET_NAME = """
(i) => {
    const items = document.querySelectorAll('ion-item[se-item]');
    if (!items[i]) return '';
    const item = items[i];
    let title = '';
    const titleEl = item.querySelector('ion-text');
    if (titleEl) {
        title = titleEl.innerText.trim();
    } else {
        title = (item.innerText || '').split('\\n')[0].trim();
    }
    items[i].click();
    return title;
}
"""

# Extract subsector list from expanded sector accordion
JS_EXTRACT_SUBSECTORS = """
(i) => {
    const items = document.querySelectorAll('ion-item[se-item]');
    const item = items[i];
    if (!item) return null;

    let title = '';
    const titleEl = item.querySelector('ion-text');
    if (titleEl) {
        title = titleEl.innerText.trim();
    } else {
        title = (item.innerText || '').split('\\n')[0].trim();
    }

    const list = document.querySelector('ion-list');
    const subSectors = [];
    if (list) {
        const listItems = list.querySelectorAll('ion-item');
        listItems.forEach(li => {
            let name = null;
            let href = null;

            const firstShadowRoot = li.shadowRoot;
            if (firstShadowRoot) {
                const anchor = firstShadowRoot.querySelector('a.item-native');
                if (anchor) {
                    href = anchor.getAttribute('href');
                }
            }

            const nameEl = li.querySelector('ion-text.normal-font');
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
}
"""

# Extract all stocks from subsector page
JS_EXTRACT_STOCK_LIST = """
() => {
    const selector = [
        'ion-list.background.list-md',
        'ion-list.list-md',
        'ion-list'
    ].join(', ');
    const listEl = document.querySelector(selector);
    if (!listEl) return [];

    const out = [];
    const selector2 = 'ion-item[role="listitem"]';
    const items = listEl.querySelectorAll(selector2);

    items.forEach((item, index) => {
        const selector3 = 'ion-col.ion-text-left';
        const nameCol = item.querySelector(selector3);
        const name = nameCol
            ? nameCol.textContent.trim().replace(/\\s+/g, ' ')
            : '';

        let href = '';
        const shadowRoot = item.shadowRoot;
        if (shadowRoot) {
            const selector4 = 'a.item-native';
            const anchor = shadowRoot.querySelector(selector4);
            if (anchor) {
                href = anchor.getAttribute('href');
            }
        }

        if (name && href) {
            out.push({name, href, index});
        }
    });

    return out;
}
"""

# Click stock item by index in subsector list
JS_CLICK_STOCK_BY_INDEX = """
(index) => {
    const selector = [
        'ion-list.background.list-md',
        'ion-list.list-md',
        'ion-list'
    ].join(', ');
    const listEl = document.querySelector(selector);
    const items = listEl.querySelectorAll('ion-item[role="listitem"]');
    if (items[index]) {
        items[index].click();
    }
}
"""

# Set page zoom level


def JS_SET_ZOOM(zoom_level):
    return f"() => {{ document.documentElement.style.zoom = '{zoom_level}'; }}"


def extract_stock_code_from_page(page, stock_name="Unknown"):
    """Extract stock exchange code from current stock detail page."""
    try:
        code_str = page.evaluate(JS_EXTRACT_CODE)

        # Debug logging when code extraction fails
        if not code_str:
            logger.debug(f"Debug info for {stock_name}:")
            logger.debug(f"  Current URL: {page.url}")

            # Check if page loaded correctly
            try:
                ion_texts = page.evaluate(
                    """() => {
                        const texts = Array.from(document.querySelectorAll('ion-text'));
                        return texts.slice(0, 10).map(el => ({
                            text: el.textContent.trim(),
                            visible: window.getComputedStyle(el).display !== 'none'
                        }));
                    }"""
                )
                logger.debug(
                    f"  Found {len(ion_texts)} ion-text elements (showing first 10):")
                for i, item in enumerate(ion_texts, 1):
                    logger.debug(
                        f"    {i}. '{item['text']}' (visible: {item['visible']})")
            except Exception as debug_e:
                logger.debug(f"  Could not extract debug info: {debug_e}")

        return code_str
    except Exception as e:
        logger.error(f"Error extracting stock code for {stock_name}: {e}")
        return None


def scrape_stocks_with_codes(subpage, subsector_url, sub_name, instrument_map=None):
    """
    Navigate to subsector page, extract stocks, visit each stock page
    to get codes, and use back navigation.

    Returns: List of stocks with codes
    """
    stocks_with_codes = []

    try:
        logger.info(f"   Opening subsector: {sub_name}")
        subpage.goto(
            subsector_url,
            wait_until="networkidle",
            timeout=20000
        )

        # Set zoom after navigation to ensure it applies correctly
        subpage.evaluate(JS_SET_ZOOM(PAGE_ZOOM))
        subpage.wait_for_timeout(1500)

        # Extract stock list with indices
        stock_list = subpage.evaluate(JS_EXTRACT_STOCK_LIST)

        total_stocks = len(stock_list)
        logger.info(f"      Found {total_stocks} stocks in {sub_name}")

        # Take screenshot for debugging when zero stocks are found
        if total_stocks == 0:
            try:
                # Create debug_screenshots directory if it doesn't exist
                screenshot_dir = "debug_screenshots"
                os.makedirs(screenshot_dir, exist_ok=True)

                # Create filename with timestamp and sector/subsector info
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_sub_name = sub_name.replace(' ', '_').replace(
                    '/', '_').replace('\\', '_')[:50]
                screenshot_filename = f"zero_stocks_{safe_sub_name}_{timestamp}.png"
                screenshot_path = os.path.join(
                    screenshot_dir, screenshot_filename)

                # Capture screenshot
                subpage.screenshot(path=screenshot_path, full_page=True)
                logger.warning(
                    f"      ⚠️  ZERO STOCKS FOUND - Screenshot saved: {screenshot_path}")
                logger.warning(f"      URL: {subpage.url}")
            except Exception as screenshot_error:
                logger.error(
                    f"      Failed to capture screenshot: {screenshot_error}")

        # Process each stock
        processed_count = 0  # Track how many stocks we've successfully processed
        while processed_count < total_stocks:
            # Re-extract stock list on each iteration to handle recovery scenarios
            current_stock_list = subpage.evaluate(JS_EXTRACT_STOCK_LIST)

            # If list is empty or different, we've lost sync - reload page
            if len(current_stock_list) != total_stocks:
                logger.warning(
                    f"      Stock list changed ({len(current_stock_list)} vs {total_stocks}), reloading page...")
                subpage.goto(
                    subsector_url, wait_until="networkidle", timeout=20000)
                subpage.evaluate(JS_SET_ZOOM(PAGE_ZOOM))
                subpage.wait_for_timeout(1500)
                current_stock_list = subpage.evaluate(JS_EXTRACT_STOCK_LIST)

            if processed_count >= len(current_stock_list):
                logger.error(
                    f"      Processed count ({processed_count}) >= list length ({len(current_stock_list)}), stopping")
                break

            stock_info = current_stock_list[processed_count]
            stock_name = stock_info['name']
            stock_index = stock_info['index']
            idx = processed_count + 1

            # Initialize variables for this iteration
            stock_code = None
            instrument_key = None
            success = False

            try:
                logger.info(
                    f"      [{idx}/{total_stocks}] Clicking: {stock_name}")

                # Click the stock item using its index
                subpage.evaluate(JS_CLICK_STOCK_BY_INDEX, stock_index)

                # Wait for navigation to stock detail page
                subpage.wait_for_load_state("domcontentloaded", timeout=15000)
                subpage.wait_for_timeout(2500)

                # Extract stock code
                stock_code = extract_stock_code_from_page(subpage, stock_name)

                # Look up instrument key if map is provided
                if instrument_map and stock_code and ":" in stock_code:
                    parts = stock_code.split(":")
                    if len(parts) >= 2:
                        exchange = parts[0].upper()
                        symbol = parts[1].upper()
                        instrument_key = instrument_map.get((exchange, symbol))

                if stock_code:
                    logger.info(f"         -> Code: {stock_code}")
                    if instrument_key:
                        logger.debug(
                            f"         -> Instrument Key: {instrument_key}")
                    else:
                        logger.warning(
                            f"         -> No instrument key found for {stock_code}")
                else:
                    logger.warning(
                        f"         -> Could not extract code for {stock_name}")
                    logger.warning(f"            URL: {subpage.url}")

                    # Take a screenshot for manual inspection
                    try:
                        screenshot_path = f"debug_no_code_{stock_name.replace(' ', '_').replace('.', '')[:30]}.png"
                        subpage.screenshot(path=screenshot_path)
                        logger.warning(
                            f"            Screenshot saved: {screenshot_path}")
                    except:
                        pass

                # Go back to stock list
                logger.debug(f"         Going back to list...")
                subpage.go_back(wait_until="domcontentloaded", timeout=15000)
                subpage.wait_for_timeout(800)
                success = True

            except PlaywrightTimeout as e:
                logger.error(f"      Timeout processing {stock_name}: {e}")
                # Recovery: reload the entire subsector page
                logger.warning("      Reloading subsector page to recover...")
                try:
                    subpage.goto(
                        subsector_url, wait_until="networkidle", timeout=20000)
                    subpage.evaluate(JS_SET_ZOOM(PAGE_ZOOM))
                    subpage.wait_for_timeout(1500)
                    success = True  # We recovered, mark as success to move on
                except Exception as recovery_error:
                    logger.error(f"      Recovery failed: {recovery_error}")
                    break  # Can't recover, exit the loop

            except Exception as e:
                logger.error(f"      Error processing {stock_name}: {e}")
                # Recovery: reload the entire subsector page
                logger.warning("      Reloading subsector page to recover...")
                try:
                    subpage.goto(
                        subsector_url, wait_until="networkidle", timeout=20000)
                    subpage.evaluate(JS_SET_ZOOM(PAGE_ZOOM))
                    subpage.wait_for_timeout(1500)
                    success = True  # We recovered, mark as success to move on
                except Exception as recovery_error:
                    logger.error(f"      Recovery failed: {recovery_error}")
                    break  # Can't recover, exit the loop

            finally:
                # Only append stock data if it has a valid instrument_key
                if instrument_key:
                    stocks_with_codes.append({
                        "name": stock_name,
                        "code": stock_code,
                        "instrument_key": instrument_key
                    })
                    logger.debug(f"         Added {stock_name} to results")
                else:
                    logger.warning(
                        f"         Skipping {stock_name}: No instrument key found")

                # Only increment if we successfully processed (or recovered)
                if success:
                    processed_count += 1
                else:
                    # If we couldn't process or recover, stop
                    logger.error(
                        f"      Failed to process {stock_name}, stopping subsector processing")
                    break

    except Exception as e:
        logger.error(f"   Error in subsector {sub_name}: {e}")

    return stocks_with_codes


def load_instrument_keys(file_path):
    """Load Upstox instruments and return a mapping of (exchange, symbol) -> instrument_key."""
    logger.info(f"Loading Upstox instruments from {file_path}...")
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Upstox instrument file not found: {file_path}")
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mapping = {}
        for item in data:
            if 'exchange' not in item or 'trading_symbol' not in item or 'instrument_key' not in item:
                continue

            # Normalize to uppercase for consistent matching
            exchange = item['exchange'].upper()
            symbol = item['trading_symbol'].upper()
            instr_key = item['instrument_key']

            mapping[(exchange, symbol)] = instr_key

        logger.info(f"Loaded {len(mapping)} instrument keys.")
        return mapping
    except Exception as e:
        logger.error(f"Error loading instrument keys: {e}")
        return {}


def run():
    """Main scraper function that extracts complete data hierarchy."""
    results = []

    # Load Upstox instrument keys first
    upstox_file = os.path.join("upstox-instruments", "complete.json")
    instrument_map = load_instrument_keys(upstox_file)

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
            # Use domcontentloaded instead of networkidle for more reliable loading
            page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
            # Wait a bit longer for dynamic content
            page.wait_for_timeout(2000)

            # Apply zoom
            page.evaluate(JS_SET_ZOOM(PAGE_ZOOM))
            page.wait_for_timeout(600)

            # Count sectors
            sector_count = page.evaluate(JS_COUNT_SECTORS)
            logger.info(f"Found {sector_count} sectors")

            for i in range(sector_count):
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Processing sector {i + 1}/{sector_count}")
                    logger.info(f"{'='*60}")

                    # Click to expand sector and get name
                    sector_name = page.evaluate(JS_CLICK_SECTOR_GET_NAME, i)
                    page.wait_for_timeout(600)

                    # Extract subsector info
                    sector_info = page.evaluate(JS_EXTRACT_SUBSECTORS, i)

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
                        "subindustries": []
                    }

                    # Create separate page for subsector navigation
                    subpage = context.new_page()

                    for sub_idx, sub in enumerate(subSectors, 1):
                        sub_name = sub.get('name', 'Unknown')
                        sub_href = sub.get('href')

                        # Skip first subsector (index 0) as it's typically "Entire [Sector]"
                        # which contains all stocks and creates duplicates
                        if sub_idx == 1:
                            logger.info(
                                f"\n   [{sub_idx}/{len(subSectors)}] Skipping: {sub_name} (Entire sector - would create duplicates)")
                            continue

                        logger.info(
                            f"\n   [{sub_idx}/{len(subSectors)}] Subsector: {sub_name}")

                        if not sub_href:
                            logger.warning(
                                f"   No href for {sub_name}, skipping")
                            continue

                        full_url = urljoin(BASE_URL, sub_href)

                        # Scrape stocks with codes using click and back navigation
                        stocks_with_codes = scrape_stocks_with_codes(
                            subpage,
                            full_url,
                            sub_name,
                            instrument_map
                        )

                        sector_record["subindustries"].append({
                            "name": sub_name,
                            "stocks": stocks_with_codes
                        })

                    subpage.close()
                    results.append(sector_record)

                    # Log progress summary
                    total_stocks = sum(
                        len(sub["stocks"])
                        for sub in sector_record["subindustries"]
                    )
                    successful_codes = sum(
                        1 for sub in sector_record["subindustries"]
                        for stock in sub["stocks"]
                        if stock.get("code")
                    )
                    logger.info(
                        f"\n[OK] Completed {sector_name}: "
                        f"{total_stocks} stocks, "
                        f"{successful_codes} codes extracted"
                    )

                except Exception as e:
                    logger.error(f"Error processing sector {i}: {e}")
                    continue

            browser.close()
            logger.info("\n" + "="*60)
            logger.info("Browser closed successfully")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}", exc_info=True)
            raise

    # Save outputs
    try:
        logger.info(f"\nSaving complete data to {OUTPUT_JSON}")
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"[OK] Saved JSON output")

        # Final statistics
        total_stocks = sum(
            len(stock) for sec in results
            for sub in sec.get("subindustries", [])
            for stock in [sub.get("stocks", [])]
        )
        successful_codes = sum(
            1 for sec in results
            for sub in sec.get("subindustries", [])
            for stock in sub.get("stocks", [])
            if stock.get("code")
        )
        logger.info(f"\n{'='*60}")
        logger.info("SCRAPING COMPLETED SUCCESSFULLY!")
        logger.info(f"{'='*60}")
        logger.info(f"Total sectors: {len(results)}")
        logger.info(
            f"Total subsectors: {sum(len(s['subindustries']) for s in results)}")
        logger.info(f"Total stocks: {total_stocks}")
        logger.info(
            f"Stock codes extracted: {successful_codes} ({successful_codes/total_stocks*100:.1f}%)")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.error(f"Error saving outputs: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        exit(1)
