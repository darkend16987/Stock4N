"""
Phase 3 tests: settle (đối chiếu kết quả), bài học thống kê, đánh giá sẵn sàng enforce.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

import config
from modules.committee import memory
from modules.committee.committee import InvestmentCommittee
from modules.committee.ledger import Ledger
from modules.committee.memory import OutcomeStore, build_lessons, evaluate_readiness, settle_pending

pytest.importorskip('talib')
from modules.simulation.point_in_time import PriceBook  # noqa: E402

DATES = pd.bdate_range('2025-01-02', periods=120)
VERSION = config.COMMITTEE_CONFIG['prompt_version']


def write_prices(raw, symbol, daily=0.01, start=10.0):
    close = start * (1 + daily) ** np.arange(len(DATES))
    pd.DataFrame({'time': DATES, 'open': close, 'high': close * 1.02, 'low': close * 0.98, 'close': close,
                  'volume': 1_000_000}).to_csv(os.path.join(raw, f'{symbol}_price.csv'), index=False)


@pytest.fixture
def env(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    for sym in ('AAA', 'BBB'):
        write_prices(str(raw), sym, daily=0.01 if sym == 'AAA' else -0.002)
    book = PriceBook(str(raw), ['AAA', 'BBB'])
    bench = pd.Series(100 * 1.005 ** np.arange(len(DATES)), index=DATES)
    return {'book': book, 'bench': bench, 'store': OutcomeStore(str(tmp_path / 'out.jsonl')),
            'ledger': Ledger(str(tmp_path / 'led.jsonl')), 'tmp': tmp_path}


def entry(as_of, symbol, action='APPROVE', flags=(), status='OK', version=VERSION, rec='MUA THĂM DÒ'):
    e = {'as_of': str(as_of), 'symbol': symbol, 'prompt_version': version, 'status': status,
         'system_recommendation': rec, 'score': 7.0}
    if status == 'OK':
        e['verdict'] = {'action': action, 'risk_flags': list(flags), 'status': 'OK'}
    return e


# ================================================================== settle
class TestSettle:
    def test_exact_returns_and_window(self, env):
        as_of = DATES[30].date()
        out = settle_pending([entry(as_of, 'AAA')], env['store'], env['book'], env['bench'], 'TEST', horizon=20)
        assert len(out) == 1
        o = out[0]
        assert o['resolved_on'] == str(DATES[50].date())
        assert o['ret'] == pytest.approx(1.01 ** 20 - 1)
        assert o['bench_ret'] == pytest.approx(1.005 ** 20 - 1)
        assert o['excess'] == pytest.approx((1.01 ** 20 - 1) - (1.005 ** 20 - 1))
        assert o['mae'] == pytest.approx(-0.02)                        # low = 0.98 × close của phiên đầu cửa sổ
        assert o['mfe'] == pytest.approx(1.02 * 1.01 ** 20 - 1)         # high = 1.02 × close của phiên cuối
        assert o['benchmark'] == 'TEST' and o['action'] == 'APPROVE'

    def test_negative_stock_negative_excess(self, env):
        out = settle_pending([entry(DATES[30].date(), 'BBB')], env['store'], env['book'], env['bench'], 'T', 20)
        assert out[0]['ret'] < 0 and out[0]['excess'] < out[0]['ret']

    def test_incomplete_window_stays_pending(self, env):
        out = settle_pending([entry(DATES[105].date(), 'AAA')], env['store'], env['book'], env['bench'], 'T', 20)
        assert out == [] and env['store'].read() == []

    def test_idempotent(self, env):
        entries = [entry(DATES[30].date(), 'AAA'), entry(DATES[31].date(), 'BBB')]
        settle_pending(entries, env['store'], env['book'], env['bench'], 'T', 20)
        again = settle_pending(entries, env['store'], env['book'], env['bench'], 'T', 20)
        assert again == [] and len(env['store'].read()) == 2

    def test_skips_failed_unknown_and_misaligned_entries(self, env):
        entries = [entry(DATES[30].date(), 'AAA', status='INVALID'),
                   entry(DATES[30].date(), 'ZZZ'),
                   entry('2025-01-04', 'AAA')]                   # thứ Bảy: không phải phiên nào
        assert settle_pending(entries, env['store'], env['book'], env['bench'], 'T', 20) == []

    def test_horizon_is_respected(self, env):
        out = settle_pending([entry(DATES[30].date(), 'AAA')], env['store'], env['book'], env['bench'], 'T', 5)
        assert out[0]['resolved_on'] == str(DATES[35].date()) and out[0]['horizon'] == 5

    def test_default_horizon_is_20_sessions(self, env):
        out = settle_pending([entry(DATES[30].date(), 'AAA')], env['store'], env['book'], env['bench'], 'T')
        assert out[0]['horizon'] == 20 == config.COMMITTEE_CONFIG['settle_horizon']


# ================================================================== lessons
def outcomes(n_veto=12, n_approve=12, resolved_start='2025-03-01', veto_excess=-0.05, approve_excess=0.02):
    rows, d = [], pd.Timestamp(resolved_start)
    for i in range(n_veto + n_approve):
        action = 'VETO' if i < n_veto else 'APPROVE'
        rows.append({'as_of': str((d - pd.Timedelta(days=30)).date()), 'symbol': f'S{i}',
                     'resolved_on': str((d + pd.Timedelta(days=i)).date()), 'action': action, 'horizon': 20,
                     'risk_flags': ['LIQUIDITY'] if action == 'VETO' else [],
                     'excess': veto_excess if action == 'VETO' else approve_excess, 'benchmark': 'T'})
    return rows


class TestLessons:
    def test_empty_when_too_few_outcomes(self):
        assert build_lessons(outcomes(5, 5), '2026-01-01') == ''

    def test_statistics_text_and_no_quote_instruction(self):
        text = build_lessons(outcomes(), '2026-01-01')
        assert 'Mã bị VETO: 12 mã' in text and 'Mã được DUYỆT: 12 mã' in text
        assert '-5.0%' in text and '+2.0%' in text and 'VETO có cờ LIQUIDITY' in text
        assert 'KHÔNG được trích dẫn' in text

    def test_small_groups_are_omitted(self):
        text = build_lessons(outcomes(n_veto=3, n_approve=25), '2026-01-01')
        assert 'Mã bị VETO' not in text and 'Mã được DUYỆT: 25 mã' in text

    def test_only_outcomes_resolved_by_as_of_are_used(self):
        rows = outcomes(12, 12, resolved_start='2025-03-01')
        early = build_lessons(rows, '2025-03-15')       # chỉ ~15 outcome đã resolved → dưới ngưỡng tổng
        late = build_lessons(rows, '2026-01-01')
        assert early == '' and late != ''

    def test_future_resolution_changes_nothing_before_it(self):
        base = outcomes(12, 12)
        extra = base + [{**base[0], 'symbol': 'LATE', 'resolved_on': '2025-12-01', 'excess': -0.9}]
        cutoff = '2025-04-30'
        assert build_lessons(base, cutoff) == build_lessons(extra, cutoff)       # outcome tương lai bị bỏ qua
        assert build_lessons(base, '2026-01-01') != build_lessons(extra, '2026-01-01')


# ================================================================== readiness
def readiness_inputs(n_dates=80, veto_excess=-0.05, approve_excess=0.02, veto_per_date=1, approve_per_date=2,
                     seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2025-01-01', periods=n_dates)
    outs, entries = [], []
    for d in dates:
        for k in range(veto_per_date + approve_per_date):
            action = 'VETO' if k < veto_per_date else 'APPROVE'
            mean = veto_excess if action == 'VETO' else approve_excess
            outs.append({'as_of': str(d.date()), 'symbol': f'S{k}', 'action': action, 'excess': float(mean + rng.normal(0, 0.03)),
                         'resolved_on': str((d + pd.Timedelta(days=28)).date()), 'benchmark': 'T', 'horizon': 20})
            entries.append(entry(d.date(), f'S{k}', action=action, flags=['LIQUIDITY'] if action == 'VETO' else []))
    return outs, entries


class TestReadiness:
    def test_empty_is_inconclusive(self):
        r = evaluate_readiness([], [])
        assert r['verdict'] == 'INCONCLUSIVE'

    def test_good_evidence_is_ready_pending_manual_never_ready(self):
        outs, entries = readiness_inputs()
        r = evaluate_readiness(outs, entries)
        assert r['verdict'] == 'READY_PENDING_MANUAL'
        assert r['diff_ci']['ci_upper'] < 0
        assert any(c['status'] == 'MANUAL' for c in r['checks'])

    def test_vetoes_that_do_not_underperform_are_not_ready(self):
        outs, entries = readiness_inputs(veto_excess=0.03, approve_excess=0.02)
        assert evaluate_readiness(outs, entries)['verdict'] == 'NOT_READY'

    def test_too_many_vetoes_not_ready(self):
        outs, entries = readiness_inputs(veto_per_date=2, approve_per_date=1)      # 67% VETO
        r = evaluate_readiness(outs, entries)
        assert r['verdict'] == 'NOT_READY'
        assert next(c for c in r['checks'] if c['name'] == 'Tỷ lệ VETO')['status'] == 'FAIL'

    def test_low_valid_rate_not_ready(self):
        outs, entries = readiness_inputs()
        for d in pd.bdate_range('2025-06-01', periods=10):                         # 10 lần chỉ có lỗi
            entries.append(entry(d.date(), 'SX', status='INVALID'))
        r = evaluate_readiness(outs, entries)
        valid = next(c for c in r['checks'] if c['name'] == 'Tỷ lệ output hợp lệ')
        assert valid['value'] == pytest.approx(240 / 250) and valid['status'] == 'PASS'
        for d in pd.bdate_range('2025-07-01', periods=30):
            entries.append(entry(d.date(), 'SY', status='LLM_ERROR'))
        assert evaluate_readiness(outs, entries)['verdict'] == 'NOT_READY'

    def test_short_history_is_inconclusive_not_pass(self):
        outs, entries = readiness_inputs(n_dates=15)
        assert evaluate_readiness(outs, entries)['verdict'] == 'INCONCLUSIVE'

    def test_bootstrap_deterministic_and_signed(self):
        outs, _ = readiness_inputs()
        a, b = memory.cluster_bootstrap_diff(outs, 500, 1), memory.cluster_bootstrap_diff(outs, 500, 1)
        assert a == b and a['observed'] < 0 and a['ci_lower'] < a['observed'] < a['ci_upper']

    def test_bootstrap_needs_both_groups(self):
        outs, _ = readiness_inputs(approve_per_date=0)
        assert memory.cluster_bootstrap_diff(outs, 200, 1) is None


# ================================================================== tích hợp với hội đồng
class TestCommitteeIntegration:
    def _sheet(self):
        from modules.committee.facts import build_fact_sheet
        price = pd.DataFrame({'time': DATES, 'open': 10.0, 'high': 10.2, 'low': 9.8, 'close': 10.0, 'volume': 1_000_000})
        return build_fact_sheet('FPT', {'Total_Score': 7.5, 'ROE': 18.5, 'Sector': 'X'}, price)

    def _llm(self, pm_claim='Rủi ro thanh khoản'):
        class Fake:
            def __init__(self):
                self.prompts = []

            def generate(self, system, prompt):
                role = ('bull' if 'ỦNG HỘ việc mua' in prompt else
                        'bear' if 'Vai trò: nhà phân tích' in prompt else
                        'risk_officer' if 'Vai trò: Giám đốc rủi ro' in prompt else 'pm')
                self.prompts.append((role, prompt))
                arg = [{'claim': 'ổn', 'fact_ids': ['F01']}]
                if role in ('bull', 'bear'):
                    return json.dumps({'arguments': arg})
                if role == 'risk_officer':
                    return json.dumps({'verdict': 'SUPPORT', 'risk_flags': [], 'arguments': arg})
                return json.dumps({'action': 'APPROVE', 'confidence': 3, 'risk_flags': [],
                                   'arguments': [{'claim': pm_claim, 'fact_ids': ['F01']}]})
        return Fake()

    def test_lessons_reach_only_the_portfolio_manager(self, tmp_path):
        llm = self._llm()
        c = InvestmentCommittee(llm, ledger=Ledger(str(tmp_path / 'l.jsonl')),
                                lessons_provider=lambda as_of: "THỐNG KÊ CÁC QUYẾT ĐỊNH TRƯỚC ĐÂY: abc\n\n")
        v = c.review(self._sheet())
        by_role = {r: p for r, p in llm.prompts}
        assert 'THỐNG KÊ CÁC QUYẾT ĐỊNH TRƯỚC ĐÂY' in by_role['pm']
        assert all('THỐNG KÊ' not in by_role[r] for r in ('bull', 'bear', 'risk_officer'))
        assert v['lessons_hash']

    def test_pm_quoting_a_lesson_number_is_rejected(self, tmp_path):
        llm = self._llm(pm_claim='VETO từng đạt hiệu quả 7,3% so với benchmark')
        c = InvestmentCommittee(llm, ledger=Ledger(str(tmp_path / 'l.jsonl')), cfg={'max_retries': 0},
                                lessons_provider=lambda as_of: "THỐNG KÊ: VETO vượt benchmark 7,3%\n\n")
        v = c.review(self._sheet())
        assert v['status'] == 'INVALID' and 'con số' in v['error']

    def test_failures_are_logged_but_do_not_block_retry(self, tmp_path):
        class Down:
            def generate(self, system, prompt):
                from modules.committee.llm import LLMUnavailable
                raise LLMUnavailable('down')
        ledger = Ledger(str(tmp_path / 'l.jsonl'))
        sheet = self._sheet()
        InvestmentCommittee(Down(), ledger=ledger).review(sheet)
        statuses = [e['status'] for e in ledger.entries()]
        assert statuses == ['LLM_ERROR'] and ledger.find(sheet.as_of, 'FPT', VERSION) is None
        # lần sau API hoạt động: chạy bình thường (không bị lần lỗi chặn)
        c = InvestmentCommittee(self._llm(), ledger=ledger)
        assert c.review(sheet)['status'] == 'OK'
        assert [e['status'] for e in ledger.entries()] == ['LLM_ERROR', 'OK']


class TestConfig:
    def test_prompt_version_bumped_for_lessons_and_horizon_matches_strategy(self):
        assert config.COMMITTEE_CONFIG['prompt_version'] != 'v1'
        assert config.COMMITTEE_CONFIG['settle_horizon'] == 20
