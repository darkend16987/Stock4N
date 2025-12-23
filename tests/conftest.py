"""
Pytest configuration and fixtures for Stock4N tests
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_price_data():
    """Sample price data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    data = {
        'time': dates,
        'open': np.random.uniform(20, 30, 100),
        'high': np.random.uniform(25, 35, 100),
        'low': np.random.uniform(15, 25, 100),
        'close': np.random.uniform(20, 30, 100),
        'volume': np.random.randint(1000000, 10000000, 100)
    }
    df = pd.DataFrame(data)
    # Ensure high >= close >= low and high >= open >= low
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    return df


@pytest.fixture
def sample_financial_data_balance():
    """Sample balance sheet data for testing"""
    current_year = datetime.now().year
    data = {
        'Năm': [current_year-1] * 4 + [current_year] * 4,
        'Kỳ': [1, 2, 3, 4, 1, 2, 3, 4],
        'Tổng tài sản': [1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350],
        'Nợ phải trả': [400, 420, 440, 460, 480, 500, 520, 540],
        'Vốn chủ sở hữu': [600, 630, 660, 690, 720, 750, 780, 810]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_financial_data_income():
    """Sample income statement data for testing"""
    current_year = datetime.now().year
    data = {
        'Năm': [current_year-1] * 4 + [current_year] * 4,
        'Kỳ': [1, 2, 3, 4, 1, 2, 3, 4],
        'Doanh thu thuần': [100, 110, 120, 130, 140, 150, 160, 170],
        'Lợi nhuận sau thuế': [10, 11, 12, 13, 14, 15, 16, 17]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_stock_symbol():
    """Sample stock symbol"""
    return "VNM"


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing"""
    return {
        'total_capital': 100_000_000,  # 100M VND
        'cash_reserve_pct': 0.20,
        'max_position_pct': 0.40,
        'positions': [
            {
                'symbol': 'VNM',
                'score': 8.5,
                'price': 85000,
                'recommendation': 'BUY'
            },
            {
                'symbol': 'FPT',
                'score': 7.8,
                'price': 95000,
                'recommendation': 'BUY'
            },
            {
                'symbol': 'VHM',
                'score': 6.2,
                'price': 45000,
                'recommendation': 'WATCH'
            }
        ]
    }


@pytest.fixture
def sample_metrics():
    """Sample calculated metrics for testing"""
    return {
        'roe': 18.5,
        'roa': 12.3,
        'profit_margin': 15.2,
        'asset_growth': 12.5,
        'equity_growth': 10.8,
        'profit_growth': 15.3,
        'revenue_growth': 14.2,
        'equity_ratio': 0.65,
        'current_price': 85000,
        'sma20': 82000,
        'sma50': 80000,
        'rsi': 58.5,
        'macd': 250,
        'volume_avg': 1500000
    }
