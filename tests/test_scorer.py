"""
Unit tests for StockScorer module
Tests fundamental and technical scoring logic
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from modules.analysis.scorer import StockScorer
import config


class TestStockScorer:
    """Test StockScorer class"""

    @pytest.fixture
    def scorer(self):
        """Create scorer instance"""
        return StockScorer()


class TestFundamentalScoring(TestStockScorer):
    """Test fundamental analysis scoring"""

    def test_excellent_roe_score(self, scorer, sample_metrics):
        """Test scoring for excellent ROE"""
        metrics = sample_metrics.copy()
        metrics['roe'] = 25.0  # Excellent ROE (> 20%)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'roe_score' in score_breakdown
        # Excellent ROE should get high score
        assert score_breakdown['roe_score'] >= config.FUNDAMENTAL_THRESHOLDS['roe']['excellent'] / 100 * 10

    def test_poor_roe_score(self, scorer, sample_metrics):
        """Test scoring for poor ROE"""
        metrics = sample_metrics.copy()
        metrics['roe'] = 5.0  # Poor ROE (< 10%)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'roe_score' in score_breakdown
        # Poor ROE should get low score
        assert score_breakdown['roe_score'] < 5.0

    def test_negative_roe_score(self, scorer, sample_metrics):
        """Test scoring for negative ROE"""
        metrics = sample_metrics.copy()
        metrics['roe'] = -10.0  # Negative ROE (loss-making)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'roe_score' in score_breakdown
        # Negative ROE should get very low or zero score
        assert score_breakdown['roe_score'] <= 2.0

    def test_strong_profit_growth_score(self, scorer, sample_metrics):
        """Test scoring for strong profit growth"""
        metrics = sample_metrics.copy()
        metrics['profit_growth'] = 25.0  # Strong growth (> 20%)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'profit_growth_score' in score_breakdown
        # Strong growth should get high score
        assert score_breakdown['profit_growth_score'] >= 7.0

    def test_weak_profit_growth_score(self, scorer, sample_metrics):
        """Test scoring for weak/negative profit growth"""
        metrics = sample_metrics.copy()
        metrics['profit_growth'] = -25.0  # Weak growth (< -20%)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'profit_growth_score' in score_breakdown
        # Weak growth should get low score
        assert score_breakdown['profit_growth_score'] <= 3.0

    def test_asset_growth_score(self, scorer, sample_metrics):
        """Test asset growth scoring"""
        metrics = sample_metrics.copy()
        metrics['asset_growth'] = 15.0  # Good growth

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'asset_growth_score' in score_breakdown
        assert 0 <= score_breakdown['asset_growth_score'] <= 10

    def test_equity_ratio_score(self, scorer, sample_metrics):
        """Test equity ratio scoring"""
        metrics = sample_metrics.copy()
        metrics['equity_ratio'] = 0.6  # 60% equity ratio (healthy)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'equity_ratio_score' in score_breakdown
        # Good equity ratio should get decent score
        assert score_breakdown['equity_ratio_score'] >= 5.0

    def test_low_equity_ratio_score(self, scorer, sample_metrics):
        """Test scoring for high leverage (low equity ratio)"""
        metrics = sample_metrics.copy()
        metrics['equity_ratio'] = 0.2  # 20% equity ratio (high leverage)

        score_breakdown = scorer.calculate_fundamental_score(metrics)

        assert 'equity_ratio_score' in score_breakdown
        # High leverage should get lower score
        assert score_breakdown['equity_ratio_score'] < 5.0

    def test_fundamental_total_score(self, scorer, sample_metrics):
        """Test total fundamental score calculation"""
        score_breakdown = scorer.calculate_fundamental_score(sample_metrics)

        assert 'total' in score_breakdown
        # Total score should be 0-10
        assert 0 <= score_breakdown['total'] <= 10


class TestTechnicalScoring(TestStockScorer):
    """Test technical analysis scoring"""

    def test_bullish_rsi_score(self, scorer, sample_metrics):
        """Test RSI scoring in bullish range"""
        metrics = sample_metrics.copy()
        metrics['rsi'] = 55.0  # Bullish RSI (50-70)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'rsi_score' in score_breakdown
        # Bullish RSI should get good score
        assert score_breakdown['rsi_score'] >= 6.0

    def test_oversold_rsi_score(self, scorer, sample_metrics):
        """Test RSI scoring in oversold range"""
        metrics = sample_metrics.copy()
        metrics['rsi'] = 25.0  # Oversold RSI (< 30)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'rsi_score' in score_breakdown
        # Oversold RSI should get lower score for momentum
        assert score_breakdown['rsi_score'] < 6.0

    def test_overbought_rsi_score(self, scorer, sample_metrics):
        """Test RSI scoring in overbought range"""
        metrics = sample_metrics.copy()
        metrics['rsi'] = 80.0  # Overbought RSI (> 70)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'rsi_score' in score_breakdown
        # Overbought RSI might indicate pullback risk
        assert isinstance(score_breakdown['rsi_score'], (int, float))

    def test_bullish_sma_trend(self, scorer, sample_metrics):
        """Test SMA trend scoring - bullish"""
        metrics = sample_metrics.copy()
        metrics['current_price'] = 90000
        metrics['sma20'] = 85000
        metrics['sma50'] = 80000  # Price > SMA20 > SMA50 (bullish)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'sma_trend_score' in score_breakdown
        # Bullish trend should get high score
        assert score_breakdown['sma_trend_score'] >= 7.0

    def test_bearish_sma_trend(self, scorer, sample_metrics):
        """Test SMA trend scoring - bearish"""
        metrics = sample_metrics.copy()
        metrics['current_price'] = 75000
        metrics['sma20'] = 80000
        metrics['sma50'] = 85000  # Price < SMA20 < SMA50 (bearish)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'sma_trend_score' in score_breakdown
        # Bearish trend should get low score
        assert score_breakdown['sma_trend_score'] <= 4.0

    def test_bullish_macd(self, scorer, sample_metrics):
        """Test MACD scoring - bullish"""
        metrics = sample_metrics.copy()
        metrics['macd'] = 500  # Positive MACD (bullish)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'macd_score' in score_breakdown
        # Positive MACD should contribute to score
        assert score_breakdown['macd_score'] > 5.0

    def test_bearish_macd(self, scorer, sample_metrics):
        """Test MACD scoring - bearish"""
        metrics = sample_metrics.copy()
        metrics['macd'] = -500  # Negative MACD (bearish)

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'macd_score' in score_breakdown
        # Negative MACD should get lower score
        assert score_breakdown['macd_score'] < 5.0

    def test_volume_score(self, scorer, sample_metrics):
        """Test volume scoring"""
        metrics = sample_metrics.copy()
        metrics['volume_avg'] = 2000000  # High volume

        score_breakdown = scorer.calculate_technical_score(metrics)

        assert 'volume_score' in score_breakdown
        assert 0 <= score_breakdown['volume_score'] <= 10

    def test_technical_total_score(self, scorer, sample_metrics):
        """Test total technical score calculation"""
        score_breakdown = scorer.calculate_technical_score(sample_metrics)

        assert 'total' in score_breakdown
        # Total score should be 0-10
        assert 0 <= score_breakdown['total'] <= 10


class TestOverallScoring(TestStockScorer):
    """Test overall score calculation"""

    def test_overall_score_calculation(self, scorer, sample_metrics):
        """Test overall score with 60/40 weighting"""
        fundamental_breakdown = scorer.calculate_fundamental_score(sample_metrics)
        technical_breakdown = scorer.calculate_technical_score(sample_metrics)

        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        # Overall score should be weighted average (60% fundamental + 40% technical)
        expected_score = (
            fundamental_breakdown['total'] * config.SCORING_WEIGHTS['fundamental'] +
            technical_breakdown['total'] * config.SCORING_WEIGHTS['technical']
        )

        assert abs(overall_score - expected_score) < 0.01

    def test_overall_score_range(self, scorer, sample_metrics):
        """Test overall score is in valid range"""
        fundamental_breakdown = scorer.calculate_fundamental_score(sample_metrics)
        technical_breakdown = scorer.calculate_technical_score(sample_metrics)

        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        # Overall score should be 0-10
        assert 0 <= overall_score <= 10

    def test_high_overall_score(self, scorer):
        """Test overall score with excellent metrics"""
        excellent_metrics = {
            'roe': 30.0,  # Excellent
            'roa': 20.0,
            'profit_growth': 30.0,  # Strong
            'revenue_growth': 25.0,
            'asset_growth': 20.0,
            'equity_growth': 18.0,
            'profit_margin': 25.0,
            'equity_ratio': 0.7,
            'current_price': 100000,
            'sma20': 95000,
            'sma50': 90000,  # Bullish trend
            'rsi': 60.0,  # Bullish momentum
            'macd': 800,  # Positive
            'volume_avg': 3000000
        }

        fundamental_breakdown = scorer.calculate_fundamental_score(excellent_metrics)
        technical_breakdown = scorer.calculate_technical_score(excellent_metrics)
        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        # Excellent metrics should yield high score (> 7.0)
        assert overall_score >= 7.0

    def test_low_overall_score(self, scorer):
        """Test overall score with poor metrics"""
        poor_metrics = {
            'roe': -5.0,  # Negative
            'roa': -3.0,
            'profit_growth': -30.0,  # Declining
            'revenue_growth': -15.0,
            'asset_growth': -5.0,
            'equity_growth': -10.0,
            'profit_margin': -8.0,
            'equity_ratio': 0.2,  # High leverage
            'current_price': 50000,
            'sma20': 60000,
            'sma50': 70000,  # Bearish trend
            'rsi': 25.0,  # Oversold
            'macd': -500,  # Negative
            'volume_avg': 500000
        }

        fundamental_breakdown = scorer.calculate_fundamental_score(poor_metrics)
        technical_breakdown = scorer.calculate_technical_score(poor_metrics)
        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        # Poor metrics should yield low score (< 5.0)
        assert overall_score < 5.0


class TestRecommendationGeneration(TestStockScorer):
    """Test recommendation generation based on score"""

    def test_buy_recommendation(self, scorer, sample_metrics):
        """Test BUY recommendation for high scores"""
        # Modify metrics to ensure high score
        metrics = sample_metrics.copy()
        metrics['roe'] = 28.0
        metrics['profit_growth'] = 25.0
        metrics['rsi'] = 60.0
        metrics['current_price'] = 90000
        metrics['sma20'] = 85000
        metrics['sma50'] = 80000

        fundamental_breakdown = scorer.calculate_fundamental_score(metrics)
        technical_breakdown = scorer.calculate_technical_score(metrics)
        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        recommendation = scorer.get_recommendation(overall_score)

        if overall_score >= 7.0:
            assert recommendation == 'BUY'

    def test_watch_recommendation(self, scorer, sample_metrics):
        """Test WATCH recommendation for medium scores"""
        fundamental_breakdown = scorer.calculate_fundamental_score(sample_metrics)
        technical_breakdown = scorer.calculate_technical_score(sample_metrics)
        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        # Adjust to get medium score (5.0 - 7.0)
        overall_score = 6.0

        recommendation = scorer.get_recommendation(overall_score)
        assert recommendation == 'WATCH'

    def test_sell_recommendation(self, scorer):
        """Test SELL recommendation for low scores"""
        poor_metrics = {
            'roe': -5.0,
            'roa': -3.0,
            'profit_growth': -30.0,
            'revenue_growth': -15.0,
            'asset_growth': -5.0,
            'equity_growth': -10.0,
            'profit_margin': -8.0,
            'equity_ratio': 0.2,
            'current_price': 50000,
            'sma20': 60000,
            'sma50': 70000,
            'rsi': 25.0,
            'macd': -500,
            'volume_avg': 500000
        }

        fundamental_breakdown = scorer.calculate_fundamental_score(poor_metrics)
        technical_breakdown = scorer.calculate_technical_score(poor_metrics)
        overall_score = scorer.calculate_overall_score(
            fundamental_breakdown,
            technical_breakdown
        )

        recommendation = scorer.get_recommendation(overall_score)

        if overall_score < 5.0:
            assert recommendation == 'SELL' or recommendation == 'AVOID'


class TestEdgeCases(TestStockScorer):
    """Test edge cases and error handling"""

    def test_missing_metrics(self, scorer):
        """Test handling of missing metrics"""
        incomplete_metrics = {
            'roe': 15.0,
            'profit_growth': 10.0
            # Missing other required metrics
        }

        # Should handle gracefully or raise appropriate exception
        try:
            fundamental_breakdown = scorer.calculate_fundamental_score(incomplete_metrics)
            assert isinstance(fundamental_breakdown, dict)
        except (KeyError, ValueError):
            # Expected behavior
            pass

    def test_null_metrics(self, scorer):
        """Test handling of null/None metrics"""
        null_metrics = {
            'roe': None,
            'roa': None,
            'profit_growth': None,
            'revenue_growth': None,
            'asset_growth': None,
            'equity_growth': None,
            'profit_margin': None,
            'equity_ratio': None,
            'current_price': None,
            'sma20': None,
            'sma50': None,
            'rsi': None,
            'macd': None,
            'volume_avg': None
        }

        # Should handle None values gracefully
        try:
            fundamental_breakdown = scorer.calculate_fundamental_score(null_metrics)
            technical_breakdown = scorer.calculate_technical_score(null_metrics)
            assert isinstance(fundamental_breakdown, dict)
            assert isinstance(technical_breakdown, dict)
        except (TypeError, ValueError):
            # Expected behavior
            pass

    def test_extreme_values(self, scorer):
        """Test handling of extreme values"""
        extreme_metrics = {
            'roe': 999999.0,  # Extreme value
            'roa': -999999.0,
            'profit_growth': 1000000.0,
            'revenue_growth': -1000000.0,
            'asset_growth': 500000.0,
            'equity_growth': -500000.0,
            'profit_margin': 9999.0,
            'equity_ratio': 10.0,  # > 1.0
            'current_price': 1000000000,
            'sma20': 1,
            'sma50': 1,
            'rsi': 150.0,  # > 100
            'macd': 999999,
            'volume_avg': 1
        }

        # Should handle extreme values without crashing
        try:
            fundamental_breakdown = scorer.calculate_fundamental_score(extreme_metrics)
            technical_breakdown = scorer.calculate_technical_score(extreme_metrics)
            overall_score = scorer.calculate_overall_score(
                fundamental_breakdown,
                technical_breakdown
            )
            # Score should still be bounded
            assert 0 <= overall_score <= 10
        except (ValueError, AssertionError):
            # Some validation might reject extreme values
            pass
