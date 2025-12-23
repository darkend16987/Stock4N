"""
Unit tests for FinancialCalculator module
Tests financial metrics calculation including ROE, ROA, growth rates, etc.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from modules.processing.calculator import FinancialCalculator
from modules.utils.exceptions import InsufficientDataException


class TestFinancialCalculator:
    """Test FinancialCalculator class"""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance"""
        return FinancialCalculator()


class TestROECalculation(TestFinancialCalculator):
    """Test ROE (Return on Equity) calculation"""

    def test_roe_calculation_basic(self, calculator, sample_financial_data_balance, sample_financial_data_income):
        """Test basic ROE calculation"""
        metrics = calculator.calculate_metrics(
            sample_financial_data_balance,
            sample_financial_data_income
        )

        assert 'roe' in metrics
        assert isinstance(metrics['roe'], (int, float))
        # ROE should be reasonable (e.g., -100% to 200%)
        assert -100 <= metrics['roe'] <= 200

    def test_roe_with_zero_equity(self, calculator):
        """Test ROE calculation when equity is zero"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Vốn chủ sở hữu': [0, 0, 0, 0]  # Zero equity
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [10, 11, 12, 13]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)
        # Should handle division by zero gracefully
        assert 'roe' in metrics
        assert metrics['roe'] is None or metrics['roe'] == 0

    def test_roe_negative_profit(self, calculator):
        """Test ROE calculation with negative profit"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Vốn chủ sở hữu': [1000, 1000, 1000, 1000]
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [-10, -11, -12, -13]  # Negative profit
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)
        assert 'roe' in metrics
        # ROE should be negative when profit is negative
        assert metrics['roe'] < 0


class TestROACalculation(TestFinancialCalculator):
    """Test ROA (Return on Assets) calculation"""

    def test_roa_calculation_basic(self, calculator, sample_financial_data_balance, sample_financial_data_income):
        """Test basic ROA calculation"""
        metrics = calculator.calculate_metrics(
            sample_financial_data_balance,
            sample_financial_data_income
        )

        assert 'roa' in metrics
        assert isinstance(metrics['roa'], (int, float))
        # ROA should typically be lower than ROE
        assert -100 <= metrics['roa'] <= 100

    def test_roa_with_zero_assets(self, calculator):
        """Test ROA calculation when assets is zero"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Tổng tài sản': [0, 0, 0, 0]  # Zero assets
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [10, 11, 12, 13]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)
        # Should handle division by zero gracefully
        assert 'roa' in metrics
        assert metrics['roa'] is None or metrics['roa'] == 0


class TestYoYGrowthCalculation(TestFinancialCalculator):
    """Test Year-over-Year growth calculation (CRITICAL)"""

    def test_profit_growth_yoy(self, calculator):
        """Test YoY profit growth calculation with proper quarter matching"""
        current_year = datetime.now().year

        income_df = pd.DataFrame({
            'Năm': [current_year-1, current_year-1, current_year, current_year],
            'Kỳ': [3, 4, 3, 4],  # Q3 and Q4 for both years
            'Lợi nhuận sau thuế': [100, 110, 120, 130]
        })
        balance_df = pd.DataFrame({
            'Năm': [current_year-1, current_year-1, current_year, current_year],
            'Kỳ': [3, 4, 3, 4],
            'Vốn chủ sở hữu': [1000, 1000, 1000, 1000],
            'Tổng tài sản': [2000, 2000, 2000, 2000]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'profit_growth' in metrics
        # Q4 current year (130) vs Q4 last year (110)
        # Growth should be (130 - 110) / 110 * 100 = 18.18%
        expected_growth = ((130 - 110) / 110) * 100
        assert abs(metrics['profit_growth'] - expected_growth) < 0.1

    def test_revenue_growth_yoy(self, calculator):
        """Test YoY revenue growth with quarter matching"""
        current_year = datetime.now().year

        income_df = pd.DataFrame({
            'Năm': [current_year-1, current_year-1, current_year-1, current_year-1,
                    current_year, current_year, current_year, current_year],
            'Kỳ': [1, 2, 3, 4, 1, 2, 3, 4],
            'Doanh thu thuần': [100, 105, 110, 115, 120, 125, 130, 135],
            'Lợi nhuận sau thuế': [10, 11, 12, 13, 14, 15, 16, 17]
        })
        balance_df = pd.DataFrame({
            'Năm': [current_year-1] * 4 + [current_year] * 4,
            'Kỳ': [1, 2, 3, 4, 1, 2, 3, 4],
            'Vốn chủ sở hữu': [1000] * 8,
            'Tổng tài sản': [2000] * 8
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'revenue_growth' in metrics
        # Q4 current year (135) vs Q4 last year (115)
        # Growth should be (135 - 115) / 115 * 100 = 17.39%
        expected_growth = ((135 - 115) / 115) * 100
        assert abs(metrics['revenue_growth'] - expected_growth) < 0.1

    def test_yoy_growth_missing_previous_quarter(self, calculator):
        """Test YoY growth when previous year's quarter is missing"""
        current_year = datetime.now().year

        # Only has Q4 for current year, missing Q4 for previous year
        income_df = pd.DataFrame({
            'Năm': [current_year-1, current_year-1, current_year],
            'Kỳ': [1, 2, 4],  # Missing Q4 from last year
            'Lợi nhuận sau thuế': [100, 105, 130],
            'Doanh thu thuần': [200, 210, 260]
        })
        balance_df = pd.DataFrame({
            'Năm': [current_year-1, current_year-1, current_year],
            'Kỳ': [1, 2, 4],
            'Vốn chủ sở hữu': [1000, 1000, 1000],
            'Tổng tài sản': [2000, 2000, 2000]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        # Should handle missing data gracefully
        assert 'profit_growth' in metrics
        assert 'revenue_growth' in metrics
        # Growth might be None or calculated using alternative method
        assert isinstance(metrics['profit_growth'], (int, float, type(None)))

    def test_yoy_growth_negative_values(self, calculator):
        """Test YoY growth with negative profit values"""
        current_year = datetime.now().year

        income_df = pd.DataFrame({
            'Năm': [current_year-1, current_year],
            'Kỳ': [4, 4],
            'Lợi nhuận sau thuế': [-100, 50],  # Loss to profit
            'Doanh thu thuần': [200, 250]
        })
        balance_df = pd.DataFrame({
            'Năm': [current_year-1, current_year],
            'Kỳ': [4, 4],
            'Vốn chủ sở hữu': [1000, 1000],
            'Tổng tài sản': [2000, 2000]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'profit_growth' in metrics
        # Growth from -100 to 50 should be positive
        # Using abs() in denominator: (50 - (-100)) / abs(-100) * 100 = 150%
        assert metrics['profit_growth'] > 0


class TestAssetGrowthCalculation(TestFinancialCalculator):
    """Test asset growth calculation"""

    def test_asset_growth_yoy(self, calculator):
        """Test YoY asset growth"""
        current_year = datetime.now().year

        balance_df = pd.DataFrame({
            'Năm': [current_year-1, current_year],
            'Kỳ': [4, 4],
            'Tổng tài sản': [1000, 1200],
            'Vốn chủ sở hữu': [600, 700]
        })
        income_df = pd.DataFrame({
            'Năm': [current_year-1, current_year],
            'Kỳ': [4, 4],
            'Lợi nhuận sau thuế': [50, 60]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'asset_growth' in metrics
        # (1200 - 1000) / 1000 * 100 = 20%
        expected_growth = ((1200 - 1000) / 1000) * 100
        assert abs(metrics['asset_growth'] - expected_growth) < 0.1


class TestEquityRatioCalculation(TestFinancialCalculator):
    """Test equity ratio calculation"""

    def test_equity_ratio_basic(self, calculator, sample_financial_data_balance, sample_financial_data_income):
        """Test basic equity ratio calculation"""
        metrics = calculator.calculate_metrics(
            sample_financial_data_balance,
            sample_financial_data_income
        )

        assert 'equity_ratio' in metrics
        # Equity ratio should be between 0 and 1
        assert 0 <= metrics['equity_ratio'] <= 1

    def test_equity_ratio_calculation(self, calculator):
        """Test equity ratio calculation accuracy"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Tổng tài sản': [1000, 1000, 1000, 1000],
            'Vốn chủ sở hữu': [600, 600, 600, 600]
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [10, 11, 12, 13]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'equity_ratio' in metrics
        # Equity ratio = 600 / 1000 = 0.6
        assert abs(metrics['equity_ratio'] - 0.6) < 0.01

    def test_equity_ratio_high_leverage(self, calculator):
        """Test equity ratio with high leverage (low equity)"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Tổng tài sản': [1000, 1000, 1000, 1000],
            'Vốn chủ sở hữu': [100, 100, 100, 100]  # Only 10% equity
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [10, 11, 12, 13]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'equity_ratio' in metrics
        # Equity ratio = 100 / 1000 = 0.1 (high leverage)
        assert abs(metrics['equity_ratio'] - 0.1) < 0.01


class TestProfitMarginCalculation(TestFinancialCalculator):
    """Test profit margin calculation"""

    def test_profit_margin_basic(self, calculator, sample_financial_data_balance, sample_financial_data_income):
        """Test basic profit margin calculation"""
        metrics = calculator.calculate_metrics(
            sample_financial_data_balance,
            sample_financial_data_income
        )

        assert 'profit_margin' in metrics
        # Profit margin should typically be between 0% and 50%
        assert -50 <= metrics['profit_margin'] <= 100

    def test_profit_margin_calculation(self, calculator):
        """Test profit margin calculation accuracy"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Vốn chủ sở hữu': [1000, 1000, 1000, 1000],
            'Tổng tài sản': [2000, 2000, 2000, 2000]
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Doanh thu thuần': [100, 100, 100, 100],
            'Lợi nhuận sau thuế': [20, 20, 20, 20]
        })

        metrics = calculator.calculate_metrics(balance_df, income_df)

        assert 'profit_margin' in metrics
        # Profit margin = 20 / 100 * 100 = 20%
        assert abs(metrics['profit_margin'] - 20.0) < 0.1


class TestEdgeCases(TestFinancialCalculator):
    """Test edge cases and error handling"""

    def test_empty_dataframe(self, calculator):
        """Test handling of empty DataFrames"""
        balance_df = pd.DataFrame()
        income_df = pd.DataFrame()

        with pytest.raises((InsufficientDataException, ValueError, KeyError)):
            calculator.calculate_metrics(balance_df, income_df)

    def test_insufficient_data(self, calculator):
        """Test handling of insufficient data"""
        balance_df = pd.DataFrame({
            'Năm': [2024],
            'Kỳ': [1],
            'Vốn chủ sở hữu': [1000],
            'Tổng tài sản': [2000]
        })
        income_df = pd.DataFrame({
            'Năm': [2024],
            'Kỳ': [1],
            'Lợi nhuận sau thuế': [10]
        })

        # Should handle gracefully or raise appropriate exception
        try:
            metrics = calculator.calculate_metrics(balance_df, income_df)
            # If it doesn't raise, check metrics are reasonable
            assert isinstance(metrics, dict)
        except InsufficientDataException:
            # Expected behavior
            pass

    def test_all_null_values(self, calculator):
        """Test handling of all null values"""
        balance_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Vốn chủ sở hữu': [np.nan] * 4,
            'Tổng tài sản': [np.nan] * 4
        })
        income_df = pd.DataFrame({
            'Năm': [2024] * 4,
            'Kỳ': [1, 2, 3, 4],
            'Lợi nhuận sau thuế': [np.nan] * 4
        })

        with pytest.raises((InsufficientDataException, ValueError, ZeroDivisionError)):
            calculator.calculate_metrics(balance_df, income_df)
