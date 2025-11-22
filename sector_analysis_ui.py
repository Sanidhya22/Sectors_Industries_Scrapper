import traceback

import collections
import json
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Tuple

from upstox_fetch import fetch_data_from_upstox
from chart_ui import render_sector_index_chart

# --- Files (assumes same folder) ---
# Unified file: sector -> subindustries -> stocks (with codes)
SECTORS_FILE = "output_complete_data.json"
# Complete formatted instrument metadata (in upstox-instruments folder)
INSTRUMENTS_FILE = "upstox-instruments/complete.json"

# --- Helpers to load files ---


@st.cache_data
def load_json(path, encoding="utf-8"):
    try:
        return json.load(open(path, "r", encoding=encoding))
    except UnicodeDecodeError:
        # If initial encoding fails, try utf-8
        if encoding != "utf-8":
            return json.load(open(path, "r", encoding="utf-8"))
        raise


sectors_data = load_json(SECTORS_FILE)
# Load the complete formatted instruments file with utf-16 encoding
instruments_data = load_json(INSTRUMENTS_FILE, encoding="utf-16")

# Build name-to-code mapping from unified JSON structure
name_to_exchange_sym = {}
for sector in sectors_data:
    for subindustry in sector.get("subindustries", []):
        for stock in subindustry.get("stocks", []):
            name = stock.get("name")
            code = stock.get("code")  # e.g. "NSE:BHARTIARTL"
            if name and code:
                name_to_exchange_sym[name.strip()] = code.strip()

# Build lookup dictionaries from complete.json
# Index instruments by trading_symbol (case-insensitive) for quick lookup
trading_symbol_to_instrument = {}

for instrument in instruments_data:
    trading_symbol = (instrument.get("trading_symbol") or "").strip().upper()
    segment = instrument.get("segment", "")

    # Filter for equity segments only (BSE_EQ and NSE_EQ)
    if trading_symbol and segment in ("NSE_EQ", "BSE_EQ"):
        trading_symbol_to_instrument[trading_symbol] = instrument


# Yahoo fallback


@st.cache_data
def fetch_data_from_yahoo(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={"Adj Close": "Close"}) if "Adj Close" in df.columns else df
    # ensure Close column available
    if "Close" not in df.columns:
        return pd.DataFrame()
    return df[["Close"]].sort_index()


# Map stock to instrument_key (from complete.json)


def get_instrument_key_for_stock(
    stock_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (instrument_key, source) or (None, reason)
    Strategy:
      - Look up name -> 'NSE:SYM' or 'BSE:SYM' from output_complete_data.json
      - Look up trading_symbol directly in trading_symbol_to_instrument
    """
    name = stock_name.strip()
    code = name_to_exchange_sym.get(name)
    if not code:
        return None, "no_code_entry"
    # parse
    try:
        exch, sym = code.split(":", 1)
    except Exception:
        return None, "bad_code_format"

    sym = sym.strip().upper()

    # Look up by trading_symbol (case-insensitive)
    instrument = trading_symbol_to_instrument.get(sym)
    if instrument:
        return instrument.get("instrument_key"), "found_by_trading_symbol"
    else:
        return None, f"trading_symbol_not_found"


# --- UI ---
st.set_page_config(page_title="Sector Analysis (Equal-weight)", layout="wide")
st.title("Sector Analysis — equal-weight aggregated chart")

# Sector selector: flatten sector titles
sector_titles = [s.get("sector_title") for s in sectors_data]
sector_choice = st.sidebar.selectbox("Choose sector", sector_titles)

# flatten subindustry stocks for the chosen sector


def get_unique_stocks_for_sector(sector_title):
    for s in sectors_data:
        if s.get("sector_title") == sector_title:
            stocks = []
            for sub in s.get("subindustries", []):
                for stock in sub.get("stocks", []):
                    stocks.append(stock.get("name"))
            # unique & preserve order
            seen = set()
            out = []
            for x in stocks:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out
    return []


stocks_in_sector = get_unique_stocks_for_sector(sector_choice)
st.sidebar.markdown(
    f"**{len(stocks_in_sector)} stocks found** in sector `{sector_choice}`."
)
st.sidebar.write("Preview:", stocks_in_sector[:10])

# Parameters
col1, col2 = st.columns([1, 2])
with col1:
    start_default = (datetime.now() - timedelta(days=365)).date()
    end_default = datetime.now().date()
    start_date = st.date_input("Start date", value=start_default)
    end_date = st.date_input("End date", value=end_default)
    interval = st.selectbox("Interval (for Upstox)", ["1d", "5m", "15m", "1h"], index=0)
    use_upstox = st.checkbox(
        "Use Upstox (requires token configured in file)", value=False
    )
    show_components = st.checkbox("Show component stock normalized series", value=False)
with col2:
    st.info(
        "Notes: Upstox option uses instrument_key from complete.json. If Upstox not available, Yahoo Finance fallback is used where possible."
    )
    st.write(
        "If using Yahoo fallback: NSE tickers use `<SYM>.NS`, BSE tickers use `<SYM>.BO` (best-effort)."
    )

if st.button("Build sector index"):
    if len(stocks_in_sector) == 0:
        st.warning("No stocks found for this sector.")
    else:
        dfs = {}
        missing = {}
        for name in stocks_in_sector:
            instrument_key, info = get_instrument_key_for_stock(name)
            if instrument_key:
                if use_upstox:
                    # upstox expects to_date / from_date in yyyy-mm-dd maybe; chartui used to_date/from_date reversed.
                    from_date = start_date.strftime("%Y-%m-%d")
                    to_date = end_date.strftime("%Y-%m-%d")
                    df = fetch_data_from_upstox(
                        instrument_key, interval, from_date, to_date
                    )
                    # prefer 'Close' column
                    if not df.empty and "Close" in df.columns:
                        s = df["Close"].resample("1D").last().dropna()  # daily close
                        dfs[name] = s
                    else:
                        missing[name] = f"upstox_no_data_{info}"
                else:
                    # use yahoo fallback using the symbol from stock_codes
                    code = name_to_exchange_sym.get(name)
                    if code:
                        exch, sym = code.split(":", 1)
                        ticker = None
                        if exch.upper() == "NSE":
                            ticker = f"{sym}.NS"
                        elif exch.upper() == "BSE":
                            ticker = f"{sym}.BO"
                        else:
                            ticker = sym
                        ydf = fetch_data_from_yahoo(
                            ticker,
                            start_date.strftime("%Y-%m-%d"),
                            (end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                        )
                        if not ydf.empty:
                            # ydf has Close
                            s = ydf["Close"].resample("1D").last().dropna()
                            dfs[name] = s
                        else:
                            missing[name] = f"yahoo_no_data_{ticker}"
                    else:
                        missing[name] = "no_stock_code"
            else:
                missing[name] = info  # reason string

        if len(dfs) == 0:
            st.error(
                "No historical data fetched for any stock in this sector. See missing table below."
            )
            st.subheader("Missing / unmatched stocks")
            st.dataframe(
                pd.DataFrame.from_dict(missing, orient="index", columns=["reason"])
                .reset_index()
                .rename(columns={"index": "stock"})
            )
        else:
            # === Replace the construction of price_df with this robust block ===
            # Convert/validate entries in dfs: ensure each value is a pd.Series with datetime index and length>0
            clean_dfs = {}
            bad_entries = {}

            for name, val in dfs.items():
                try:
                    # if it's a DataFrame with Close column, pick that series
                    if isinstance(val, pd.DataFrame):
                        if "Close" in val.columns:
                            s = val["Close"]
                        else:
                            # try last column
                            s = val.iloc[:, 0]
                    # if it's already a Series, use it
                    elif isinstance(val, pd.Series):
                        s = val
                    # if it's a list/ndarray convertible to Series
                    elif isinstance(val, (list, tuple, np.ndarray)):
                        s = pd.Series(val)
                    # if it's a scalar or something else, mark as bad
                    else:
                        raise ValueError(f"unsupported type: {type(val)}")

                    # ensure datetime index: if index is numeric or RangeIndex, attempt to coerce if possible
                    if not isinstance(s.index, pd.DatetimeIndex):
                        try:
                            s.index = pd.to_datetime(s.index)
                        except Exception:
                            # if index cannot be coerced and there's only one value, create a 1-day range index at start_date
                            if len(s) == 1:
                                s.index = pd.to_datetime([start_date])
                            else:
                                raise

                    # require at least 2 data points to compute returns meaningfully (you can relax to 1 if desired)
                    if len(s.dropna()) < 1:
                        raise ValueError("no valid datapoints after dropna")

                    # sort index and keep
                    s = s.sort_index()
                    clean_dfs[name] = s

                except Exception as e:
                    bad_entries[name] = str(e)

            # Debug: show which stocks were kept / dropped
            st.write("Stocks included (time series):", len(clean_dfs))
            if clean_dfs:
                sample = {
                    k: (
                        len(v),
                        v.index.min().strftime("%Y-%m-%d"),
                        v.index.max().strftime("%Y-%m-%d"),
                    )
                    for k, v in list(clean_dfs.items())[:10]
                }
                st.write("Sample included (name -> (n_points, start, end))", sample)
            if bad_entries:
                st.subheader("Excluded stocks (reasons)")
                st.dataframe(
                    pd.DataFrame.from_dict(
                        bad_entries, orient="index", columns=["reason"]
                    )
                    .reset_index()
                    .rename(columns={"index": "stock"})
                )

            if len(clean_dfs) == 0:
                st.error(
                    "No valid time series were retrieved for any stock in this sector. See 'Excluded stocks' for reasons."
                )
            else:
                # Build price_df from clean_dfs (each is a Series). This will have a proper DatetimeIndex.
                price_df = pd.DataFrame(clean_dfs).sort_index()

                # Forward-fill and drop rows that are all-NaN
                price_df = price_df.ffill().dropna(how="all")

                # proceed as before: compute returns, avg return, sector index...
                returns = price_df.pct_change().fillna(0)
                avg_return = returns.mean(axis=1)
                sector_index = (1 + avg_return).cumprod() * 100.0
                sector_index = sector_index.rename("Sector Index (equal-weight)")

                # Render chart using lightweight charts
                component_series = price_df if show_components else None
                render_sector_index_chart(
                    sector_index,
                    sector_choice,
                    component_series=component_series,
                    show_components=show_components,
                )

                st.subheader("Summary")
                total_data = len(clean_dfs)
                total_missing = len(missing) + len(bad_entries)
                st.write(
                    f"Stocks with usable data: {total_data}  |  "
                    f"Missing / unmatched: {total_missing}"
                )
                if missing or bad_entries:
                    combined = {**missing, **bad_entries}
                    st.subheader("Missing / unmatched stocks (reasons)")
                    st.dataframe(
                        pd.DataFrame.from_dict(
                            combined, orient="index", columns=["reason"]
                        )
                        .reset_index()
                        .rename(columns={"index": "stock"})
                    )

                tmp = pd.DataFrame({"SectorIndex": sector_index})
                csv = tmp.to_csv(index=True)
                st.download_button(
                    "Download sector index CSV",
                    data=csv,
                    file_name=f"{sector_choice}_sector_index.csv",
                    mime="text/csv",
                )
