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

CALCULATE_RETURNS_QUERY = """
WITH latest AS (
    SELECT close as current_close, time as current_time
    FROM stock_prices
    WHERE symbol = %s
    ORDER BY time DESC
    LIMIT 1
),
past_1w AS (
    SELECT close as close_1w
    FROM stock_prices
    WHERE symbol = %s AND time <= (SELECT current_time FROM latest) - INTERVAL '1 week'
    ORDER BY time DESC
    LIMIT 1
),
past_30d AS (
    SELECT close as close_30d
    FROM stock_prices
    WHERE symbol = %s AND time <= (SELECT current_time FROM latest) - INTERVAL '30 days'
    ORDER BY time DESC
    LIMIT 1
),
past_3m AS (
    SELECT close as close_3m
    FROM stock_prices
    WHERE symbol = %s AND time <= (SELECT current_time FROM latest) - INTERVAL '3 months'
    ORDER BY time DESC
    LIMIT 1
),
past_6m AS (
    SELECT close as close_6m
    FROM stock_prices
    WHERE symbol = %s AND time <= (SELECT current_time FROM latest) - INTERVAL '6 months'
    ORDER BY time DESC
    LIMIT 1
)
SELECT
    current_close,
    ((current_close - close_1w) / close_1w) * 100 as return_1w,
    ((current_close - close_30d) / close_30d) * 100 as return_30d,
    ((current_close - close_3m) / close_3m) * 100 as return_3m,
    ((current_close - close_6m) / close_6m) * 100 as return_6m
FROM latest
LEFT JOIN past_1w ON TRUE
LEFT JOIN past_30d ON TRUE
LEFT JOIN past_3m ON TRUE
LEFT JOIN past_6m ON TRUE;
"""
