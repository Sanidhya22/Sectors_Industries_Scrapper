"""
Chart UI module for rendering sector analysis charts using lightweight charts.
"""

import json

import numpy as np
import pandas as pd
import streamlit as st

from streamlit_lightweight_charts import renderLightweightCharts

COLOR_BULL = 'rgba(38,166,154,0.9)'  # #26a69a
COLOR_BEAR = 'rgba(239,83,80,0.9)'   # #ef5350


def prepare_ohlcv_data(price_df: pd.DataFrame) -> tuple:
    """
    Prepare candlestick and volume data from price dataframe.

    Args:
        price_df: DataFrame with Close prices (index is datetime)

    Returns:
        tuple: (candles_list, volume_list)
    """
    # Create a simple OHLCV structure from Close prices
    # In a real scenario, you'd have OHLCV data from your data source
    df = price_df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df = df.reset_index()
    if "time" not in df.columns:
        df.columns = ["time", "close"]
    else:
        df.columns = ["time"] + list(df.columns[1:])

    # For now, estimate OHLC from close prices with simple logic
    # (In production, use actual OHLCV data)
    df['open'] = df['close'].shift(1).fillna(df['close'])
    df['high'] = df[['open', 'close']].max(axis=1)
    df['low'] = df[['open', 'close']].min(axis=1)
    df['volume'] = 1000000  # Placeholder volume

    df['time'] = df['time'].dt.strftime('%Y-%m-%d')
    df['color'] = np.where(
        df['open'] > df['close'], COLOR_BEAR, COLOR_BULL
    )

    candles_df = df[['time', 'open', 'high', 'low', 'close', 'color']]
    candles = json.loads(candles_df.to_json(orient="records"))
    volume_df = df.rename(columns={"volume": "value"})
    volume = json.loads(volume_df.to_json(orient="records"))

    return candles, volume


def prepare_line_series(series: pd.Series, series_name: str = "Index") -> list:
    """
    Prepare line chart data from a pandas Series.

    Args:
        series: pd.Series with datetime index
        series_name: Name of the series

    Returns:
        list: Data formatted for lightweight charts
    """
    df = series.reset_index()
    df.columns = ['time', 'value']
    df['time'] = df['time'].dt.strftime('%Y-%m-%d')

    return json.loads(df.to_json(orient="records"))


def render_sector_index_chart(
    sector_index: pd.Series,
    sector_name: str,
    component_series: dict = None,
    show_components: bool = False,
):
    """
    Render sector index chart with optional component stocks.

    Args:
        sector_index: pd.Series with sector index values (datetime index)
        sector_name: Name of the sector
        component_series: dict of stock_name -> pd.Series
        show_components: Whether to show component stock lines
    """
    # Prepare main line chart data
    line_data = prepare_line_series(sector_index, "Sector Index")

    series_config = [
        {
            "type": "Line",
            "data": line_data,
            "options": {
                "color": 'rgba(38, 166, 154, 0.9)',
                "lineWidth": 2
            }
        }
    ]

    # Add component series if requested
    if show_components and component_series is not None and len(component_series) > 0:
        colors = [
            'rgba(25, 103, 210, 0.7)',
            'rgba(56, 142, 60, 0.7)',
            'rgba(211, 47, 47, 0.7)',
            'rgba(245, 127, 23, 0.7)',
            'rgba(123, 31, 162, 0.7)',
            'rgba(0, 150, 136, 0.7)',
        ]

        for idx, (stock_name, series) in enumerate(component_series.items()):
            # Normalize series to percentage change from first value
            normalized = (series / series.iloc[0] - 1) * 100
            line_data = prepare_line_series(normalized, stock_name)

            series_config.append({
                "type": "Line",
                "data": line_data,
                "options": {
                    "color": colors[idx % len(colors)],
                    "lineWidth": 1,
                    "title": stock_name
                }
            })

    # Chart configuration
    chart_options = {
        "width": 1200,
        "height": 500,
        "layout": {
            "background": {
                "type": "solid",
                "color": 'white'
            },
            "textColor": "black"
        },
        "grid": {
            "vertLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            },
            "horzLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            }
        },
        "crosshair": {
            "mode": 1  # Magnet mode
        },
        "priceScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)"
        },
        "timeScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)",
            "barSpacing": 15,
            "fixLeftEdge": True
        },
        "watermark": {
            "visible": True,
            "fontSize": 48,
            "horzAlign": 'center',
            "vertAlign": 'center',
            "color": 'rgba(171, 71, 188, 0.3)',
            "text": f'{sector_name} - Sector Index',
        }
    }

    # Render the chart
    renderLightweightCharts([
        {
            "chart": chart_options,
            "series": series_config
        }
    ], 'sector_index')


def render_candlestick_chart(price_data: pd.DataFrame, stock_name: str = "Stock"):
    """
    Render candlestick chart with volume.

    Args:
        price_data: DataFrame with OHLCV columns
        stock_name: Name of the stock
    """
    candles, volume = prepare_ohlcv_data(price_data)

    # Candlestick pane
    candlestick_config = {
        "width": 1200,
        "height": 400,
        "layout": {
            "background": {
                "type": "solid",
                "color": 'white'
            },
            "textColor": "black"
        },
        "grid": {
            "vertLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            },
            "horzLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            }
        },
        "crosshair": {
            "mode": 1
        },
        "priceScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)"
        },
        "timeScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)",
            "barSpacing": 15
        },
        "watermark": {
            "visible": True,
            "fontSize": 36,
            "horzAlign": 'center',
            "vertAlign": 'center',
            "color": 'rgba(171, 71, 188, 0.3)',
            "text": f'{stock_name}',
        }
    }

    # Volume pane
    volume_config = {
        "width": 1200,
        "height": 120,
        "layout": {
            "background": {
                "type": 'solid',
                "color": 'white'
            },
            "textColor": 'black',
        },
        "grid": {
            "vertLines": {
                "color": 'rgba(197, 203, 206, 0.5)',
            },
            "horzLines": {
                "color": 'rgba(197, 203, 206, 0.5)',
            }
        },
        "timeScale": {
            "visible": False,
        },
        "watermark": {
            "visible": True,
            "fontSize": 16,
            "horzAlign": 'left',
            "vertAlign": 'top',
            "color": 'rgba(171, 71, 188, 0.7)',
            "text": 'Volume',
        }
    }

    # Series configuration
    candlestick_series = [
        {
            "type": 'Candlestick',
            "data": candles,
            "options": {
                "upColor": COLOR_BULL,
                "downColor": COLOR_BEAR,
                "borderVisible": False,
                "wickUpColor": COLOR_BULL,
                "wickDownColor": COLOR_BEAR
            }
        }
    ]

    volume_series = [
        {
            "type": 'Histogram',
            "data": volume,
            "options": {
                "color": 'rgba(0, 0, 0, 0.1)',
            },
            "priceScale": {
                "scaleMargins": {
                    "top": 0,
                    "bottom": 0,
                },
                "alignLabels": False
            }
        }
    ]

    # Render the charts
    renderLightweightCharts([
        {
            "chart": candlestick_config,
            "series": candlestick_series
        },
        {
            "chart": volume_config,
            "series": volume_series
        }
    ], 'candlestick')
