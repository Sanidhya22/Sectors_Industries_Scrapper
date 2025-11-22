# SQL Queries for Stock Data

CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS stock_prices (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    oi BIGINT,
    UNIQUE (time, symbol)
);
"""

# Convert the table into a hypertable partitioned by time
CREATE_HYPERTABLE_QUERY = """
SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);
"""

INSERT_STOCK_DATA_QUERY = """
INSERT INTO stock_prices (time, symbol, open, high, low, close, volume, oi)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (time, symbol) DO UPDATE
SET open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    oi = EXCLUDED.oi;
"""
