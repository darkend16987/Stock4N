"""
Adaptive Parameter Optimizer
Tìm tham số tối ưu (RSI period, MA lengths) tự động theo biến động gần nhất.

Phương pháp:
  - Brute-force Parameter Sweeping: quét toàn bộ dải [min, max]
  - Rolling Window Optimization: dùng cửa sổ quá khứ gần (recent volatility)
  - Mask Layer (Q3 feedback): loại bỏ downtrend windows trước khi optimize,
    tránh overfit vào chu kỳ giảm.

Tham khảo: Perry Kaufman (KAMA / Adaptive Indicators),
           Robert Carver (Systematic Trading), concept từ Q2/Q3 của user.
"""
import pandas as pd
import numpy as np
import os
import sys
from functools import lru_cache

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Metric helpers
# ──────────────────────────────────────────────

def _sharpe(returns, risk_free=0.0):
    """Annualised Sharpe ratio from daily return series."""
    if len(returns) < 5:
        return -99.0
    mu  = returns.mean()
    std = returns.std(ddof=1)
    if std < 1e-9:
        return 0.0
    return (mu - risk_free / 252) / std * np.sqrt(252)


def _profit_factor(returns):
    wins  = returns[returns > 0].sum()
    loss  = abs(returns[returns < 0].sum())
    return wins / loss if loss > 1e-9 else 0.0


def _rsi_series(close, period):
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / (loss + 1e-9)
    return 100 - 100 / (1 + rs)


def _sma_signal(close, fast, slow):
    """Return +1/-1 based on fast > slow MA crossover."""
    sma_f = close.rolling(fast).mean()
    sma_s = close.rolling(slow).mean()
    sig   = np.where(sma_f > sma_s, 1, -1)
    return pd.Series(sig, index=close.index)


def _rsi_signal(close, period, ob=70, os_=30):
    """Simple RSI mean-reversion signal."""
    rsi = _rsi_series(close, period)
    sig = np.where(rsi < os_, 1, np.where(rsi > ob, -1, np.nan))
    return pd.Series(sig, index=close.index).ffill().fillna(0)


# ──────────────────────────────────────────────
# Mask Layer  (answers Q3 feedback)
# ──────────────────────────────────────────────

class MaskLayer:
    """
    Validates optimisation windows:
    - Filters out downtrend windows (prevents overfitting to bear regimes)
    - Validates that the 'best' param actually works on a held-out truth slice.

    Two masks:
    1. trend_mask  – exclude windows where price was in downtrend >50% of time
    2. truth_mask  – final cross-validation: param must beat baseline on
                     the 20% future slice it never saw during sweep.
    """

    def __init__(self, trend_threshold=0.50, truth_split=0.20):
        self.trend_threshold = trend_threshold
        self.truth_split     = truth_split

    def is_uptrend_window(self, close_window: pd.Series) -> bool:
        """True if window is predominantly uptrend (close > SMA50 >50% of bars)."""
        if len(close_window) < 20:
            return True   # too short to judge, include
        sma = close_window.rolling(20).mean().dropna()
        aligned = close_window.reindex(sma.index)
        frac_above = (aligned > sma).mean()
        return frac_above >= self.trend_threshold

    def split_truth(self, close: pd.Series):
        """Split series: sweep window | truth window."""
        n_truth = max(5, int(len(close) * self.truth_split))
        return close.iloc[:-n_truth], close.iloc[-n_truth:]

    def validate_param(self, close_truth: pd.Series, param_type: str,
                       best_param, baseline_param) -> dict:
        """
        Check if best_param beats baseline_param on truth data.
        Returns {'valid': bool, 'best_score': float, 'baseline_score': float}
        """
        if len(close_truth) < max(best_param if isinstance(best_param, tuple)
                                   else [best_param]) + 5:
            return {"valid": True, "best_score": 0, "baseline_score": 0,
                    "reason": "truth_too_short"}

        def score_param(p):
            if param_type == "rsi":
                sig = _rsi_signal(close_truth, p)
            elif param_type == "ma_fast":
                sig = _sma_signal(close_truth, p, p * 2)
            elif param_type == "ma_cross":
                sig = _sma_signal(close_truth, p[0], p[1])
            else:
                return 0.0
            ret = close_truth.pct_change().shift(-1) * sig
            return _sharpe(ret.dropna())

        best_score     = score_param(best_param)
        baseline_score = score_param(baseline_param)

        valid = best_score >= baseline_score * 0.8   # allow 20% degradation
        return {
            "valid":          valid,
            "best_score":     round(best_score, 4),
            "baseline_score": round(baseline_score, 4),
            "reason":         "validated" if valid else "failed_truth_check",
        }


# ──────────────────────────────────────────────
# Adaptive Parameter Optimizer
# ──────────────────────────────────────────────

class AdaptiveParamOptimizer:
    """
    Brute-force sweeps tham số trong cửa sổ rolling gần nhất,
    với MaskLayer để tránh bias từ downtrend.

    Supported param types:
        'rsi'       – tìm RSI period tối ưu
        'ma_fast'   – tìm fast MA period tối ưu
        'ma_cross'  – tìm cặp (fast, slow) tối ưu
    """

    # Parameter search ranges
    RSI_RANGE    = (5, 30)     # RSI period: 5 → 30
    MA_FAST_RANGE = (5, 50)    # Fast MA: 5 → 50
    MA_SLOW_RANGE = (20, 100)  # Slow MA: 20 → 100

    # Defaults (baseline / fallback)
    DEFAULT_RSI    = 14
    DEFAULT_MA_FAST = 10
    DEFAULT_MA_SLOW = 50

    # Rolling window for optimization (bars)
    WINDOW_BARS = 120   # ~6 months of daily data

    def __init__(self, mask_layer: MaskLayer | None = None):
        self.mask = mask_layer or MaskLayer()

    def _score_rsi(self, close: pd.Series, period: int,
                   ob=70, os_=30) -> float:
        sig = _rsi_signal(close, period, ob, os_)
        ret = close.pct_change().shift(-1) * sig
        return _sharpe(ret.dropna())

    def _score_ma_cross(self, close: pd.Series, fast: int, slow: int) -> float:
        if fast >= slow:
            return -99.0
        sig = _sma_signal(close, fast, slow)
        ret = close.pct_change().shift(-1) * sig
        return _sharpe(ret.dropna())

    def find_best_rsi(self, close: pd.Series) -> dict:
        """
        Sweeps RSI periods 5–30 on recent window.
        Applies MaskLayer before & after sweep.
        Returns best period or DEFAULT_RSI if validation fails.
        """
        window = close.iloc[-self.WINDOW_BARS:] if len(close) > self.WINDOW_BARS else close

        # Mask 1: skip downtrend windows
        if not self.mask.is_uptrend_window(window):
            logger.debug("RSI sweep skipped: window is downtrend dominated")
            return {
                "best_param": self.DEFAULT_RSI,
                "best_score": None,
                "source":     "default_downtrend",
                "mask_result": "downtrend_skipped",
            }

        sweep_data, truth_data = self.mask.split_truth(window)

        best_p, best_s = self.DEFAULT_RSI, -99.0
        scores = {}
        for p in range(*self.RSI_RANGE):
            s = self._score_rsi(sweep_data, p)
            scores[p] = s
            if s > best_s:
                best_s, best_p = s, p

        # Mask 2: validate on truth slice
        val = self.mask.validate_param(truth_data, "rsi",
                                        best_p, self.DEFAULT_RSI)

        final_p = best_p if val["valid"] else self.DEFAULT_RSI

        logger.info(f"RSI sweep → best={best_p} (score={best_s:.3f}), "
                    f"truth_valid={val['valid']}, final={final_p}")

        return {
            "best_param":   final_p,
            "best_score":   round(best_s, 4),
            "source":       "adaptive" if val["valid"] else "default_truth_failed",
            "sweep_scores": {str(k): round(v, 4) for k, v in sorted(
                             scores.items(), key=lambda x: -x[1])[:5]},
            "mask_result":  val,
        }

    def find_best_ma_cross(self, close: pd.Series) -> dict:
        """
        Sweeps (fast, slow) MA combinations.
        Returns best (fast, slow) or defaults if validation fails.
        """
        window = close.iloc[-self.WINDOW_BARS:] if len(close) > self.WINDOW_BARS else close

        if not self.mask.is_uptrend_window(window):
            return {
                "best_param": (self.DEFAULT_MA_FAST, self.DEFAULT_MA_SLOW),
                "source":     "default_downtrend",
                "mask_result": "downtrend_skipped",
            }

        sweep_data, truth_data = self.mask.split_truth(window)

        best_pair, best_s = (self.DEFAULT_MA_FAST, self.DEFAULT_MA_SLOW), -99.0
        top_scores = {}

        fast_range = range(self.MA_FAST_RANGE[0], self.MA_FAST_RANGE[1], 5)
        slow_range = range(self.MA_SLOW_RANGE[0], self.MA_SLOW_RANGE[1], 10)

        for fast in fast_range:
            for slow in slow_range:
                s = self._score_ma_cross(sweep_data, fast, slow)
                top_scores[(fast, slow)] = s
                if s > best_s:
                    best_s, best_pair = s, (fast, slow)

        val = self.mask.validate_param(
            truth_data, "ma_cross", best_pair,
            (self.DEFAULT_MA_FAST, self.DEFAULT_MA_SLOW)
        )

        final_pair = best_pair if val["valid"] else (self.DEFAULT_MA_FAST, self.DEFAULT_MA_SLOW)

        # Top 5 pairs
        top5 = sorted(top_scores.items(), key=lambda x: -x[1])[:5]

        logger.info(f"MA cross sweep → best={best_pair} (score={best_s:.3f}), "
                    f"truth_valid={val['valid']}, final={final_pair}")

        return {
            "best_param":   final_pair,
            "best_score":   round(best_s, 4),
            "source":       "adaptive" if val["valid"] else "default_truth_failed",
            "top5_pairs":   [(str(p), round(s, 4)) for p, s in top5],
            "mask_result":  val,
        }

    def optimize_all(self, close: pd.Series) -> dict:
        """
        Run full adaptive sweep for all parameter types.

        Returns:
            dict: {
                'rsi':      {best_param, source, ...},
                'ma_cross': {best_param, source, ...},
                'adaptive': bool (True if adaptive params were used)
            }
        """
        rsi_result   = self.find_best_rsi(close)
        ma_result    = self.find_best_ma_cross(close)

        adaptive_used = (rsi_result["source"] == "adaptive" or
                         ma_result["source"] == "adaptive")

        return {
            "rsi":      rsi_result,
            "ma_cross": ma_result,
            "adaptive": adaptive_used,
        }


# ──────────────────────────────────────────────
# Convenience: per-symbol batch
# ──────────────────────────────────────────────

class AdaptiveParamManager:
    """
    Run AdaptiveParamOptimizer trên tất cả symbols và cache kết quả.
    """

    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir  = data_dir
        self.optimizer = AdaptiveParamOptimizer()
        self._cache: dict = {}

    def load_close(self, symbol) -> pd.Series | None:
        path = os.path.join(self.data_dir, f"{symbol}_price.csv")
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path, parse_dates=['time'])
        df = df.sort_values('time')
        return df.set_index('time')['close']

    def get_params(self, symbol) -> dict:
        """Return adaptive params for a single symbol (cached)."""
        if symbol in self._cache:
            return self._cache[symbol]

        close = self.load_close(symbol)
        if close is None or len(close) < 60:
            result = {
                "rsi":      {"best_param": AdaptiveParamOptimizer.DEFAULT_RSI,   "source": "default_no_data"},
                "ma_cross": {"best_param": (AdaptiveParamOptimizer.DEFAULT_MA_FAST,
                                            AdaptiveParamOptimizer.DEFAULT_MA_SLOW), "source": "default_no_data"},
                "adaptive": False,
            }
        else:
            result = self.optimizer.optimize_all(close)

        self._cache[symbol] = result
        return result

    def run_all(self, symbols) -> dict:
        """Run adaptive optimisation for all symbols."""
        logger.info(f"Running adaptive param optimization for {len(symbols)} symbols...")
        results = {}
        adaptive_count = 0

        for sym in symbols:
            try:
                r = self.get_params(sym)
                results[sym] = r
                if r.get("adaptive"):
                    adaptive_count += 1
                    rsi_p = r["rsi"]["best_param"]
                    ma_p  = r["ma_cross"]["best_param"]
                    logger.info(f"  ✓ {sym}: RSI={rsi_p}, MA=({ma_p[0]},{ma_p[1]})")
            except Exception as e:
                logger.error(f"  ✗ {sym}: {e}")
                results[sym] = None

        logger.info(f"Adaptive params used for {adaptive_count}/{len(symbols)} symbols.")
        return results

    def get_summary_df(self, results: dict) -> pd.DataFrame:
        """Convert results dict → DataFrame for display."""
        rows = []
        for sym, r in results.items():
            if r is None:
                continue
            rows.append({
                "Symbol":     sym,
                "RSI_Period": r["rsi"]["best_param"],
                "RSI_Source": r["rsi"]["source"],
                "MA_Fast":    r["ma_cross"]["best_param"][0],
                "MA_Slow":    r["ma_cross"]["best_param"][1],
                "MA_Source":  r["ma_cross"]["source"],
                "Adaptive":   r["adaptive"],
            })
        return pd.DataFrame(rows)
