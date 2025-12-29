"""
Backtest Performance Metrics Module
Tính toán các chỉ số hiệu suất của portfolio/strategy
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class PerformanceMetrics:
    """Calculate portfolio performance metrics"""

    def __init__(self, trades_df, initial_capital=100_000_000):
        """
        Args:
            trades_df: DataFrame with columns [date, symbol, action, price, shares, pnl]
            initial_capital: Vốn ban đầu (VND)
        """
        self.trades = trades_df
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

    def calculate_returns(self):
        """Tính lợi nhuận theo thời gian"""
        if self.trades.empty:
            return pd.DataFrame()

        # Cumulative P&L
        self.trades['cumulative_pnl'] = self.trades['pnl'].cumsum()
        self.trades['portfolio_value'] = self.initial_capital + self.trades['cumulative_pnl']
        self.trades['return_pct'] = (self.trades['cumulative_pnl'] / self.initial_capital) * 100

        return self.trades

    def total_return(self):
        """Tổng lợi nhuận %"""
        if self.trades.empty:
            return 0

        total_pnl = self.trades['pnl'].sum()
        return (total_pnl / self.initial_capital) * 100

    def sharpe_ratio(self, risk_free_rate=0.05):
        """
        Sharpe Ratio (Risk-adjusted return)
        Công thức: (Return - Risk-free) / Volatility
        """
        if self.trades.empty or len(self.trades) < 2:
            return 0

        # Calculate daily returns
        self.calculate_returns()
        daily_returns = self.trades.set_index('date')['return_pct'].pct_change().dropna()

        if len(daily_returns) == 0:
            return 0

        # Annualized
        excess_return = daily_returns.mean() * 252 - risk_free_rate
        volatility = daily_returns.std() * np.sqrt(252)

        if volatility == 0:
            return 0

        return excess_return / volatility

    def max_drawdown(self):
        """
        Max Drawdown (%) - Sụt giảm lớn nhất từ đỉnh
        """
        if self.trades.empty:
            return 0

        self.calculate_returns()
        portfolio_values = self.trades['portfolio_value'].values

        # Calculate running maximum
        running_max = np.maximum.accumulate(portfolio_values)

        # Calculate drawdown at each point
        drawdown = (portfolio_values - running_max) / running_max * 100

        return abs(drawdown.min())

    def win_rate(self):
        """Tỷ lệ giao dịch thắng (%)"""
        if self.trades.empty:
            return 0

        winning_trades = len(self.trades[self.trades['pnl'] > 0])
        total_trades = len(self.trades[self.trades['action'] == 'SELL'])

        if total_trades == 0:
            return 0

        return (winning_trades / total_trades) * 100

    def average_win_loss(self):
        """Lợi nhuận trung bình / Lỗ trung bình"""
        wins = self.trades[self.trades['pnl'] > 0]['pnl']
        losses = self.trades[self.trades['pnl'] < 0]['pnl']

        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0

        return avg_win, avg_loss

    def profit_factor(self):
        """
        Profit Factor = Total Win / Total Loss
        > 1 = Profitable
        """
        total_win = self.trades[self.trades['pnl'] > 0]['pnl'].sum()
        total_loss = abs(self.trades[self.trades['pnl'] < 0]['pnl'].sum())

        if total_loss == 0:
            return float('inf') if total_win > 0 else 0

        return total_win / total_loss

    def summary(self):
        """Tổng hợp tất cả metrics"""
        avg_win, avg_loss = self.average_win_loss()

        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital + self.trades['pnl'].sum(),
            'total_return_pct': self.total_return(),
            'total_pnl': self.trades['pnl'].sum(),
            'sharpe_ratio': self.sharpe_ratio(),
            'max_drawdown_pct': self.max_drawdown(),
            'win_rate_pct': self.win_rate(),
            'profit_factor': self.profit_factor(),
            'total_trades': len(self.trades[self.trades['action'] == 'SELL']),
            'winning_trades': len(self.trades[self.trades['pnl'] > 0]),
            'losing_trades': len(self.trades[self.trades['pnl'] < 0]),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
        }
