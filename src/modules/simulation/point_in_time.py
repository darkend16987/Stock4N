"""
Lớp dữ liệu point-in-time cho backtest: tại ngày t chỉ trả về thông tin đã biết đến hết phiên t.

Các điểm chống nhìn trước (look-ahead):
  - history()/returns(): chỉ lấy các phiên <= as_of
  - market_filter(): breadth tính từ SMA nhân quả (SMA tại t chỉ dùng dữ liệu <= t)
  - báo cáo tài chính: xem FinancialCalculator.calculate_metrics(as_of=...) + config.REPORTING_LAG_DAYS
Hạn chế KHÔNG thể khắc phục từ dữ liệu hiện có: universe là danh sách VN100 hiện tại (thiên lệch sống sót).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.analysis.breadth_analyzer import MarketBreadthAnalyzer
from modules.utils.logger import get_logger

logger = get_logger(__name__)

PRICE_COLS = ['open', 'high', 'low', 'close']


class PriceBook:
    """Giá ngày của universe, chuẩn hoá về VND, index theo ngày (đã bỏ giờ)."""

    MIN_BREADTH_ROWS = 25   # khớp MarketBreadthAnalyzer: len(df) >= max(periods) + 5

    def __init__(self, raw_dir, symbols):
        self.raw_dir = raw_dir
        self.bars = {}
        for symbol in symbols:
            df = self._load(symbol)
            if df is not None:
                self.bars[symbol] = df
        self.symbols = sorted(self.bars)
        if not self.symbols:
            raise ValueError(f"Không có dữ liệu giá nào trong {raw_dir}")
        self.calendar = sorted(set().union(*[set(b.index) for b in self.bars.values()]))
        self._above_both = None

    def _load(self, symbol):
        path = os.path.join(self.raw_dir, f"{symbol}_price.csv")
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        required = {'time', 'open', 'high', 'low', 'close', 'volume'}
        if not required.issubset(df.columns):
            logger.warning(f"{symbol}: thiếu cột {sorted(required - set(df.columns))} → bỏ qua")
            return None
        df['time'] = pd.to_datetime(df['time']).dt.normalize()
        df = df.drop_duplicates('time', keep='last').sort_values('time').set_index('time')
        df = df.dropna(subset=['close'])
        if df.empty:
            return None
        # Đơn vị: vnstock trả nghìn đồng. Quyết định theo TRUNG VỊ cả chuỗi (không theo từng giá trị)
        if df['close'].median() < config.PRICE_UNIT_CONFIG['threshold']:
            for col in PRICE_COLS:
                df[col] = df[col] * config.PRICE_UNIT_CONFIG['multiplier']
        df['volume'] = df['volume'].fillna(0)
        return df[PRICE_COLS + ['volume']]

    # ---- truy vấn point-in-time -------------------------------------------------
    def history(self, symbol, as_of):
        """Các phiên <= as_of, kèm cột 'time' (định dạng StockScorer cần). None nếu chưa có dữ liệu."""
        bars = self.bars.get(symbol)
        if bars is None:
            return None
        sliced = bars.loc[:pd.Timestamp(as_of)]
        if sliced.empty:
            return None
        return sliced.reset_index()

    def bar(self, symbol, date):
        bars = self.bars.get(symbol)
        if bars is None:
            return None
        ts = pd.Timestamp(date)
        return bars.loc[ts] if ts in bars.index else None

    def prev_close(self, symbol, date):
        """Đóng cửa của phiên giao dịch gần nhất TRƯỚC `date` (giá tham chiếu)."""
        bars = self.bars.get(symbol)
        if bars is None:
            return None
        before = bars.loc[:pd.Timestamp(date) - pd.Timedelta(days=1), 'close']
        return float(before.iloc[-1]) if not before.empty else None

    def last_close(self, symbol, as_of):
        """Đóng cửa gần nhất <= as_of (định giá vị thế kể cả khi mã không có phiên hôm nay)."""
        bars = self.bars.get(symbol)
        if bars is None:
            return None
        sliced = bars.loc[:pd.Timestamp(as_of), 'close']
        return float(sliced.iloc[-1]) if not sliced.empty else None

    def returns(self, symbol, as_of, lookback):
        bars = self.bars.get(symbol)
        if bars is None:
            return None
        closes = bars.loc[:pd.Timestamp(as_of), 'close']
        return closes.pct_change().dropna().tail(lookback)

    # ---- breadth point-in-time --------------------------------------------------
    def _build_above_both(self, periods=(10, 20)):
        flags = {}
        for symbol, bars in self.bars.items():
            close = bars['close']
            ok = pd.Series(True, index=close.index)
            for p in periods:
                ok &= close > close.rolling(p).mean()
            valid = pd.Series(np.arange(len(close)) + 1 >= self.MIN_BREADTH_ROWS, index=close.index)
            # NaN nếu chưa đủ dữ liệu; ffill giới hạn 5 phiên cho mã nghỉ giao dịch ngắn
            flags[symbol] = ok.astype(float).where(valid)
        return pd.DataFrame(flags).reindex(self.calendar).ffill(limit=5)

    def market_filter(self, as_of):
        """Market filter tại as_of, cùng quy tắc với MarketBreadthAnalyzer.get_market_filter."""
        if self._above_both is None:
            self._above_both = self._build_above_both()
        upto = self._above_both.loc[:pd.Timestamp(as_of)]
        if upto.empty:
            return None
        row = upto.iloc[-1]
        valid = int(row.notna().sum())
        if valid == 0:
            return None
        analyzer = MarketBreadthAnalyzer(data_dir=self.raw_dir)
        pct = float(row.sum() / valid)
        sentiment, signal, strength = analyzer._classify(pct)
        breadth = {
            'sentiment': sentiment, 'signal': signal, 'signal_strength': strength,
            'pct_above_both': round(pct, 4), 'pct_above_sma10': 0, 'pct_above_sma20': 0,
            'above_both': int(row.sum()), 'valid_symbols': valid,
        }
        return analyzer.build_market_filter(breadth)

    # ---- benchmark --------------------------------------------------------------
    def benchmark(self):
        """
        Trả về (Series chỉ số theo ngày, nhãn).
        Ưu tiên VNINDEX_price.csv trong thư mục dữ liệu; nếu không có dùng chỉ số cân bằng của universe
        (trung bình lợi suất ngày) - yếu hơn VN-Index và cũng bị thiên lệch sống sót.
        """
        path = os.path.join(self.raw_dir, 'VNINDEX_price.csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['time'] = pd.to_datetime(df['time']).dt.normalize()
            s = df.drop_duplicates('time', keep='last').sort_values('time').set_index('time')['close']
            return s.reindex(self.calendar).ffill().dropna(), 'VNINDEX'
        closes = pd.DataFrame({s: b['close'] for s, b in self.bars.items()}).reindex(self.calendar)
        daily = closes.pct_change(fill_method=None).mean(axis=1).fillna(0.0)
        return (1 + daily).cumprod(), 'EW_UNIVERSE'
