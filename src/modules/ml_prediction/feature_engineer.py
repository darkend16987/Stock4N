"""
Feature Engineer - Tạo features cho ML models
Tự động tạo technical indicators và derived features
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """
    Tạo features từ raw price data cho ML models
    """

    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir
        self.feature_names = []

    def load_price_data(self, symbol):
        """Load dữ liệu giá của 1 symbol"""
        try:
            price_file = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if not os.path.exists(price_file):
                return None

            df = pd.read_csv(price_file)
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time').reset_index(drop=True)

            return df
        except Exception as e:
            logger.error(f"Error loading price for {symbol}: {e}")
            return None

    def create_technical_features(self, df):
        """
        Tạo technical indicators làm features

        Features:
        - Price-based: Returns, Volatility
        - Moving Averages: SMA5, SMA10, SMA20, SMA50
        - Momentum: RSI, MACD
        - Volume: Volume change, Volume MA
        """
        df = df.copy()

        # Price returns
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        df['return_20d'] = df['close'].pct_change(20)

        # Volatility
        df['volatility_5d'] = df['return_1d'].rolling(5).std()
        df['volatility_20d'] = df['return_1d'].rolling(20).std()

        # Moving Averages
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()

        # Price vs MA
        df['price_vs_sma5'] = (df['close'] - df['sma_5']) / df['sma_5']
        df['price_vs_sma20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']

        # MA crossovers
        df['sma5_vs_sma20'] = (df['sma_5'] - df['sma_20']) / df['sma_20']
        df['sma20_vs_sma50'] = (df['sma_20'] - df['sma_50']) / df['sma_50']

        # RSI
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)

        # MACD
        df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
        df['macd_diff'] = df['macd'] - df['macd_signal']

        # Volume
        df['volume_change'] = df['volume'].pct_change(1)
        df['volume_ma_5'] = df['volume'].rolling(5).mean()
        df['volume_vs_ma'] = (df['volume'] - df['volume_ma_5']) / df['volume_ma_5']

        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / df['close']

        # Price momentum
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        df['momentum_20'] = df['close'] - df['close'].shift(20)

        return df

    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()

        return macd, macd_signal

    def create_lag_features(self, df, columns, lags=[1, 2, 3, 5]):
        """
        Tạo lag features (giá trị quá khứ)

        Args:
            columns: Columns to create lags for
            lags: List of lag periods
        """
        df = df.copy()

        for col in columns:
            if col in df.columns:
                for lag in lags:
                    df[f"{col}_lag{lag}"] = df[col].shift(lag)

        return df

    def create_rolling_features(self, df, columns, windows=[5, 10, 20]):
        """
        Tạo rolling statistics (mean, std, min, max)

        Args:
            columns: Columns to create rolling stats for
            windows: Window sizes
        """
        df = df.copy()

        for col in columns:
            if col in df.columns:
                for window in windows:
                    df[f"{col}_mean_{window}"] = df[col].rolling(window).mean()
                    df[f"{col}_std_{window}"] = df[col].rolling(window).std()
                    df[f"{col}_min_{window}"] = df[col].rolling(window).min()
                    df[f"{col}_max_{window}"] = df[col].rolling(window).max()

        return df

    def create_target_variable(self, df, horizon=5, threshold=0.02):
        """
        Tạo target variable cho classification

        Args:
            horizon: Số ngày nhìn về tương lai
            threshold: Ngưỡng để phân loại (2% = 0.02)

        Returns:
            df with 'target' column:
                1 = UP (tăng > threshold)
                0 = NEUTRAL (|change| <= threshold)
                -1 = DOWN (giảm > threshold)
        """
        df = df.copy()

        # Future return
        df['future_return'] = df['close'].shift(-horizon).pct_change(horizon)

        # Classify
        df['target'] = 0  # neutral
        df.loc[df['future_return'] > threshold, 'target'] = 1  # up
        df.loc[df['future_return'] < -threshold, 'target'] = -1  # down

        return df

    def prepare_ml_dataset(self, symbol, horizon=5, threshold=0.02):
        """
        Tạo dataset hoàn chỉnh cho ML

        Returns:
            df: DataFrame with features and target
        """
        logger.info(f"Preparing ML dataset for {symbol}...")

        # Load data
        df = self.load_price_data(symbol)
        if df is None or df.empty:
            logger.error(f"No data for {symbol}")
            return None

        # Create technical features
        df = self.create_technical_features(df)

        # Create lag features for key indicators
        lag_cols = ['return_1d', 'rsi_14', 'macd_diff', 'volume_change']
        df = self.create_lag_features(df, lag_cols, lags=[1, 2, 3, 5])

        # Create rolling features
        rolling_cols = ['return_1d', 'volume']
        df = self.create_rolling_features(df, rolling_cols, windows=[5, 10, 20])

        # Create target
        df = self.create_target_variable(df, horizon=horizon, threshold=threshold)

        # Drop NaN rows
        df = df.dropna()

        # Store feature names (exclude target and metadata)
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'volume',
                       'future_return', 'target']
        self.feature_names = [col for col in df.columns if col not in exclude_cols]

        logger.info(f"{symbol}: {len(df)} samples, {len(self.feature_names)} features")

        return df

    def get_feature_names(self):
        """Return list of feature names"""
        return self.feature_names

    def prepare_batch_datasets(self, symbols, horizon=5, threshold=0.02):
        """
        Tạo datasets cho nhiều symbols

        Returns:
            dict: {symbol: dataframe}
        """
        logger.info(f"Preparing datasets for {len(symbols)} symbols...")

        datasets = {}

        for symbol in symbols:
            try:
                df = self.prepare_ml_dataset(symbol, horizon, threshold)
                if df is not None and not df.empty:
                    datasets[symbol] = df
                    logger.info(f"✓ {symbol}: {len(df)} samples")
            except Exception as e:
                logger.error(f"Error preparing {symbol}: {e}")

        logger.info(f"Prepared {len(datasets)} datasets")
        return datasets

    def get_latest_features(self, symbol):
        """
        Lấy features mới nhất (để predict realtime)

        Returns:
            Series: Latest feature values
        """
        df = self.prepare_ml_dataset(symbol)
        if df is None or df.empty:
            return None

        # Get last row's features
        latest_features = df[self.feature_names].iloc[-1]

        return latest_features
