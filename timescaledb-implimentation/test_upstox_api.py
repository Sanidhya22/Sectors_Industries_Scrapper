"""Simple Upstox API testing with hardcoded values."""

import os
import requests
from urllib.parse import quote
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv('tiger-cloud-db-36044-credentials.env')

# Hardcoded values
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")  # Get from env
INSTRUMENT_KEY = "NSE_EQ|INE467B01029"  # TCS

# Calculate dates for the last 6 months + buffer
end_date = datetime.now()
start_date = end_date - timedelta(days=200)  # Approx 6.5 months

TO_DATE = end_date.strftime("%Y-%m-%d")
FROM_DATE = start_date.strftime("%Y-%m-%d")
INTERVAL = "1"  # Correct interval for daily candles


def test_upstox_api():
    """Test Upstox API with hardcoded instrument key and dates."""

    # URL encode the instrument key (pipe character becomes %7C)
    encoded_key = quote(INSTRUMENT_KEY, safe='')

    url = (
        f"https://api.upstox.com/v3/historical-candle/"
        f"{encoded_key}/days/{INTERVAL}/{TO_DATE}/{FROM_DATE}"
    )

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    print(f"Fetching data from {FROM_DATE} to {TO_DATE}...")

    try:
        response = requests.get(url, headers=headers, timeout=30)

        # Check the response status
        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] API Response received.")

            # Insert into Database
            if data and 'data' in data and 'candles' in data['data']:
                candles = data['data']['candles']
                print(
                    f"Found {len(candles)} candles. Inserting into TimescaleDB...")

                try:
                    from database_config import get_db_connection
                    from sql_queries import CREATE_TABLE_QUERY, CREATE_HYPERTABLE_QUERY, INSERT_STOCK_DATA_QUERY, CALCULATE_RETURNS_QUERY

                    conn = get_db_connection()
                    cur = conn.cursor()

                    # Create table and hypertable
                    cur.execute(CREATE_TABLE_QUERY)
                    try:
                        cur.execute(CREATE_HYPERTABLE_QUERY)
                    except Exception as e:
                        # Hypertable might already exist
                        conn.rollback()
                        # print(f"Hypertable creation note: {e}")

                    conn.commit()  # Commit table creation

                    # Insert data
                    inserted_count = 0
                    symbol = "TCS"  # Derived from INSTRUMENT_KEY

                    for candle in candles:
                        # Candle format: [timestamp, open, high, low, close, volume, oi]
                        # Timestamp from Upstox is usually ISO format string
                        timestamp_str = candle[0]
                        # timestamps from upstox might have timezone info, ensure it's handled
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            # Fallback
                            timestamp = timestamp_str

                        # Explicit type casting
                        open_price = float(
                            candle[1]) if candle[1] is not None else None
                        high = float(
                            candle[2]) if candle[2] is not None else None
                        low = float(
                            candle[3]) if candle[3] is not None else None
                        close = float(
                            candle[4]) if candle[4] is not None else None
                        volume = int(
                            candle[5]) if candle[5] is not None else None
                        oi = int(candle[6]) if candle[6] is not None else None

                        if inserted_count == 0:
                            print(f"DEBUG: Inserting record 1:")
                            print(
                                f"  timestamp: {timestamp} (type: {type(timestamp)})")
                            print(f"  symbol: {symbol} (type: {type(symbol)})")
                            print(
                                f"  open: {open_price} (type: {type(open_price)})")
                            print(f"  volume: {volume} (type: {type(volume)})")

                        cur.execute(INSERT_STOCK_DATA_QUERY, (
                            timestamp, symbol, open_price, high, low, close, volume, oi
                        ))
                        inserted_count += 1

                    conn.commit()
                    print(
                        f"[SUCCESS] Successfully inserted {inserted_count} records into stock_prices.")
                    cur.execute(CALCULATE_RETURNS_QUERY,
                                (symbol, symbol, symbol, symbol, symbol))
                    result = cur.fetchone()

                    if result:
                        current_close, r1w, r30d, r3m, r6m = result
                        print(f"Current Close: {current_close}")
                        print(
                            f"1 Week Return: {r1w:.2f}%" if r1w is not None else "1 Week Return: N/A")
                        print(
                            f"30 Day Return: {r30d:.2f}%" if r30d is not None else "30 Day Return: N/A")
                        print(
                            f"3 Month Return: {r3m:.2f}%" if r3m is not None else "3 Month Return: N/A")
                        print(
                            f"6 Month Return: {r6m:.2f}%" if r6m is not None else "6 Month Return: N/A")
                    else:
                        print("Could not calculate returns.")

                    cur.close()
                    conn.close()

                except Exception as db_err:
                    import traceback
                    traceback.print_exc()
                    print(f"[ERROR] Database Error: {db_err}")
            else:
                print("No candle data found in response.")

            return data
        else:
            # Print an error message if the request was not successful
            print(f"[ERROR] Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        print("[ERROR] Error: Request timeout")
        return None
    except Exception as e:
        print(f"[ERROR] Error: {str(e)}")
        return None


if __name__ == "__main__":
    test_upstox_api()
