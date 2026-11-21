"""
Phase 4 - Kiểm định ML ngoài mẫu (purged walk-forward) với mục tiêu 20 phiên, xếp hạng chéo mã.

Câu hỏi duy nhất: "ML xếp hạng mã có dự báo được mã nào vượt thị trường trong 20 phiên tới, đủ để bù chi phí,
ngoài mẫu, và tốt hơn một baseline động lượng đơn giản không?" Nếu không trả lời được là CÓ thì ML chỉ là thông tin
tham khảo và KHÔNG được đưa vào điểm số/quy tắc cứng.

Thiết kế chống rò rỉ / ảo giác:
  - Đặc trưng chỉ là tỷ lệ không phụ thuộc mức giá (không để mã/thời kỳ lộ qua giá tuyệt đối), rồi xếp hạng phần trăm
    theo từng ngày (loại bỏ chế độ thị trường chung)
  - Nhãn = lợi suất 20 phiên TRỪ trung vị của universe cùng ngày (trung hòa thị trường)
  - Walk-forward mở rộng dần, purge `horizon` phiên giữa train và test (xem purged_cv.py)
  - Chỉ số: Spearman IC theo ngày + lợi suất vượt của nhóm top; KTC bằng block bootstrap (nhãn chồng lấn)
  - So với baseline động lượng (ret_60) và ngẫu nhiên; nhóm top phải vượt chi phí khứ hồi
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.ml_prediction.purged_cv import PurgedWalkForward
from modules.utils.logger import get_logger

logger = get_logger(__name__)

FEATURE_COLS = ['ret_5', 'ret_10', 'ret_20', 'ret_60', 'vol_20', 'vol_60', 'dist_sma20', 'dist_sma50',
                'dist_sma200', 'rsi14', 'macd_diff_n', 'vol_ratio', 'hl_range_10', 'range_pos_252',
                'dist_high_252']
RANK_COLS = ['r_' + c for c in FEATURE_COLS]


# ----------------------------------------------------------------------------- features
def stationary_features(df):
    """Đặc trưng không phụ thuộc mức giá, point-in-time (mỗi dòng chỉ dùng dữ liệu <= ngày đó)."""
    df = df.copy()
    df['time'] = pd.to_datetime(df['time']).dt.normalize()
    df = df.drop_duplicates('time', keep='last').sort_values('time').set_index('time')
    close, high, low, vol = df['close'].astype(float), df['high'].astype(float), df['low'].astype(float), \
        df['volume'].astype(float)
    ret1 = close.pct_change()

    out = pd.DataFrame(index=df.index)
    for n in (5, 10, 20, 60):
        out[f'ret_{n}'] = close.pct_change(n)
    out['vol_20'] = ret1.rolling(20).std()
    out['vol_60'] = ret1.rolling(60).std()
    for n in (20, 50, 200):
        out[f'dist_sma{n}'] = close / close.rolling(n).mean() - 1
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out['rsi14'] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    out['macd_diff_n'] = (macd - macd.ewm(span=9, adjust=False).mean()) / close
    out['vol_ratio'] = vol / vol.rolling(20).mean()
    out['hl_range_10'] = ((high - low) / close).rolling(10).mean()
    hi, lo = high.rolling(252).max(), low.rolling(252).min()
    out['range_pos_252'] = (close - lo) / (hi - lo).replace(0, np.nan)
    out['dist_high_252'] = close / hi - 1
    return out.replace([np.inf, -np.inf], np.nan), close


def build_panel(price_frames, horizon=None, min_symbols=None, labeled=True):
    """
    Panel (ngày × mã) với đặc trưng đã xếp hạng chéo mã theo ngày.
    labeled=True: thêm fwd_ret, excess (so với trung vị ngày), y = excess > 0, bỏ dòng chưa có nhãn.
    labeled=False: giữ cả các ngày gần nhất (không nhãn) để dự đoán.
    """
    cfg = config.ML_VALIDATION
    horizon = horizon or cfg['horizon']
    min_symbols = min_symbols or cfg['min_symbols_per_date']
    parts = []
    for symbol, df in price_frames.items():
        if df is None or len(df) < 60:
            continue
        feats, close = stationary_features(df)
        feats['fwd_ret'] = close.shift(-horizon) / close - 1
        feats['symbol'] = symbol
        parts.append(feats.reset_index())
    if not parts:
        raise ValueError("Không có dữ liệu giá để dựng panel")
    panel = pd.concat(parts, ignore_index=True).rename(columns={'time': 'date'})
    panel = panel.dropna(subset=FEATURE_COLS)
    counts = panel.groupby('date')['symbol'].transform('count')
    panel = panel[counts >= min_symbols].copy()
    ranks = panel.groupby('date')[FEATURE_COLS].rank(pct=True)
    ranks.columns = RANK_COLS
    panel = pd.concat([panel, ranks], axis=1)
    if labeled:
        panel = panel.dropna(subset=['fwd_ret']).copy()
        panel['excess'] = panel['fwd_ret'] - panel.groupby('date')['fwd_ret'].transform('median')
        panel['y'] = (panel['excess'] > 0).astype(int)
    return panel.sort_values(['date', 'symbol']).reset_index(drop=True)


# ----------------------------------------------------------------------------- metrics
def block_bootstrap_mean(x, block, n_resamples, seed=42, confidence=0.95):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < max(30, 2 * block):
        return None
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n, size=(n_resamples, n_blocks))
    idx = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(n_resamples, -1)[:, :n]
    means = x[idx].mean(axis=1)
    a = (1 - confidence) / 2
    return {'mean': float(x.mean()), 'ci_lower': float(np.quantile(means, a)),
            'ci_upper': float(np.quantile(means, 1 - a)), 'n': int(n)}


def daily_cross_section(oos, score_col, top_q, min_symbols):
    """Với mỗi ngày: Spearman IC giữa điểm và excess, và excess trung bình của nhóm top."""
    ics, tops, dates = [], [], []
    for date, g in oos.groupby('date'):
        if len(g) < min_symbols or g[score_col].nunique() < 2:
            continue
        ic = g[score_col].rank().corr(g['excess'].rank())
        k = max(1, int(round(len(g) * top_q)))
        top = g.nlargest(k, score_col)['excess'].mean()
        ics.append(ic)
        tops.append(top)
        dates.append(date)
    return pd.DataFrame({'date': dates, 'ic': ics, 'top_excess': tops})


def summarize_scorer(oos, score_col, cfg):
    cs = daily_cross_section(oos, score_col, cfg['top_quantile'], cfg['min_symbols_per_date'])
    if cs.empty:
        return {'n_dates': 0, 'ic': None, 'top_excess': None}
    return {'n_dates': int(len(cs)),
            'ic': block_bootstrap_mean(cs['ic'], cfg['bootstrap_block'], cfg['bootstrap_resamples']),
            'top_excess': block_bootstrap_mean(cs['top_excess'], cfg['bootstrap_block'],
                                               cfg['bootstrap_resamples'])}


def round_trip_cost():
    p = config.BACKTEST_V2
    return 2 * p['fee_rate'] + p['sell_tax_rate'] + 2 * p['slippage']


# ----------------------------------------------------------------------------- evaluation
def default_model_factory():
    from sklearn.ensemble import RandomForestClassifier
    c = config.ML_VALIDATION
    return RandomForestClassifier(n_estimators=c['n_estimators'], max_depth=c['max_depth'],
                                  min_samples_leaf=c['min_samples_leaf'], n_jobs=-1, random_state=42)


def walk_forward_oos(panel, model_factory=None, cfg=None):
    """Dự đoán ngoài mẫu cho mọi dòng thuộc các khối test; trả về (DataFrame OOS, thông tin các fold)."""
    cfg = {**config.ML_VALIDATION, **(cfg or {})}
    model_factory = model_factory or default_model_factory
    splitter = PurgedWalkForward(cfg['n_splits'], cfg['horizon'], cfg['min_train_dates'])
    X, y = panel[RANK_COLS].to_numpy(), panel['y'].to_numpy()
    rng = np.random.default_rng(config.BACKTEST_V2['seed'])
    parts, folds = [], []
    for k, (tr, te) in enumerate(splitter.split(panel['date'])):
        if len(np.unique(y[tr])) < 2:
            continue
        model = model_factory()
        model.fit(X[tr], y[tr])
        proba = model.predict_proba(X[te])[:, list(model.classes_).index(1)]
        part = panel.iloc[te][['date', 'symbol', 'excess', 'y', 'r_ret_60']].copy()
        part['ml'] = proba
        part['momentum'] = part['r_ret_60']
        part['random'] = rng.uniform(size=len(part))
        parts.append(part)
        folds.append({'fold': k, 'train_end': str(panel['date'].iloc[tr].max().date()),
                      'test_start': str(panel['date'].iloc[te].min().date()),
                      'test_end': str(panel['date'].iloc[te].max().date()),
                      'n_train': int(len(tr)), 'n_test': int(len(te))})
    if not parts:
        raise ValueError("Không có fold hợp lệ")
    return pd.concat(parts, ignore_index=True), folds


def auc_oos(oos):
    from sklearn.metrics import roc_auc_score
    if oos['y'].nunique() < 2:
        return None
    return float(roc_auc_score(oos['y'], oos['ml']))


def decide(ml, momentum, cfg, cost):
    """Verdict + từng điều kiện. Không đủ số ngày OOS → INCONCLUSIVE."""
    checks = []

    def add(name, value, rule, threshold, ok, sufficiency=False):
        status = 'NA' if value is None else ('PASS' if ok(value) else 'FAIL')
        checks.append({'name': name, 'value': value, 'rule': rule, 'threshold': threshold,
                       'status': status, 'sufficiency': sufficiency})

    add('Số ngày ngoài mẫu', ml['n_dates'], '>=', cfg['min_oos_dates'], lambda v: v >= cfg['min_oos_dates'], True)
    ic, top = ml['ic'], ml['top_excess']
    add('IC trung bình, cận dưới KTC95', ic['ci_lower'] if ic else None, '>', 0.0, lambda v: v > 0.0)
    add('Lợi suất vượt nhóm top, cận dưới KTC95', top['ci_lower'] if top else None, '>', round(cost, 4),
        lambda v: v > cost)
    mom_ic = momentum['ic']['mean'] if momentum.get('ic') else None
    add('IC của ML hơn IC của baseline động lượng', (ic['mean'] - mom_ic) if ic and mom_ic is not None else None,
        '>', 0.0, lambda v: v > 0.0)

    if any(c['status'] == 'FAIL' and not c['sufficiency'] for c in checks) and ic and top \
            and (ic['ci_upper'] <= 0 or top['mean'] <= 0):
        verdict = 'NO_EDGE'
    elif all(c['status'] == 'PASS' for c in checks):
        verdict = 'HAS_EDGE'
    else:
        verdict = 'INCONCLUSIVE'
    return verdict, checks


def run_validation(price_frames, cfg=None, model_factory=None, write=False):
    """Chạy toàn bộ kiểm định; trả về báo cáo (dict)."""
    cfg = {**config.ML_VALIDATION, **(cfg or {})}
    panel = build_panel(price_frames, cfg['horizon'], cfg['min_symbols_per_date'])
    oos, folds = walk_forward_oos(panel, model_factory, cfg)
    ml, mom, rnd = (summarize_scorer(oos, c, cfg) for c in ('ml', 'momentum', 'random'))
    cost = round_trip_cost()
    verdict, checks = decide(ml, mom, cfg, cost)
    report = {
        'verdict': verdict, 'checks': checks, 'ml': ml, 'momentum_baseline': mom, 'random_baseline': rnd,
        'auc_oos': auc_oos(oos), 'folds': folds, 'round_trip_cost': cost,
        'n_symbols': int(panel['symbol'].nunique()), 'n_samples': int(len(panel)),
        'horizon': cfg['horizon'],
        'caveats': [
            "Universe là VN100 hiện tại (thiên lệch sống sót).",
            "Chỉ dùng dữ liệu giá/khối lượng; không có dữ liệu cơ bản point-in-time cho ML.",
            "Nhãn 20 phiên chồng lấn nên KTC dùng block bootstrap; vẫn là ước lượng thô.",
            "HAS_EDGE chỉ nghĩa là có dấu hiệu ngoài mẫu trên dữ liệu này, không đảm bảo tương lai.",
        ]}
    if write:
        os.makedirs(os.path.dirname(cfg['report_file']), exist_ok=True)
        with open(cfg['report_file'], 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    return report
