import yfinance as yf
from tabulate import tabulate
import time


def get_market_data():
    # Dictionary of Index Name -> Yahoo Finance Ticker
    # Note: Nifty IPO and Defence are not available on free Yahoo Finance.
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

    print("\nFetching live data from Yahoo Finance...\n")

    table_data = []

    # Bulk download is faster, but tickers vary too much, so we loop for safety/formatting
    for name, ticker_symbol in indices.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Get fast info first (works better for indices during market hours)
            # Some YF indices use 'regularMarketPrice', others need history
            hist = ticker.history(period="1d")

            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                open_price = hist['Open'].iloc[-1]
                # Approx prev close proxy for indices
                prev_close = hist['Open'].iloc[0]

                # Calculating change based on Day's Open vs Current
                # (YF 'previousClose' can sometimes be delayed for indices)
                change = current_price - open_price
                pct_change = (change / open_price) * 100

                # Formatting color for terminal (Green for +ve, Red for -ve)
                # ANSI escape codes
                color = "\033[92m" if change >= 0 else "\033[91m"
                reset = "\033[0m"

                table_data.append([
                    name,
                    ticker_symbol,
                    f"{current_price:,.2f}",
                    f"{color}{change:+.2f}{reset}",
                    f"{color}{pct_change:+.2f}%{reset}"
                ])
            else:
                table_data.append([name, ticker_symbol, "N/A", "N/A", "N/A"])

        except Exception as e:
            table_data.append([name, ticker_symbol, "Error", "-", "-"])

    # Define headers
    headers = ["Index Name", "Ticker (YF)", "Price", "Change", "% Change"]

    # Print cool table
    print(tabulate(table_data, headers=headers, tablefmt="simple"))
    print("\nNote: 'N/A' indicates the index is not currently supported by Yahoo Finance's free feed.")


if __name__ == "__main__":
    get_market_data()
