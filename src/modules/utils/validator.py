"""
Data Validation Module - Validate data quality and format
"""

import pandas as pd
import re
from typing import Tuple, Optional
from .exceptions import (
    InvalidSymbolException,
    InvalidDataException,
    DataQualityException,
    InsufficientDataException
)
from .logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """
    Validator for stock data quality and format
    """

    @staticmethod
    def validate_symbol(symbol: str) -> Tuple[bool, str]:
        """
        Validate Vietnamese stock symbol format

        Args:
            symbol: Stock symbol to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not symbol:
            return False, "Symbol is empty"

        # Vietnamese stock symbols: 3 uppercase letters
        pattern = r'^[A-Z]{3}$'
        if not re.match(pattern, symbol):
            return False, f"Invalid symbol format: {symbol}. Expected 3 uppercase letters (e.g., VCB, HPG)"

        return True, "OK"

    @staticmethod
    def validate_price_data(df: pd.DataFrame, symbol: str = "Unknown",
                           min_rows: int = 30) -> Tuple[bool, str]:
        """
        Validate price data DataFrame

        Args:
            df: Price DataFrame
            symbol: Stock symbol (for error messages)
            min_rows: Minimum number of rows required

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df is None or df.empty:
            return False, f"Price data is empty for {symbol}"

        # Check required columns
        required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return False, f"Missing required columns for {symbol}: {missing_cols}"

        # Check minimum rows
        if len(df) < min_rows:
            return False, f"Insufficient data for {symbol}: {len(df)} rows (minimum: {min_rows})"

        # Check for too many nulls
        null_pct = df[['open', 'high', 'low', 'close']].isnull().sum().sum() / (len(df) * 4)
        if null_pct > 0.1:  # More than 10% nulls
            return False, f"Too many null values for {symbol}: {null_pct*100:.1f}%"

        # Check for invalid price values (negative or zero)
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if (df[col] <= 0).any():
                invalid_count = (df[col] <= 0).sum()
                return False, f"Invalid price values in {col} for {symbol}: {invalid_count} rows with value <= 0"

        # Check for logical consistency (high >= low)
        if (df['high'] < df['low']).any():
            return False, f"Logical error in {symbol}: high < low in some rows"

        # Check for outliers (price change > 20% in one day - suspicious)
        df_sorted = df.sort_values('time')
        price_changes = df_sorted['close'].pct_change().abs()
        outliers = (price_changes > 0.20).sum()
        if outliers > len(df) * 0.05:  # More than 5% of days have >20% change
            logger.warning(f"Suspicious price volatility for {symbol}: {outliers} days with >20% change")

        return True, "OK"

    @staticmethod
    def validate_financial_data(df: pd.DataFrame, symbol: str = "Unknown",
                                report_type: str = "Financial") -> Tuple[bool, str]:
        """
        Validate financial report DataFrame

        Args:
            df: Financial DataFrame
            symbol: Stock symbol (for error messages)
            report_type: Type of report (BalanceSheet, IncomeStatement, etc.)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df is None or df.empty:
            return False, f"{report_type} data is empty for {symbol}"

        # Check for year and quarter columns
        has_year = any('năm' in col.lower() or 'year' in col.lower() for col in df.columns)
        has_quarter = any('kỳ' in col.lower() or 'quarter' in col.lower() or 'quý' in col.lower() for col in df.columns)

        if not (has_year and has_quarter):
            return False, f"Missing year/quarter columns in {report_type} for {symbol}"

        # Check minimum quarters (at least 4 quarters for meaningful analysis)
        if len(df) < 4:
            return False, f"Insufficient {report_type} data for {symbol}: {len(df)} quarters (minimum: 4)"

        # Check if all values are null
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) == 0:
            return False, f"No numeric columns in {report_type} for {symbol}"

        all_null = df[numeric_cols].isnull().all().all()
        if all_null:
            return False, f"All numeric values are null in {report_type} for {symbol}"

        return True, "OK"

    @staticmethod
    def validate_metrics(metrics: dict, symbol: str = "Unknown") -> Tuple[bool, str]:
        """
        Validate calculated metrics

        Args:
            metrics: Dictionary of calculated metrics
            symbol: Stock symbol (for error messages)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not metrics:
            return False, f"Metrics is empty for {symbol}"

        # Check for required fields
        required_fields = ['Symbol', 'Price', 'ROE']
        missing_fields = [field for field in required_fields if field not in metrics]

        if missing_fields:
            return False, f"Missing required metrics for {symbol}: {missing_fields}"

        # Check for valid price
        price = metrics.get('Price')
        if price is None or price <= 0:
            return False, f"Invalid price for {symbol}: {price}"

        # Check ROE if present
        roe = metrics.get('ROE')
        if roe is not None:
            if not isinstance(roe, (int, float)):
                return False, f"ROE is not numeric for {symbol}: {roe}"

            # ROE > 100% or < -100% is suspicious
            if abs(roe) > 100:
                logger.warning(f"Suspicious ROE value for {symbol}: {roe}%")

        return True, "OK"

    @staticmethod
    def validate_analysis_report(df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate analysis report DataFrame

        Args:
            df: Analysis report DataFrame

        Returns:
            Tuple of (is_valid, error_message)
        """
        if df is None or df.empty:
            return False, "Analysis report is empty"

        required_cols = ['Symbol', 'Total_Score', 'Recommendation']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return False, f"Missing required columns in analysis report: {missing_cols}"

        # Check score range
        if (df['Total_Score'] < 0).any() or (df['Total_Score'] > 10).any():
            return False, "Total_Score out of range (0-10)"

        return True, "OK"

    @staticmethod
    def check_data_quality(df: pd.DataFrame, quality_threshold: float = 0.7) -> Tuple[bool, float, str]:
        """
        Calculate overall data quality score

        Args:
            df: DataFrame to check
            quality_threshold: Minimum quality score (0-1)

        Returns:
            Tuple of (passes_threshold, quality_score, message)
        """
        if df is None or df.empty:
            return False, 0.0, "Data is empty"

        score = 0.0
        max_score = 0.0

        # 1. Completeness (40%)
        max_score += 0.4
        completeness = 1 - df.isnull().sum().sum() / (len(df) * len(df.columns))
        score += completeness * 0.4

        # 2. Consistency (30%)
        max_score += 0.3
        # Check for duplicates
        duplicate_ratio = df.duplicated().sum() / len(df)
        consistency = 1 - duplicate_ratio
        score += consistency * 0.3

        # 3. Validity (30%)
        max_score += 0.3
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            # Check for outliers using IQR method
            valid_count = 0
            total_count = 0
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR
                valid = ((df[col] >= lower_bound) & (df[col] <= upper_bound)).sum()
                valid_count += valid
                total_count += len(df[col].dropna())

            if total_count > 0:
                validity = valid_count / total_count
                score += validity * 0.3
            else:
                score += 0.3
        else:
            score += 0.3

        quality_score = score / max_score if max_score > 0 else 0

        passes = quality_score >= quality_threshold
        message = f"Quality score: {quality_score:.2%} ({'PASS' if passes else 'FAIL'}, threshold: {quality_threshold:.2%})"

        return passes, quality_score, message


# Convenience functions
def validate_symbol(symbol: str) -> bool:
    """Validate symbol and raise exception if invalid"""
    is_valid, message = DataValidator.validate_symbol(symbol)
    if not is_valid:
        raise InvalidSymbolException(message)
    return True


def validate_price_data(df: pd.DataFrame, symbol: str = "Unknown") -> bool:
    """Validate price data and raise exception if invalid"""
    is_valid, message = DataValidator.validate_price_data(df, symbol)
    if not is_valid:
        raise InvalidDataException(message)
    return True


def validate_financial_data(df: pd.DataFrame, symbol: str = "Unknown", report_type: str = "Financial") -> bool:
    """Validate financial data and raise exception if invalid"""
    is_valid, message = DataValidator.validate_financial_data(df, symbol, report_type)
    if not is_valid:
        raise InvalidDataException(message)
    return True
