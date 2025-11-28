"""Upstox API data fetching module."""

from urllib.parse import quote

import pandas as pd
import requests

import streamlit as st


def fetch_data_from_upstox(
    instrument_key: str, interval: str, from_date: str, to_date: str
) -> pd.DataFrame:
    """
    Fetches historical candles from Upstox API.

    You MUST replace 'YOUR_ACCESS_TOKEN' below with a valid token.
    Returns dataframe with Date index and OHLCV columns.

    Args:
        instrument_key: Upstox instrument key (e.g., NSE_EQ|INE467B01029)
        interval: Interval (1d, 5m, 15m, 1h, etc.)
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        DataFrame with Date index and columns: Open, High, Low, Close, Volume
    """
    access_token = "YOUR_ACCESS_TOKEN"
    api_version = "v3"

    # URL encode instrument key (pipe | becomes %7C)
    encoded_key = quote(instrument_key, safe='')

    # Upstox v3 format:
    # /v3/historical-candle/{key}/days/1/{to_date}/{from_date}
    url_path = (
        f"https://api.upstox.com/{api_version}/historical-candle/"
        f"{encoded_key}/days/1/{to_date}/{from_date}"
    )

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    try:
        r = requests.get(url_path, headers=headers, timeout=30)

        if r.status_code == 200:
            data = r.json()
            #test
            # For v3 response: data['data']['candles']
            # list of [timestamp, open, high, low, close, volume, oi]
            if data.get("status") == "success":
                candles = data.get("data", {}).get("candles", [])
                if not candles:
                    return pd.DataFrame()

                df = pd.DataFrame(
                    candles,
                    columns=[
                        "Timestamp",
                        "Open",
                        "High",
                        "Low",
                        "Close",
                        "Volume",
                        "OpenInterest",
                    ],
                )
                df["Date"] = pd.to_datetime(df["Timestamp"])
                df.set_index("Date", inplace=True)
                for c in ["Open", "High", "Low", "Close", "Volume"]:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                return df.sort_index()
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()

    except Exception as e:
        return pd.DataFrame()

