"""
Phase 0 tests: RuleGate, config consistency, price-unit fix, scorer gating.
Không cần mạng, không cần dữ liệu thật.
"""
import numpy as np
import pytest

import config
from modules.analysis.rule_gate import RuleGate
from modules.utils.units import price_to_vnd


def good_row(**overrides):
    row = {
        'Symbol': 'FPT', 'Price': 90.6, 'ROE': 25.0, 'PE': 15.0,
        'Debt_Equity': 1.0, 'Total_Score': 7.8,
    }
    row.update(overrides)
    return row


OPEN_MARKET = {'allow_new_buys': True, 'sentiment': 'BULLISH', 'pct_above_both': 0.65}


class TestRuleGate:
    gate = RuleGate()

    def test_good_row_passes(self):
        res = self.gate.evaluate(good_row(), OPEN_MARKET)
        assert res['passed'] and not res['reasons']

    def test_low_roe_blocks(self):
        res = self.gate.evaluate(good_row(ROE=8.0), OPEN_MARKET)
        assert not res['passed'] and any('ROE' in r for r in res['reasons'])

    def test_missing_roe_blocks_fail_closed(self):
        res = self.gate.evaluate(good_row(ROE=np.nan), OPEN_MARKET)
        assert not res['passed'] and any('Thiếu ROE' in r for r in res['reasons'])

    def test_high_pe_blocks(self):
        res = self.gate.evaluate(good_row(PE=45.0), OPEN_MARKET)
        assert not res['passed'] and any('P/E' in r for r in res['reasons'])

    def test_missing_pe_warns_but_passes(self):
        res = self.gate.evaluate(good_row(PE=np.nan), OPEN_MARKET)
        assert res['passed'] and any('P/E' in w for w in res['warnings'])

    def test_high_debt_blocks_non_financial(self):
        res = self.gate.evaluate(good_row(Debt_Equity=2.5), OPEN_MARKET)
        assert not res['passed'] and any('Nợ/Vốn' in r for r in res['reasons'])

    def test_bank_is_exempt_from_debt_equity(self):
        # Ngân hàng có Nợ/Vốn ~ 10 là bình thường
        res = self.gate.evaluate(good_row(Symbol='VCB', Debt_Equity=9.7), OPEN_MARKET)
        assert res['passed']

    def test_real_estate_gets_relaxed_debt_cap(self):
        # VHM: D/E 2.17 > 2.0 chung nhưng ≤ 2.5 trần riêng của BĐS
        assert self.gate.evaluate(good_row(Symbol='VHM', Debt_Equity=2.17), OPEN_MARKET)['passed']
        res = self.gate.evaluate(good_row(Symbol='VHM', Debt_Equity=2.8), OPEN_MARKET)
        assert not res['passed'] and any('2.5' in r for r in res['reasons'])

    def test_relaxed_cap_does_not_leak_to_other_sectors(self):
        res = self.gate.evaluate(good_row(Symbol='FPT', Debt_Equity=2.17), OPEN_MARKET)
        assert not res['passed']

    def test_penny_blocked_in_thousand_vnd_unit(self):
        res = self.gate.evaluate(good_row(Price=8.5), OPEN_MARKET)   # 8,500đ
        assert not res['passed'] and any('Penny' in r for r in res['reasons'])

    def test_high_price_stock_is_not_penny(self):
        # FRT 167.3 (nghìn đồng) = 167,300đ — không phải penny
        res = self.gate.evaluate(good_row(Symbol='FRT', Price=167.3), OPEN_MARKET)
        assert res['passed']

    def test_market_not_allowing_buys_blocks(self):
        mf = {'allow_new_buys': False, 'sentiment': 'BEARISH', 'pct_above_both': 0.30}
        res = self.gate.evaluate(good_row(), mf)
        assert not res['passed']

    def test_breadth_below_floor_blocks_even_if_allowed(self):
        mf = {'allow_new_buys': True, 'sentiment': 'NEUTRAL', 'pct_above_both': 0.30}
        res = self.gate.evaluate(good_row(), mf)
        assert not res['passed'] and any('Breadth' in r for r in res['reasons'])

    def test_no_market_filter_skips_breadth_only(self):
        res = self.gate.evaluate(good_row(), None)
        assert res['passed']


class TestConfigConsistency:
    def test_no_duplicate_symbols(self):
        assert len(config.VN100_SYMBOLS) == len(set(config.VN100_SYMBOLS))

    def test_every_symbol_has_sector(self):
        missing = [s for s in config.VN100_SYMBOLS if s not in config.SECTOR_MAP]
        assert missing == []

    def test_skill_uses_config_hard_rules(self):
        from modules.analysis.stock_option_skill import StockOptionSkill
        assert StockOptionSkill.HARD_RULES == config.HARD_RULES

    def test_hard_rules_follow_portfolio_and_thresholds(self):
        assert config.HARD_RULES['min_score'] == config.RECOMMENDATION_THRESHOLDS['buy']
        assert config.HARD_RULES['max_positions'] == config.PORTFOLIO_CONFIG['max_positions']
        assert config.HARD_RULES['cash_reserve'] == config.PORTFOLIO_CONFIG['cash_reserve_pct']

    def test_sector_cap_guaranteed_by_position_cap(self):
        cfg = config.PORTFOLIO_CONFIG
        per_sector = int(cfg['max_sector_pct'] // cfg['max_position_pct'])
        assert per_sector * cfg['max_position_pct'] <= cfg['max_sector_pct'] + 1e-9


class TestPriceUnit:
    def test_thousand_vnd_converted(self):
        assert price_to_vnd(29.3) == pytest.approx(29300)

    def test_prices_100_to_999_thousand_are_converted(self):
        # Lỗi cũ: ngưỡng 100 → FRT 167 / PNJ 121 bị coi là 167đ / 121đ
        assert price_to_vnd(167.3) == pytest.approx(167300)
        assert price_to_vnd(120.9) == pytest.approx(120900)

    def test_already_vnd_untouched(self):
        assert price_to_vnd(85000) == 85000


class TestScorerGating:
    def test_gate_only_downgrades_never_upgrades(self):
        pytest.importorskip('talib')
        from modules.analysis.scorer import StockScorer
        scorer = StockScorer()

        # MUA nhưng ROE thấp → hạ
        rec, res = scorer.apply_gate(good_row(ROE=5.0), 7.8, 'MUA MẠNH', OPEN_MARKET)
        assert rec == 'THEO DÕI' and not res['passed']

        # MUA và đạt quy tắc → giữ
        rec, _ = scorer.apply_gate(good_row(), 7.8, 'MUA MẠNH', OPEN_MARKET)
        assert rec == 'MUA MẠNH'

        # THEO DÕI / BÁN không bao giờ bị nâng
        rec, _ = scorer.apply_gate(good_row(), 5.5, 'THEO DÕI', OPEN_MARKET)
        assert rec == 'THEO DÕI'
        rec, _ = scorer.apply_gate(good_row(), 3.0, 'BÁN / CƠ CẤU', OPEN_MARKET)
        assert rec == 'BÁN / CƠ CẤU'
