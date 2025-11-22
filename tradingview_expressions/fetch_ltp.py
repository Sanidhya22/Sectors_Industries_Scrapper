"""Fetch Last Traded Prices (LTP) from Upstox API with rate limiting."""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import requests


class UpstoxLTPFetcher:
    """
    Fetches LTP (Last Traded Price) for multiple instruments from Upstox API.
    Handles rate limiting: 50 requests/sec, 500 requests/min, 2000 requests/30min.
    """

    def __init__(self, access_token: str):
        """
        Initialize the LTP fetcher.

        Args:
            access_token: Upstox API access token
        """
        self.access_token = access_token
        self.base_url = "https://api.upstox.com/v3/market-quote/ltp"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        self.request_times = []  # Track request times for rate limiting
        self.max_per_second = 50
        self.max_per_minute = 500
        self.max_per_30min = 2000

    def _check_rate_limit(self):
        """Check and enforce rate limits."""
        now = time.time()

        # Remove old timestamps outside rate limit windows
        self.request_times = [
            t for t in self.request_times if now - t < 1800
        ]  # 30 min

        # Check 30-minute limit
        if len(self.request_times) >= self.max_per_30min:
            sleep_time = 1800 - (now - self.request_times[0])
            if sleep_time > 0:
                print(
                    f"Rate limit: Sleeping for {sleep_time:.1f}s (30-min limit)")
                time.sleep(sleep_time)
                self.request_times = []

        # Check minute limit
        requests_in_min = sum(1 for t in self.request_times if now - t < 60)
        if requests_in_min >= self.max_per_minute:
            sleep_time = 60 - (now - self.request_times[-self.max_per_minute])
            if sleep_time > 0:
                print(
                    f"Rate limit: Sleeping for {sleep_time:.1f}s (minute limit)")
                time.sleep(sleep_time)

        # Check per-second limit
        requests_in_sec = sum(1 for t in self.request_times if now - t < 1)
        if requests_in_sec >= self.max_per_second:
            sleep_time = 1 - (now - self.request_times[-self.max_per_second])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.request_times.append(time.time())

    def fetch_ltp_batch(self, instrument_keys: List[str]) -> Dict[str, Optional[float]]:
        """
        Fetch LTP for multiple instruments. Upstox API accepts comma-separated keys.
        Max ~20-30 instruments per request is recommended.

        Args:
            instrument_keys: List of instrument keys (e.g., ["NSE_EQ|INE467B01029", "NSE_EQ|INE848E01016"])

        Returns:
            Dict mapping instrument_key -> last_price (or None if fetch failed)
        """
        if not instrument_keys:
            return {}

        self._check_rate_limit()

        # Join keys with comma for batch query
        keys_param = ",".join(instrument_keys)

        try:
            response = requests.get(
                self.base_url,
                params={'instrument_key': keys_param},
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                # Debug: print first batch response to check format
                print(f"DEBUG: API Response: {json.dumps(data)[:500]}...")

                if data.get('status') == 'success' and 'data' in data:
                    prices = {}
                    for key, quote_data in data['data'].items():
                        prices[key] = quote_data.get('last_price')
                    return prices
                else:
                    print(f"Unexpected response format: {data}")
                    return {k: None for k in instrument_keys}
            else:
                print(f"Error {response.status_code}: {response.text}")
                return {k: None for k in instrument_keys}

        except Exception as e:
            print(f"Exception fetching LTP: {e}")
            return {k: None for k in instrument_keys}

    def fetch_all_ltp(self, instrument_keys: List[str], batch_size: int = 20) -> Dict[str, Optional[float]]:
        """
        Fetch LTP for all instruments, processing in batches to respect API limits.

        Args:
            instrument_keys: List of all instrument keys
            batch_size: Number of instruments per request (Upstox recommends ~20-30)

        Returns:
            Dict mapping all instrument_keys -> last_price (or None if failed)
        """
        all_prices = {}
        total = len(instrument_keys)

        for i in range(0, total, batch_size):
            batch = instrument_keys[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            print(
                f"Fetching batch {batch_num}/{total_batches} ({len(batch)} instruments)...")
            prices = self.fetch_ltp_batch(batch)
            all_prices.update(prices)

            # Small delay between batches
            if i + batch_size < total:
                time.sleep(0.1)

        return all_prices


def load_access_token(env_file: str = "tiger-cloud-db-36044-credentials.env") -> Optional[str]:
    """
    Load Upstox access token from environment file.

    Args:
        env_file: Path to .env file containing UPSTOX_ACCESS_TOKEN

    Returns:
        Access token string or None if not found
    """
    try:
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('UPSTOX_ACCESS_TOKEN'):
                    return line.split('=', 1)[1].strip().strip('"\'')
    except FileNotFoundError:
        print(f"Environment file '{env_file}' not found.")

    return None


def get_all_instrument_keys_from_sectors(sectors_file: str = "output_complete_data.json") -> List[str]:
    """
    Extract all unique instrument keys from the sectors JSON file.

    Args:
        sectors_file: Path to output_complete_data.json

    Returns:
        List of instrument keys in format "NSE_EQ|XXXXXX"
    """
    try:
        with open(sectors_file, 'r', encoding='utf-8') as f:
            sectors_data = json.load(f)

        instrument_keys = set()
        name_to_code = {}

        # Extract name->code mappings
        for sector in sectors_data:
            for subindustry in sector.get('subindustries', []):
                for stock in subindustry.get('stocks', []):
                    name = stock.get('name', '').strip()
                    # Format: "NSE:SYMBOL" or "BSE:SYMBOL"
                    code = stock.get('code', '').strip()
                    if name and code:
                        name_to_code[name] = code

        # Convert codes to Upstox instrument key format
        # This requires a mapping which we'll get from complete.json
        return name_to_code

    except Exception as e:
        print(f"Error reading sectors file: {e}")
        return {}


if __name__ == "__main__":
    # Example usage
    access_token = load_access_token()
    if not access_token:
        print("Could not load access token. Set UPSTOX_ACCESS_TOKEN in environment file.")
        exit(1)

    fetcher = UpstoxLTPFetcher(access_token)

    # Example: fetch specific instruments
    test_keys = [
        "NSE_EQ|INE467B01029",  # TCS
        "NSE_EQ|INE848E01016",  # INFY
        "NSE_EQ|INE062A01020"   # ITC
    ]

    prices = fetcher.fetch_all_ltp(test_keys)
    print("\nFetched Prices:")
    for key, price in prices.items():
        print(f"  {key}: {price}")
