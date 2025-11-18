"""
Extract Stock Codes from StockEdge.

This script extracts stock exchange codes (NSE/BSE symbols) from
stockedge.com links using the stocks data from output_sectors_stocks.json.

Usage:
    python extract_stock_codes.py

Output:
    - output_stock_codes.json: Stock names mapped to exchange codes
    - extract_stocks.log: Detailed operation logs
"""

import logging
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://web.stockedge.com"
INPUT_JSON = "output_sectors_stocks.json"
OUTPUT_JSON = "output_stock_codes.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extract_stocks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://web.stockedge.com"
INPUT_JSON = "output_sectors_stocks.json"
OUTPUT_JSON = "output_stock_codes.json"


def extract_stocks_from_json():
    """Extract all unique stock entries from the input JSON."""
    logger.info(f"Reading stocks from {INPUT_JSON}")
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            sectors_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {INPUT_JSON}")
        raise

    processed_hrefs = set()
    all_stocks = []

    for sector in sectors_data:
        for subindustry in sector.get('subindustries', []):
            for stock in subindustry.get('stocks', []):
                stock_href = stock.get('href')
                if stock_href and stock_href not in processed_hrefs:
                    processed_hrefs.add(stock_href)
                    all_stocks.append({
                        'name': stock.get('name'),
                        'href': stock_href
                    })

    logger.info(f"Found {len(all_stocks)} unique stocks")
    return all_stocks


JS_EXTRACT = r"""
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


def extract_stock_codes(stocks):
    """Extract stock codes from stock detail pages."""
    stock_codes = []
    total = len(stocks)

    with sync_playwright() as p:
        try:
            logger.info("Launching browser for stock extraction")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120 Safari/537.36"
                )
            )
            page = context.new_page()

            for idx, stock in enumerate(stocks, 1):
                try:
                    stock_url = urljoin(BASE_URL, stock['href'])
                    logger.info(
                        f"[{idx}/{total}] Processing {stock['name']}"
                    )

                    page.goto(
                        stock_url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )
                    page.wait_for_timeout(3000)

                    code_str = page.evaluate(JS_EXTRACT)

                    stock_codes.append({
                        "name": stock['name'],
                        "code": code_str
                    })

                    if code_str:
                        logger.debug(f"  -> Found code: {code_str}")
                    else:
                        logger.warning(
                            f"  -> Could not extract code for "
                            f"{stock['name']}"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to process {stock['name']}: {e}"
                    )
                    stock_codes.append({
                        "name": stock['name'],
                        "code": None
                    })

            browser.close()
            logger.info("Browser closed successfully")

        except Exception as e:
            logger.error(f"Fatal error during extraction: {e}",
                         exc_info=True)
            raise

    return stock_codes


def main():
    """Main function to extract stock codes."""
    try:
        stocks = extract_stocks_from_json()

        logger.info("Starting stock code extraction...")
        stock_codes = extract_stock_codes(stocks)

        logger.info(f"Saving results to {OUTPUT_JSON}")
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(stock_codes, f, indent=2, ensure_ascii=False)

        success_count = sum(1 for s in stock_codes if s['code'])
        logger.info(
            f"Extraction complete: {success_count}/{len(stock_codes)} "
            f"stocks extracted successfully"
        )

    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
