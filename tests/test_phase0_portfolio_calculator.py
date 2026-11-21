"""
Phase 0 tests: PortfolioManager selection rules + FinancialCalculator new metrics.
Dùng thư mục tạm, không đụng dữ liệu thật.
"""
import os

import numpy as np
import pandas as pd
import pytest

import config
from modules.portfolio.manager import PortfolioManager
from modules.processing.calculator import FinancialCalculator


# ---------------------------------------------------------------- portfolio
def write_report(processed_dir, rows):
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(processed_dir, 'analysis_report.csv'), index=False)


def make_row(symbol, score, price, sector=None, rec='MUA THĂM DÒ'):
    return {'Symbol': symbol, 'Total_Score': score, 'Recommendation': rec, 'Price': price,
            'Sector': sector if sector else config.SECTOR_MAP.get(symbol, 'Khác')}


@pytest.fixture
def dirs(tmp_path):
    processed = tmp_path / 'processed'
    raw = tmp_path / 'raw'
    processed.mkdir()
    raw.mkdir()
    return str(processed), str(raw)


def run(dirs, rows, market_filter=None, capital=100_000_000):
    processed, raw = dirs
    write_report(processed, rows)
    pm = PortfolioManager(processed_dir=processed, raw_dir=raw)
    return pm.generate_recommendation(total_capital=capital, market_filter=market_filter)


def many_rows(n):
    """n mã thuộc nhiều ngành khác nhau, giá nhỏ để đủ tiền mua lô."""
    sectors = list(config._SECTOR_GROUPS.keys())
    return [make_row(f'T{i:02d}', 8.0 - i * 0.05, 20.0, sector=sectors[i % len(sectors)])
            for i in range(n)]


class TestPortfolioSelection:
    def test_max_positions_enforced(self, dirs):
        df = run(dirs, many_rows(15))
        assert len(df) <= config.PORTFOLIO_CONFIG['max_positions']

    def test_sector_cap_enforced(self, dirs):
        rows = [make_row(f'B{i}', 8.0 - i * 0.1, 20.0, sector='Ngân hàng') for i in range(6)]
        rows += [make_row(f'R{i}', 6.8 - i * 0.1, 20.0, sector='Bất động sản') for i in range(3)]
        df = run(dirs, rows)
        cfg = config.PORTFOLIO_CONFIG
        per_sector = int(cfg['max_sector_pct'] // cfg['max_position_pct'])
        assert df['Sector'].value_counts().max() <= per_sector

    def test_unaffordable_lot_is_skipped_not_mis_sized(self, dirs):
        # FRT 167.3 (nghìn đồng): 1 lô = 16.7M > mức tối đa 1 vị thế (15M) → phải bỏ qua,
        # tuyệt đối không được ra "25,000 cổ" như bug cũ.
        rows = [make_row('FRT', 7.5, 167.3), make_row('PNJ', 7.0, 120.9), make_row('FPT', 6.9, 90.6)]
        df = run(dirs, rows)
        assert 'FRT' not in set(df['Symbol'])
        pnj = df[df['Symbol'] == 'PNJ'].iloc[0]
        assert pnj['Entry_Price'] == '120,900'
        assert pnj['Volume_Shares'] <= 200   # ~12M / 120,900đ ≈ 100 cổ

    def test_total_investment_within_budget(self, dirs):
        df = run(dirs, many_rows(10))
        invested = sum(float(c.replace(',', '')) for c in df['Capital_VND'])
        assert invested <= 100_000_000 * (1 - config.PORTFOLIO_CONFIG['cash_reserve_pct']) + 1

    def test_duplicate_symbols_collapsed(self, dirs):
        rows = [make_row('GMD', 7.0, 82.5), make_row('GMD', 7.0, 82.5), make_row('FPT', 6.8, 90.6)]
        df = run(dirs, rows)
        assert df['Symbol'].is_unique

    def test_correlated_candidate_skipped(self, dirs):
        processed, raw = dirs
        rng = np.random.default_rng(0)
        dates = pd.bdate_range(end='2026-02-27', periods=120)
        base = pd.Series(20 * np.exp(np.cumsum(rng.normal(0, 0.02, 120))), index=dates)
        other = pd.Series(20 * np.exp(np.cumsum(rng.normal(0, 0.02, 120))), index=dates)
        for sym, series in {'AAA1': base, 'AAA2': base * 1.5, 'CCC1': other}.items():
            pd.DataFrame({'time': dates, 'close': series.values}).to_csv(
                os.path.join(raw, f'{sym}_price.csv'), index=False)

        rows = [make_row('AAA1', 8.0, 20.0, sector='Bất động sản'),
                make_row('AAA2', 7.9, 30.0, sector='Dầu khí'),
                make_row('CCC1', 7.8, 20.0, sector='Tiêu dùng & Bán lẻ')]
        df = run(dirs, rows)
        symbols = set(df['Symbol'])
        assert 'AAA1' in symbols and 'CCC1' in symbols
        assert 'AAA2' not in symbols   # tương quan 1.0 với AAA1

    def test_bearish_market_holds_cash(self, dirs):
        mf = {'allow_new_buys': False, 'sentiment': 'BEARISH', 'risk_multiplier': 0.5,
              'pct_above_both': 0.3}
        assert run(dirs, many_rows(5), market_filter=mf) is None
        assert not os.path.exists(os.path.join(dirs[0], 'portfolio_recommendation.csv'))

    def test_risk_multiplier_scales_investment(self, dirs):
        mf = {'allow_new_buys': True, 'sentiment': 'NEUTRAL', 'risk_multiplier': 0.5,
              'pct_above_both': 0.5}
        df = run(dirs, many_rows(8), market_filter=mf)
        invested = sum(float(c.replace(',', '')) for c in df['Capital_VND'])
        assert invested <= 100_000_000 * (1 - config.PORTFOLIO_CONFIG['cash_reserve_pct']) * 0.5 + 1


# --------------------------------------------------------------- calculator
YEARS_Q = [(2024, 1), (2024, 2), (2024, 3), (2024, 4), (2025, 1), (2025, 2), (2025, 3), (2025, 4)]


@pytest.fixture
def calc_env(tmp_path):
    raw = tmp_path / 'raw'
    out = tmp_path / 'out'
    raw.mkdir()
    out.mkdir()

    pd.DataFrame({
        'time': pd.bdate_range(end='2026-02-27', periods=40),
        'open': 20.0, 'high': 20.0, 'low': 20.0, 'close': 20.0, 'volume': 1000000,
    }).to_csv(raw / 'TST_price.csv', index=False)

    profit = [5e10] * 7 + [6e10]          # TTM = 5e10*3 + 6e10 = 2.1e11
    revenue = [1e11] * 4 + [1e11, 1e11, 1e11, 1.5e11]   # Q4/2025 vs Q4/2024 = +50%
    pd.DataFrame({
        'Năm': [y for y, _ in YEARS_Q], 'Kỳ': [q for _, q in YEARS_Q],
        'Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)': profit,
        'Doanh thu thuần': revenue,                     # tên cột thực tế (không có "(đồng)")
    }).to_csv(raw / 'TST_fin_IncomeStatement.csv', index=False)

    pd.DataFrame({
        'Năm': [y for y, _ in YEARS_Q], 'Kỳ': [q for _, q in YEARS_Q],
        'VỐN CHỦ SỞ HỮU (đồng)': [2e12] * 8,
        'NỢ PHẢI TRẢ (đồng)': [3e12] * 8,
        'Vốn góp của chủ sở hữu (đồng)': [1e12] * 8,   # → 1e8 cổ phiếu (mệnh giá 10,000đ)
    }).to_csv(raw / 'TST_fin_BalanceSheet.csv', index=False)

    return FinancialCalculator(data_dir=str(raw), output_dir=str(out))


class TestCalculatorNewMetrics:
    def test_find_col_prefers_exact_match(self):
        calc = FinancialCalculator()
        df = pd.DataFrame(columns=['Các khoản giảm trừ doanh thu', 'Doanh thu thuần', 'Doanh thu (đồng)'])
        assert calc._find_col(df, calc.col_map['revenue']) == 'Doanh thu thuần'

    def test_revenue_growth_no_longer_nan(self, calc_env):
        m = calc_env.calculate_metrics('TST')
        assert m['Revenue_Growth_YoY'] == pytest.approx(50.0, abs=0.01)

    def test_pe_pb_debt_equity_values(self, calc_env):
        m = calc_env.calculate_metrics('TST')
        # shares = 1e12 / 10,000 = 1e8; EPS = 2.1e11 / 1e8 = 2,100; giá 20.0 nghìn = 20,000đ
        assert m['Shares_Est'] == 1e8
        assert m['PE'] == pytest.approx(20000 / 2100, abs=0.01)
        # BVPS = 2e12 / 1e8 = 20,000 → PB = 1.0
        assert m['PB'] == pytest.approx(1.0, abs=0.01)
        assert m['Debt_Equity'] == pytest.approx(1.5, abs=0.01)
        assert m['ROE'] == pytest.approx(2.1e11 / 2e12 * 100, abs=0.01)

    def test_loss_making_has_no_pe(self, calc_env, tmp_path):
        inc_path = os.path.join(calc_env.data_dir, 'TST_fin_IncomeStatement.csv')
        inc = pd.read_csv(inc_path)
        inc['Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)'] = -1e10
        inc.to_csv(inc_path, index=False)
        m = calc_env.calculate_metrics('TST')
        assert m['PE'] is None
        assert m['PB'] is not None

    def test_missing_capital_column_gives_none_not_crash(self, calc_env):
        bs_path = os.path.join(calc_env.data_dir, 'TST_fin_BalanceSheet.csv')
        bs = pd.read_csv(bs_path).drop(columns=['Vốn góp của chủ sở hữu (đồng)'])
        bs.to_csv(bs_path, index=False)
        m = calc_env.calculate_metrics('TST')
        assert m['PE'] is None and m['PB'] is None
        assert m['ROE'] is not None
