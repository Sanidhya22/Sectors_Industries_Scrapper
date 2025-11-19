# StockEdge Sector Scraper

A Python-based web scraper that extracts the complete hierarchy of sectors, subsectors, stocks, and their exchange codes from [StockEdge](https://web.stockedge.com/sectors) using Playwright.

## Features

- **Unified single-pass solution** - No intermediate files needed
- Scrapes complete hierarchy: sectors → subsectors → stocks → exchange codes
- Automatically extracts stock exchange codes (NSE/BSE) from individual stock pages
- Efficient back navigation to traverse stock lists without page reloads
- Handles dynamic content loading and shadow DOM elements
- Optimized viewport and zoom settings for efficient data collection
- Robust error handling with detailed logging
- Exports data in both JSON and Excel formats with stock codes
- Captures:
  - Sector information
  - Subsector details with links
  - Individual stock listings with exchange codes (e.g., NSE:TCS, BSE:SENSEX)

## Prerequisites

- Python 3.x
- pip (Python package manager)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd Sector-scrapper
```

2. Install the required dependencies:
```bash
pip install playwright pandas openpyxl
```

3. Install Playwright browsers:
```bash
playwright install
```

## Usage

Run the scraper:
```bash
python scrap_stockedge_sectors.py
```

The script will:
1. Launch a Chromium browser (headless by default)
2. Navigate to the StockEdge sectors page
3. Extract all sectors from the main page
4. For each sector:
   - Expand and extract subsectors with URLs
   - Visit each subsector to get the stock list
   - Click on each stock to navigate to its detail page
   - Extract the exchange code and symbol (NSE/BSE) from the detail page
   - Use back navigation to return to the stock list efficiently
5. Generate output files with complete hierarchical data including stock codes

## Output Files

Run the scraper to generate:
- **`output_complete_data.json`**: Complete hierarchical data with stock codes
- **`output_complete_data.xlsx`**: Flattened data in Excel format
- **`scraper_complete.log`**: Detailed operation logs with debug information

## Output Format

### JSON Structure
```json
{
  "sector_title": "Technology",
  "subindustries": [
    {
      "name": "Software",
      "href": "/stock?industry=123",
      "stocks": [
        {
          "name": "Tata Consultancy Services",
          "code": "NSE:TCS"
        },
        {
          "name": "Infosys",
          "code": "NSE:INFY"
        }
      ]
    }
  ]
}
```

### Excel Format
The Excel file contains columns:
- **sector**: Sector name (e.g., "Technology")
- **subindustry**: Subsector name (e.g., "Software")
- **sub_href**: URL path to the subsector on StockEdge
- **stock_name**: Individual stock name
- **stock_code**: Exchange code with symbol (e.g., "NSE:TCS", "BSE:RELIANCE")

## Technical Details

- **Browser Automation**: Uses Playwright for reliable browser automation
- **Stock Code Extraction**: Custom JavaScript injection to extract NSE/BSE codes from stock detail pages
- **Back Navigation**: Implements efficient back navigation to avoid page reloads when traversing stock lists
- **DOM Traversal**: Handles shadow DOM and ionic elements (ion-item, ion-text, etc.)
- **Viewport Optimization**: 
  - Large viewport (2560x8000) to capture more content
  - Page zoom factor (0.75) to optimize data visibility
- **Error Recovery**: Graceful recovery from timeouts and navigation failures
- **Logging**: Multi-level logging with both console (INFO) and file (DEBUG) outputs
- **Data Validation**: Stops execution with detailed debug info if code extraction fails

## Performance Optimization

The script includes several optimizations:
- Large viewport dimensions (2560x8000) to capture full content without scrolling
- Page zoom factor (0.75) to increase visible content density
- Efficient DOM traversal using targeted selectors and shadow DOM queries
- Back navigation instead of full page reloads to traverse stock lists
- Timeout handling for slow network conditions
- Batch processing with progress tracking

## Configuration

You can customize the scraper by modifying these variables in the script:

```python
SHOW_BROWSER = False          # Set to True to see browser during scraping
PAGE_ZOOM = 0.75              # Adjust zoom factor (0.5-1.0)
VIEWPORT_WIDTH = 2560         # Browser window width
VIEWPORT_HEIGHT = 8000        # Browser window height
OUTPUT_JSON = "output_complete_data.json"
OUTPUT_XLSX = "output_complete_data.xlsx"
```

## Error Handling

The script includes robust error handling:
- **Timeout Recovery**: Gracefully handles network timeouts during page navigation
- **Code Extraction Validation**: Validates successful code extraction for each stock with debug screenshots
- **Skip and Continue**: Skips failed subsectors/stocks and continues with the next item
- **Detailed Logging**: 
  - Console logs show INFO level and above
  - File logs (`scraper_complete.log`) capture all DEBUG level details
  - Screenshots saved for stocks where code extraction fails
- **Completion Summary**: Displays final statistics including success rate

## Logging

The scraper produces detailed logs to help with debugging:
- **Console Output**: Shows progress, current stocks being processed, and extracted codes
- **Log File** (`scraper_complete.log`): Contains DEBUG level details for troubleshooting
- **Debug Screenshots**: Automatically captures screenshots when code extraction fails

Example console output:
```
2025-11-20 14:23:45,123 - INFO - Found 12 sectors
2025-11-20 14:23:52,456 - INFO - Sector: Technology | 8 subsectors found
2025-11-20 14:24:10,789 - INFO - [1/8] Subsector: Software
2025-11-20 14:24:15,234 - INFO - Found 25 stocks in Software
2025-11-20 14:24:18,567 - INFO - [1/25] Clicking: Tata Consultancy Services
2025-11-20 14:24:22,890 - INFO - -> Code: NSE:TCS
```

## Limitations

- Respects StockEdge's website structure and DOM layout
- Requires stable internet connection for full scraping session
- May timeout on very slow connections (configurable timeouts)
- Stock code extraction depends on current StockEdge UI structure
- Running the scraper may take 30-60+ minutes depending on number of stocks

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Ensure you comply with StockEdge's terms of service and implement appropriate rate limiting when using the scraper.
