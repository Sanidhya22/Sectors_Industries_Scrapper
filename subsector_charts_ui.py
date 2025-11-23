import json
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

from upstox_fetch import fetch_data_from_upstox
from chart_ui import render_sector_index_chart

# --- Configuration ---
SECTORS_FILE = "output_complete_data.json"
INSTRUMENTS_FILE = "upstox-instruments/complete.json"

# --- Load Data ---


@st.cache_data
def load_json(path, encoding="utf-8"):
    try:
        return json.load(open(path, "r", encoding=encoding))
    except UnicodeDecodeError:
        if encoding != "utf-8":
            return json.load(open(path, "r", encoding="utf-8"))
        raise


sectors_data = load_json(SECTORS_FILE)
instruments_data = load_json(INSTRUMENTS_FILE, encoding="utf-16")

# Build name-to-code mapping
name_to_exchange_sym = {}
for sector in sectors_data:
    for subindustry in sector.get("subindustries", []):
        for stock in subindustry.get("stocks", []):
            name = stock.get("name")
            code = stock.get("code")
            if name and code:
                name_to_exchange_sym[name.strip()] = code.strip()

# Build trading symbol lookup
trading_symbol_to_instrument = {}
for instrument in instruments_data:
    trading_symbol = (instrument.get("trading_symbol") or "").strip().upper()
    segment = instrument.get("segment", "")
    if trading_symbol and segment in ("NSE_EQ", "BSE_EQ"):
        trading_symbol_to_instrument[trading_symbol] = instrument


# --- Helper Functions ---
def get_all_subsectors() -> List[Dict]:
    """Get all subsectors from all sectors"""
    subsectors = []
    for sector in sectors_data:
        sector_title = sector.get("sector_title", "Unknown")
        for subindustry in sector.get("subindustries", []):
            subsectors.append({
                "sector_title": sector_title,
                "subsector_name": subindustry.get("name", "Unknown"),
                "stocks": subindustry.get("stocks", [])
            })
    return subsectors


def get_instrument_key_for_stock(stock_name: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (instrument_key, source) or (None, reason)"""
    name = stock_name.strip()
    code = name_to_exchange_sym.get(name)
    if not code:
        return None, "no_code_entry"

    try:
        exch, sym = code.split(":", 1)
    except Exception:
        return None, "bad_code_format"

    sym = sym.strip().upper()
    instrument = trading_symbol_to_instrument.get(sym)

    if instrument:
        return instrument.get("instrument_key"), "found_by_trading_symbol"
    else:
        return None, "trading_symbol_not_found"


@st.cache_data
def fetch_data_from_yahoo(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch data from Yahoo Finance"""
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={"Adj Close": "Close"}
                   ) if "Adj Close" in df.columns else df
    if "Close" not in df.columns:
        return pd.DataFrame()
    return df[["Close"]].sort_index()


def build_subsector_index(subsector_data: Dict, start_date, end_date, interval="1d", use_upstox=True):
    """Build index for a single subsector"""
    stocks = subsector_data.get("stocks", [])
    stock_names = [stock.get("name") for stock in stocks if stock.get("name")]

    if len(stock_names) == 0:
        return None, {"error": "No stocks found"}

    dfs = {}
    missing = {}

    for name in stock_names:
        instrument_key, info = get_instrument_key_for_stock(name)

        if instrument_key:
            if use_upstox:
                from_date = start_date.strftime("%Y-%m-%d")
                to_date = end_date.strftime("%Y-%m-%d")
                df = fetch_data_from_upstox(
                    instrument_key, interval, from_date, to_date)

                if not df.empty and "Close" in df.columns:
                    s = df["Close"].resample("1D").last().dropna()
                    dfs[name] = s
                else:
                    missing[name] = f"upstox_no_data_{info}"
            else:
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
                        s = ydf["Close"].resample("1D").last().dropna()
                        dfs[name] = s
                    else:
                        missing[name] = f"yahoo_no_data_{ticker}"
                else:
                    missing[name] = "no_stock_code"
        else:
            missing[name] = info

    if len(dfs) == 0:
        return None, {"missing": missing, "error": "No data fetched"}

    # Clean and validate data
    clean_dfs = {}
    bad_entries = {}

    for name, val in dfs.items():
        try:
            if isinstance(val, pd.DataFrame):
                s = val["Close"] if "Close" in val.columns else val.iloc[:, 0]
            elif isinstance(val, pd.Series):
                s = val
            elif isinstance(val, (list, tuple, np.ndarray)):
                s = pd.Series(val)
            else:
                raise ValueError(f"unsupported type: {type(val)}")

            if not isinstance(s.index, pd.DatetimeIndex):
                try:
                    s.index = pd.to_datetime(s.index)
                except Exception:
                    if len(s) == 1:
                        s.index = pd.to_datetime([start_date])
                    else:
                        raise

            if len(s.dropna()) < 1:
                raise ValueError("no valid datapoints after dropna")

            s = s.sort_index()
            clean_dfs[name] = s

        except Exception as e:
            bad_entries[name] = str(e)

    if len(clean_dfs) == 0:
        return None, {"missing": missing, "bad_entries": bad_entries, "error": "No valid data"}

    # Build sector index
    price_df = pd.DataFrame(clean_dfs).sort_index()
    price_df = price_df.ffill().dropna(how="all")

    returns = price_df.pct_change().fillna(0)
    avg_return = returns.mean(axis=1)
    sector_index = (1 + avg_return).cumprod() * 100.0

    return sector_index, {
        "total_stocks": len(stock_names),
        "data_stocks": len(clean_dfs),
        "missing": missing,
        "bad_entries": bad_entries
    }


# --- UI ---
st.set_page_config(page_title="Subsector Charts", layout="wide")
st.title("📊 Subsector Charts - All in One View")

# Get all subsectors
all_subsectors = get_all_subsectors()

# Create select options
subsector_options = [
    f"{sub['sector_title']} → {sub['subsector_name']}"
    for sub in all_subsectors
]

# Add "All Subsectors" option
subsector_options.insert(0, "📋 All Subsectors")

# Settings in a single row
st.markdown("### ⚙️ Settings")
col1, col2, col3, col4 = st.columns(4)

with col1:
    start_default = (datetime.now() - timedelta(days=365)).date()
    start_date = st.date_input("Start Date", value=start_default)

with col2:
    end_default = datetime.now().date()
    end_date = st.date_input("End Date", value=end_default)

with col3:
    interval = st.selectbox("Interval", ["1d", "5m", "15m", "1h"], index=0)

with col4:
    use_upstox = st.checkbox("Use Upstox API", value=True,
                             help="Use Upstox API for data fetching (requires configured token)")

st.markdown("---")

# Subsector selection
selected_option = st.selectbox(
    "🎯 Select Subsector to Analyze",
    subsector_options,
    help="Choose a subsector to fetch and display its chart, or select 'All Subsectors' to view all"
)

# Display selected subsectors
if selected_option == "📋 All Subsectors":
    st.info("📌 Displaying all subsectors. Click on individual subsectors to analyze specific ones.")

    if st.button("🚀 Generate All Charts", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        total = len(all_subsectors)

        for idx, subsector in enumerate(all_subsectors):
            status_text.text(
                f"Processing: {subsector['sector_title']} → {subsector['subsector_name']} ({idx+1}/{total})")
            progress_bar.progress((idx + 1) / total)

            st.markdown(
                f"## {subsector['sector_title']} → {subsector['subsector_name']}")
            st.markdown(
                f"**Stocks in subsector:** {len(subsector.get('stocks', []))}")

            sector_index, metadata = build_subsector_index(
                subsector, start_date, end_date, interval, use_upstox
            )

            if sector_index is not None:
                render_sector_index_chart(
                    sector_index,
                    f"{subsector['sector_title']} → {subsector['subsector_name']}",
                    component_series=None,
                    show_components=False
                )

                st.caption(
                    f"✅ Data stocks: {metadata.get('data_stocks', 0)} / {metadata.get('total_stocks', 0)}")
            else:
                st.error(
                    f"❌ Could not generate chart: {metadata.get('error', 'Unknown error')}")

            st.markdown("---")

        status_text.text("✅ All charts generated!")
        progress_bar.empty()

else:
    # Single subsector selected
    selected_idx = subsector_options.index(selected_option) - 1
    selected_subsector = all_subsectors[selected_idx]

    st.markdown(
        f"## {selected_subsector['sector_title']} → {selected_subsector['subsector_name']}")
    st.markdown(
        f"**Total stocks in subsector:** {len(selected_subsector.get('stocks', []))}")

    # Show stock preview
    with st.expander("📝 View stocks in this subsector"):
        stock_names = [stock.get("name")
                       for stock in selected_subsector.get("stocks", [])]
        st.write(stock_names)

    if st.button("🚀 Generate Chart", type="primary"):
        with st.spinner("Fetching data and building chart..."):
            sector_index, metadata = build_subsector_index(
                selected_subsector, start_date, end_date, interval, use_upstox
            )

            if sector_index is not None:
                render_sector_index_chart(
                    sector_index,
                    f"{selected_subsector['sector_title']} → {selected_subsector['subsector_name']}",
                    component_series=None,
                    show_components=False
                )

                st.success(
                    f"✅ Chart generated successfully! ({metadata.get('data_stocks', 0)}/{metadata.get('total_stocks', 0)} stocks)")

                # Show missing stocks if any
                if metadata.get("missing") or metadata.get("bad_entries"):
                    with st.expander("⚠️ View missing/problematic stocks"):
                        combined = {
                            **metadata.get("missing", {}), **metadata.get("bad_entries", {})}
                        st.dataframe(
                            pd.DataFrame.from_dict(
                                combined, orient="index", columns=["reason"])
                            .reset_index()
                            .rename(columns={"index": "stock"})
                        )
            else:
                st.error(
                    f"❌ Could not generate chart: {metadata.get('error', 'Unknown error')}")

                if metadata.get("missing") or metadata.get("bad_entries"):
                    st.subheader("Missing/Problematic Stocks")
                    combined = {
                        **metadata.get("missing", {}), **metadata.get("bad_entries", {})}
                    st.dataframe(
                        pd.DataFrame.from_dict(
                            combined, orient="index", columns=["reason"])
                        .reset_index()
                        .rename(columns={"index": "stock"})
                    )

# Footer
st.markdown("---")
st.caption("💡 Tip: Use the Upstox API for faster and more reliable data fetching. Make sure your access token is configured.")
