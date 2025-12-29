"""
Pattern Analyzer - Phát hiện patterns và seasonality
Tìm kiếm chu kỳ, xu hướng, và patterns lặp lại
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class PatternAnalyzer:
    """
    Phân tích patterns trong dữ liệu lịch sử
    """

    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir
        self.patterns = {}

    def load_price_history(self, symbol, days=730):
        """Load giá lịch sử của 1 mã"""
        try:
            price_file = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if not os.path.exists(price_file):
                return None

            df = pd.read_csv(price_file)
            df['time'] = pd.to_datetime(df['time'])

            # Get last N days
            cutoff = datetime.now() - timedelta(days=days)
            df = df[df['time'] >= cutoff].copy()
            df = df.sort_values('time').reset_index(drop=True)

            return df
        except Exception as e:
            logger.error(f"Error loading price for {symbol}: {e}")
            return None

    def detect_seasonality(self, symbol, lookback_days=730):
        """
        Phát hiện seasonality (chu kỳ theo tháng/quý)

        Returns:
            dict: {
                'monthly_returns': {1: avg_return, 2: avg_return, ...},
                'quarterly_returns': {1: avg_return, 2: avg_return, ...},
                'best_months': [int],
                'worst_months': [int],
                'best_quarter': int,
                'worst_quarter': int
            }
        """
        df = self.load_price_history(symbol, lookback_days)
        if df is None or df.empty:
            return None

        df['month'] = df['time'].dt.month
        df['quarter'] = df['time'].dt.quarter
        df['return'] = df['close'].pct_change()

        # Monthly returns
        monthly_returns = df.groupby('month')['return'].mean() * 100
        monthly_returns = monthly_returns.to_dict()

        # Quarterly returns
        quarterly_returns = df.groupby('quarter')['return'].mean() * 100
        quarterly_returns = quarterly_returns.to_dict()

        # Best/worst months
        sorted_months = sorted(monthly_returns.items(), key=lambda x: x[1], reverse=True)
        best_months = [m[0] for m in sorted_months[:3]]
        worst_months = [m[0] for m in sorted_months[-3:]]

        # Best/worst quarters
        sorted_quarters = sorted(quarterly_returns.items(), key=lambda x: x[1], reverse=True)
        best_quarter = sorted_quarters[0][0] if sorted_quarters else None
        worst_quarter = sorted_quarters[-1][0] if sorted_quarters else None

        result = {
            'symbol': symbol,
            'monthly_returns': monthly_returns,
            'quarterly_returns': quarterly_returns,
            'best_months': best_months,
            'worst_months': worst_months,
            'best_quarter': best_quarter,
            'worst_quarter': worst_quarter
        }

        logger.info(f"{symbol} seasonality: Best months={best_months}, Best Q={best_quarter}")
        return result

    def detect_price_momentum(self, symbol, periods=[5, 10, 20, 60]):
        """
        Phát hiện momentum (đà tăng/giảm) qua các khung thời gian

        Returns:
            dict: {5: momentum_5d, 10: momentum_10d, ...}
        """
        df = self.load_price_history(symbol, days=max(periods) + 30)
        if df is None or df.empty or len(df) < max(periods):
            return None

        momentum = {}
        current_price = df.iloc[-1]['close']

        for period in periods:
            if len(df) >= period:
                past_price = df.iloc[-period]['close']
                momentum_pct = (current_price - past_price) / past_price * 100
                momentum[period] = round(momentum_pct, 2)

        logger.info(f"{symbol} momentum: {momentum}")
        return momentum

    def detect_support_resistance(self, symbol, lookback_days=180, threshold=0.02):
        """
        Phát hiện support/resistance levels (mức hỗ trợ/kháng cự)

        Args:
            threshold: % tolerance để coi là cùng mức (mặc định 2%)

        Returns:
            dict: {
                'support_levels': [price1, price2, ...],
                'resistance_levels': [price1, price2, ...],
                'current_price': float,
                'nearest_support': float,
                'nearest_resistance': float
            }
        """
        df = self.load_price_history(symbol, lookback_days)
        if df is None or df.empty:
            return None

        # Find local minima (support) and maxima (resistance)
        df['is_support'] = (
            (df['low'] < df['low'].shift(1)) &
            (df['low'] < df['low'].shift(-1))
        )
        df['is_resistance'] = (
            (df['high'] > df['high'].shift(1)) &
            (df['high'] > df['high'].shift(-1))
        )

        supports = df[df['is_support']]['low'].values
        resistances = df[df['is_resistance']]['high'].values

        # Cluster similar levels
        support_levels = self._cluster_levels(supports, threshold)
        resistance_levels = self._cluster_levels(resistances, threshold)

        current_price = df.iloc[-1]['close']

        # Find nearest support/resistance
        supports_below = [s for s in support_levels if s < current_price]
        resistances_above = [r for r in resistance_levels if r > current_price]

        nearest_support = max(supports_below) if supports_below else None
        nearest_resistance = min(resistances_above) if resistances_above else None

        result = {
            'symbol': symbol,
            'support_levels': sorted(support_levels),
            'resistance_levels': sorted(resistance_levels),
            'current_price': current_price,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance
        }

        logger.info(f"{symbol} S/R: Support={nearest_support}, Resistance={nearest_resistance}")
        return result

    def _cluster_levels(self, levels, threshold=0.02):
        """
        Gom nhóm các mức giá gần nhau

        Args:
            levels: Array of price levels
            threshold: % tolerance (0.02 = 2%)

        Returns:
            list: Clustered levels (average of each cluster)
        """
        if len(levels) == 0:
            return []

        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            # If within threshold of cluster average
            cluster_avg = np.mean(current_cluster)
            if abs(level - cluster_avg) / cluster_avg <= threshold:
                current_cluster.append(level)
            else:
                # Start new cluster
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        # Add last cluster
        clusters.append(np.mean(current_cluster))

        return clusters

    def analyze_all_patterns(self, symbols):
        """
        Phân tích tất cả patterns cho danh sách symbols

        Returns:
            dict: {symbol: {seasonality, momentum, support_resistance}}
        """
        logger.info(f"Analyzing patterns for {len(symbols)} symbols...")

        results = {}

        for symbol in symbols:
            try:
                seasonality = self.detect_seasonality(symbol)
                momentum = self.detect_price_momentum(symbol)
                support_resistance = self.detect_support_resistance(symbol)

                results[symbol] = {
                    'seasonality': seasonality,
                    'momentum': momentum,
                    'support_resistance': support_resistance
                }

                logger.info(f"✓ {symbol} patterns analyzed")

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results[symbol] = None

        logger.info(f"Pattern analysis completed for {len(results)} symbols")
        return results

    def get_trading_signals(self, symbol):
        """
        Tạo tín hiệu trading dựa trên patterns

        Returns:
            dict: {
                'seasonality_signal': int (-1, 0, 1),
                'momentum_signal': int (-1, 0, 1),
                'support_resistance_signal': int (-1, 0, 1),
                'combined_signal': int (-1, 0, 1),
                'confidence': float (0-1)
            }
        """
        seasonality = self.detect_seasonality(symbol)
        momentum = self.detect_price_momentum(symbol)
        sr = self.detect_support_resistance(symbol)

        signals = []
        confidence_scores = []

        # Seasonality signal
        if seasonality:
            current_month = datetime.now().month
            if current_month in seasonality['best_months']:
                signals.append(1)
                confidence_scores.append(0.3)
            elif current_month in seasonality['worst_months']:
                signals.append(-1)
                confidence_scores.append(0.3)
            else:
                signals.append(0)
                confidence_scores.append(0.1)

        # Momentum signal
        if momentum:
            # Use 20-day momentum
            mom_20 = momentum.get(20, 0)
            if mom_20 > 5:
                signals.append(1)
                confidence_scores.append(0.4)
            elif mom_20 < -5:
                signals.append(-1)
                confidence_scores.append(0.4)
            else:
                signals.append(0)
                confidence_scores.append(0.2)

        # Support/Resistance signal
        if sr and sr['nearest_support'] and sr['nearest_resistance']:
            current_price = sr['current_price']
            support = sr['nearest_support']
            resistance = sr['nearest_resistance']

            # Distance to support/resistance
            dist_to_support = (current_price - support) / support
            dist_to_resistance = (resistance - current_price) / current_price

            if dist_to_support < 0.02:  # Near support (within 2%)
                signals.append(1)
                confidence_scores.append(0.3)
            elif dist_to_resistance < 0.02:  # Near resistance
                signals.append(-1)
                confidence_scores.append(0.3)
            else:
                signals.append(0)
                confidence_scores.append(0.1)

        # Combined signal
        if signals:
            combined_signal = 1 if sum(signals) > 0 else (-1 if sum(signals) < 0 else 0)
            confidence = sum(confidence_scores) / len(confidence_scores)
        else:
            combined_signal = 0
            confidence = 0

        result = {
            'symbol': symbol,
            'seasonality_signal': signals[0] if len(signals) > 0 else 0,
            'momentum_signal': signals[1] if len(signals) > 1 else 0,
            'support_resistance_signal': signals[2] if len(signals) > 2 else 0,
            'combined_signal': combined_signal,
            'confidence': round(confidence, 2)
        }

        return result
