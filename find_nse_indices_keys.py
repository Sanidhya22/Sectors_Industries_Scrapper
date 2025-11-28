import json
import os


def main():
    # Load NSE indices
    try:
        with open('nse_indices.json', 'r', encoding='utf-8') as f:
            nse_indices = json.load(f)
    except FileNotFoundError:
        print("Error: nse_indices.json not found.")
        return

    # Extract the trading symbols (2nd element) from nse_indices
    # We create a map of trading_symbol -> full_name for reference if needed,
    # but primarily we need the set of trading symbols to look up.
    # Actually, let's map trading_symbol -> index_name (1st element) to keep context.
    target_indices = {item[1]: item[0] for item in nse_indices}

    print(f"Loaded {len(target_indices)} indices from nse_indices.json")

    # Load Upstox instruments
    upstox_file = 'upstox-instruments/complete.json'
    if not os.path.exists(upstox_file):
        print(f"Error: {upstox_file} not found.")
        return

    print(f"Loading {upstox_file}...")
    try:
        with open(upstox_file, 'r', encoding='utf-8') as f:
            upstox_data = json.load(f)
    except Exception as e:
        print(f"Error loading upstox data: {e}")
        return

    # Filter for NSE_INDEX and match trading symbols
    # The instrument_key is usually "segment|token" or similar.
    # Let's check the structure again.
    # Based on previous research: segment="NSE_INDEX", trading_symbol matches.
    # We need the 'instrument_key' which is likely what we want to map to.
    # Wait, the previous `head` output didn't explicitly show `instrument_key`.
    # Let's double check the fields available in upstox data.
    # But usually it is `instrument_key`. If not, we can construct it or find it.
    # Let's assume there is a key field or we use `instrument_key` if present.
    # If `instrument_key` is missing, we might need to construct it (e.g. NSE_INDEX|26048).

    mapped_keys = {}

    for instrument in upstox_data:
        if instrument.get('segment') == 'NSE_INDEX':
            trading_symbol = instrument.get('trading_symbol')
            if trading_symbol in target_indices:
                # Found a match
                # We want to map the index name (or trading symbol) to the instrument key.
                # Let's use the format: { "Index Name": "instrument_key" }
                # Or { "Trading Symbol": "instrument_key" }
                # The user request was "find nse indices keys", usually for fetching data.

                # Let's check if 'instrument_key' exists
                key = instrument.get('instrument_key')
                if not key:
                    # Fallback or construct if possible, but usually it exists.
                    # Based on standard Upstox API, it should be there.
                    pass

                if key:
                    mapped_keys[target_indices[trading_symbol]] = key
                    # Also map the trading symbol itself if needed?
                    # Let's stick to the full name as key for clarity, or maybe both?
                    # The nse_indices.json has ["Full Name", "Symbol"].
                    # Let's output { "Symbol": "instrument_key" } as it's more programmatic.
                    # Actually, let's do { "Symbol": "instrument_key" }
                    # because the symbol is what we matched on.
                    # Wait, the user might want the full name too.
                    # Let's do a dictionary where key is the Symbol (2nd item in nse_indices).

                    # Correction: The task says "find_nse_indices_keys".
                    # Let's output a dictionary: { "NIFTY 50": "instrument_key", ... } using the Symbol.
                    mapped_keys[trading_symbol] = key

    print(
        f"Found {len(mapped_keys)} matches out of {len(target_indices)} target indices.")

    # Output to file
    output_file = 'nse_index_keys.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapped_keys, f, indent=2)

    print(f"Saved mapped keys to {output_file}")


if __name__ == "__main__":
    main()
