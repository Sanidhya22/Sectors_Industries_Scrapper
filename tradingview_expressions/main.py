"""
Main orchestrator for generating TradingView expressions for all sectors.

This script:
1. Fetches LTP for all stocks
2. Generates expressions for each sector and subsector
3. Saves prices and expressions to JSON files
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

from fetch_ltp import UpstoxLTPFetcher, load_access_token
from generate_expressions import TradingViewExpressionGenerator


class TradingViewExpressionOrchestrator:
    """Orchestrates full workflow for generating trading view expressions."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        data_dir: str = "data",
        sectors_file: str = "../output_complete_data.json",
        instruments_file: str = "../upstox-instruments/complete.json"
    ):
        """
        Initialize the orchestrator.

        Args:
            access_token: Upstox API access token (optional)
            data_dir: Directory to store output files
            sectors_file: Path to sectors JSON
            instruments_file: Path to instruments JSON
        """
        self.access_token = access_token
        self.data_dir = data_dir
        self.fetcher = (
            UpstoxLTPFetcher(access_token) if access_token else None
        )
        self.generator = TradingViewExpressionGenerator(
            sectors_file, instruments_file
        )

        # Create data directory if needed
        os.makedirs(data_dir, exist_ok=True)

    def get_all_unique_stocks(self) -> List[str]:
        """Get list of all unique stock names from sectors."""
        stocks = set()
        for sector in self.generator.sectors_data:
            for subind in sector.get('subindustries', []):
                for stock in subind.get('stocks', []):
                    name = stock.get('name', '').strip()
                    if name:
                        stocks.add(name)
        return sorted(list(stocks))

    def convert_names_to_upstox_keys(
        self, stock_names: List[str]
    ) -> List[str]:
        """Convert stock names to Upstox instrument keys."""
        keys = []
        for name in stock_names:
            code = self.generator.name_to_code.get(name)
            if code:
                upstox_key = self.generator.code_to_upstox_key.get(code)
                if upstox_key:
                    keys.append(upstox_key)
        return keys

    def load_cached_prices(self) -> Optional[Dict[str, float]]:
        """
        Load prices from cached ltp_prices.json file.

        Returns:
            Dict mapping stock names -> prices, or None if not found
        """
        filepath = os.path.join(self.data_dir, 'ltp_prices.json')
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('prices', {})
        except Exception as e:
            print(f"Error loading cached prices: {e}")
            return None

    def fetch_all_prices(self) -> Dict[str, float]:
        """
        Fetch LTP for all stocks using Upstox API.

        Returns:
            Dict mapping stock names -> prices
        """
        if not self.fetcher:
            print(
                "Error: Access token not provided. "
                "Cannot fetch prices from Upstox."
            )
            return {}

        stock_names = self.get_all_unique_stocks()
        print(f"Found {len(stock_names)} unique stocks")

        # Convert names to Upstox keys
        upstox_keys = self.convert_names_to_upstox_keys(stock_names)
        print(f"Found {len(upstox_keys)} valid Upstox keys")

        if not upstox_keys:
            print("Error: No valid Upstox keys found")
            return {}

        # Fetch prices (API returns keys in format "NSE_EQ:SYMBOL")
        prices_by_key = self.fetcher.fetch_all_ltp(upstox_keys)

        # Build reverse mapping: instrument_key -> stock_name
        instrument_to_name = {}
        for stock_name in stock_names:
            code = self.generator.name_to_code.get(stock_name)
            if code:
                upstox_key = self.generator.code_to_upstox_key.get(code)
                if upstox_key:
                    instrument_to_name[upstox_key] = stock_name

        # Convert API response to stock_name -> price mapping
        # API keys are in format "NSE_EQ:SYMBOL", we need to match them
        # with our instrument keys using the instrument_to_symbol mapping
        prices_by_name = {}
        for upstox_key, stock_name in instrument_to_name.items():
            # Get the API format key for this instrument
            api_key = self.generator.instrument_to_symbol.get(upstox_key)
            if api_key and api_key in prices_by_key:
                price = prices_by_key[api_key]
                if price is not None:
                    prices_by_name[stock_name] = price

        return prices_by_name

    def save_prices(self, prices: Dict[str, float]):
        """Save fetched prices to JSON file."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'total_stocks': len(prices),
            'prices': prices
        }

        filepath = os.path.join(self.data_dir, 'ltp_prices.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        print(f"OK Saved {len(prices)} prices to {filepath}")

    def generate_all_expressions(
        self, prices: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Generate expressions for all sectors and subsectors.

        Args:
            prices: Dict mapping stock names -> prices

        Returns:
            Dict mapping sector names -> expression data
        """
        result = {}
        sector_titles = [
            s.get('sector_title') for s in self.generator.sectors_data
        ]

        print(f"\nGenerating expressions for {len(sector_titles)} sectors...")

        for i, sector_title in enumerate(sector_titles, 1):
            print(f"  [{i}/{len(sector_titles)}] {sector_title}...", end=' ')

            expressions = (
                self.generator.generate_sector_expressions(
                    sector_title, prices
                )
            )

            if expressions.get('sector_expression'):
                result[sector_title] = expressions
                print("✓")
            else:
                print("(no stocks with prices)")

        return result

    def save_expressions(self, expressions: Dict[str, Dict]):
        """Save generated expressions to JSON file."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'total_sectors': len(expressions),
            'sectors': expressions
        }

        filepath = os.path.join(
            self.data_dir, 'tradingview_expressions.json'
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        print(f"OK Saved expressions for {len(expressions)} sectors to "
              f"{filepath}")

    def save_summary(
        self,
        prices: Dict[str, float],
        expressions: Dict[str, Dict]
    ):
        """Save a human-readable summary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_with_prices': len(prices),
            'total_sectors_with_expressions': len(expressions),
            'sectors_summary': {}
        }

        for sector_name, expr_data in expressions.items():
            subsector_count = len(expr_data.get('subsectors', {}))
            stock_count = len(expr_data.get('sector_components', {}))
            summary['sectors_summary'][sector_name] = {
                'subsectors': subsector_count,
                'stocks': stock_count,
                'expression_length': len(
                    expr_data.get('sector_expression', '')
                )
            }

        filepath = os.path.join(self.data_dir, 'summary.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

            print("✓ Saved summary to {filepath}")

    def run(self):
        """Execute the full workflow."""
        print("=" * 60)
        print("TradingView Expression Generator")
        print("=" * 60)

        # Try to get prices (fetch or use cached)
        print("\n[1/3] Loading prices...")
        prices = None

        # Try cached prices first
        if os.path.exists(
            os.path.join(self.data_dir, 'ltp_prices.json')
        ):
            print("  -> Found cached prices, loading...")
            prices = self.load_cached_prices()
            if prices:
                print(f"  OK Loaded {len(prices)} cached prices")

        # Check if we need to fetch fresh prices
        # Fetch if:
        # 1. No prices loaded
        # 2. Very few prices loaded (likely incomplete cache)
        # 3. User explicitly wants fresh prices (not implemented yet, but good to have logic)

        all_stocks_count = len(self.get_all_unique_stocks())
        should_fetch = False

        if not prices:
            should_fetch = True
            print("  -> No cache found.")
        elif len(prices) < (all_stocks_count * 0.1):  # If less than 10% coverage
            should_fetch = True
            print(
                f"  -> Cache incomplete ({len(prices)}/{all_stocks_count} stocks), forcing refresh...")

        # Fetch from API if needed and possible
        if should_fetch and self.fetcher:
            print("  -> Fetching prices from Upstox API...")
            new_prices = self.fetch_all_prices()

            if new_prices:
                print(f"  OK Fetched {len(new_prices)} prices from API")
                # Merge with existing prices if any, preferring new ones
                if prices:
                    prices.update(new_prices)
                else:
                    prices = new_prices
            else:
                print("  ! Warning: API fetch returned no prices")

        if not prices:
            print(
                "\n✗ No prices available. "
                "Please either:\n"
                "  1. Set UPSTOX_ACCESS_TOKEN to fetch prices\n"
                "  2. Place ltp_prices.json in data/ directory"
            )
            return

        self.save_prices(prices)

        print("\n[2/3] Generating sector/subsector expressions...")
        expressions = self.generate_all_expressions(prices)

        if not expressions:
            print("✗ No expressions generated. Exiting.")
            return

        self.save_expressions(expressions)

        print("\n[3/3] Creating summary...")
        self.save_summary(prices, expressions)

        print("\n" + "=" * 60)
        print("OK Complete!")
        print("=" * 60)
        print(f"Output files saved to: {os.path.abspath(self.data_dir)}")


def main():
    """Main entry point."""
    # Load environment variables from .env file
    load_dotenv()

    # Get access token from environment variable
    access_token = os.getenv('UPSTOX_ACCESS_TOKEN')

    if not access_token:
        print("Warning: UPSTOX_ACCESS_TOKEN not found in .env file")
        print("Please create a .env file with UPSTOX_ACCESS_TOKEN=your_token")
    else:
        print("+ Upstox access token configured from .env")

    orchestrator = TradingViewExpressionOrchestrator(access_token)
    orchestrator.run()


if __name__ == "__main__":
    main()
