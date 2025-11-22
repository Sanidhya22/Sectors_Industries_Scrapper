"""Simple Upstox API testing with hardcoded values."""

import requests
from urllib.parse import quote

# Hardcoded values
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"  # Replace with your token
INSTRUMENT_KEY = "NSE_EQ|INE467B01029"  # TCS
FROM_DATE = "2025-01-01"
TO_DATE = "2025-01-02"
INTERVAL = "1"


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

    try:
        response = requests.get(url, headers=headers, timeout=30)

        # Check the response status
        if response.status_code == 200:
            data = response.json()
            print("✓ API Response:")
            # print(data) # Commented out to avoid clutter

            # Insert into Database
            if data and 'data' in data and 'candles' in data['data']:
                candles = data['data']['candles']
                print(
                    f"Found {len(candles)} candles. Inserting into TimescaleDB...")

                try:
                    from database_config import get_db_connection
                    from sql_queries import CREATE_TABLE_QUERY, CREATE_HYPERTABLE_QUERY, INSERT_STOCK_DATA_QUERY

                    conn = get_db_connection()
                    cur = conn.cursor()

                    # Create table and hypertable
                    cur.execute(CREATE_TABLE_QUERY)
                    # cur.execute(CREATE_HYPERTABLE_QUERY) # Hypertable creation might fail if it exists, handled in SQL or ignore
                    # Better to handle hypertable creation gracefully or assume it's done.
                    # The query uses if_not_exists=>TRUE so it should be fine, but let's wrap in try-except or just run it.
                    try:
                        cur.execute(CREATE_HYPERTABLE_QUERY)
                    except Exception as e:
                        print(f"Hypertable creation note: {e}")
                        conn.rollback()  # Rollback if it fails (e.g. already exists and function throws)

                    conn.commit()  # Commit table creation

                    # Insert data
                    inserted_count = 0
                    for candle in candles:
                        # Candle format: [timestamp, open, high, low, close, volume, oi]
                        # Timestamp from Upstox is usually ISO format string
                        timestamp = candle[0]
                        open_price = candle[1]
                        high = candle[2]
                        low = candle[3]
                        close = candle[4]
                        volume = candle[5]
                        oi = candle[6]

                        # Symbol is hardcoded for this test, but should be dynamic in real app
                        symbol = "TCS"  # Derived from INSTRUMENT_KEY

                        cur.execute(INSERT_STOCK_DATA_QUERY, (
                            timestamp, symbol, open_price, high, low, close, volume, oi
                        ))
                        inserted_count += 1

                    conn.commit()
                    print(
                        f"✓ Successfully inserted {inserted_count} records into stock_prices.")
                    cur.close()
                    conn.close()

                except Exception as db_err:
                    print(f"✗ Database Error: {db_err}")
            else:
                print("No candle data found in response.")

            return data
        else:
            # Print an error message if the request was not successful
            print(f"✗ Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        print("✗ Error: Request timeout")
        return None
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None


if __name__ == "__main__":
    test_upstox_api()
