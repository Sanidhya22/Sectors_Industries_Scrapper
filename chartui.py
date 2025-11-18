import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests  # New library for making API calls

# --- Page Configuration ---
st.set_page_config(
    page_title="Stock Behavior Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- Upstox API Data Fetching Function ---


def fetch_data_from_upstox(instrument_key, interval, from_date, to_date):
    """
    Fetches historical candle data from the Upstox API.

    NOTE: You must replace 'YOUR_ACCESS_TOKEN' with your actual Upstox access token.
    """
    #
    # --- IMPORTANT ---
    # PASTE YOUR UPSTOX ACCESS TOKEN HERE
    access_token = "YOUR_ACCESS_TOKEN"
    #
    #

    # if access_token == "YOUR_ACCESS_TOKEN":
    #     st.error(
    #         "Please replace 'YOUR_ACCESS_TOKEN' in the Python script with your actual Upstox access token.")
    #     return pd.DataFrame()

    api_version = "v2"
    url_path = f"https://api.upstox.com/{api_version}/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"

    headers = {
        'Accept': 'application/json',
        # 'Authorization': f'Bearer {access_token}'
    }

    try:
        response = requests.get(url_path, headers=headers)
        response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)

        data = response.json()

        if data.get("status") == "success":
            candles = data.get("data", {}).get("candles", [])
            if not candles:
                st.warning(
                    "No data returned from Upstox for the selected parameters.")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=[
                              'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Open Interest'])
            df['Date'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Date', inplace=True)
            # Ensure numeric types
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            # Keep only the necessary columns in the right order
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            return df.sort_index()
        else:
            st.error(
                f"Upstox API Error: {data.get('errors', [{}])[0].get('message', 'Unknown error')}")
            return pd.DataFrame()

    except requests.exceptions.HTTPError as http_err:
        st.error(
            f"HTTP error occurred: {http_err} - Check your Instrument Key and token.")
    except Exception as err:
        st.error(f"An unexpected error occurred: {err}")

    return pd.DataFrame()


# --- Yahoo Finance Data Fetching Function ---
@st.cache_data
def fetch_data_from_yahoo(ticker, start_date, end_date):
    """Fetches stock data from Yahoo Finance."""
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        if data.empty:
            st.warning(
                f"No data found for ticker '{ticker}' in the given date range.")
            return pd.DataFrame()
        return data
    except Exception as e:
        st.error(f"Error fetching data from Yahoo Finance: {e}")
        return pd.DataFrame()

# --- Main App Logic ---


def run_app():
    st.title("📈 Stock Behavior Analysis Dashboard")
    st.markdown(
        "An interactive tool to analyze stock price movements, patterns, and technical indicators.")

    # --- Sidebar for Data Input ---
    with st.sidebar:
        st.header("⚙️ Data Source")
        source = st.radio(
            "Select data source",
            ("Yahoo Finance", "Upstox", "Upload CSV")
        )

        df = pd.DataFrame()  # Initialize empty dataframe

        if source == "Yahoo Finance":
            st.subheader("Yahoo Finance")
            ticker = st.text_input("Enter Stock Ticker", "AAPL").upper()
            end_date = datetime.now().date()
            start_date = st.date_input(
                "Start Date", end_date - timedelta(days=365))
            if st.button("Fetch Yahoo Finance Data"):
                with st.spinner(f"Fetching data for {ticker}..."):
                    df = fetch_data_from_yahoo(ticker, start_date, end_date)

        elif source == "Upstox":
            st.subheader("Upstox Historical API")
            instrument_key = st.text_input(
                "Enter Instrument Key", "NSE_EQ|INE002A01018")
            interval = st.selectbox(
                "Select Interval",
                ("day", "week", "month", "1minute", "5minute",
                 "15minute", "30minute", "60minute")
            )
            to_date = datetime.now().date()
            from_date = st.date_input(
                "From Date", to_date - timedelta(days=30))
            if st.button("Fetch Upstox Data"):
                with st.spinner(f"Fetching data for {instrument_key}..."):
                    df = fetch_data_from_upstox(instrument_key, interval, from_date.strftime(
                        '%Y-%m-%d'), to_date.strftime('%Y-%m-%d'))

        elif source == "Upload CSV":
            st.subheader("Upload OHLCV CSV File")
            uploaded_file = st.file_uploader("Choose a file", type="csv")
            if uploaded_file:
                df = pd.read_csv(
                    uploaded_file, index_col='Date', parse_dates=True)
                # Basic validation
                expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in df.columns for col in expected_cols):
                    st.error(
                        f"CSV must contain the following columns: {', '.join(expected_cols)}")
                    df = pd.DataFrame()

    if df.empty:
        st.info("Please select a data source and fetch data to begin analysis.")
        return

    # --- Data Preview ---
    st.subheader("Data Preview")
    st.dataframe(df.tail())

    # --- Section 1: Return Analysis ---
    st.header("1. Daily Return Distribution Analysis")

    # --- NEW, MORE ROBUST LOGIC ---

    # Check if 'Close' column exists and if there's enough data to calculate a return
    if 'Close' in df.columns and len(df) > 1:
        df['Daily Return %'] = df['Close'].pct_change() * 100

        # Create a new, clean dataframe for analysis, dropping rows where return is NaN.
        # This is safer than modifying the main dataframe in place.
        returns_df = df[['Daily Return %']].dropna()

        # Proceed only if we have valid return data after cleaning
        if not returns_df.empty:
            # Add a slider to control the histogram's x-axis range
            min_val = float(returns_df['Daily Return %'].min() - 1)
            max_val = float(returns_df['Daily Return %'].max() + 1)

            # A safety check for the slider's range
            if min_val >= max_val:
                min_val, max_val = -10.0, 10.0

            hist_range = st.slider(
                "Select Histogram X-axis Range (%)",
                min_value=min_val,
                max_value=max_val,
                value=(-5.0, 5.0),
                step=0.5,
                help="Adjust the range to focus on specific return percentages."
            )

            col1, col2, col3, col4 = st.columns(4)
            # All metrics are now calculated on the clean returns_df
            col1.metric("Mean Daily Return",
                        f"{returns_df['Daily Return %'].mean():.2f}%")
            col2.metric("Std. Dev (Volatility)",
                        f"{returns_df['Daily Return %'].std():.2f}%")
            col3.metric(
                "Skewness", f"{returns_df['Daily Return %'].skew():.2f}")
            col4.metric(
                "Kurtosis", f"{returns_df['Daily Return %'].kurtosis():.2f}")

            # Histogram of returns
            fig_hist = go.Figure()
            # The histogram also uses the clean returns_df
            fig_hist.add_trace(go.Histogram(
                x=returns_df['Daily Return %'], nbinsx=100, name='Return Frequency'))
            fig_hist.update_layout(
                title_text='Histogram of Daily Percentage Returns',
                xaxis_title='Daily Return (%)',
                yaxis_title='Frequency',
                bargap=0.05,
                template='plotly_dark',
                xaxis_range=[hist_range[0], hist_range[1]]
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning(
                "Could not analyze daily returns. The dataset might be too small.")
    else:
        st.warning(
            "Not enough data (or 'Close' column is missing) to calculate daily returns.")

    # --- END OF NEW LOGIC ---

    st.markdown("""
    **Interpretation:**
    - **Mean:** The average daily percentage change.
    - **Std. Dev (Volatility):** A measure of the stock's riskiness. Higher means more price swings.
    - **Skewness:** Measures the asymmetry of returns. Positive skew suggests more frequent small losses and a few large gains. Negative skew suggests more frequent small gains and a few large losses.
    - **Kurtosis:** Measures the "tailedness" of the distribution. High kurtosis (>3) indicates that extreme returns (outliers) are more likely than in a normal distribution.
    """)

    # --- Section 2: Candlestick Pattern Analysis ---
    st.header("2. Candlestick and Technical Analysis")

    # Technical Indicators Calculations
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    df['Bollinger High'] = df['MA20'] + 2 * \
        df['Close'].rolling(window=20).std()
    df['Bollinger Low'] = df['MA20'] - 2 * df['Close'].rolling(window=20).std()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean(
    ) - df['Close'].ewm(span=26, adjust=False).mean()
    df['Signal Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()

    # Candlestick chart
    fig_candle = go.Figure()

    # Add Candlestick trace
    fig_candle.add_trace(
        go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                       low=df['Low'], close=df['Close'], name='OHLC')
    )

    # Add Technical Indicator traces
    fig_candle.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(
        color='yellow', width=1), name='MA 20'))
    fig_candle.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(
        color='orange', width=1), name='MA 50'))
    fig_candle.add_trace(go.Scatter(x=df.index, y=df['Bollinger High'], line=dict(
        color='cyan', width=1, dash='dash'), name='Bollinger High'))
    fig_candle.add_trace(go.Scatter(x=df.index, y=df['Bollinger Low'], line=dict(
        color='cyan', width=1, dash='dash'), name='Bollinger Low'))

    fig_candle.update_layout(
        title='Candlestick Chart with Technical Indicators',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        template='plotly_dark'
    )
    st.plotly_chart(fig_candle, use_container_width=True)

    # Subplots for volume and other indicators
    st.markdown("#### Volume and Oscillator Indicators")

    # Volume Chart
    fig_vol = px.bar(df, x=df.index, y='Volume', title='Volume')
    fig_vol.update_layout(template='plotly_dark')
    st.plotly_chart(fig_vol, use_container_width=True)

    # RSI Chart
    fig_rsi = px.line(df, x=df.index, y='RSI',
                      title='Relative Strength Index (RSI)')
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
    fig_rsi.update_layout(template='plotly_dark')
    st.plotly_chart(fig_rsi, use_container_width=True)

    # MACD Chart
    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(
        x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue', width=1)))
    fig_macd.add_trace(go.Scatter(
        x=df.index, y=df['Signal Line'], name='Signal Line', line=dict(color='orange', width=1)))
    fig_macd.update_layout(title='MACD', template='plotly_dark')
    st.plotly_chart(fig_macd, use_container_width=True)

    # OBV Chart
    fig_obv = px.line(df, x=df.index, y='OBV', title='On-Balance Volume (OBV)')
    fig_obv.update_layout(template='plotly_dark')
    st.plotly_chart(fig_obv, use_container_width=True)


if __name__ == "__main__":
    run_app()
