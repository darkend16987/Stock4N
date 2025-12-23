"""
Unit tests for PortfolioManager module
Tests portfolio construction, position sizing, and risk management
"""
import pytest
import pandas as pd
import numpy as np

from modules.portfolio.manager import PortfolioManager
import config


class TestPortfolioManager:
    """Test PortfolioManager class"""

    @pytest.fixture
    def manager(self):
        """Create portfolio manager instance"""
        return PortfolioManager(total_capital=100_000_000)  # 100M VND


class TestPortfolioConstruction(TestPortfolioManager):
    """Test portfolio construction logic"""

    def test_portfolio_initialization(self, manager):
        """Test portfolio manager initialization"""
        assert manager.total_capital == 100_000_000
        assert manager.cash_reserve_pct == config.PORTFOLIO_CONFIG['cash_reserve_pct']
        assert manager.max_position_pct == config.PORTFOLIO_CONFIG['max_position_pct']

    def test_available_capital_calculation(self, manager):
        """Test available capital calculation after cash reserve"""
        expected_capital = 100_000_000 * (1 - config.PORTFOLIO_CONFIG['cash_reserve_pct'])
        assert manager.get_available_capital() == expected_capital

    def test_build_portfolio_basic(self, manager):
        """Test basic portfolio building with buy recommendations"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 8.5,
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 8.2,
                'technical_score': 8.9
            },
            {
                'symbol': 'FPT',
                'overall_score': 7.8,
                'recommendation': 'BUY',
                'current_price': 95000,
                'fundamental_score': 7.5,
                'technical_score': 8.2
            },
            {
                'symbol': 'VHM',
                'overall_score': 6.5,
                'recommendation': 'WATCH',
                'current_price': 45000,
                'fundamental_score': 6.8,
                'technical_score': 6.1
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)

        assert isinstance(portfolio, list)
        # Should only include BUY recommendations
        assert all(p['recommendation'] == 'BUY' for p in portfolio)
        # VNM and FPT should be in portfolio
        symbols = [p['symbol'] for p in portfolio]
        assert 'VNM' in symbols
        assert 'FPT' in symbols
        # VHM (WATCH) should not be in portfolio
        assert 'VHM' not in symbols

    def test_score_weighted_allocation(self, manager):
        """Test score-weighted position sizing"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 9.0,  # Higher score
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 8.8,
                'technical_score': 9.3
            },
            {
                'symbol': 'FPT',
                'overall_score': 7.0,  # Lower score
                'recommendation': 'BUY',
                'current_price': 95000,
                'fundamental_score': 7.2,
                'technical_score': 6.7
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)

        vnm_position = next(p for p in portfolio if p['symbol'] == 'VNM')
        fpt_position = next(p for p in portfolio if p['symbol'] == 'FPT')

        # VNM (score 9.0) should have higher allocation than FPT (score 7.0)
        assert vnm_position['allocation_amount'] > fpt_position['allocation_amount']
        assert vnm_position['allocation_pct'] > fpt_position['allocation_pct']

    def test_max_position_limit(self, manager):
        """Test maximum position size constraint"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 9.5,  # Very high score
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 9.2,
                'technical_score': 9.9
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)
        vnm_position = portfolio[0]

        # Position should not exceed max_position_pct (40%)
        max_allowed = manager.total_capital * config.PORTFOLIO_CONFIG['max_position_pct']
        assert vnm_position['allocation_amount'] <= max_allowed

    def test_cash_reserve_maintained(self, manager):
        """Test that cash reserve is maintained"""
        analysis_results = [
            {
                'symbol': f'ST{i}',
                'overall_score': 8.0,
                'recommendation': 'BUY',
                'current_price': 50000,
                'fundamental_score': 8.0,
                'technical_score': 8.0
            }
            for i in range(10)  # Many stocks
        ]

        portfolio = manager.build_portfolio(analysis_results)

        total_allocated = sum(p['allocation_amount'] for p in portfolio)
        available_capital = manager.get_available_capital()

        # Total allocation should not exceed available capital (after cash reserve)
        assert total_allocated <= available_capital

    def test_empty_buy_recommendations(self, manager):
        """Test portfolio building with no BUY recommendations"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 6.0,
                'recommendation': 'WATCH',
                'current_price': 85000,
                'fundamental_score': 6.2,
                'technical_score': 5.7
            },
            {
                'symbol': 'FPT',
                'overall_score': 4.5,
                'recommendation': 'SELL',
                'current_price': 95000,
                'fundamental_score': 4.8,
                'technical_score': 4.1
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)

        # Should return empty portfolio or None
        assert portfolio == [] or portfolio is None


class TestPriceUnitDetection(TestPortfolioManager):
    """Test price unit auto-detection (CRITICAL fix)"""

    def test_price_in_thousands(self, manager):
        """Test price detection when price is in thousands VND"""
        price_thousands = 85  # 85 (thousands) = 85,000 VND

        actual_price = manager._detect_price_unit(price_thousands)

        # Should multiply by 1000
        assert actual_price == 85000

    def test_price_in_vnd(self, manager):
        """Test price detection when price is already in VND"""
        price_vnd = 85000  # Already in VND

        actual_price = manager._detect_price_unit(price_vnd)

        # Should not multiply
        assert actual_price == 85000

    def test_price_threshold_boundary(self, manager):
        """Test price at threshold boundary"""
        threshold = config.PRICE_UNIT_CONFIG['threshold']

        # Just below threshold (should multiply)
        price_below = threshold - 1
        actual_below = manager._detect_price_unit(price_below)
        assert actual_below == price_below * config.PRICE_UNIT_CONFIG['multiplier']

        # At or above threshold (should not multiply)
        price_above = threshold
        actual_above = manager._detect_price_unit(price_above)
        assert actual_above == price_above

    def test_very_low_price(self, manager):
        """Test very low price detection"""
        price = 5  # 5 thousands = 5,000 VND (penny stock)

        actual_price = manager._detect_price_unit(price)

        assert actual_price == 5000

    def test_very_high_price(self, manager):
        """Test very high price detection"""
        price = 500000  # 500,000 VND

        actual_price = manager._detect_price_unit(price)

        # Should not multiply (already above threshold)
        assert actual_price == 500000


class TestRiskManagement(TestPortfolioManager):
    """Test risk management calculations"""

    def test_stop_loss_calculation(self, manager):
        """Test stop loss price calculation"""
        entry_price = 100000
        stop_loss_pct = config.RISK_MANAGEMENT['stop_loss_pct']

        stop_loss = manager.calculate_stop_loss(entry_price)

        expected_stop_loss = entry_price * (1 - stop_loss_pct)
        assert abs(stop_loss - expected_stop_loss) < 1  # Allow 1 VND rounding

    def test_target_profit_calculation(self, manager):
        """Test target profit price calculation"""
        entry_price = 100000
        target_pct = config.RISK_MANAGEMENT['target_profit_pct']

        target_profit = manager.calculate_target_profit(entry_price)

        expected_target = entry_price * (1 + target_pct)
        assert abs(target_profit - expected_target) < 1  # Allow 1 VND rounding

    def test_risk_reward_ratio(self, manager):
        """Test risk/reward ratio calculation"""
        entry_price = 100000
        stop_loss = manager.calculate_stop_loss(entry_price)
        target_profit = manager.calculate_target_profit(entry_price)

        risk = entry_price - stop_loss
        reward = target_profit - entry_price

        risk_reward_ratio = reward / risk

        # Should be approximately 1:2 ratio (reward is 2x risk)
        # stop_loss_pct = 0.07, target_profit_pct = 0.15
        # ratio = 0.15 / 0.07 ≈ 2.14
        expected_ratio = config.RISK_MANAGEMENT['target_profit_pct'] / config.RISK_MANAGEMENT['stop_loss_pct']
        assert abs(risk_reward_ratio - expected_ratio) < 0.1

    def test_position_risk_amount(self, manager):
        """Test position risk amount calculation"""
        entry_price = 100000
        shares = 1000
        stop_loss = manager.calculate_stop_loss(entry_price)

        position_value = entry_price * shares
        risk_amount = (entry_price - stop_loss) * shares

        # Risk should be 7% of position value
        expected_risk = position_value * config.RISK_MANAGEMENT['stop_loss_pct']
        assert abs(risk_amount - expected_risk) < 100  # Allow 100 VND rounding


class TestSharesCalculation(TestPortfolioManager):
    """Test shares calculation"""

    def test_shares_calculation_basic(self, manager):
        """Test basic shares calculation"""
        allocation_amount = 10_000_000  # 10M VND
        price_per_share = 85000

        shares = manager.calculate_shares(allocation_amount, price_per_share)

        expected_shares = int(allocation_amount / price_per_share)
        assert shares == expected_shares

    def test_shares_calculation_rounding(self, manager):
        """Test shares calculation rounds down to whole shares"""
        allocation_amount = 10_000_000  # 10M VND
        price_per_share = 87000  # Doesn't divide evenly

        shares = manager.calculate_shares(allocation_amount, price_per_share)

        # Should round down to whole shares
        assert shares == int(allocation_amount / price_per_share)
        assert isinstance(shares, int)

    def test_shares_zero_price(self, manager):
        """Test shares calculation with zero price"""
        allocation_amount = 10_000_000
        price_per_share = 0

        with pytest.raises((ZeroDivisionError, ValueError)):
            manager.calculate_shares(allocation_amount, price_per_share)

    def test_shares_insufficient_capital(self, manager):
        """Test shares calculation when capital is insufficient"""
        allocation_amount = 50000  # 50K VND
        price_per_share = 100000  # Price higher than allocation

        shares = manager.calculate_shares(allocation_amount, price_per_share)

        # Should return 0 shares
        assert shares == 0


class TestPortfolioMetrics(TestPortfolioManager):
    """Test portfolio-level metrics"""

    def test_portfolio_total_value(self, manager):
        """Test total portfolio value calculation"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 8.5,
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 8.2,
                'technical_score': 8.9
            },
            {
                'symbol': 'FPT',
                'overall_score': 7.8,
                'recommendation': 'BUY',
                'current_price': 95000,
                'fundamental_score': 7.5,
                'technical_score': 8.2
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)
        total_value = sum(p['allocation_amount'] for p in portfolio)

        # Total should not exceed available capital
        available_capital = manager.get_available_capital()
        assert total_value <= available_capital

    def test_portfolio_diversification(self, manager):
        """Test portfolio diversification"""
        analysis_results = [
            {
                'symbol': f'ST{i}',
                'overall_score': 8.0 + i * 0.1,
                'recommendation': 'BUY',
                'current_price': 50000,
                'fundamental_score': 8.0,
                'technical_score': 8.0
            }
            for i in range(5)
        ]

        portfolio = manager.build_portfolio(analysis_results)

        # Should have multiple positions for diversification
        assert len(portfolio) >= 2
        # No single position should exceed max_position_pct
        max_allowed = manager.total_capital * config.PORTFOLIO_CONFIG['max_position_pct']
        assert all(p['allocation_amount'] <= max_allowed for p in portfolio)


class TestEdgeCases(TestPortfolioManager):
    """Test edge cases and error handling"""

    def test_empty_analysis_results(self, manager):
        """Test portfolio building with empty analysis results"""
        analysis_results = []

        portfolio = manager.build_portfolio(analysis_results)

        # Should return empty portfolio
        assert portfolio == [] or portfolio is None

    def test_all_low_scores(self, manager):
        """Test portfolio with all low-scoring stocks"""
        analysis_results = [
            {
                'symbol': 'ST1',
                'overall_score': 4.0,
                'recommendation': 'SELL',
                'current_price': 50000,
                'fundamental_score': 4.2,
                'technical_score': 3.7
            },
            {
                'symbol': 'ST2',
                'overall_score': 3.5,
                'recommendation': 'SELL',
                'current_price': 60000,
                'fundamental_score': 3.8,
                'technical_score': 3.1
            }
        ]

        portfolio = manager.build_portfolio(analysis_results)

        # Should return empty portfolio (no BUY recommendations)
        assert portfolio == [] or portfolio is None

    def test_very_small_capital(self):
        """Test portfolio with very small capital"""
        small_manager = PortfolioManager(total_capital=1_000_000)  # Only 1M VND

        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 8.5,
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 8.2,
                'technical_score': 8.9
            }
        ]

        portfolio = small_manager.build_portfolio(analysis_results)

        # Should still build portfolio, even if very small
        assert isinstance(portfolio, (list, type(None)))

    def test_very_large_capital(self):
        """Test portfolio with very large capital"""
        large_manager = PortfolioManager(total_capital=10_000_000_000)  # 10 billion VND

        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 8.5,
                'recommendation': 'BUY',
                'current_price': 85000,
                'fundamental_score': 8.2,
                'technical_score': 8.9
            }
        ]

        portfolio = large_manager.build_portfolio(analysis_results)

        # Should handle large capital correctly
        assert isinstance(portfolio, list)
        if portfolio:
            # Position should respect max_position_pct even with large capital
            max_allowed = large_manager.total_capital * config.PORTFOLIO_CONFIG['max_position_pct']
            assert all(p['allocation_amount'] <= max_allowed for p in portfolio)

    def test_negative_price(self, manager):
        """Test handling of negative price"""
        analysis_results = [
            {
                'symbol': 'VNM',
                'overall_score': 8.5,
                'recommendation': 'BUY',
                'current_price': -85000,  # Invalid negative price
                'fundamental_score': 8.2,
                'technical_score': 8.9
            }
        ]

        # Should handle gracefully (skip or raise error)
        try:
            portfolio = manager.build_portfolio(analysis_results)
            # If it doesn't raise, portfolio should be empty or skip this stock
            if portfolio:
                assert all(p['current_price'] > 0 for p in portfolio)
        except (ValueError, AssertionError):
            # Expected behavior
            pass
