"""Generate TradingView expressions for sector and subsector indices."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class TradingViewExpressionGenerator:
    """Generates equal-weight TradingView expressions for sectors."""

    def __init__(
        self,
        sectors_file: str = "../output_complete_data.json",
        instruments_file: str = "../upstox-instruments/complete.json",
    ):
        """
        Initialize the expression generator.

        Args:
            sectors_file: Path to output_complete_data.json
            instruments_file: Path to complete.json (instruments metadata)
        """
        self.sectors_file = sectors_file
        self.instruments_file = instruments_file
        self.sectors_data = self._load_json(sectors_file)
        self.instruments_data = self._load_json(
            instruments_file, "utf-16"
        )
        self.name_to_code = self._build_name_to_code_mapping()
        self.code_to_upstox_key = self._build_code_to_upstox_key()
        self.instrument_to_symbol = self._build_instrument_to_symbol_mapping()

    @staticmethod
    def _load_json(path: str, encoding: str = "utf-8") -> Dict:
        """Load JSON file with error handling."""
        try:
            with open(path, 'r', encoding=encoding) as f:
                return json.load(f)
        except UnicodeDecodeError:
            if encoding != "utf-8":
                with open(path, 'r', encoding="utf-8") as f:
                    return json.load(f)
            raise
        except FileNotFoundError:
            print(f"File not found: {path}")
            return {}

    def _build_name_to_code_mapping(self) -> Dict[str, str]:
        """Build mapping of stock names to exchange:symbol codes."""
        mapping = {}
        for sector in self.sectors_data:
            for subind in sector.get('subindustries', []):
                for stock in subind.get('stocks', []):
                    name = stock.get('name', '').strip()
                    code = stock.get('code', '').strip()
                    if name and code:
                        mapping[name] = code
        return mapping

    def _build_code_to_upstox_key(self) -> Dict[str, str]:
        """Build mapping of exchange:symbol to Upstox instrument_key."""
        mapping = {}
        for instrument in self.instruments_data:
            trading_symbol = (
                instrument.get('trading_symbol') or ""
            ).strip().upper()
            segment = instrument.get('segment', '')
            ikey = instrument.get('instrument_key', '')

            if trading_symbol and segment in ("NSE_EQ", "BSE_EQ") and ikey:
                # Map trading_symbol to full upstox format
                exchange = "NSE" if segment == "NSE_EQ" else "BSE"
                mapping[f"{exchange}:{trading_symbol}"] = ikey

        return mapping

    def _build_instrument_to_symbol_mapping(self) -> Dict[str, str]:
        """Build mapping of Upstox instrument_key to segment:symbol format.

        This maps instrument keys (e.g., 'NSE_EQ|INE467B01029') to the format
        returned by the API (e.g., 'NSE_EQ:RELIANCE').
        """
        mapping = {}
        for instrument in self.instruments_data:
            trading_symbol = (
                instrument.get('trading_symbol') or ""
            ).strip().upper()
            segment = instrument.get('segment', '')
            ikey = instrument.get('instrument_key', '')

            if trading_symbol and segment in ("NSE_EQ", "BSE_EQ") and ikey:
                # Map instrument_key to segment:symbol format (API response format)
                mapping[ikey] = f"{segment}:{trading_symbol}"

        return mapping

    def get_sector_stocks(
        self, sector_title: str
    ) -> Dict[str, List[str]]:
        """
        Get all stocks for a sector, grouped by subsector.

        Args:
            sector_title: Title of the sector

        Returns:
            Dict mapping subsector names -> list of stock names
        """
        for sector in self.sectors_data:
            if sector.get('sector_title') == sector_title:
                subsector_stocks = {}
                for subind in sector.get('subindustries', []):
                    subind_name = subind.get('name', '')
                    stocks = [
                        s.get('name') for s in subind.get('stocks', [])
                        if s.get('name')
                    ]
                    if stocks:
                        subsector_stocks[subind_name] = stocks
                return subsector_stocks
        return {}

    def generate_expression(
        self,
        stock_names: List[str],
        prices: Dict[str, float],
        target_per_stock: float = 1000.0,
    ) -> Tuple[str, Dict]:
        """
        Generate a TradingView expression with equal-weight coefficients.

        Args:
            stock_names: List of stock names
            prices: Dict mapping stock names -> LTP prices
            target_per_stock: Coefficient = target_per_stock / price

        Returns:
            Tuple of (expression_string, coefficient_dict)
        """
        if not stock_names or not prices:
            return "", {}

        expression_parts = []
        coefficients = {}

        for stock_name in stock_names:
            code = self.name_to_code.get(stock_name)
            price = prices.get(stock_name)

            if not code or price is None or price == 0:
                continue

            # Calculate coefficient
            coefficient = target_per_stock / price

            # Round to 6 significant figures
            coeff_rounded = round(coefficient, 6)

            expression_parts.append(
                f"{code} * {coeff_rounded}"
            )
            coefficients[stock_name] = {
                'code': code,
                'price': price,
                'coefficient': coeff_rounded
            }

        if not expression_parts:
            return "", {}

        expression = "(" + " + ".join(expression_parts) + ")"
        return expression, coefficients

    def generate_sector_expressions(
        self,
        sector_title: str,
        prices: Dict[str, float],
        target_per_stock: float = 1000.0,
    ) -> Dict:
        """
        Generate expressions for a sector and all its subsectors.

        Args:
            sector_title: Title of the sector
            prices: Dict mapping stock names -> LTP prices
            target_per_stock: Target coefficient denominator

        Returns:
            Dict containing sector and subsector expressions
        """
        result = {
            'sector': sector_title,
            'timestamp': datetime.now().isoformat(),
            'target_per_stock': target_per_stock,
            'sector_expression': None,
            'sector_components': {},
            'subsectors': {}
        }

        subsector_stocks = self.get_sector_stocks(sector_title)
        all_sector_stocks = []

        # Generate expressions for each subsector
        for subsector_name, stocks in subsector_stocks.items():
            expr, coeffs = self.generate_expression(
                stocks, prices, target_per_stock
            )
            if expr:
                result['subsectors'][subsector_name] = {
                    'stocks': stocks,
                    'expression': expr,
                    'components': coeffs
                }
                all_sector_stocks.extend(stocks)

        # Generate expression for entire sector
        all_sector_stocks = list(set(all_sector_stocks))
        sector_expr, sector_coeffs = self.generate_expression(
            all_sector_stocks, prices, target_per_stock
        )

        result['sector_expression'] = sector_expr
        result['sector_components'] = sector_coeffs

        return result
