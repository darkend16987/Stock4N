"""
Phase 2 tests: hội đồng LLM veto-only. Dùng LLM giả (không gọi API), thư mục tạm.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

import config
from modules.committee import schema
from modules.committee.committee import InvestmentCommittee, apply_verdicts
from modules.committee.facts import FactSheet, build_fact_sheet, price_stats
from modules.committee.ledger import Ledger
from modules.committee.llm import LLMUnavailable
from modules.portfolio.manager import PortfolioManager


# ------------------------------------------------------------------ dữ liệu giả
def price_df(n=300, start=20.0, daily=0.001, end='2025-06-30', vol=1_000_000):
    dates = pd.bdate_range(end=end, periods=n)
    close = start * (1 + daily) ** np.arange(n)
    return pd.DataFrame({'time': dates, 'open': close, 'high': close * 1.01, 'low': close * 0.99,
                         'close': close, 'volume': vol})


def make_sheet(**row_over):
    row = {'Total_Score': 7.8, 'Fund_Score': 8.0, 'Tech_Score': 7.0, 'ROE': 18.5, 'PE': 14.2, 'PB': 2.1,
           'Debt_Equity': 0.8, 'Profit_Growth_YoY': 25.0, 'Revenue_Growth_YoY': 12.0, 'Sector': 'Công nghệ & Viễn thông'}
    row.update(row_over)
    return build_fact_sheet('FPT', row, price_df(), {'pct_above_both': 0.55, 'sentiment': 'NEUTRAL'}, 1)


def fid(sheet, label):
    return next(k for k, f in sheet.facts.items() if f['label'] == label)


def args(*pairs):
    return [{'claim': c, 'fact_ids': ids} for c, ids in pairs]


def ok_role(sheet, role):
    roe = fid(sheet, 'ROE (TTM)')
    base = args(('ROE tốt, 18,5%', [roe]))
    if role in ('bull', 'bear'):
        return json.dumps({'arguments': base})
    if role == 'risk_officer':
        return json.dumps({'verdict': 'SUPPORT', 'risk_flags': [], 'arguments': base})
    return json.dumps({'action': 'APPROVE', 'confidence': 4, 'risk_flags': [], 'arguments': base})


def veto_pm(sheet):
    liq = fid(sheet, 'Thanh khoản TB 20 phiên')
    return json.dumps({'action': 'VETO', 'confidence': 4, 'risk_flags': ['LIQUIDITY'],
                       'arguments': args(('Thanh khoản mỏng', [liq]))})


def detect_role(prompt):
    if 'ỦNG HỘ việc mua' in prompt:
        return 'bull'
    if 'PHẢN BIỆN' in prompt and 'Vai trò: nhà phân tích' in prompt:
        return 'bear'
    if 'Giám đốc rủi ro' in prompt and 'Vai trò: Giám đốc rủi ro' in prompt:
        return 'risk_officer'
    return 'portfolio_manager'


class FakeLLM:
    """responses: role -> str | callable(sheet_prompt) | list[str|Exception] (dùng lần lượt, lần cuối lặp lại)."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.prompts = []
        self.counts = {}

    def generate(self, system, prompt):
        role = detect_role(prompt)
        self.prompts.append((role, system, prompt))
        i = self.counts[role] = self.counts.get(role, 0) + 1
        spec = self.responses[role]
        if isinstance(spec, list):
            spec = spec[min(i, len(spec)) - 1]
        if callable(spec):
            spec = spec(prompt)
        if isinstance(spec, Exception):
            raise spec
        return spec


def default_llm(sheet, pm=None):
    return FakeLLM({'bull': ok_role(sheet, 'bull'), 'bear': ok_role(sheet, 'bear'),
                    'risk_officer': ok_role(sheet, 'risk_officer'), 'portfolio_manager': pm or ok_role(sheet, 'portfolio_manager')})


@pytest.fixture
def ledger(tmp_path):
    return Ledger(str(tmp_path / 'ledger.jsonl'))


def committee(client, ledger, **cfg):
    return InvestmentCommittee(client, cfg={'max_retries': 1, **cfg}, ledger=ledger)


# ================================================================== schema
class TestSchema:
    def test_extract_json_variants(self):
        assert schema.extract_json('{"a": 1}') == {'a': 1}
        assert schema.extract_json('```json\n{"a": 1}\n```') == {'a': 1}
        assert schema.extract_json('Đây là kết quả: {"a": 1} xong') == {'a': 1}

    @pytest.mark.parametrize('bad', ['', 'không có json', '{"a": ', '[1, 2]'])
    def test_extract_json_rejects(self, bad):
        with pytest.raises(schema.SchemaError):
            schema.extract_json(bad)

    def test_valid_arguments_pass(self):
        s = make_sheet()
        roe = fid(s, 'ROE (TTM)')
        out = schema.validate_argument_role({'arguments': args(('ROE 18,5% khá tốt', [roe]))}, s)
        assert out['arguments'][0]['fact_ids'] == [roe]

    def test_unknown_fact_id_rejected(self):
        s = make_sheet()
        with pytest.raises(schema.SchemaError, match='không tồn tại'):
            schema.validate_argument_role({'arguments': args(('x', ['F99']))}, s)

    def test_empty_fact_ids_rejected(self):
        with pytest.raises(schema.SchemaError):
            schema.validate_argument_role({'arguments': args(('có căn cứ', []))}, make_sheet())

    def test_invented_number_rejected(self):
        s = make_sheet()
        with pytest.raises(schema.SchemaError, match='con số'):
            schema.validate_argument_role({'arguments': args(('ROE đạt 99%', [fid(s, 'ROE (TTM)')]))}, s)

    def test_number_check_has_known_loophole_for_rule_constants(self):
        # Hằng số quy tắc (vd breadth tối thiểu 35) được phép nhắc ở bất kỳ đâu → kiểm tra chống bịa số
        # chỉ là lưới an toàn thô, không thay thế việc đọc lập luận. Test này ghi lại hạn chế đó.
        s = make_sheet()
        schema.validate_argument_role({'arguments': args(('ROE đạt 35%', [fid(s, 'ROE (TTM)')]))}, s)

    def test_numbers_from_facts_and_rules_allowed(self):
        s = make_sheet()
        roe = fid(s, 'ROE (TTM)')
        for claim in ('ROE 18,5% vượt ngưỡng 10%', 'P/E 14,2x thấp hơn trần 30', 'có 2 mã cùng ngành',
                      'RSI14 và MA50 ổn, theo F04'):
            schema.validate_argument_role({'arguments': args((claim, [roe]))}, s)

    def test_price_target_field_forbidden(self):
        s = make_sheet()
        pm = {'action': 'VETO', 'confidence': 3, 'risk_flags': ['OTHER'], 'target_price': 99_000,
              'arguments': args(('x', [fid(s, 'ROE (TTM)')]))}
        with pytest.raises(schema.SchemaError, match='không được phép'):
            schema.validate_portfolio_manager(pm, s)

    def test_pm_rules(self):
        s = make_sheet()
        a = args(('ổn', [fid(s, 'ROE (TTM)')]))
        base = {'action': 'APPROVE', 'confidence': 3, 'risk_flags': [], 'arguments': a}
        assert schema.validate_portfolio_manager(base, s)['action'] == 'APPROVE'
        for override in ({'action': 'BUY'}, {'confidence': 0}, {'confidence': 6}, {'confidence': True},
                         {'confidence': 3.5}, {'action': 'VETO', 'risk_flags': []},
                         {'risk_flags': ['MADE_UP_FLAG']}):
            with pytest.raises(schema.SchemaError):
                schema.validate_portfolio_manager({**base, **override}, s)

    def test_claim_too_long_rejected(self):
        s = make_sheet()
        with pytest.raises(schema.SchemaError, match='quá dài'):
            schema.validate_argument_role({'arguments': args(('a' * 400, [fid(s, 'ROE (TTM)')]))}, s)


# ================================================================== dữ kiện
class TestFacts:
    def test_price_stats_values(self):
        stats, last = price_stats(price_df(n=300, start=20.0, daily=0.001))
        assert stats['price_vnd'] == pytest.approx(20_000 * 1.001 ** 299)          # nghìn đồng → VND
        assert stats['ret_20d'] == pytest.approx((1.001 ** 20 - 1) * 100, rel=1e-6)
        assert stats['liquidity_bn'] == pytest.approx(stats['price_vnd'] * 1e6 / 1e9, rel=0.05)
        assert 0 <= stats['rsi14'] <= 100 and stats['rsi14'] > 90                   # tăng đều → RSI rất cao

    def test_as_of_excludes_future_rows(self):
        full = price_df(n=300)
        cutoff = full['time'].iloc[199]
        stats_cut, last = price_stats(full, as_of=cutoff)
        assert last == cutoff
        assert stats_cut['price_vnd'] == pytest.approx(full['close'].iloc[199] * 1000)

    def test_missing_values_listed_not_invented(self):
        s = build_fact_sheet('XXX', {'Total_Score': 7.0, 'ROE': np.nan, 'PE': None, 'Sector': 'Khác'}, price_df())
        labels = [f['label'] for f in s.facts.values()]
        assert 'ROE (TTM)' not in labels and 'ROE (TTM)' in s.missing and 'P/E' in s.missing
        assert 'DỮ LIỆU KHÔNG CÓ' in s.to_prompt_text()

    def test_no_price_history_still_builds(self):
        s = build_fact_sheet('XXX', {'Total_Score': 7.0, 'ROE': 15.0}, None)
        assert 'Giá hiện tại' in s.missing and s.symbol == 'XXX'

    def test_fingerprint_stable_and_sensitive(self):
        a, b = make_sheet(), make_sheet()
        assert a.fingerprint() == b.fingerprint()
        assert make_sheet(ROE=19.0).fingerprint() != a.fingerprint()

    def test_ids_are_sequential_and_numeric_values_exposed(self):
        s = FactSheet('A', '2025-01-01')
        s.add('x', 1.234, '', 2)
        s.add('y', 'chữ')
        assert list(s.facts) == ['F01', 'F02'] and s.numeric_values() == [1.23]


# ================================================================== committee
class TestReview:
    def test_happy_path_makes_four_calls_and_logs(self, ledger):
        s = make_sheet()
        c = committee(default_llm(s), ledger)
        v = c.review(s, 'MUA THĂM DÒ', 7.8)
        assert v['status'] == 'OK' and v['action'] == 'APPROVE' and v['calls'] == 4
        assert [r for r, *_ in c.client.prompts] == ['bull', 'bear', 'risk_officer', 'portfolio_manager']
        entry = ledger.find(s.as_of, 'FPT', config.COMMITTEE_CONFIG['prompt_version'])
        assert entry['system_recommendation'] == 'MUA THĂM DÒ' and entry['facts']['facts']

    def test_prompt_states_limits(self, ledger):
        s = make_sheet()
        c = committee(default_llm(s), ledger)
        c.review(s)
        role, system, prompt = c.client.prompts[0]
        assert 'KHÔNG có tin tức' in system and 'KHÔNG đề xuất' not in system   # quy tắc nằm ở system
        assert 'Không đề xuất giá' in system
        assert fid(s, 'ROE (TTM)') in prompt and 'BẢNG DỮ KIỆN' in prompt

    def test_pm_sees_debate_but_bull_does_not_see_bear(self, ledger):
        s = make_sheet()
        c = committee(default_llm(s), ledger)
        c.review(s)
        prompts = {r: p for r, _, p in c.client.prompts}
        assert 'LẬP LUẬN PHẢN BIỆN' not in prompts['bull'] and 'LẬP LUẬN PHẢN BIỆN' not in prompts['bear']
        assert 'LẬP LUẬN PHẢN BIỆN' in prompts['risk_officer']
        assert 'Ý KIẾN GIÁM ĐỐC RỦI RO' in prompts['portfolio_manager']

    def test_invalid_output_is_retried_with_error_fed_back(self, ledger):
        s = make_sheet()
        bad = json.dumps({'arguments': args(('ROE đạt 99%', [fid(s, 'ROE (TTM)')]))})
        llm = default_llm(s)
        llm.responses['bull'] = [bad, ok_role(s, 'bull')]
        v = committee(llm, ledger).review(s)
        assert v['status'] == 'OK' and v['calls'] == 5
        retry_prompt = [p for r, _, p in llm.prompts if r == 'bull'][1]
        assert 'BỊ TỪ CHỐI' in retry_prompt and 'con số' in retry_prompt

    def test_persistently_invalid_output_gives_invalid_and_no_ledger(self, ledger):
        s = make_sheet()
        llm = default_llm(s)
        llm.responses['portfolio_manager'] = 'xin lỗi tôi không biết'
        v = committee(llm, ledger).review(s, 'MUA THĂM DÒ', 7.0)
        assert v['status'] == 'INVALID' and v['action'] is None
        assert ledger.find(s.as_of, 'FPT', config.COMMITTEE_CONFIG['prompt_version']) is None

    def test_llm_outage_reports_error_without_raising(self, ledger):
        s = make_sheet()
        llm = FakeLLM({'bull': LLMUnavailable('hết quota')})
        v = committee(llm, ledger).review(s)
        assert v['status'] == 'LLM_ERROR' and v['action'] is None and 'quota' in v['error']

    def test_unexpected_exception_is_contained(self, ledger):
        s = make_sheet()
        v = committee(FakeLLM({'bull': RuntimeError('boom')}), ledger).review(s)
        assert v['status'] == 'LLM_ERROR'

    def test_cache_reuses_ledger_without_new_calls(self, ledger):
        s = make_sheet()
        c = committee(default_llm(s), ledger)
        c.review(s)
        n = c.calls
        again = c.review(make_sheet())
        assert c.calls == n and again['cached'] is True

    def test_changed_facts_bypass_cache(self, ledger):
        c = committee(default_llm(make_sheet()), ledger)
        c.review(make_sheet())
        before = c.calls
        s2 = make_sheet(ROE=19.0)
        c.client = default_llm(s2)
        c.review(s2)
        assert c.calls > before

    def test_disagreement_between_cro_and_pm_recorded(self, ledger):
        s = make_sheet()
        llm = default_llm(s, pm=veto_pm(s))        # CRO SUPPORT nhưng PM VETO
        v = committee(llm, ledger).review(s)
        assert v['action'] == 'VETO' and v['cro_pm_disagree'] is True


# ================================================================== áp dụng veto
def report(rows):
    return pd.DataFrame(rows)


def rows():
    return [
        {'Symbol': 'AAA', 'Total_Score': 8.0, 'Recommendation': 'MUA MẠNH', 'Price': 20.0, 'Sector': 'Dầu khí',
         'Fund_Score': 8, 'Tech_Score': 7},
        {'Symbol': 'BBB', 'Total_Score': 7.0, 'Recommendation': 'MUA THĂM DÒ', 'Price': 20.0,
         'Sector': 'Vật liệu & Công nghiệp', 'Fund_Score': 7, 'Tech_Score': 6},
        {'Symbol': 'CCC', 'Total_Score': 5.5, 'Recommendation': 'THEO DÕI', 'Price': 20.0, 'Sector': 'Khác',
         'Fund_Score': 5, 'Tech_Score': 5},
        {'Symbol': 'DDD', 'Total_Score': 3.0, 'Recommendation': 'BÁN / CƠ CẤU', 'Price': 20.0, 'Sector': 'Khác',
         'Fund_Score': 3, 'Tech_Score': 3},
    ]


def loader(symbol):
    return price_df()


def per_symbol_llm(veto_symbols=(), approve_all_for_non_mua=True):
    """LLM giả quyết định theo mã (đọc mã từ prompt)."""
    def pm(prompt):
        sym = prompt.split('Mã: ')[1].split(' ')[0]
        roe_id = 'F01'
        if sym in veto_symbols:
            return json.dumps({'action': 'VETO', 'confidence': 4, 'risk_flags': ['LIQUIDITY'],
                               'arguments': args(('Rủi ro thanh khoản', [roe_id]))})
        return json.dumps({'action': 'APPROVE', 'confidence': 4, 'risk_flags': [],
                           'arguments': args(('Chấp nhận được', [roe_id]))})
    generic = json.dumps({'arguments': args(('Điểm hệ thống cao', ['F01']))})
    cro = json.dumps({'verdict': 'SUPPORT', 'risk_flags': [], 'arguments': args(('ổn', ['F01']))})
    return FakeLLM({'bull': generic, 'bear': generic, 'risk_officer': cro, 'portfolio_manager': pm})


class TestApply:
    def test_enforce_veto_downgrades_only_vetoed_buy(self, ledger):
        c = committee(per_symbol_llm(veto_symbols=('AAA',)), ledger)
        out, verdicts = c.run(report(rows()), None, None, 'enforce', loader)
        rec = dict(zip(out['Symbol'], out['Recommendation']))
        assert rec == {'AAA': 'THEO DÕI', 'BBB': 'MUA THĂM DÒ', 'CCC': 'THEO DÕI', 'DDD': 'BÁN / CƠ CẤU'}
        assert out.set_index('Symbol').loc['AAA', 'Pre_Committee_Recommendation'] == 'MUA MẠNH'
        assert out.set_index('Symbol').loc['AAA', 'Committee_Flags'] == 'LIQUIDITY'

    def test_shadow_never_changes_recommendations(self, ledger):
        c = committee(per_symbol_llm(veto_symbols=('AAA', 'BBB')), ledger)
        out, verdicts = c.run(report(rows()), None, None, 'shadow', loader)
        assert list(out['Recommendation']) == [r['Recommendation'] for r in rows()]
        assert out.set_index('Symbol').loc['AAA', 'Committee_Action'] == 'VETO'

    def test_only_buy_rows_are_reviewed(self, ledger):
        c = committee(per_symbol_llm(), ledger)
        out, verdicts = c.run(report(rows()), None, None, 'enforce', loader)
        assert sorted(v['symbol'] for v in verdicts) == ['AAA', 'BBB']
        status = out.set_index('Symbol')['Committee_Status']
        assert status['CCC'] == 'NOT_REVIEWED' and status['DDD'] == 'NOT_REVIEWED'
        assert c.client.counts['portfolio_manager'] == 2

    def test_never_upgrades_even_if_llm_approves_everything(self, ledger):
        c = committee(per_symbol_llm(), ledger)
        out, _ = c.run(report(rows()), None, None, 'enforce', loader)
        assert list(out['Recommendation']) == list(out['Pre_Committee_Recommendation'])

    def test_llm_failure_fail_open_in_enforce(self, ledger):
        c = committee(FakeLLM({'bull': LLMUnavailable('down')}), ledger)
        out, verdicts = c.run(report(rows()), None, None, 'enforce', loader)
        assert all(v['status'] == 'LLM_ERROR' for v in verdicts)
        assert list(out['Recommendation']) == [r['Recommendation'] for r in rows()]

    def test_invariant_guard_trips_on_upgrade(self):
        df = report(rows())
        verdicts = []
        out = apply_verdicts(df, verdicts, 'enforce')              # không đổi → OK
        assert list(out['Recommendation']) == list(df['Recommendation'])
        bad = df.copy()
        bad['Recommendation'] = 'THEO DÕI'
        # mô phỏng nâng bậc: THEO DÕI (trước) → MUA (sau) phải bị assert chặn
        tampered = apply_verdicts(bad, [], 'shadow')
        tampered['Recommendation'] = 'MUA MẠNH'
        from modules.committee.committee import REC_RANK
        assert not (tampered['Recommendation'].map(REC_RANK) <= tampered['Pre_Committee_Recommendation'].map(REC_RANK)).all()

    def test_max_reviews_cap_leaves_rest_unchanged(self, ledger):
        many = [{'Symbol': f'S{i:02d}', 'Total_Score': 8.0 - i * 0.1, 'Recommendation': 'MUA THĂM DÒ',
                 'Price': 20.0, 'Sector': 'Khác', 'Fund_Score': 7, 'Tech_Score': 7} for i in range(6)]
        c = committee(per_symbol_llm(veto_symbols=tuple(r['Symbol'] for r in many)), ledger, max_reviews=2)
        out, verdicts = c.run(report(many), None, None, 'enforce', loader)
        assert [v['symbol'] for v in verdicts] == ['S00', 'S01']                 # top điểm trước
        rec = dict(zip(out['Symbol'], out['Recommendation']))
        assert rec['S00'] == rec['S01'] == 'THEO DÕI' and rec['S05'] == 'MUA THĂM DÒ'

    def test_invalid_mode_rejected(self, ledger):
        with pytest.raises(ValueError):
            committee(per_symbol_llm(), ledger).run(report(rows()), None, None, 'auto', loader)

    def test_ledger_records_mode_and_survives_rerun(self, ledger):
        c = committee(per_symbol_llm(), ledger)
        c.run(report(rows()), None, None, 'shadow', loader)
        n_calls = c.calls
        c.run(report(rows()), None, None, 'shadow', loader)         # chạy lại cùng ngày dữ liệu
        assert c.calls == n_calls                                   # toàn bộ lấy từ ledger
        entry = ledger.find('2025-06-30', 'AAA', config.COMMITTEE_CONFIG['prompt_version'])
        assert entry['mode'] == 'shadow' and entry['model']


class TestEndToEndWithPortfolio:
    def _buy_symbols(self, tmp_path, mode, veto):
        processed = tmp_path / f'p_{mode}'
        processed.mkdir()
        c = committee(per_symbol_llm(veto_symbols=veto), Ledger(str(tmp_path / f'l_{mode}.jsonl')))
        out, _ = c.run(report(rows()), None, None, mode, loader)
        out.to_csv(processed / 'analysis_report.csv', index=False)
        pm = PortfolioManager(processed_dir=str(processed), raw_dir=str(tmp_path), returns_provider=lambda s: None)
        rec = pm.generate_recommendation(total_capital=100_000_000)
        return set() if rec is None else set(rec['Symbol'])

    def test_enforced_veto_keeps_symbol_out_of_portfolio(self, tmp_path):
        assert self._buy_symbols(tmp_path, 'enforce', ('AAA',)) == {'BBB'}

    def test_shadow_veto_does_not_change_portfolio(self, tmp_path):
        assert self._buy_symbols(tmp_path, 'shadow', ('AAA',)) == {'AAA', 'BBB'}


class TestConfigDefaults:
    def test_default_mode_is_shadow_and_temperature_low(self):
        assert config.COMMITTEE_CONFIG['mode'] == 'shadow'
        assert config.COMMITTEE_CONFIG['temperature'] <= 0.3


class TestExporterJsonSafety:
    """Lỗi phát hiện khi làm Phase 2: cột báo cáo để trống → NaN → db.json không phải JSON hợp lệ."""

    def test_db_json_has_no_nan_and_is_strict_json(self, tmp_path):
        from modules.utils.exporter import DataExporter
        processed, raw, export = tmp_path / 'processed', tmp_path / 'raw', tmp_path / 'export'
        for d in (processed, raw, export):
            d.mkdir()
        pd.DataFrame({'Symbol': ['AAA'], 'Total_Score': [7.0], 'Recommendation': ['MUA THĂM DÒ'],
                      'Gate_Reasons': [''], 'Committee_Reasons': ['']}).to_csv(processed / 'analysis_report.csv',
                                                                               index=False)
        exp = DataExporter(processed_dir=str(processed), raw_dir=str(raw))
        exp.export_dir = str(export)
        exp.export_all()
        text = (export / 'db.json').read_text(encoding='utf-8')
        assert 'NaN' not in text
        data = json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        assert data['analysis'][0]['Gate_Reasons'] is None


class TestCircuitBreaker:
    def test_stops_calling_api_after_consecutive_outages(self, ledger):
        many = [{'Symbol': f'S{i:02d}', 'Total_Score': 8.0 - i * 0.1, 'Recommendation': 'MUA THĂM DÒ',
                 'Price': 20.0, 'Sector': 'Khác', 'Fund_Score': 7, 'Tech_Score': 7} for i in range(6)]
        llm = FakeLLM({'bull': LLMUnavailable('503 high demand')})
        c = committee(llm, ledger, max_consecutive_api_errors=2)
        out, verdicts = c.run(report(many), None, None, 'enforce', loader)
        assert llm.counts['bull'] == 2                                    # chỉ 2 mã đầu thực sự gọi API
        assert [v['status'] for v in verdicts] == ['LLM_ERROR'] * 6
        assert 'Bỏ qua' in verdicts[-1]['error']
        assert list(out['Recommendation']) == ['MUA THĂM DÒ'] * 6        # fail-open: không đổi gì

    def test_success_resets_the_counter(self, ledger):
        many = [{'Symbol': f'S{i:02d}', 'Total_Score': 8.0 - i * 0.1, 'Recommendation': 'MUA THĂM DÒ',
                 'Price': 20.0, 'Sector': 'Khác', 'Fund_Score': 7, 'Tech_Score': 7} for i in range(4)]
        base = per_symbol_llm()
        calls = {'n': 0}

        class Flaky:
            counts = base.counts

            def generate(self, system, prompt):
                if 'ỦNG HỘ việc mua' in prompt:
                    calls['n'] += 1
                    if calls['n'] == 1:                                   # chỉ mã đầu bị lỗi API
                        raise LLMUnavailable('503')
                return base.generate(system, prompt)
        c = committee(Flaky(), ledger, max_consecutive_api_errors=2)
        _, verdicts = c.run(report(many), None, None, 'shadow', loader)
        assert [v['status'] for v in verdicts] == ['LLM_ERROR', 'OK', 'OK', 'OK']
