import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

indices = {
    # --- Broad Market ---
    "Nifty 50": "^NSEI",
    "BSE Sensex": "^BSESN",
    "Nifty Next 50": "^NSMIDCP",  # Often tracks Junior/Midcap behavior on YF

    # --- F&O Eligible Indices ---
    "Nifty Bank": "^NSEBANK",
    "Nifty Fin Service": "NIFTY_FIN_SERVICE.NS",  # Sometimes works, else ^CNXFIN

    # --- Sectoral Indices (Legacy ^CNX Tickers) ---
    "Nifty Auto": "^CNXAUTO",
    "Nifty IT": "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
    "Nifty FMCG": "^CNXFMCG",
    "Nifty Metal": "^CNXMETAL",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Realty": "^CNXREALTY",
    "Nifty PSU Bank": "^CNXPSUBANK",
    "Nifty Media": "^CNXMEDIA",

    # --- BSE Sectoral ---
    # BSE indices on YF are limited, but major ones exist
    "BSE SmallCap": "BSE-SMLCAP.BO",
    "BSE MidCap": "BSE-MIDCAP.BO",
    "BSE Tech": "BSE-TECK.BO"
}

# --- Configuration & Styling ---
# Use a wide layout
st.set_page_config(layout="wide")

# Define color variables based on user specifications
COLOR_BULLISH = "#328E6E"    # Green - Bullish
COLOR_POSITIVE = "#67AE6E"   # Light green - Positive
COLOR_NEUTRAL = "#FADA7A"    # Neutral yellow - Neutral
COLOR_NEGATIVE = "#B82132"   # Red - Negative
COLOR_BEARISH = "#D2665A"    # Light Red - Bearish
COLOR_BACKGROUND = "#FFFFFF"  # White - Background

# Custom CSS for the dashboard elements (simplifies text, headers, and color blocks)

# Function to style the Factors Table specifically


def style_factors_table(df):
    def color_performance(val):
        # Use positive (light green) for positive values, negative (red) for negative
        color = COLOR_POSITIVE if val > 0 else (
            COLOR_NEGATIVE if val < 0 else COLOR_NEUTRAL)
        text_color = 'white' if color in [
            COLOR_POSITIVE, COLOR_NEGATIVE] else '#333333'
        return f'background-color: {color}; color: {text_color}; text-align: center;'

    # Apply coloring to the specific columns used in factors_data
    # Note: These column names must match the DataFrame definition below.
    styled = df.style.map(
        lambda x: color_performance(x) if isinstance(x, (int, float)) else '',
        subset=pd.IndexSlice[:, ['0-5%', '5-50%', '50-100%']]
    ).format(lambda x: f"{x:+.2f}%" if isinstance(x, (int, float)) else x)

    return styled


st.markdown(f"""
    <style>
        .stApp {{
            background-color: {COLOR_BACKGROUND};
            color: #333333;
        }}
        .header-box {{
            padding: 5px;
            margin-bottom: 10px;
            text-align: center;
            font-weight: bold;
            border-radius: 4px;
            color: white;
            font-size: 16px;
        }}
        .bullish {{ background-color: {COLOR_BULLISH}; }}
        .bearish {{ background-color: {COLOR_BEARISH}; }}
        .positive {{ background-color: {COLOR_POSITIVE}; }}
        .negative {{ background-color: {COLOR_NEGATIVE}; }}
        .neutral {{ background-color: {COLOR_NEUTRAL}; color: #333333; }}
        .market-header {{
            font-size: 24px;
            font-weight: 700;
            color: #1c3d52; /* Darker blue/grey for main title */
        }}
        /* Style for the tiny status blocks (Yes/No/Neutral) */
        .status-block {{
            display: inline-block;
            padding: 2px 6px;
            margin: 0 2px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            color: white;
            text-align: center;
        }}
        .dataframe {{
            font-size: 12px;
            border-collapse: collapse;
            width: 100%;
        }}
        .dataframe th {{
            background-color: #f1f1f1;
            font-weight: bold;
            padding: 4px;
            text-align: left;
        }}
        .dataframe td {{
            padding: 4px;
        }}
    </style>
""", unsafe_allow_html=True)

# Function to render a styled header box


def render_header(title, style_class):
    st.markdown(
        f'<div class="header-box {style_class}">{title}</div>', unsafe_allow_html=True)

# Function to create a simple status block (Yes/No/Neutral)


def status_block(status):
    status_lower = status.lower()
    color_class = "positive" if status_lower == "yes" else (
        "negative" if status_lower == "no" else "neutral")
    text = "Yes" if status_lower == "yes" else (
        "No" if status_lower == "no" else "Neutral")
    return f'<div class="status-block {color_class}">{text}</div>'

# --- Dummy Data Generation ---


# Data for Market Dashboard (Top Left)
market_exposure = pd.DataFrame({
    'Exposure': ['Bullish', 'Positive', 'Neutral', 'Negative', 'Bearish'],
    'Range': ['100% - 80%', '80% - 60%', '60% - 40%', '40% - 20%', '20% - 0%'],
    'Value': [0.1, 0.4, 0.3, 0.1, 0.1]
})

# Dummy Ticker Data
tickers = ['SPY', 'QQQ', 'MAGS', 'DOG', 'TLT', 'IWM']
market_data = pd.DataFrame({
    'Ticker': tickers,
    'Index': ['S&P 500', 'NASDAQ 100', 'Magnificent Seven', 'Eq Wght S&P 500', 'iShares 20+ Year T-Bnd', 'Russell 2000'],
    'Price': np.round(np.random.uniform(100, 500, len(tickers)), 2),
    '1 D': np.round(np.random.uniform(-1, 1, len(tickers)), 2),
    'Relative Strength': [f"{x}%" for x in np.random.randint(0, 100, len(tickers))],
    'RS S7S %': np.random.randint(0, 100, len(tickers))
})

# Dummy Sector/Macro Data
sectors = ['EPU', 'XLF', 'EWG', 'GLD', 'IYR']
sector_data = pd.DataFrame({
    'Ticker': sectors,
    'Sector': ['Poland', 'Finance', 'Germany', 'Gold', 'Real Estate'],
    'Price': np.round(np.random.uniform(30, 100, len(sectors)), 2),
    '1 D': np.round(np.random.uniform(-3, 3, len(sectors)), 2),
    'Relative Strength': [f"{x}%" for x in np.random.randint(0, 100, len(sectors))],
    'RS S7S %': np.random.randint(0, 100, len(sectors))
})

# Dummy Performance Data
perf_data = pd.DataFrame({
    'Factor': ['Growth', 'Value', 'Small-Cap'],
    '1 W': np.round(np.random.uniform(-3, 3, 3), 2),
    '1 M': np.round(np.random.uniform(-5, 5, 3), 2),
    '1 Y': np.round(np.random.uniform(-10, 10, 3), 2),
})
perf_data = perf_data.set_index('Factor')

# Dummy Trend Indicators (MA)
ma_statuses = ['Yes', 'No', 'Neutral']
ma_data = pd.DataFrame({
    '20MA': np.random.choice(ma_statuses, len(tickers)),
    '50MA': np.random.choice(ma_statuses, len(tickers)),
    '20-50MA': np.random.choice(ma_statuses, len(tickers)),
    '50-200MA': np.random.choice(ma_statuses, len(tickers)),
})

# Function to style performance tables


def style_performance_table(df):
    def color_performance(val):
        # Use positive (light green) for positive values, negative (red) for negative
        color = COLOR_POSITIVE if val > 0 else (
            COLOR_NEGATIVE if val < 0 else COLOR_NEUTRAL)
        text_color = 'white' if color in [
            COLOR_POSITIVE, COLOR_NEGATIVE] else '#333333'
        return f'background-color: {color}; color: {text_color}; text-align: center;'

    # Apply coloring to all numeric columns
    styled = df.style.map(
        lambda x: color_performance(x) if isinstance(x, (int, float)) else '',
        subset=pd.IndexSlice[:, ['1 W', '1 M', '1 Y']]
    ).format(lambda x: f"{x:+.2f}%" if isinstance(x, (int, float)) else x)

    return styled

# Function to render MA Status as HTML


def render_ma_table(df):
    html_table = '<table class="dataframe">'
    # Header Row
    html_table += '<thead><tr><th></th><th>10MA</th><th>20MA</th><th>50MA</th><th>20-50MA</th><th>50-200MA</th></tr></thead>'
    html_table += '<tbody>'

    for i, row in df.iterrows():
        ticker = market_data.iloc[i]['Ticker']
        html_table += f'<tr><td>{ticker}</td>'
        # Dummy MA statuses for illustration (The image uses tiny up/down/neutral indicators)
        for col in ['20MA', '50MA', '20-50MA', '50-200MA']:
            # Random status for dummy data
            status = np.random.choice(['Yes', 'No', 'Neutral'])
            html_table += f'<td>{status_block(status)}</td>'
        html_table += '</tr>'
    html_table += '</tbody></table>'
    return html_table


# --- Streamlit Layout ---

st.markdown(f'<p class="market-header">Market Dashboard</p>',
            unsafe_allow_html=True)

# Use columns for the main layout (3 main columns)
col1, col2, col3 = st.columns([1.5, 2.5, 2])  # Adjusted ratio for better look

with col1:
    # --- Market Exposure & Tickers ---
    render_header("Market Exposure", "")

    # 1. Market Exposure Gauge (Simplified Text/Bar)
    st.markdown(f"""
        **33.33%**
        <div style="background-color: {COLOR_BEARISH}; width: 33.33%; height: 10px; border-radius: 5px;"></div>
    """, unsafe_allow_html=True)

    st.dataframe(market_exposure, hide_index=True)

    st.markdown("---")

    # 2. Market Tickers Table
    render_header("Market", "")
    st.dataframe(market_data.drop(
        columns=['Relative Strength']), hide_index=True)

    st.markdown("---")

    # 3. Sectors Table
    render_header("Sectors", "")
    st.dataframe(sector_data.drop(
        columns=['Relative Strength']), hide_index=True)

    st.markdown("---")

    # 4. Macro Tickers Table (Bottom Left)
    render_header("Macro", "")
    st.dataframe(pd.DataFrame({
        'Ticker': ['TLT', 'USDX'],
        'Price': [99.47, 104.53],
        '1 D': [-0.02, 0.16]
    }), hide_index=True)


with col2:
    # --- Market Performance ---
    render_header(f"November 10, {date.today().year}", "")

    # 1. Market Performance Overview
    render_header("Market Performance Overview", "")
    overview_data = pd.DataFrame({
        'Metric': ['SPY', 'QQQ', 'IWM'],
        '1 W': [0.66, 0.94, -0.44],
        '1 M': [0.68, 1.09, 0.26],
        '1 Y': [18.70, 21.90, 1.28],
    }).set_index('Metric')
    st.markdown(style_performance_table(
        overview_data).to_html(), unsafe_allow_html=True)

    st.markdown("---")

    # 2. Factors vs SP500
    render_header("Factors vs SP500", "")
    factors_data = pd.DataFrame({
        'Groups': ['Growth', 'Value', 'Momentum', 'Quality'],
        '0-5%': [0.66, -0.44, 0.94, 0.26],
        '5-50%': [0.68, 1.09, -0.44, 0.26],
        '50-100%': [18.70, 1.28, 21.90, 10.20],
    }).set_index('Groups')
    st.markdown(style_factors_table(
        factors_data).to_html(), unsafe_allow_html=True)

    st.markdown("---")

    # 3. Performance Tables (More Detailed)
    render_header("Performance", "")
    # Use the sector data for a big performance table
    perf_table = sector_data[['Ticker', '1 D']].copy()
    perf_table['1 W'] = np.round(np.random.uniform(-5, 5, len(perf_table)), 2)
    perf_table['1 M'] = np.round(
        np.random.uniform(-10, 10, len(perf_table)), 2)
    perf_table['1 Y'] = np.round(
        np.random.uniform(-20, 20, len(perf_table)), 2)
    perf_table = perf_table.set_index('Ticker')
    st.markdown(style_performance_table(
        perf_table).to_html(), unsafe_allow_html=True)


with col3:
    # --- Highs, VIX, and Trend Indicators ---
    render_header("High & VIX", "")

    # 1. Broad Market Overview (Simplified Blocks)
    render_header("Broad Market Overview", "")
    st.markdown(f"""
        <div style="display: flex; justify-content: space-around; font-size: 12px; margin-bottom: 10px;">
            <div>**Short-Term:** {status_block('Neutral')}</div>
            <div>**Mid-Term:** {status_block('Positive')}</div>
            <div>**Long-Term:** {status_block('Positive')}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. Bond Yields & Power Trend
    col3_1, col3_2 = st.columns(2)
    with col3_1:
        render_header("Bond Yields", "")
        st.markdown("*10Y US:* **4.110**")
        st.markdown("*2Y US:* **4.900**")

    with col3_2:
        render_header("Power Trend (QQQ)", "")
        st.markdown(f"""
            *3-Days Above 20MA:* **{status_block('Yes')}**
            *10-Days Above 50MA:* **{status_block('Yes')}**
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 3. Highs Table (Simplified)
    render_header("Highs", "")
    highs_data = pd.DataFrame({
        '% From 52W High': np.round(np.random.uniform(1, 15, len(tickers)), 2),
    }, index=tickers)

    # Add a simple bar chart visualization to mimic the bar in the image
    st.bar_chart(highs_data)

    st.markdown("---")

    # 4. Trend Indicators (MAs)
    render_header("Trend Indicators (MAs)", "")
    st.markdown(render_ma_table(ma_data), unsafe_allow_html=True)
