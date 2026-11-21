"""
Chỉ số hiệu suất, kiểm định thống kê và ngưỡng nghiệm thu cho BacktestEngineV2.

Ý tưởng kiểm định tham khảo cách tiếp cận của Vibe-Trading (bootstrap Sharpe, Monte Carlo, walk-forward)
nhưng viết lại độc lập, có khác biệt:
  - Bootstrap dùng CIRCULAR BLOCK (lợi suất ngày có tự tương quan; i.i.d. làm KTC quá hẹp)
  - Monte Carlo chỉ đo RỦI RO THỨ TỰ giao dịch (drawdown), không dùng để suy ra "p-value của Sharpe"
    (hoán vị thứ tự giao dịch không đổi tổng lãi)
  - Walk-forward ở đây là chẩn đoán độ ổn định theo thời gian, KHÔNG phải kiểm thử ngoài mẫu
"""
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

TRADING_DAYS = 252


# ----------------------------------------------------------------------------- metrics
def max_drawdown(equity):
    """Sụt giảm tối đa (số dương, 0.10 = 10%)."""
    eq = np.asarray(equity, dtype=float)
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    return float(np.max((peak - eq) / peak))


def sharpe_ratio(daily_returns, rf_annual=0.0):
    r = np.asarray(daily_returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return None
    excess = r - rf_annual / TRADING_DAYS
    sd = excess.std(ddof=1)
    if sd == 0:
        return None
    return float(excess.mean() / sd * math.sqrt(TRADING_DAYS))


def cagr(equity):
    """Lợi suất kép hàng năm theo lịch (ngày thực)."""
    if len(equity) < 2:
        return None
    days = (equity.index[-1] - equity.index[0]).days
    if days <= 0 or equity.iloc[0] <= 0 or equity.iloc[-1] <= 0:
        return None
    return float((equity.iloc[-1] / equity.iloc[0]) ** (365.25 / days) - 1)


def trade_stats(trades):
    """Thống kê trên các lệnh BÁN đã đóng (pnl là lãi lỗ ròng sau phí và thuế)."""
    empty = {'n_trades': 0, 'win_rate': None, 'profit_factor': None, 'avg_win_pct': None,
             'avg_loss_pct': None, 'expectancy_pct': None, 'avg_hold_sessions': None, 'exit_reasons': {}}
    if trades is None or len(trades) == 0:
        return empty
    sells = trades[trades['action'] == 'SELL']
    if sells.empty:
        return empty
    wins = sells[sells['pnl'] > 0]
    losses = sells[sells['pnl'] <= 0]
    gross_win = float(wins['pnl'].sum())
    gross_loss = float(-losses['pnl'].sum())
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        profit_factor = float('inf') if gross_win > 0 else None
    return {
        'n_trades': int(len(sells)),
        'win_rate': float(len(wins) / len(sells)),
        'profit_factor': profit_factor,
        'avg_win_pct': float(wins['return_pct'].mean()) if len(wins) else None,
        'avg_loss_pct': float(losses['return_pct'].mean()) if len(losses) else None,
        'expectancy_pct': float(sells['return_pct'].mean()),
        'avg_hold_sessions': float(sells['hold_sessions'].mean()),
        'exit_reasons': sells['reason'].value_counts().to_dict(),
    }


def compute_metrics(equity, trades=None, benchmark=None, invested=None, rf_annual=0.0):
    """
    Args:
        equity: Series giá trị danh mục theo ngày (index = ngày giao dịch)
        trades: DataFrame lệnh (cột action/pnl/return_pct/hold_sessions/reason)
        benchmark: Series chỉ số tham chiếu (cùng hoặc rộng hơn index của equity)
        invested: Series tỷ trọng đã đầu tư theo ngày (0..1)
    """
    returns = equity.pct_change().dropna()
    out = {
        'start': str(equity.index[0].date()), 'end': str(equity.index[-1].date()),
        'sessions': int(len(equity)),
        'total_return': float(equity.iloc[-1] / equity.iloc[0] - 1),
        'cagr': cagr(equity),
        'sharpe': sharpe_ratio(returns, rf_annual),
        'max_drawdown': max_drawdown(equity.values),
        'avg_exposure': float(invested.mean()) if invested is not None and len(invested) else None,
    }
    out['calmar'] = (out['cagr'] / out['max_drawdown']
                     if out['cagr'] is not None and out['max_drawdown'] > 0 else None)
    out.update(trade_stats(trades))

    if benchmark is not None:
        bench = benchmark.reindex(equity.index).ffill().dropna()
        if len(bench) >= 2:
            bench_cagr = cagr(bench)
            out['benchmark_cagr'] = bench_cagr
            out['benchmark_total_return'] = float(bench.iloc[-1] / bench.iloc[0] - 1)
            out['excess_cagr'] = (out['cagr'] - bench_cagr
                                  if out['cagr'] is not None and bench_cagr is not None else None)
    return out


# ----------------------------------------------------------------------------- statistics
def block_bootstrap_sharpe(daily_returns, rf_annual=0.0, n_resamples=2000, block=10, seed=42,
                           confidence=0.95):
    """KTC Sharpe bằng circular block bootstrap. Trả về None nếu chuỗi quá ngắn."""
    r = np.asarray(daily_returns, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < max(30, 2 * block):
        return None
    rng = np.random.default_rng(seed)
    excess = r - rf_annual / TRADING_DAYS
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n, size=(n_resamples, n_blocks))
    idx = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(n_resamples, -1)[:, :n]
    samples = excess[idx]
    sd = samples.std(axis=1, ddof=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        sharpes = np.where(sd > 0, samples.mean(axis=1) / sd * math.sqrt(TRADING_DAYS), np.nan)
    sharpes = sharpes[~np.isnan(sharpes)]
    if len(sharpes) == 0:
        return None
    alpha = (1 - confidence) / 2
    return {
        'observed': sharpe_ratio(r, rf_annual),
        'ci_lower': float(np.quantile(sharpes, alpha)),
        'ci_upper': float(np.quantile(sharpes, 1 - alpha)),
        'prob_positive': float((sharpes > 0).mean()),
        'confidence': confidence, 'block': block, 'n_resamples': n_resamples,
    }


def monte_carlo_drawdown(trades, initial_capital, n_resamples=2000, seed=42):
    """
    Rủi ro THỨ TỰ giao dịch: xáo trộn thứ tự lãi/lỗ (VND) của các lệnh đã đóng, đo phân bố max drawdown.
    Xấp xỉ mức lệnh (bỏ qua việc các vị thế chồng thời gian) - chỉ dùng để thấy "nếu xui thì sụt bao nhiêu".
    """
    if trades is None or len(trades) == 0:
        return None
    pnls = trades.loc[trades['action'] == 'SELL', 'pnl'].to_numpy(dtype=float)
    if len(pnls) < 10:
        return None
    rng = np.random.default_rng(seed)
    dds = np.empty(n_resamples)
    for i in range(n_resamples):
        path = initial_capital + np.cumsum(rng.permutation(pnls))
        path = np.concatenate([[initial_capital], path])
        peak = np.maximum.accumulate(path)
        dds[i] = np.max((peak - path) / peak)
    return {
        'dd_median': float(np.median(dds)), 'dd_p95': float(np.quantile(dds, 0.95)),
        'dd_max': float(dds.max()), 'n_trades': int(len(pnls)), 'n_resamples': n_resamples,
    }


def walk_forward(equity, benchmark=None, n_windows=6):
    """Chia đường vốn thành n cửa sổ liên tiếp; báo lợi suất từng cửa sổ và tỷ lệ cửa sổ có lãi."""
    if len(equity) < 2 * n_windows:
        return None
    bounds = np.linspace(0, len(equity) - 1, n_windows + 1).astype(int)
    bench = benchmark.reindex(equity.index).ffill() if benchmark is not None else None
    rows = []
    for k in range(n_windows):
        a, b = bounds[k], bounds[k + 1]
        ret = float(equity.iloc[b] / equity.iloc[a] - 1)
        row = {'start': str(equity.index[a].date()), 'end': str(equity.index[b].date()), 'return': ret}
        if bench is not None and pd.notna(bench.iloc[a]) and pd.notna(bench.iloc[b]) and bench.iloc[a] > 0:
            row['benchmark_return'] = float(bench.iloc[b] / bench.iloc[a] - 1)
            row['excess'] = ret - row['benchmark_return']
        rows.append(row)
    return {
        'windows': rows,
        'positive_windows_pct': float(np.mean([w['return'] > 0 for w in rows])),
        'outperform_windows_pct': (float(np.mean([w['excess'] > 0 for w in rows if 'excess' in w]))
                                   if any('excess' in w for w in rows) else None),
    }


# ----------------------------------------------------------------------------- acceptance
def evaluate_acceptance(metrics, bootstrap, mc, stress_total_return, thresholds=None):
    """
    Áp ngưỡng nghiệm thu (config.BACKTEST_ACCEPTANCE).
    Verdict:
      FAIL         - có chỉ số rủi ro/hiệu suất KHÔNG đạt
      INCONCLUSIVE - chưa đủ dữ liệu/mẫu để kết luận (không bao giờ tính là PASS)
      PASS         - đạt tất cả
    """
    t = thresholds or config.BACKTEST_ACCEPTANCE
    checks = []

    def add(name, kind, value, threshold, ok_fn, sufficiency=False):
        if value is None:
            status = 'NA'
        else:
            status = 'PASS' if ok_fn(value) else 'FAIL'
        checks.append({'name': name, 'value': value, 'threshold': threshold, 'status': status,
                       'sufficiency': sufficiency, 'rule': kind})

    wf_pos = metrics.get('walk_forward', {}).get('positive_windows_pct') if metrics.get('walk_forward') else None

    add('Số phiên', '>=', metrics['sessions'], t['min_sessions'], lambda v: v >= t['min_sessions'], True)
    add('Số lệnh đóng', '>=', metrics['n_trades'], t['min_trades'], lambda v: v >= t['min_trades'], True)
    add('Sharpe KTC95 cận dưới', '>', bootstrap['ci_lower'] if bootstrap else None,
        t['min_sharpe_ci_lower'], lambda v: v > t['min_sharpe_ci_lower'])
    add('Vượt benchmark (CAGR) sau chi phí', '>', metrics.get('excess_cagr'),
        t['min_excess_cagr'], lambda v: v > t['min_excess_cagr'])
    add('Max drawdown thực tế', '<=', metrics['max_drawdown'], t['max_drawdown'],
        lambda v: v <= t['max_drawdown'])
    add('Max drawdown Monte Carlo p95', '<=', mc['dd_p95'] if mc else None,
        t['max_mc_drawdown_p95'], lambda v: v <= t['max_mc_drawdown_p95'])
    add('Profit factor', '>=', metrics.get('profit_factor'), t['min_profit_factor'],
        lambda v: v >= t['min_profit_factor'])
    add('Cửa sổ walk-forward có lãi', '>=', wf_pos, t['min_positive_windows_pct'],
        lambda v: v >= t['min_positive_windows_pct'])
    add(f"Lợi suất khi chi phí x{t['cost_stress_multiplier']:g}", '>', stress_total_return, 0.0,
        lambda v: v > 0.0)

    if any(c['status'] == 'FAIL' and not c['sufficiency'] for c in checks):
        verdict = 'FAIL'
    elif any(c['status'] != 'PASS' for c in checks):
        verdict = 'INCONCLUSIVE'
    else:
        verdict = 'PASS'
    return {'verdict': verdict, 'checks': checks}
