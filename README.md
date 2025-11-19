# StockEdge Sector Scraper

A Python-based web scraper that extracts sector, subsector, and stock information from [StockEdge](https://web.stockedge.com/sectors) using Playwright.

## Features

- Scrapes the complete hierarchy of sectors and their constituent stocks
- Handles dynamic content loading and shadow DOM elements
- Optimized viewport and zoom settings for efficient data collection
- Exports data in both JSON and Excel formats
- Captures:
  - Sector information
  - Subsector details with links
  - Individual stock listings for each subsector

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
python scrape_stockedge_sectors.py
```

The script will:
1. Launch a headless browser
2. Navigate through all sectors on StockEdge
3. Extract subsector information
4. Visit each subsector page to collect stock details
5. Generate two output files:
   - `output_sectors_stocks.json`: Complete hierarchical data
   - `output_sectors_stocks.xlsx`: Flattened data in Excel format

## Output Format

### JSON Structure
```json
[
  {
    "sector_title": "Sector Name",
    "subindustries": [
      {
        "name": "Subsector Name",
        "href": "/sector/subsector-url",
        "stocks": [
          {
            "name": "Stock Name",
            "href": "/company/stock-url"
          }
        ]
      }
    ]
  }
]

{
  "sector_title": "Technology",
  "subindustries": [{
    "name": "Software",
    "href": "/stock?industry=123",
    "stocks": [
      {
        "name": "TCS",
        "code": "NSE:TCS"
      }
    ]
  }]
}
```

### Excel Format
The Excel file contains columns:
- sector
- subindustry
- sub_href

## Technical Details

- Uses Playwright for browser automation
- Implements custom viewport sizing and zoom settings for optimal scraping
- Handles shadow DOM traversal for extracting nested content
- Includes error handling and retry mechanisms
- Optimized for StockEdge's web interface

## Performance Optimization

The script includes several optimizations:
- Large viewport dimensions (2560x8000)
- Page zoom factor (0.75)
- Efficient DOM traversal using targeted selectors
- Parallel processing of sectors and subsectors

## Error Handling

The script includes robust error handling:
- Graceful recovery from network timeouts
- Skip and continue on sector/subsector failures
- Detailed error logging

## Limitations

- Respects StockEdge's website structure
- Rate-limited to avoid overloading the server
- Requires stable internet connection

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Ensure you comply with StockEdge's terms of service and implement appropriate rate limiting when using the scraper.
