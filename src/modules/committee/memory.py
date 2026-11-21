"""
Phase 3 - Đối chiếu kết quả (settle), bài học thống kê (lessons) và đánh giá sẵn sàng `enforce`.

Ý tưởng "settle-then-reflect" của TradingAgents (đã đọc code của họ), điều chỉnh cho dự án này:
  - Chu kỳ settle 20 phiên (không phải 5) vì chiến lược nắm giữ 1-3 tháng; so với benchmark (VN-Index nếu có).
  - "Bài học" KHÔNG do LLM viết mà là THỐNG KÊ tính bằng code (n, lợi suất vượt benchmark, tỷ lệ thắng) theo
    quyết định/cờ rủi ro, chỉ hiện khi đủ mẫu. LLM viết bài học dễ thêm ảo giác và kể chuyện từ vài trường hợp.
  - Chống nhìn trước: chỉ dùng kết quả đã settle xong (`resolved_on` <= ngày ra quyết định).

Quy ước đo (chất lượng quyết định, không phải mô phỏng giao dịch): giá đóng cửa ngày dữ liệu → đóng cửa sau
`horizon` phiên của chính mã đó; benchmark đo cùng cửa sổ ngày. Bỏ qua phí/khớp lệnh vì cả hai nhóm (VETO/APPROVE)
chịu cùng sai lệch.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger

logger = get_logger(__name__)


# ----------------------------------------------------------------------------- store
class OutcomeStore:
    def __init__(self, path=None):
        self.path = path or config.COMMITTEE_CONFIG['outcomes_file']

    def read(self):
        if not os.path.exists(self.path):
            return []
        rows = []
        with open(self.path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Outcome store: bỏ qua dòng hỏng")
        return rows

    def append(self, rows):
        if not rows:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'a', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')


def _key(e, horizon):
    return (str(e['as_of']), e['symbol'], e['prompt_version'], horizon)


# ----------------------------------------------------------------------------- settle
def settle_pending(ledger_entries, store, book, benchmark, benchmark_label, horizon=None):
    """
    Đối chiếu các quyết định OK chưa settle mà đã đủ `horizon` phiên dữ liệu.

    Args:
        book: PriceBook (giá VND, index theo ngày)
        benchmark: Series chỉ số tham chiếu theo ngày
    Returns:
        list outcome mới (đã ghi vào store)
    """
    horizon = horizon or config.COMMITTEE_CONFIG['settle_horizon']
    done = {_key(o, o['horizon']) for o in store.read()}
    latest = {}
    for e in ledger_entries:
        if e.get('status') == 'OK':
            latest[(str(e['as_of']), e['symbol'], e['prompt_version'])] = e

    new = []
    for (as_of, symbol, version), e in sorted(latest.items()):
        if (as_of, symbol, version, horizon) in done:
            continue
        bars = book.bars.get(symbol)
        if bars is None:
            continue
        as_of_ts = pd.Timestamp(as_of)
        if as_of_ts not in bars.index:
            continue                                   # ngày dữ liệu không khớp phiên nào → không đoán
        i0 = bars.index.get_loc(as_of_ts)
        if i0 + horizon >= len(bars):
            continue                                   # chưa đủ cửa sổ: vẫn pending
        window = bars.iloc[i0:i0 + horizon + 1]
        entry, exit_ = float(window['close'].iloc[0]), float(window['close'].iloc[-1])
        exit_date = window.index[-1]
        b0 = benchmark.loc[:as_of_ts]
        b1 = benchmark.loc[:exit_date]
        if b0.empty or b1.empty or b0.iloc[-1] <= 0:
            continue
        ret = exit_ / entry - 1
        bench_ret = float(b1.iloc[-1] / b0.iloc[-1] - 1)
        verdict = e.get('verdict', {})
        new.append({
            'as_of': as_of, 'symbol': symbol, 'prompt_version': version, 'horizon': horizon,
            'action': verdict.get('action'), 'risk_flags': verdict.get('risk_flags', []),
            'system_recommendation': e.get('system_recommendation'), 'score': e.get('score'),
            'entry_close': entry, 'exit_close': exit_, 'resolved_on': str(exit_date.date()),
            'ret': ret, 'bench_ret': bench_ret, 'excess': ret - bench_ret,
            'mae': float(window['low'].min() / entry - 1), 'mfe': float(window['high'].max() / entry - 1),
            'benchmark': benchmark_label,
            'settled_at': pd.Timestamp.now().isoformat(timespec='seconds'),
        })
    store.append(new)
    logger.info(f"Settle: {len(new)} quyết định mới (horizon {horizon} phiên)")
    return new


# ----------------------------------------------------------------------------- lessons
def _group_stats(rows):
    ex = np.array([r['excess'] for r in rows], dtype=float)
    return {'n': len(ex), 'mean_excess': float(ex.mean()), 'hit_rate': float((ex > 0).mean())}


def build_lessons(outcomes, as_of, min_total=None, min_group=None):
    """
    Bài học thống kê từ các quyết định ĐÃ settle xong tại `as_of`. Trả về chuỗi rỗng nếu chưa đủ mẫu.
    Tránh nhìn trước: chỉ lấy outcome có resolved_on <= as_of.
    """
    cfg = config.COMMITTEE_CONFIG
    min_total = cfg['lessons_min_total'] if min_total is None else min_total
    min_group = cfg['lessons_min_group'] if min_group is None else min_group
    cutoff = str(pd.Timestamp(as_of).date())
    usable = [o for o in outcomes if o.get('resolved_on') and o['resolved_on'] <= cutoff and o.get('action')]
    if len(usable) < min_total:
        return ''

    lines = []
    for action, label in (('APPROVE', 'Mã được DUYỆT'), ('VETO', 'Mã bị VETO')):
        rows = [o for o in usable if o['action'] == action]
        if len(rows) >= min_group:
            s = _group_stats(rows)
            lines.append(f"- {label}: {s['n']} mã, lợi suất vượt benchmark TB {s['mean_excess']:+.1%} "
                         f"sau {usable[0]['horizon']} phiên, {s['hit_rate']:.0%} mã vượt benchmark")
    flags = sorted({f for o in usable if o['action'] == 'VETO' for f in o.get('risk_flags', [])})
    for flag in flags:
        rows = [o for o in usable if o['action'] == 'VETO' and flag in o.get('risk_flags', [])]
        if len(rows) >= min_group:
            s = _group_stats(rows)
            lines.append(f"- VETO có cờ {flag}: {s['n']} mã, vượt benchmark TB {s['mean_excess']:+.1%}")
    if not lines:
        return ''
    return ("THỐNG KÊ CÁC QUYẾT ĐỊNH TRƯỚC ĐÂY (đã settle, chỉ để định hướng mức thận trọng; "
            "KHÔNG được trích dẫn các con số này trong lập luận):\n" + "\n".join(lines) + "\n\n")


# ----------------------------------------------------------------------------- readiness
def cluster_bootstrap_diff(outcomes, n_resamples=2000, seed=42, confidence=0.95):
    """
    KTC cho (lợi suất vượt TB của VETO) - (của APPROVE), bootstrap theo CỤM NGÀY (các mã cùng ngày tương quan
    và cửa sổ 20 phiên chồng lấn nên coi từng ngày là một đơn vị).
    """
    dates = sorted({o['as_of'] for o in outcomes})
    idx_of = {d: i for i, d in enumerate(dates)}
    sv, cv = np.zeros(len(dates)), np.zeros(len(dates))
    sa, ca = np.zeros(len(dates)), np.zeros(len(dates))
    for o in outcomes:
        i = idx_of[o['as_of']]
        if o['action'] == 'VETO':
            sv[i] += o['excess']
            cv[i] += 1
        elif o['action'] == 'APPROVE':
            sa[i] += o['excess']
            ca[i] += 1
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(dates), size=(n_resamples, len(dates)))
    cv_s, ca_s = cv[draws].sum(axis=1), ca[draws].sum(axis=1)
    valid = (cv_s > 0) & (ca_s > 0)
    if valid.sum() < n_resamples * 0.5:
        return None
    diff = sv[draws].sum(axis=1)[valid] / cv_s[valid] - sa[draws].sum(axis=1)[valid] / ca_s[valid]
    alpha = (1 - confidence) / 2
    observed = sv.sum() / cv.sum() - sa.sum() / ca.sum()
    return {'observed': float(observed), 'ci_lower': float(np.quantile(diff, alpha)),
            'ci_upper': float(np.quantile(diff, 1 - alpha)), 'n_dates': len(dates)}


def evaluate_readiness(outcomes, ledger_entries, thresholds=None):
    """
    Đánh giá có nên chuyển hội đồng sang `enforce` hay chưa (tiêu chí trong docs/PHASE2_COMMITTEE.md).
    Verdict: NOT_READY (một tiêu chí tính được không đạt) | INCONCLUSIVE (thiếu mẫu/số liệu) |
             READY_PENDING_MANUAL (đạt hết tiêu chí tự động; vẫn cần bạn đọc tay lập luận VETO).
    Không bao giờ tự trả READY: tiêu chí đọc tay không thể tự động hoá.
    """
    t = thresholds or config.COMMITTEE_READINESS
    checks = []

    def add(name, value, rule, threshold, ok, sufficiency=False):
        status = 'NA' if value is None else ('PASS' if ok(value) else 'FAIL')
        checks.append({'name': name, 'value': value, 'rule': rule, 'threshold': threshold,
                       'status': status, 'sufficiency': sufficiency})

    settled = [o for o in outcomes if o.get('action')]
    veto = [o for o in settled if o['action'] == 'VETO']
    approve = [o for o in settled if o['action'] == 'APPROVE']
    span = None
    if settled:
        d = pd.to_datetime([o['as_of'] for o in settled])
        span = int((d.max() - d.min()).days)

    attempts = {}
    for e in ledger_entries:
        attempts.setdefault((str(e['as_of']), e['symbol']), []).append(e.get('status'))
    valid_rate = (sum('OK' in s for s in attempts.values()) / len(attempts)) if attempts else None
    ok_entries = {}
    for e in ledger_entries:
        if e.get('status') == 'OK':
            ok_entries[(str(e['as_of']), e['symbol'])] = e
    veto_rate = (sum(e['verdict']['action'] == 'VETO' for e in ok_entries.values()) / len(ok_entries)
                 if ok_entries else None)

    add('Số quyết định đã settle', len(settled), '>=', t['min_settled'], lambda v: v >= t['min_settled'], True)
    add('Số ngày trải dài', span, '>=', t['min_span_days'], lambda v: v >= t['min_span_days'], True)
    add('Số mã VETO đã settle', len(veto), '>=', t['min_group'], lambda v: v >= t['min_group'], True)
    add('Số mã APPROVE đã settle', len(approve), '>=', t['min_group'], lambda v: v >= t['min_group'], True)
    add('Tỷ lệ output hợp lệ', valid_rate, '>=', t['min_valid_rate'], lambda v: v >= t['min_valid_rate'])
    add('Tỷ lệ VETO', veto_rate, '<=', t['max_veto_rate'], lambda v: v <= t['max_veto_rate'])

    ci = (cluster_bootstrap_diff(settled, t['bootstrap_resamples'], config.BACKTEST_V2['seed'])
          if len(veto) >= 1 and len(approve) >= 1 else None)
    add('Chênh lệch VETO-APPROVE (cận trên KTC95)', ci['ci_upper'] if ci else None, '<', 0.0, lambda v: v < 0.0)
    checks.append({'name': 'Đọc tay 20 lập luận VETO ngẫu nhiên', 'value': None, 'rule': 'manual',
                   'threshold': None, 'status': 'MANUAL', 'sufficiency': False})

    auto = [c for c in checks if c['status'] != 'MANUAL']
    if any(c['status'] == 'FAIL' and not c['sufficiency'] for c in auto):
        verdict = 'NOT_READY'
    elif any(c['status'] != 'PASS' for c in auto):
        verdict = 'INCONCLUSIVE'
    else:
        verdict = 'READY_PENDING_MANUAL'
    return {'verdict': verdict, 'checks': checks, 'diff_ci': ci,
            'benchmarks': sorted({o.get('benchmark') for o in settled if o.get('benchmark')})}
