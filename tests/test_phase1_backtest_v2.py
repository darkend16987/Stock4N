"""
Phase 1 tests: BacktestEngineV2 (point-in-time, quy tắc HOSE), validation, calculator as_of.
Dữ liệu tổng hợp trong thư mục tạm; không cần mạng, không đụng dữ liệu thật.
"""
import os

import numpy as np
import pandas as pd
import pytest

import config
from modules.processing.calculator import FinancialCalculator
from modules.simulation import validation
from modules.simulation.vn_market import (CostModel, price_band, round_down_to_tick,
                                          round_up_to_tick, tick_size)

pytest.importorskip('talib')
from modules.analysis.breadth_analyzer import MarketBreadthAnalyzer  # noqa: E402
from modules.portfolio.manager import PortfolioManager  # noqa: E402
from modules.simulation.backtest_v2 import BacktestEngineV2  # noqa: E402
from modules.simulation.point_in_time import PriceBook  # noqa: E402


# =============================================================== luật thị trường
class TestMarketRules:
    def test_tick_sizes(self):
        assert tick_size(9_990) == 10
        assert tick_size(10_000) == 50
        assert tick_size(49_950) == 50
        assert tick_size(50_000) == 100

    def test_tick_rounding(self):
        assert round_down_to_tick(50_150) == 50_100
        assert round_up_to_tick(50_050) == 50_100
        assert round_down_to_tick(10_218.5) == 10_200
        assert round_up_to_tick(8_881.5) == 8_890

    def test_price_band(self):
        assert price_band(50_000) == (46_500, 53_500)
        assert price_band(9_550) == (8_890, 10_200)

    def test_price_band_disabled(self):
        floor, ceiling = price_band(50_000, limit=0)
        assert floor == 0 and ceiling == float('inf')

    def test_cost_math_exact(self):
        cost = CostModel()
        assert cost.buy_cost(1000, 50_000) == pytest.approx(50_075_000)          # + phí 0.15%
        assert cost.sell_proceeds(1000, 50_000) == pytest.approx(49_875_000)     # - phí 0.15% - thuế 0.10%
        assert cost.buy_fill_price(50_000) == 50_100                              # trượt lên, làm tròn lên
        assert cost.sell_fill_price(50_000) == 49_950                             # trượt xuống, làm tròn xuống

    def test_max_affordable_shares_is_lot_multiple_and_within_cash(self):
        cost = CostModel()
        shares = cost.max_affordable_shares(10_000_000, 33_300)
        assert shares % 100 == 0 and cost.buy_cost(shares, 33_300) <= 10_000_000
        assert cost.buy_cost(shares + 100, 33_300) > 10_000_000

    def test_stressed_multiplies_all_frictions(self):
        s = CostModel().stressed(2)
        assert s.fee_rate == pytest.approx(0.003) and s.sell_tax_rate == pytest.approx(0.002)
        assert s.slippage == pytest.approx(0.002)


# =============================================================== validation
class TestValidation:
    def test_max_drawdown(self):
        assert validation.max_drawdown([100, 120, 90, 110]) == pytest.approx(0.25)
        assert validation.max_drawdown([100, 101, 102]) == 0.0

    def test_cagr_doubling_in_one_year(self):
        idx = pd.to_datetime(['2024-01-01', '2024-12-31'])
        assert validation.cagr(pd.Series([100.0, 200.0], index=idx)) == pytest.approx(1.0, abs=0.01)

    def test_sharpe_none_for_constant_series(self):
        assert validation.sharpe_ratio([0.0] * 50) is None

    def test_bootstrap_ci_positive_edge_excludes_zero(self):
        rng = np.random.default_rng(1)
        r = rng.normal(0.003, 0.005, 400)
        res = validation.block_bootstrap_sharpe(r, n_resamples=500, block=10, seed=1)
        assert res['ci_lower'] > 0 and res['prob_positive'] > 0.99

    def test_bootstrap_ci_noise_includes_zero(self):
        rng = np.random.default_rng(2)
        r = rng.normal(0.0, 0.01, 400)
        res = validation.block_bootstrap_sharpe(r, n_resamples=500, block=10, seed=2)
        assert res['ci_lower'] < 0 < res['ci_upper']

    def test_bootstrap_deterministic_and_short_series_none(self):
        r = np.random.default_rng(3).normal(0.001, 0.01, 200)
        a = validation.block_bootstrap_sharpe(r, n_resamples=200, seed=7)
        b = validation.block_bootstrap_sharpe(r, n_resamples=200, seed=7)
        assert a == b
        assert validation.block_bootstrap_sharpe(r[:20]) is None

    def test_monte_carlo_all_wins_no_drawdown(self):
        trades = pd.DataFrame({'action': ['SELL'] * 12, 'pnl': [1_000_000.0] * 12})
        mc = validation.monte_carlo_drawdown(trades, 100_000_000, n_resamples=50, seed=1)
        assert mc['dd_p95'] == 0.0

    def test_monte_carlo_too_few_trades_none(self):
        trades = pd.DataFrame({'action': ['SELL'] * 3, 'pnl': [1.0, -1.0, 1.0]})
        assert validation.monte_carlo_drawdown(trades, 1e8) is None

    def test_walk_forward_windows(self):
        idx = pd.bdate_range('2024-01-01', periods=120)
        wf = validation.walk_forward(pd.Series(np.linspace(100, 130, 120), index=idx), n_windows=6)
        assert len(wf['windows']) == 6 and wf['positive_windows_pct'] == 1.0

    def test_trade_stats_profit_factor(self):
        trades = pd.DataFrame({
            'action': ['SELL', 'SELL', 'SELL'], 'pnl': [300.0, 100.0, -200.0],
            'return_pct': [3.0, 1.0, -2.0], 'hold_sessions': [10, 20, 30],
            'reason': ['TAKE_PROFIT', 'TAKE_PROFIT', 'STOP_LOSS']})
        s = validation.trade_stats(trades)
        assert s['profit_factor'] == pytest.approx(2.0)
        assert s['win_rate'] == pytest.approx(2 / 3)
        assert s['exit_reasons'] == {'TAKE_PROFIT': 2, 'STOP_LOSS': 1}


def good_metrics(**over):
    m = {'sessions': 800, 'n_trades': 80, 'excess_cagr': 0.05, 'max_drawdown': 0.08,
         'profit_factor': 1.6, 'walk_forward': {'positive_windows_pct': 0.83}}
    m.update(over)
    return m


GOOD_BOOT = {'ci_lower': 0.3}
GOOD_MC = {'dd_p95': 0.12}


class TestAcceptance:
    def test_all_pass(self):
        res = validation.evaluate_acceptance(good_metrics(), GOOD_BOOT, GOOD_MC, 0.10)
        assert res['verdict'] == 'PASS'

    def test_drawdown_over_limit_fails(self):
        res = validation.evaluate_acceptance(good_metrics(max_drawdown=0.18), GOOD_BOOT, GOOD_MC, 0.10)
        assert res['verdict'] == 'FAIL'

    def test_not_beating_benchmark_fails(self):
        res = validation.evaluate_acceptance(good_metrics(excess_cagr=-0.01), GOOD_BOOT, GOOD_MC, 0.10)
        assert res['verdict'] == 'FAIL'

    def test_cost_stress_loss_fails(self):
        res = validation.evaluate_acceptance(good_metrics(), GOOD_BOOT, GOOD_MC, -0.02)
        assert res['verdict'] == 'FAIL'

    def test_too_few_trades_is_inconclusive_not_pass(self):
        res = validation.evaluate_acceptance(good_metrics(n_trades=12), GOOD_BOOT, GOOD_MC, 0.10)
        assert res['verdict'] == 'INCONCLUSIVE'

    def test_missing_bootstrap_is_inconclusive(self):
        res = validation.evaluate_acceptance(good_metrics(), None, GOOD_MC, 0.10)
        assert res['verdict'] == 'INCONCLUSIVE'

    def test_real_failure_beats_insufficient_sample(self):
        res = validation.evaluate_acceptance(good_metrics(n_trades=12, max_drawdown=0.30),
                                             GOOD_BOOT, GOOD_MC, 0.10)
        assert res['verdict'] == 'FAIL'


# =============================================================== calculator point-in-time
@pytest.fixture
def pit_calc(tmp_path):
    raw = tmp_path / 'raw'
    raw.mkdir()
    pd.DataFrame({
        'time': pd.bdate_range('2023-01-02', '2025-12-31'), 'open': 20.0, 'high': 20.0, 'low': 20.0,
        'close': 20.0, 'volume': 1_000_000,
    }).to_csv(raw / 'TST_price.csv', index=False)

    quarters = [(y, q) for y in (2023, 2024) for q in (1, 2, 3, 4)]
    # lợi nhuận mỗi quý khác nhau để biết chính xác quý nào đã được tính vào TTM
    profit = [1e10, 2e10, 3e10, 4e10, 5e10, 6e10, 7e10, 8e10]
    pd.DataFrame({'Năm': [y for y, _ in quarters], 'Kỳ': [q for _, q in quarters],
                  'Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)': profit}
                 ).to_csv(raw / 'TST_fin_IncomeStatement.csv', index=False)
    pd.DataFrame({'Năm': [y for y, _ in quarters], 'Kỳ': [q for _, q in quarters],
                  'VỐN CHỦ SỞ HỮU (đồng)': [1e12] * 8, 'NỢ PHẢI TRẢ (đồng)': [1e12] * 8,
                  'Vốn góp của chủ sở hữu (đồng)': [5e11] * 8}
                 ).to_csv(raw / 'TST_fin_BalanceSheet.csv', index=False)
    return FinancialCalculator(data_dir=str(raw), output_dir=str(tmp_path), cache_raw=True)


class TestCalculatorPointInTime:
    def test_q4_report_hidden_until_90_days_after_year_end(self, pit_calc):
        # Q4/2024 công bố ≥ 2024-12-31 + 90 ngày = 2025-03-31
        before = pit_calc.calculate_metrics('TST', as_of='2025-03-15')
        after = pit_calc.calculate_metrics('TST', as_of='2025-04-05')
        # trước: Q1/2024..Q3/2024 + Q4/2023 → TTM = 4+5+6+7 = 22e10 ; sau: 5+6+7+8 = 26e10
        assert before['Net_Profit_TTM'] == pytest.approx(22e10)
        assert after['Net_Profit_TTM'] == pytest.approx(26e10)

    def test_q1_report_uses_45_day_lag(self, pit_calc):
        # Q3/2024 công bố 2024-09-30 + 45 = 2024-11-14
        a = pit_calc.calculate_metrics('TST', as_of='2024-11-13')
        b = pit_calc.calculate_metrics('TST', as_of='2024-11-15')
        assert b['Net_Profit_TTM'] > a['Net_Profit_TTM']

    def test_no_as_of_uses_latest(self, pit_calc):
        assert pit_calc.calculate_metrics('TST')['Net_Profit_TTM'] == pytest.approx(26e10)

    def test_as_of_before_any_report_returns_none(self, pit_calc):
        assert pit_calc.calculate_metrics('TST', as_of='2023-02-01') is None

    def test_lag_setting_actually_matters(self, pit_calc, monkeypatch):
        # Kiểm tra độ nhạy: nếu bỏ độ trễ, quý chưa công bố sẽ lọt vào → test trên phải phát hiện được
        monkeypatch.setattr(config, 'REPORTING_LAG_DAYS', {1: 0, 2: 0, 3: 0, 4: 0})
        leaked = pit_calc.calculate_metrics('TST', as_of='2025-03-15')
        assert leaked['Net_Profit_TTM'] == pytest.approx(26e10)

    def test_price_cut_at_as_of(self, pit_calc, tmp_path):
        raw = pit_calc.data_dir
        prices = pd.read_csv(os.path.join(raw, 'TST_price.csv'))
        prices.loc[pd.to_datetime(prices['time']) > '2025-01-31', 'close'] = 99.0
        prices.to_csv(os.path.join(raw, 'TST_price.csv'), index=False)
        fresh = FinancialCalculator(data_dir=raw, output_dir=str(tmp_path), cache_raw=True)
        assert fresh.calculate_metrics('TST', as_of='2025-01-31')['Price'] == 20.0
        assert fresh.calculate_metrics('TST')['Price'] == 99.0


# =============================================================== dữ liệu tổng hợp cho engine
N_SESSIONS = 330
DATES = pd.bdate_range('2023-01-02', periods=N_SESSIONS)


def random_walk(seed, drift, sigma=0.012, start=30.0, n=N_SESSIONS):
    rng = np.random.default_rng(seed)
    closes = start * np.exp(np.cumsum(rng.normal(drift, sigma, n)))
    opens = np.concatenate([[start], closes[:-1]]) * (1 + rng.normal(0, 0.003, n))
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.004, n)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.004, n)))
    volume = (1_000_000 * (1 + rng.uniform(-0.3, 0.6, n))).astype(int)
    return pd.DataFrame({'time': DATES[:n], 'open': opens.round(2), 'high': highs.round(2),
                         'low': lows.round(2), 'close': closes.round(2), 'volume': volume})


def write_fin(raw, symbol, profit0=6e10, growth=1.08, liabilities=1e12):
    quarters = [(y, q) for y in range(2021, 2026) for q in (1, 2, 3, 4)]
    profit = [profit0 * growth ** k for k in range(len(quarters))]
    years, qs = [y for y, _ in quarters], [q for _, q in quarters]
    pd.DataFrame({'Năm': years, 'Kỳ': qs,
                  'Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)': profit,
                  'Doanh thu thuần': [1e11 * 1.05 ** k for k in range(len(quarters))]}
                 ).to_csv(os.path.join(raw, f'{symbol}_fin_IncomeStatement.csv'), index=False)
    pd.DataFrame({'Năm': years, 'Kỳ': qs, 'VỐN CHỦ SỞ HỮU (đồng)': [1e12] * len(quarters),
                  'NỢ PHẢI TRẢ (đồng)': [liabilities] * len(quarters),
                  'Vốn góp của chủ sở hữu (đồng)': [5e11] * len(quarters)}
                 ).to_csv(os.path.join(raw, f'{symbol}_fin_BalanceSheet.csv'), index=False)


def pick_symbols():
    skip = set(config.FINANCIAL_SECTORS) | {'Bất động sản'}
    firsts = [v[0] for k, v in config._SECTOR_GROUPS.items() if k not in skip]
    return firsts[:7], firsts[7:9]       # (7 mã tốt, 2 mã "xấu")


GOOD, BAD = pick_symbols()
LOW_ROE, HIGH_DEBT = BAD


def build_universe(raw, drift=0.003, bad_drift=0.004):
    os.makedirs(raw, exist_ok=True)
    for i, sym in enumerate(GOOD):
        random_walk(100 + i, drift).to_csv(os.path.join(raw, f'{sym}_price.csv'), index=False)
        write_fin(raw, sym)
    # Hai mã giá tăng rất đẹp nhưng vi phạm quy tắc cứng
    random_walk(200, bad_drift).to_csv(os.path.join(raw, f'{LOW_ROE}_price.csv'), index=False)
    write_fin(raw, LOW_ROE, profit0=1e10, growth=1.0)                  # ROE ~4%
    random_walk(201, bad_drift).to_csv(os.path.join(raw, f'{HIGH_DEBT}_price.csv'), index=False)
    write_fin(raw, HIGH_DEBT, liabilities=3.5e12)                       # Nợ/Vốn 3.5
    return GOOD + BAD


FAST = {'warmup_sessions': 60, 'rebalance_every': 5}


def make_engine(raw, symbols, **overrides):
    return BacktestEngineV2(raw_dir=str(raw), symbols=symbols, params={**FAST, **overrides})


@pytest.fixture(scope='module')
def universe(tmp_path_factory):
    raw = str(tmp_path_factory.mktemp('bull') / 'raw')
    return raw, build_universe(raw)


@pytest.fixture(scope='module')
def bull_result(universe):
    raw, symbols = universe
    return make_engine(raw, symbols).run()


# =============================================================== PriceBook
class TestPriceBook:
    def test_thousand_vnd_normalised_to_vnd(self, universe):
        raw, symbols = universe
        book = PriceBook(raw, symbols)
        first = pd.read_csv(os.path.join(raw, f'{GOOD[0]}_price.csv'))['close'].iloc[0]
        assert book.bars[GOOD[0]]['close'].iloc[0] == pytest.approx(first * 1000)

    def test_history_never_after_as_of(self, universe):
        raw, symbols = universe
        book = PriceBook(raw, symbols)
        cutoff = DATES[100]
        hist = book.history(GOOD[0], cutoff)
        assert hist['time'].max() == cutoff and len(hist) == 101

    def test_prev_close_is_strictly_before(self, universe):
        raw, symbols = universe
        book = PriceBook(raw, symbols)
        assert book.prev_close(GOOD[0], DATES[50]) == book.bars[GOOD[0]]['close'].loc[DATES[49]]

    def test_breadth_matches_live_analyzer_on_truncated_data(self, universe, tmp_path):
        raw, symbols = universe
        book = PriceBook(raw, symbols)
        for k in (80, 150, 250):
            date = DATES[k]
            cut = tmp_path / f'cut{k}'
            cut.mkdir()
            for sym in symbols:
                df = pd.read_csv(os.path.join(raw, f'{sym}_price.csv'))
                df[pd.to_datetime(df['time']) <= date].to_csv(cut / f'{sym}_price.csv', index=False)
            live = MarketBreadthAnalyzer(data_dir=str(cut)).get_market_filter(symbols)
            pit = book.market_filter(date)
            assert pit['pct_above_both'] == pytest.approx(live['pct_above_both'], abs=1e-4)
            assert pit['sentiment'] == live['sentiment']
            assert pit['allow_new_buys'] == live['allow_new_buys']

    def test_benchmark_fallback_label(self, universe):
        raw, symbols = universe
        _, label = PriceBook(raw, symbols).benchmark()
        assert label == 'EW_UNIVERSE'


# =============================================================== cơ chế khớp lệnh (đơn vị)
def scripted_engine(tmp_path, bars, symbol='AAA', params=None):
    """Engine với 1 mã có dữ liệu kịch bản. bars: list (open, high, low, close) theo VND."""
    raw = tmp_path / 'raw'
    raw.mkdir(exist_ok=True)
    dates = pd.bdate_range('2024-01-02', periods=len(bars))
    pd.DataFrame({'time': dates, 'open': [b[0] / 1000 for b in bars], 'high': [b[1] / 1000 for b in bars],
                  'low': [b[2] / 1000 for b in bars], 'close': [b[3] / 1000 for b in bars],
                  'volume': 1_000_000}).to_csv(raw / f'{symbol}_price.csv', index=False)
    engine = BacktestEngineV2(raw_dir=str(raw), symbols=[symbol], params=params,
                              scorer=object(), calculator=object())
    return engine, dates


def make_pos(entry=50_000, entry_idx=0, shares=1000, stop_pending=False):
    cost = CostModel()
    return {'shares': shares, 'entry_price': entry, 'entry_idx': entry_idx, 'entry_date': None,
            'settle_idx': entry_idx + 2, 'cost_total': cost.buy_cost(shares, entry),
            'stop_pending': stop_pending, 'score': 7.0, 'sector': 'X'}


class TestExecution:
    def test_buy_fills_at_open_plus_slippage_and_locks_t2(self, tmp_path):
        engine, dates = scripted_engine(tmp_path, [(50_000, 50_500, 49_500, 50_000), (50_000, 50_800, 49_800, 50_300)])
        positions = {}
        cash, trade = engine._try_buy({'symbol': 'AAA', 'amount': 10_000_000, 'score': 7.0},
                                      dates[1], 1, 20_000_000, positions)
        assert trade['price'] == 50_100                              # 50,000 * 1.001 → tick 100
        assert positions['AAA']['settle_idx'] == 3                   # mua phiên 1 → bán được từ phiên 3
        assert trade['shares'] % 100 == 0
        assert cash == pytest.approx(20_000_000 - CostModel().buy_cost(trade['shares'], 50_100))
        assert CostModel().buy_cost(trade['shares'], 50_100) <= 10_000_000

    def test_buy_blocked_at_limit_up(self, tmp_path):
        # tham chiếu 50,000 → trần 53,500; mở cửa 53,500 → giá khớp 53,600 ≥ trần → không mua
        engine, dates = scripted_engine(tmp_path, [(50_000, 50_000, 50_000, 50_000), (53_500, 53_500, 53_500, 53_500)])
        cash, trade = engine._try_buy({'symbol': 'AAA', 'amount': 10_000_000, 'score': 7.0},
                                      dates[1], 1, 20_000_000, {})
        assert trade is None and cash == 20_000_000

    def test_buy_limited_by_cash(self, tmp_path):
        engine, dates = scripted_engine(tmp_path, [(50_000, 50_000, 50_000, 50_000), (50_000, 50_000, 50_000, 50_000)])
        order = {'symbol': 'AAA', 'amount': 50_000_000, 'score': 7.0}
        # Lệnh muốn 50M nhưng chỉ có 12M tiền → 239 cổ mua được, làm tròn lô còn 200
        cash, trade = engine._try_buy(order, dates[1], 1, 12_000_000, {})
        assert trade['shares'] == 200 and cash >= 0
        # 5M không đủ 1 lô (100 × 50,100) → không khớp, tiền giữ nguyên
        cash, trade = engine._try_buy(order, dates[1], 1, 5_000_000, {})
        assert trade is None and cash == 5_000_000

    def test_stop_hit_intraday_fills_at_stop_not_low(self, tmp_path):
        bars = [(50_000, 50_000, 50_000, 49_500), (49_500, 49_800, 46_300, 47_000)]
        engine, dates = scripted_engine(tmp_path, bars)
        res = engine._exit_decision(make_pos(), 'AAA', engine.book.bar('AAA', dates[1]), 49_500, 5)
        price, reason = res
        assert reason == 'STOP_LOSS' and price == 46_450             # stop 46,500 → trượt → 46,450

    def test_gap_down_fills_at_open_worse_than_stop(self, tmp_path):
        bars = [(52_000, 52_000, 52_000, 52_000), (47_000, 47_200, 46_800, 47_000)]
        engine, dates = scripted_engine(tmp_path, bars)
        pos = make_pos(entry=52_000)
        price, reason = engine._exit_decision(pos, 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5)
        assert reason == 'STOP_LOSS' and price == 46_950 and price < 52_000 * 0.93

    def test_sell_blocked_at_limit_down(self, tmp_path):
        # tham chiếu 50,000 → sàn 46,500; mở cửa đúng sàn → không bán được, nhớ trạng thái stop
        bars = [(50_000, 50_000, 50_000, 50_000), (46_500, 46_500, 46_500, 46_500)]
        engine, dates = scripted_engine(tmp_path, bars)
        pos = make_pos(entry=50_000)
        assert engine._exit_decision(pos, 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5) is None
        assert pos['stop_pending'] is True

    def test_take_profit_limit_fill_at_target(self, tmp_path):
        bars = [(55_000, 55_000, 55_000, 55_000), (55_000, 58_000, 54_000, 57_000)]
        engine, dates = scripted_engine(tmp_path, bars)
        price, reason = engine._exit_decision(make_pos(), 'AAA', engine.book.bar('AAA', dates[1]), 55_000, 5)
        assert reason == 'TAKE_PROFIT' and price == 57_500            # +15% của 50,000, không trượt giá

    def test_gap_up_through_target_fills_at_open(self, tmp_path):
        bars = [(55_000, 55_000, 55_000, 55_000), (58_000, 58_500, 57_900, 58_200)]
        engine, dates = scripted_engine(tmp_path, bars)
        price, reason = engine._exit_decision(make_pos(), 'AAA', engine.book.bar('AAA', dates[1]), 55_000, 5)
        assert reason == 'TAKE_PROFIT' and price == 58_000

    def test_stop_and_target_same_bar_counts_as_stop(self, tmp_path):
        # Với biên ±7% thì stop (-7%) và target (+15%) không thể cùng nằm trong 1 phiên; tắt biên độ
        # để kiểm tra quy tắc phòng thủ "chạm cả hai trong ngày → tính stop".
        bars = [(50_000, 50_000, 50_000, 50_000), (50_000, 58_000, 46_000, 50_000)]
        engine, dates = scripted_engine(tmp_path, bars, params={'price_limit': 0})
        _, reason = engine._exit_decision(make_pos(), 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5)
        assert reason == 'STOP_LOSS'

    def test_stop_exactly_at_limit_down_cannot_fill(self, tmp_path):
        # Giá vốn = giá tham chiếu → mức stop (-7%) trùng giá sàn → lệnh stop không khớp được trong ngày
        bars = [(50_000, 50_000, 50_000, 50_000), (49_000, 49_000, 46_500, 46_500)]
        engine, dates = scripted_engine(tmp_path, bars)
        pos = make_pos(entry=50_000)
        assert engine._exit_decision(pos, 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5) is None
        assert pos['stop_pending'] is True

    def test_stop_triggered_while_locked_exits_at_first_sellable_open(self, tmp_path):
        bars = [(50_000, 50_000, 50_000, 50_000), (50_200, 50_400, 50_000, 50_300)]
        engine, dates = scripted_engine(tmp_path, bars)
        pos = make_pos(stop_pending=True)           # đã chạm stop khi còn khoá T+2
        price, reason = engine._exit_decision(pos, 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5)
        assert reason == 'STOP_LOSS' and price == 50_100             # 50,200 trượt giá → tick 100

    def test_no_exit_inside_range(self, tmp_path):
        bars = [(50_000, 50_000, 50_000, 50_000), (50_100, 51_000, 49_000, 50_500)]
        engine, dates = scripted_engine(tmp_path, bars)
        assert engine._exit_decision(make_pos(), 'AAA', engine.book.bar('AAA', dates[1]), 50_000, 5) is None

    def test_max_hold_exit(self, tmp_path):
        bars = [(50_000, 50_000, 50_000, 50_000), (50_100, 51_000, 49_000, 50_500)]
        engine, dates = scripted_engine(tmp_path, bars)
        res = engine._exit_decision(make_pos(entry_idx=0), 'AAA', engine.book.bar('AAA', dates[1]), 50_000,
                                    config.BACKTEST_V2['max_hold_sessions'])
        assert res is not None and res[1] == 'MAX_HOLD'

    def test_sell_pnl_includes_all_costs(self, tmp_path):
        engine, _ = scripted_engine(tmp_path, [(50_000, 50_000, 50_000, 50_000)] * 2)
        pos = make_pos(entry=50_000, shares=1000)
        proceeds, trade = engine._sell('AAA', pos, 55_000, pd.Timestamp('2024-02-01'), 30, 'TAKE_PROFIT')
        assert proceeds == pytest.approx(55_000_000 * (1 - 0.0015 - 0.001))
        assert trade['pnl'] == pytest.approx(proceeds - 50_000_000 * 1.0015)
        assert trade['pnl'] < 5_000_000 - 0                      # lãi gộp 5M bị phí+thuế ăn bớt


# =============================================================== chạy cả vòng lặp
class TestEngineRun:
    def test_trades_happen(self, bull_result):
        assert (bull_result.trades['action'] == 'BUY').sum() >= 3

    def test_equity_equals_capital_plus_realised_pnl(self, bull_result):
        # Cuối kỳ đã đóng hết vị thế → vốn cuối = vốn đầu + tổng lãi/lỗ ròng các lệnh bán
        sells = bull_result.trades[bull_result.trades['action'] == 'SELL']
        expected = config.BACKTEST_V2['initial_capital'] + sells['pnl'].sum()
        assert bull_result.equity.iloc[-1] == pytest.approx(expected, rel=1e-9)

    def test_cash_never_negative(self, bull_result):
        assert (bull_result.cash >= -1e-6).all()

    def test_t_plus_2_respected(self, bull_result, universe):
        raw, symbols = universe
        calendar = list(PriceBook(raw, symbols).calendar)
        idx = {d: i for i, d in enumerate(calendar)}
        trades = bull_result.trades
        for sym in trades['symbol'].unique():
            t = trades[trades['symbol'] == sym].sort_values('date')
            buy_idx = None
            for _, row in t.iterrows():
                if row['action'] == 'BUY':
                    buy_idx = idx[row['date']]
                elif row['reason'] != 'END_OF_BACKTEST':
                    assert idx[row['date']] - buy_idx >= 2, f'{sym} bán trước T+2'

    def test_buys_only_the_session_after_a_signal_day(self, bull_result, universe):
        raw, symbols = universe
        calendar = list(PriceBook(raw, symbols).calendar)
        signal_next = {calendar[calendar.index(pd.Timestamp(r['date'])) + 1] for r in bull_result.rebalances}
        buys = bull_result.trades[bull_result.trades['action'] == 'BUY']
        assert set(buys['date']).issubset(signal_next)

    def test_limits_positions_and_sector_cap(self, bull_result):
        cfg = config.PORTFOLIO_CONFIG
        per_sector = int(cfg['max_sector_pct'] // cfg['max_position_pct'])
        held = {}
        for _, row in bull_result.trades.sort_values(['date', 'action']).iterrows():
            if row['action'] == 'BUY':
                held[row['symbol']] = row['sector']
            else:
                held.pop(row['symbol'], None)
            assert len(held) <= cfg['max_positions']
            sectors = list(held.values())
            assert all(sectors.count(s) <= per_sector for s in set(sectors))

    def test_hard_rule_violators_never_bought(self, bull_result):
        bought = set(bull_result.trades['symbol'])
        assert LOW_ROE not in bought, 'mã ROE thấp bị mua'
        assert HIGH_DEBT not in bought, 'mã Nợ/Vốn 3.5 bị mua'

    def test_deterministic(self, universe, bull_result):
        raw, symbols = universe
        again = make_engine(raw, symbols).run()
        pd.testing.assert_series_equal(again.equity, bull_result.equity)

    def test_bear_market_produces_no_buys(self, tmp_path):
        raw = str(tmp_path / 'bear' / 'raw')
        symbols = build_universe(raw, drift=-0.004, bad_drift=-0.004)
        res = make_engine(raw, symbols).run()
        assert (res.trades['action'] == 'BUY').sum() == 0
        assert res.equity.iloc[-1] == pytest.approx(config.BACKTEST_V2['initial_capital'])

    def test_costs_reduce_return(self, universe, bull_result):
        raw, symbols = universe
        free = make_engine(raw, symbols, fee_rate=0.0, sell_tax_rate=0.0, slippage=0.0).run()
        assert free.equity.iloc[-1] > bull_result.equity.iloc[-1]


class TestNoLookAhead:
    CUT = DATES[200]

    def _mutated_universe(self, raw, tmp_path):
        """Bản sao dữ liệu: mọi giá SAU CUT và các báo cáo CHƯA công bố tại CUT bị đổi mạnh."""
        new_raw = str(tmp_path / 'mut' / 'raw')
        os.makedirs(new_raw, exist_ok=True)
        rng = np.random.default_rng(5)
        for fname in os.listdir(raw):
            src = pd.read_csv(os.path.join(raw, fname))
            if fname.endswith('_price.csv'):
                future = pd.to_datetime(src['time']) > self.CUT
                factor = rng.uniform(0.6, 1.6, future.sum())
                for col in ('open', 'high', 'low', 'close'):
                    src.loc[future, col] = src.loc[future, col].to_numpy() * factor
                src['high'] = src[['open', 'high', 'low', 'close']].max(axis=1)
                src['low'] = src[['open', 'high', 'low', 'close']].min(axis=1)
            else:
                # báo cáo công bố sau CUT: Q ≥ 2023Q1 (công bố từ 2023-05-15) → CUT = 2023-10-... nên đổi từ 2023Q3
                late = (src['Năm'] > 2023) | ((src['Năm'] == 2023) & (src['Kỳ'] >= 3))
                numeric = [c for c in src.columns if c not in ('Năm', 'Kỳ')]
                src.loc[late, numeric] = src.loc[late, numeric] * 0.05
            src.to_csv(os.path.join(new_raw, fname), index=False)
        return new_raw

    def test_results_up_to_cut_unchanged_by_future_data(self, universe, bull_result, tmp_path):
        raw, symbols = universe
        # 2023Q3 công bố 2023-11-14; DATES[200] ≈ 2023-10-05 → 2023Q3 chưa công bố tại CUT
        assert pd.Timestamp('2023-11-14') > self.CUT
        mutated = make_engine(self._mutated_universe(raw, tmp_path), symbols).run()
        a, b = bull_result.equity.loc[:self.CUT], mutated.equity.loc[:self.CUT]
        pd.testing.assert_series_equal(a, b)
        ta = bull_result.trades[bull_result.trades['date'] <= self.CUT].reset_index(drop=True)
        tb = mutated.trades[mutated.trades['date'] <= self.CUT].reset_index(drop=True)
        pd.testing.assert_frame_equal(ta, tb)
        assert len(ta) > 0, 'cần có giao dịch trước CUT để phép so sánh có ý nghĩa'

    def test_future_data_does_change_later_results(self, universe, bull_result, tmp_path):
        raw, symbols = universe
        mutated = make_engine(self._mutated_universe(raw, tmp_path), symbols).run()
        assert not np.allclose(bull_result.equity.loc[self.CUT:].values, mutated.equity.loc[self.CUT:].values)

    def test_detector_catches_a_deliberate_leak(self, universe, bull_result, tmp_path, monkeypatch):
        # Kiểm tra độ nhạy: cố tình để history() trả về TOÀN BỘ lịch sử → phép so sánh phải thấy khác biệt
        raw, symbols = universe
        orig = PriceBook.history
        monkeypatch.setattr(PriceBook, 'history',
                            lambda self, symbol, as_of: orig(self, symbol, self.calendar[-1]))
        leaky = make_engine(self._mutated_universe(raw, tmp_path), symbols).run()
        a, b = bull_result.equity.loc[:self.CUT], leaky.equity.loc[:self.CUT]
        assert not np.allclose(a.values, b.values)


# =============================================================== suite + portfolio helper
class TestSuite:
    def test_run_suite_report_structure(self, universe, tmp_path):
        raw, symbols = universe
        engine = make_engine(raw, symbols, bootstrap_resamples=200, mc_resamples=200)
        report, base = engine.run_suite(output_dir=str(tmp_path / 'out'), write=True)
        assert report['acceptance']['verdict'] in ('PASS', 'FAIL', 'INCONCLUSIVE')
        assert report['metrics']['benchmark'] == 'EW_UNIVERSE'
        assert report['limitations'], 'phải liệt kê hạn chế'
        # Mẫu ngắn (330 phiên < 504) → không được kết luận PASS
        assert report['acceptance']['verdict'] != 'PASS'
        assert os.path.isdir(tmp_path / 'out') and len(os.listdir(tmp_path / 'out')) == 3

    def test_cost_stress_not_better_than_base(self, universe):
        raw, symbols = universe
        engine = make_engine(raw, symbols, bootstrap_resamples=100, mc_resamples=100)
        report, base = engine.run_suite(write=False)
        base_return = float(base.equity.iloc[-1] / base.equity.iloc[0] - 1)
        assert report['cost_stress']['total_return'] <= base_return + 1e-12


class TestPortfolioHeldSymbols:
    def _buy_list(self):
        rows = [{'Symbol': s, 'Total_Score': 8.0 - i * 0.1, 'Price': 20.0,
                 'Sector': config.SECTOR_MAP.get(s, 'Khác'), 'Recommendation': 'MUA THĂM DÒ'}
                for i, s in enumerate(['HPG', 'GVR', 'DCM', 'FPT'])]       # 3 mã Vật liệu + 1 CNTT
        return pd.DataFrame(rows)

    def test_held_symbols_count_toward_sector_cap(self, tmp_path):
        pm = PortfolioManager(processed_dir=str(tmp_path), raw_dir=str(tmp_path),
                              returns_provider=lambda s: None)
        # Đang giữ 1 mã Vật liệu → chỉ còn 1 chỗ cho ngành này (trần 2)
        chosen = pm.select_candidates(self._buy_list(), 75_000_000, held_symbols=['HPG'])
        symbols = [r['Symbol'] for r in chosen]
        assert 'HPG' not in symbols
        assert sum(config.SECTOR_MAP[s] == 'Vật liệu & Công nghiệp' for s in symbols) == 1

    def test_slots_limit_new_positions(self, tmp_path):
        pm = PortfolioManager(processed_dir=str(tmp_path), raw_dir=str(tmp_path),
                              returns_provider=lambda s: None)
        held = [f'H{i}' for i in range(7)]
        assert len(pm.select_candidates(self._buy_list(), 75_000_000, held_symbols=held)) == 1

    def test_returns_provider_drives_correlation_filter(self, tmp_path):
        rng = np.random.default_rng(0)
        base = pd.Series(rng.normal(0, 0.02, 60))
        series = {'HPG': base, 'FPT': base * 1.2}     # tương quan 1.0
        pm = PortfolioManager(processed_dir=str(tmp_path), raw_dir=str(tmp_path),
                              returns_provider=lambda s: series.get(s))
        buy_list = self._buy_list()
        buy_list = buy_list[buy_list['Symbol'].isin(['HPG', 'FPT'])]
        assert [r['Symbol'] for r in pm.select_candidates(buy_list, 75_000_000)] == ['HPG']
