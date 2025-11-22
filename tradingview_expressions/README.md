# TradingView Expressions Generator

This module generates equal-weight TradingView expressions for sectors and subsectors. These expressions can be pasted directly into TradingView's custom index input panels to create composite sector indices.

## Features

- **LTP Fetching**: Fetches Last Traded Prices from Upstox API with built-in rate limiting
- **Equal-Weight Coefficients**: Calculates coefficients using the formula: `coefficient = 1000 / price`
- **Sector + Subsector Expressions**: Generates expressions for entire sectors and individual subsectors
- **Data Persistence**: Saves prices and expressions to JSON files for reference and future use

## Directory Structure

```
tradingview_expressions/
├── data/                           # Output directory
│   ├── ltp_prices.json            # Latest fetched prices
│   ├── tradingview_expressions.json # Generated expressions
│   └── summary.json               # Summary statistics
├── fetch_ltp.py                   # LTP fetching with rate limiting
├── generate_expressions.py        # Expression generator logic
├── main.py                        # Main orchestrator script
└── README.md                      # This file
```

## Requirements

- `requests` library for API calls
- `python 3.8+`
- **Upstox API access token** (optional - set `UPSTOX_ACCESS_TOKEN` in `.env` file to fetch live prices)
- **OR** cached prices in `data/ltp_prices.json`

## Usage

### Option 1: With Upstox Access Token (Fetch Live Prices)

```bash
# Set your access token in environment file
export UPSTOX_ACCESS_TOKEN=your_token_here

python main.py
```

### Option 2: With Cached Prices (No Access Token Needed)

Place previously fetched prices in the `data/` folder:

```bash
# First time: Fetch prices with token
python main.py

# Later: Reuse cached prices without token
python main.py  # Will automatically use data/ltp_prices.json
```

### Example Output

**LTP Prices** (`data/ltp_prices.json`):
```json
{
  "timestamp": "2025-01-15T10:30:00.123456",
  "total_stocks": 450,
  "prices": {
    "SCI": 249.10,
    "MAZDOCK": 2783.40,
    "GRSE": 2829.40,
    "KMEW": 2813.20
  }
}
```

**Generated Expressions** (`data/tradingview_expressions.json`):
```json
{
  "timestamp": "2025-01-15T10:35:00.654321",
  "total_sectors": 30,
  "sectors": {
    "Shipping": {
      "sector": "Shipping",
      "sector_expression": "(NSE:SCI * 1.003613 + NSE:MAZDOCK * 0.089818 + NSE:GRSE * 0.088357 + NSE:KMEW * 0.088867)",
      "sector_components": {
        "SCI": {
          "code": "NSE:SCI",
          "price": 249.10,
          "coefficient": 1.003613
        },
        "MAZDOCK": {
          "code": "NSE:MAZDOCK",
          "price": 2783.40,
          "coefficient": 0.089818
        }
      },
      "subsectors": {
        "Ship Building": {
          "stocks": ["SCI", "MAZDOCK", "GRSE", "KMEW"],
          "expression": "(...)",
          "components": {...}
        }
      }
    }
  }
}
```

## API Rate Limiting

The LTP fetcher respects Upstox API rate limits:
- **50 requests/second**
- **500 requests/minute**
- **2000 requests/30 minutes**

Rate limiting is automatic and transparent—the script will pause when approaching limits.

## Coefficient Calculation Example

For stocks with prices:
- SCI: ₹249.10 → coefficient = 1000 / 249.10 = **1.003613**
- MAZDOCK: ₹2,783.40 → coefficient = 1000 / 2,783.40 = **0.089818**
- GRSE: ₹2,829.40 → coefficient = 1000 / 2,829.40 = **0.088357**
- KMEW: ₹2,813.20 → coefficient = 1000 / 2,813.20 = **0.088867**

**TradingView Expression**:
```
(NSE:SCI * 1.003613 + NSE:MAZDOCK * 0.089818 + NSE:GRSE * 0.088357 + NSE:KMEW * 0.088867)
```

To use in TradingView:
1. Open Chart
2. Click "Create New" → "Custom Index"
3. Paste the expression
4. Name it (e.g., "Shipping Sector Index")
5. Click Create

## Configuration

### Environment File

Set your Upstox token in `tiger-cloud-db-36044-credentials.env`:
```
UPSTOX_ACCESS_TOKEN=your_token_here
```

### Custom Target Per Stock

By default, coefficients are calculated with a target of 1000 per stock. To customize:

```python
orchestrator = TradingViewExpressionOrchestrator(access_token)
prices = orchestrator.fetch_all_prices()

# Generate with custom target (e.g., 500)
expressions = orchestrator.generator.generate_sector_expressions(
    "Banking",
    prices,
    target_per_stock=500.0
)
```

## Data Files

### ltp_prices.json
Contains latest fetched LTP for all stocks. Useful for:
- Backing up recent prices
- Debugging coefficient calculations
- Reusing prices without re-fetching

### tradingview_expressions.json
Main output with all sector and subsector expressions. Each expression includes:
- Stock names and their coefficients
- Original prices (for verification)
- Full TradingView-compatible expression string

### summary.json
Quick overview with:
- Total stocks with prices
- Total sectors with expressions
- Number of subsectors per sector
- Expression length (for copy-paste reference)

## Troubleshooting

**"No prices available..."**
- Set `UPSTOX_ACCESS_TOKEN` in your `.env` file to fetch live prices, OR
- Place cached prices in `data/ltp_prices.json` from a previous run

**"Could not load access token" (info message)**
- This is fine! The script will look for cached prices
- Only needed if you want to fetch fresh prices

**"Rate limit: Sleeping..."**
- This is normal and expected with large stock lists
- The script handles it automatically

## Performance

Typical performance on a full sector list (200-500 stocks):
- **Fetching prices**: 2-5 minutes (depends on stock count and rate limiting)
- **Generating expressions**: <1 second
- **Saving files**: <1 second

## License

Part of the Sector Scrapper project.
