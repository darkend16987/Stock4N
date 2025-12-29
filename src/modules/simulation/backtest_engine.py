"""
Backtest Engine - Core backtesting logic
Mô phỏng giao dịch dựa trên chiến lược scoring
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """
    Engine để backtest chiến lược trading
    """

    def __init__(
        self,
        data_dir=config.RAW_DIR,
        initial_capital=100_000_000,
        max_positions=10,
        position_size_pct=0.10,
        stop_loss_pct=0.07,
        take_profit_pct=0.15
    ):
        self.data_dir = data_dir
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

        self.current_capital = initial_capital
        self.positions = {}  # {symbol: {'shares': X, 'entry_price': Y, 'entry_date': Z}}
        self.trades = []  # List of all trades

        logger.info(f"BacktestEngine initialized: Capital={initial_capital:,}, Max positions={max_positions}")

    def load_historical_scores(self, analysis_file):
        """Load analysis scores (từ file CSV đã phân tích)"""
        try:
            df = pd.read_csv(analysis_file)
            logger.info(f"Loaded {len(df)} stock scores from {analysis_file}")
            return df
        except Exception as e:
            logger.error(f"Error loading scores: {e}")
            return pd.DataFrame()

    def load_price_history(self, symbol, start_date, end_date):
        """Load giá lịch sử của 1 mã"""
        try:
            price_file = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if not os.path.exists(price_file):
                return None

            df = pd.read_csv(price_file)
            df['time'] = pd.to_datetime(df['time'])

            # Filter by date range
            mask = (df['time'] >= start_date) & (df['time'] <= end_date)
            df = df.loc[mask].copy()
            df = df.sort_values('time').reset_index(drop=True)

            return df
        except Exception as e:
            logger.error(f"Error loading price for {symbol}: {e}")
            return None

    def get_buy_signals(self, scores_df, min_score=6.0):
        """
        Lấy danh sách mã có tín hiệu MUA
        Điều kiện: Score >= min_score và Recommendation chứa "MUA"
        """
        buy_signals = scores_df[
            (scores_df['Total_Score'] >= min_score) &
            (scores_df['Recommendation'].str.contains('MUA', na=False))
        ].copy()

        buy_signals = buy_signals.sort_values('Total_Score', ascending=False)
        return buy_signals

    def should_sell(self, symbol, current_price, current_date):
        """
        Kiểm tra xem có nên bán không
        Điều kiện:
        - Stop loss: Giá giảm > 7%
        - Take profit: Giá tăng > 15%
        """
        if symbol not in self.positions:
            return False, None

        position = self.positions[symbol]
        entry_price = position['entry_price']

        # Calculate return
        price_change_pct = (current_price - entry_price) / entry_price

        # Stop loss
        if price_change_pct <= -self.stop_loss_pct:
            return True, 'STOP_LOSS'

        # Take profit
        if price_change_pct >= self.take_profit_pct:
            return True, 'TAKE_PROFIT'

        return False, None

    def execute_buy(self, symbol, price, date, score):
        """Thực hiện lệnh MUA"""
        # Check if already holding
        if symbol in self.positions:
            return False

        # Check max positions
        if len(self.positions) >= self.max_positions:
            return False

        # Calculate position size
        position_value = self.current_capital * self.position_size_pct
        shares = int(position_value / price / 100) * 100  # Round to lot size

        if shares == 0:
            return False

        cost = shares * price

        # Execute
        self.positions[symbol] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': date,
            'score': score
        }
        self.current_capital -= cost

        # Record trade
        self.trades.append({
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'price': price,
            'shares': shares,
            'cost': cost,
            'pnl': 0,
            'reason': f'Score={score:.1f}'
        })

        logger.info(f"BUY {symbol}: {shares} shares @ {price:,.0f} = {cost:,.0f} VND")
        return True

    def execute_sell(self, symbol, price, date, reason='MANUAL'):
        """Thực hiện lệnh BÁN"""
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]
        shares = position['shares']
        entry_price = position['entry_price']

        # Calculate P&L
        proceeds = shares * price
        cost = shares * entry_price
        pnl = proceeds - cost

        # Execute
        self.current_capital += proceeds
        del self.positions[symbol]

        # Record trade
        self.trades.append({
            'date': date,
            'symbol': symbol,
            'action': 'SELL',
            'price': price,
            'shares': shares,
            'proceeds': proceeds,
            'pnl': pnl,
            'reason': reason,
            'return_pct': (price - entry_price) / entry_price * 100
        })

        logger.info(f"SELL {symbol}: {shares} shares @ {price:,.0f} | P&L: {pnl:,.0f} ({reason})")
        return True

    def run_backtest(self, scores_df, start_date, end_date, min_score=6.0):
        """
        Chạy backtest chính

        Logic:
        1. Lấy buy signals từ scores
        2. Với mỗi mã, load giá lịch sử
        3. Simulate buy tại ngày phân tích
        4. Theo dõi giá mỗi ngày, check stop loss / take profit
        5. Bán khi trigger điều kiện
        """
        logger.info(f"Starting backtest: {start_date} to {end_date}")
        logger.info(f"Buy threshold: Score >= {min_score}")

        # Get buy candidates
        buy_signals = self.get_buy_signals(scores_df, min_score)
        logger.info(f"Found {len(buy_signals)} buy signals")

        if buy_signals.empty:
            logger.warning("No buy signals found!")
            return pd.DataFrame()

        # For each buy signal
        for idx, row in buy_signals.iterrows():
            symbol = row['Symbol']
            score = row['Total_Score']
            entry_price = row['Price']

            # Load price history
            price_df = self.load_price_history(symbol, start_date, end_date)
            if price_df is None or price_df.empty:
                logger.warning(f"No price data for {symbol}, skipping")
                continue

            # Buy at first available date
            first_date = price_df.iloc[0]['time']
            first_price = price_df.iloc[0]['close']

            buy_success = self.execute_buy(symbol, first_price, first_date, score)

            if not buy_success:
                continue

            # Monitor position daily
            for _, price_row in price_df.iterrows():
                current_date = price_row['time']
                current_price = price_row['close']

                # Check sell conditions
                should_sell_flag, reason = self.should_sell(symbol, current_price, current_date)

                if should_sell_flag:
                    self.execute_sell(symbol, current_price, current_date, reason)
                    break

        # Close remaining positions at end date
        if self.positions:
            logger.info(f"Closing {len(self.positions)} remaining positions at end date")
            for symbol in list(self.positions.keys()):
                price_df = self.load_price_history(symbol, start_date, end_date)
                if price_df is not None and not price_df.empty:
                    final_price = price_df.iloc[-1]['close']
                    final_date = price_df.iloc[-1]['time']
                    self.execute_sell(symbol, final_price, final_date, 'END_OF_PERIOD')

        # Convert trades to DataFrame
        trades_df = pd.DataFrame(self.trades)
        logger.info(f"Backtest completed: {len(trades_df)} total trades")

        return trades_df
