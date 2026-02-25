"""
Market Breadth Analyzer - Phân tích Market Sentiment
Đếm số mã > SMA10/SMA20 để đo lường trạng thái thị trường
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class MarketBreadthAnalyzer:
    """
    Phân tích market breadth (sức mạnh thị trường).

    Dựa trên thực tế:
    - Vùng đỉnh: >80% mã vượt SMA10 & SMA20 → quá mua, cẩn thận
    - Vùng đáy: <20% mã vượt SMA10 & SMA20 → quá bán, cơ hội
    - Trung tính: 40–60% → thị trường đang tích lũy

    Tham khảo: NYSE Advance/Decline breadth, McClellan Oscillator concept.
    """

    # Thresholds phân loại sentiment
    BULL_THRESHOLD    = 0.80   # >80% above SMAs → cực kỳ tích cực / có thể quá mua
    BULL_ZONE         = 0.60   # >60% → tích cực
    BEAR_ZONE         = 0.40   # <40% → tiêu cực
    BEAR_THRESHOLD    = 0.20   # <20% → cực kỳ tiêu cực / có thể quá bán

    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def load_prices(self, symbol):
        """Load giá đóng cửa của một mã."""
        path = os.path.join(self.data_dir, f"{symbol}_price.csv")
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        return df

    def compute_breadth_snapshot(self, symbols, periods=(10, 20)):
        """
        Tính breadth tại ngày mới nhất cho danh sách symbols.

        Returns:
            dict với các trường:
              - above_sma{p}: số mã close > SMA{p}
              - below_sma{p}: số mã close < SMA{p}
              - pct_above_sma{p}: tỷ lệ mã > SMA{p}
              - above_both: số mã > cả SMA10 & SMA20
              - below_both: số mã < cả SMA10 & SMA20
              - pct_above_both / pct_below_both
              - sentiment: nhãn thị trường
              - signal: +1 (BULL) / 0 (NEUTRAL) / -1 (BEAR)
              - signal_strength: 0.0–1.0
        """
        stats = {p: {"above": 0, "below": 0, "total": 0} for p in periods}
        above_all = 0
        below_all = 0
        valid = 0

        for symbol in symbols:
            df = self.load_prices(symbol)
            if df is None or len(df) < max(periods) + 5:
                continue
            close = df['close'].iloc[-1]
            flags = {}
            for p in periods:
                sma = df['close'].rolling(p).mean().iloc[-1]
                if pd.isna(sma):
                    flags[p] = None
                    continue
                flags[p] = close > sma
                if flags[p]:
                    stats[p]["above"] += 1
                else:
                    stats[p]["below"] += 1
                stats[p]["total"] += 1

            if all(flags.get(p) is not None for p in periods):
                valid += 1
                if all(flags[p] for p in periods):
                    above_all += 1
                elif all(not flags[p] for p in periods):
                    below_all += 1

        result = {"timestamp": datetime.now().isoformat(), "n_symbols": len(symbols)}

        for p in periods:
            total = stats[p]["total"] or 1
            result[f"above_sma{p}"] = stats[p]["above"]
            result[f"below_sma{p}"] = stats[p]["below"]
            result[f"pct_above_sma{p}"] = round(stats[p]["above"] / total, 4)

        result["above_both"]      = above_all
        result["below_both"]      = below_all
        result["valid_symbols"]   = valid
        pct_both = above_all / valid if valid else 0
        result["pct_above_both"]  = round(pct_both, 4)
        result["pct_below_both"]  = round(below_all / valid, 4) if valid else 0

        # Sentiment label + signal
        sentiment, signal, strength = self._classify(pct_both)
        result["sentiment"]        = sentiment
        result["signal"]           = signal
        result["signal_strength"]  = round(strength, 4)

        return result

    def _classify(self, pct_above_both):
        """Phân loại sentiment từ tỷ lệ mã trên cả hai SMA."""
        if pct_above_both >= self.BULL_THRESHOLD:
            return "OVERBOUGHT", 1, 1.0
        elif pct_above_both >= self.BULL_ZONE:
            strength = (pct_above_both - self.BULL_ZONE) / (self.BULL_THRESHOLD - self.BULL_ZONE)
            return "BULLISH", 1, strength
        elif pct_above_both <= self.BEAR_THRESHOLD:
            return "OVERSOLD", -1, 1.0
        elif pct_above_both <= self.BEAR_ZONE:
            strength = (self.BEAR_ZONE - pct_above_both) / (self.BEAR_ZONE - self.BEAR_THRESHOLD)
            return "BEARISH", -1, strength
        else:
            return "NEUTRAL", 0, 0.5

    # ------------------------------------------------------------------
    # Historical breadth (rolling time-series)
    # ------------------------------------------------------------------

    def compute_breadth_history(self, symbols, periods=(10, 20), lookback_days=180):
        """
        Tính breadth theo từng ngày trong lookback_days gần nhất.

        Returns:
            pd.DataFrame với cột: date, pct_above_sma10, pct_above_sma20,
                                  pct_above_both, sentiment, signal
        """
        # Collect all close prices into a pivot table
        closes = {}
        for symbol in symbols:
            df = self.load_prices(symbol)
            if df is not None and not df.empty:
                closes[symbol] = df.set_index('time')['close']

        if not closes:
            logger.warning("No price data available for breadth history")
            return pd.DataFrame()

        price_df = pd.DataFrame(closes).sort_index()

        # Limit to lookback window
        if lookback_days:
            price_df = price_df.iloc[-lookback_days:]

        records = []
        for p in periods:
            price_df[f'sma{p}_'] = price_df.apply(
                lambda col: col.rolling(p).mean()
            )

        sma_dfs = {p: price_df.rolling(p).mean() for p in periods}

        for date in price_df.index:
            row_close = price_df.loc[date]
            flags = {}
            for p in periods:
                sma_row = sma_dfs[p].loc[date]
                flags[p] = (row_close > sma_row).dropna()

            valid = flags[periods[0]].index.intersection(*[flags[p].index for p in periods[1:]])
            if valid.empty:
                continue

            pct = {p: flags[p][valid].mean() for p in periods}
            above_both = all(flags[p][valid] for p in periods)
            # Above both: stock above ALL SMAs simultaneously
            above_both_mask = pd.concat([flags[p][valid] for p in periods], axis=1).all(axis=1)
            pct_both = above_both_mask.mean()

            sentiment, signal, strength = self._classify(pct_both)

            rec = {"date": date}
            for p in periods:
                rec[f"pct_above_sma{p}"] = round(pct[p], 4)
            rec["pct_above_both"]  = round(pct_both, 4)
            rec["sentiment"]       = sentiment
            rec["signal"]          = signal
            rec["signal_strength"] = round(strength, 4)
            records.append(rec)

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Integration helper
    # ------------------------------------------------------------------

    def get_market_filter(self, symbols):
        """
        Trả về bộ lọc cho individual stock decisions.

        Returns:
            dict:
              - allow_new_buys: bool
              - risk_multiplier: float (0.5 cực cẩn thận ↔ 1.5 tích cực)
              - sentiment: str
              - summary: str hiển thị cho user
        """
        breadth = self.compute_breadth_snapshot(symbols)
        sentiment = breadth["sentiment"]
        pct_above = breadth["pct_above_both"]
        signal    = breadth["signal"]

        # Quy tắc:
        # OVERBOUGHT (>80%): Cho phép mua nhưng risk_multiplier = 0.7 (vốn nhỏ hơn)
        # BULLISH (60-80%):  Cho phép mua, risk_multiplier = 1.0
        # NEUTRAL (40-60%):  Cho phép mua thăm dò, risk_multiplier = 0.8
        # BEARISH (20-40%):  Hạn chế mua, risk_multiplier = 0.5
        # OVERSOLD (<20%):   Không mua mới, chờ đáy, risk_multiplier = 0.3

        allow_map = {
            "OVERBOUGHT": (True,  0.70),
            "BULLISH":    (True,  1.00),
            "NEUTRAL":    (True,  0.80),
            "BEARISH":    (False, 0.50),
            "OVERSOLD":   (False, 0.30),
        }
        allow_buys, risk_mult = allow_map.get(sentiment, (True, 0.80))

        pct_str = f"{pct_above:.1%}"
        summary = (
            f"Market Breadth: {pct_str} mã > SMA10 & SMA20 → {sentiment} "
            f"| {'✅ Cho phép mua' if allow_buys else '⛔ Hạn chế mua'} "
            f"| Risk multiplier: {risk_mult}"
        )

        return {
            "allow_new_buys":  allow_buys,
            "risk_multiplier": risk_mult,
            "sentiment":       sentiment,
            "signal":          signal,
            "pct_above_both":  pct_above,
            "pct_above_sma10": breadth.get("pct_above_sma10", 0),
            "pct_above_sma20": breadth.get("pct_above_sma20", 0),
            "n_above_both":    breadth.get("above_both", 0),
            "n_valid":         breadth.get("valid_symbols", 0),
            "summary":         summary,
        }

    def print_breadth_report(self, symbols):
        """In báo cáo breadth ra terminal."""
        b = self.compute_breadth_snapshot(symbols)
        n = b.get("valid_symbols", 1)
        print("\n" + "=" * 55)
        print("  📊 MARKET BREADTH / SENTIMENT REPORT")
        print("=" * 55)
        print(f"  Timestamp : {b['timestamp'][:19]}")
        print(f"  Symbols   : {n}/{len(symbols)}")
        print(f"  > SMA10   : {b['above_sma10']:3d}  ({b['pct_above_sma10']:.1%})")
        print(f"  > SMA20   : {b['above_sma20']:3d}  ({b['pct_above_sma20']:.1%})")
        print(f"  > Both    : {b['above_both']:3d}  ({b['pct_above_both']:.1%})")
        print(f"  < Both    : {b['below_both']:3d}  ({b['pct_below_both']:.1%})")
        print(f"  Sentiment : {b['sentiment']}")
        print(f"  Signal    : {b['signal']:+d}  (strength {b['signal_strength']:.2f})")
        print("=" * 55)
        # Warning zones
        pct = b["pct_above_both"]
        if pct >= self.BULL_THRESHOLD:
            print("  ⚠️  CẢNH BÁO: >80% mã trên cả SMA10 & SMA20 — vùng đỉnh tiềm năng!")
        elif pct <= self.BEAR_THRESHOLD:
            print("  💡 CƠ HỘI: <20% mã trên cả SMA10 & SMA20 — vùng đáy tiềm năng!")
        print("=" * 55 + "\n")
        return b
