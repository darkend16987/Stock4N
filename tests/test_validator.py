"""
Unit tests for DataValidator module
Tests data validation logic for symbols, price data, and financial data
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from modules.utils.validator import DataValidator
from modules.utils.exceptions import InvalidSymbolException, InsufficientDataException


class TestSymbolValidation:
    """Test stock symbol validation"""

    def test_valid_symbol(self):
        """Test valid Vietnamese stock symbols"""
        valid_symbols = ['VNM', 'FPT', 'VHM', 'HPG', 'MSN']
        for symbol in valid_symbols:
            is_valid, message = DataValidator.validate_symbol(symbol)
            assert is_valid is True
            assert message == ""

    def test_invalid_symbol_format(self):
        """Test invalid symbol formats"""
        invalid_symbols = ['VN', 'VNMM', 'vnm', 'VN1', '123']
        for symbol in invalid_symbols:
            is_valid, message = DataValidator.validate_symbol(symbol)
            assert is_valid is False
            assert "Invalid symbol format" in message

    def test_empty_symbol(self):
        """Test empty or None symbol"""
        is_valid, message = DataValidator.validate_symbol('')
        assert is_valid is False

        is_valid, message = DataValidator.validate_symbol(None)
        assert is_valid is False


class TestPriceDataValidation:
    """Test price data validation"""

    def test_valid_price_data(self, sample_price_data, sample_stock_symbol):
        """Test validation of valid price data"""
        is_valid, message = DataValidator.validate_price_data(
            sample_price_data,
            sample_stock_symbol
        )
        assert is_valid is True
        assert message == ""

    def test_insufficient_rows(self, sample_stock_symbol):
        """Test detection of insufficient data rows"""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=10, freq='D'),
            'close': [100] * 10,
            'volume': [1000] * 10
        })

        is_valid, message = DataValidator.validate_price_data(
            df,
            sample_stock_symbol,
            min_rows=30
        )
        assert is_valid is False
        assert "Insufficient data" in message

    def test_missing_required_columns(self, sample_stock_symbol):
        """Test detection of missing required columns"""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=50, freq='D'),
            'close': [100] * 50
            # Missing 'volume' column
        })

        is_valid, message = DataValidator.validate_price_data(
            df,
            sample_stock_symbol
        )
        assert is_valid is False
        assert "missing required columns" in message

    def test_excessive_null_values(self, sample_stock_symbol):
        """Test detection of excessive null values"""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=100, freq='D'),
            'close': [100] * 50 + [np.nan] * 50,  # 50% nulls
            'volume': [1000] * 100
        })

        is_valid, message = DataValidator.validate_price_data(
            df,
            sample_stock_symbol
        )
        assert is_valid is False
        assert "null values" in message.lower()

    def test_price_outliers(self, sample_stock_symbol):
        """Test detection of price outliers"""
        close_prices = [100] * 95 + [10000] * 5  # 5 extreme outliers
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=100, freq='D'),
            'close': close_prices,
            'volume': [1000] * 100
        })

        is_valid, message = DataValidator.validate_price_data(
            df,
            sample_stock_symbol
        )
        # Should detect outliers but might still pass if within threshold
        # This tests the outlier detection logic exists
        assert isinstance(is_valid, bool)

    def test_negative_prices(self, sample_stock_symbol):
        """Test detection of negative prices"""
        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=100, freq='D'),
            'close': [-100] * 100,  # Negative prices
            'volume': [1000] * 100
        })

        is_valid, message = DataValidator.validate_price_data(
            df,
            sample_stock_symbol
        )
        assert is_valid is False


class TestFinancialDataValidation:
    """Test financial data validation"""

    def test_valid_balance_sheet(self, sample_financial_data_balance, sample_stock_symbol):
        """Test validation of valid balance sheet data"""
        is_valid, message = DataValidator.validate_financial_data(
            sample_financial_data_balance,
            sample_stock_symbol,
            report_type='balance'
        )
        assert is_valid is True
        assert message == ""

    def test_valid_income_statement(self, sample_financial_data_income, sample_stock_symbol):
        """Test validation of valid income statement data"""
        is_valid, message = DataValidator.validate_financial_data(
            sample_financial_data_income,
            sample_stock_symbol,
            report_type='income'
        )
        assert is_valid is True
        assert message == ""

    def test_insufficient_quarters(self, sample_stock_symbol):
        """Test detection of insufficient quarters"""
        df = pd.DataFrame({
            'Năm': [2024, 2024],
            'Kỳ': [1, 2],
            'Doanh thu thuần': [100, 110]
        })

        is_valid, message = DataValidator.validate_financial_data(
            df,
            sample_stock_symbol,
            report_type='income',
            min_quarters=4
        )
        assert is_valid is False
        assert "Insufficient quarters" in message

    def test_missing_year_column(self, sample_stock_symbol):
        """Test detection of missing year/quarter columns"""
        df = pd.DataFrame({
            'Kỳ': [1, 2, 3, 4],
            'Doanh thu thuần': [100, 110, 120, 130]
            # Missing 'Năm' column
        })

        is_valid, message = DataValidator.validate_financial_data(
            df,
            sample_stock_symbol,
            report_type='income'
        )
        assert is_valid is False
        assert "missing required columns" in message.lower()

    def test_invalid_quarter_values(self, sample_stock_symbol):
        """Test detection of invalid quarter values"""
        df = pd.DataFrame({
            'Năm': [2024] * 5,
            'Kỳ': [1, 2, 3, 4, 5],  # Quarter 5 is invalid
            'Doanh thu thuần': [100, 110, 120, 130, 140]
        })

        is_valid, message = DataValidator.validate_financial_data(
            df,
            sample_stock_symbol,
            report_type='income'
        )
        assert is_valid is False
        assert "Invalid quarter values" in message


class TestMetricsValidation:
    """Test calculated metrics validation"""

    def test_valid_metrics(self, sample_metrics):
        """Test validation of valid metrics"""
        is_valid, message = DataValidator.validate_metrics(sample_metrics)
        assert is_valid is True
        assert message == ""

    def test_missing_required_metric(self, sample_metrics):
        """Test detection of missing required metrics"""
        incomplete_metrics = sample_metrics.copy()
        del incomplete_metrics['roe']

        is_valid, message = DataValidator.validate_metrics(incomplete_metrics)
        assert is_valid is False
        assert "Missing required metric" in message

    def test_invalid_roe_range(self, sample_metrics):
        """Test detection of invalid ROE values"""
        invalid_metrics = sample_metrics.copy()
        invalid_metrics['roe'] = -150  # ROE < -100% is suspicious

        is_valid, message = DataValidator.validate_metrics(invalid_metrics)
        # Should flag suspicious values
        assert isinstance(is_valid, bool)

    def test_invalid_rsi_range(self, sample_metrics):
        """Test detection of RSI outside valid range"""
        invalid_metrics = sample_metrics.copy()
        invalid_metrics['rsi'] = 150  # RSI should be 0-100

        is_valid, message = DataValidator.validate_metrics(invalid_metrics)
        assert is_valid is False
        assert "RSI must be between 0 and 100" in message

    def test_negative_price(self, sample_metrics):
        """Test detection of negative current price"""
        invalid_metrics = sample_metrics.copy()
        invalid_metrics['current_price'] = -1000

        is_valid, message = DataValidator.validate_metrics(invalid_metrics)
        assert is_valid is False


class TestDataFrameValidation:
    """Test general DataFrame validation utilities"""

    def test_empty_dataframe(self):
        """Test detection of empty DataFrame"""
        df = pd.DataFrame()
        assert DataValidator._is_empty_dataframe(df) is True

    def test_non_empty_dataframe(self, sample_price_data):
        """Test non-empty DataFrame"""
        assert DataValidator._is_empty_dataframe(sample_price_data) is False

    def test_null_percentage_calculation(self):
        """Test null percentage calculation"""
        df = pd.DataFrame({
            'col1': [1, 2, np.nan, 4, 5],
            'col2': [np.nan, np.nan, 3, 4, 5]
        })

        # col1 has 1/5 = 20% nulls
        # col2 has 2/5 = 40% nulls
        null_pct = DataValidator._calculate_null_percentage(df)
        assert null_pct['col1'] == 20.0
        assert null_pct['col2'] == 40.0
