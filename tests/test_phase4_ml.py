"""
Phase 4 tests: chia dữ liệu theo thời gian có purge, đặc trưng point-in-time, kiểm định ML ngoài mẫu.
Dữ liệu tổng hợp; không cần mạng.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

import config
from modules.ml_prediction import research
from modules.ml_prediction.feature_engineer import FeatureEngineer
from modules.ml_prediction.purged_cv import PurgedWalkForward, purged_time_split
from modules.ml_prediction.trend_classifier import TrendClassifier

FAST = {'horizon': 20, 'n_splits': 3, 'min_train_dates': 150, 'min_oos_dates': 150,
        'min_symbols_per_date': 10, 'n_estimators': 40, 'max_depth': 5, 'min_samples_leaf': 50,
        'bootstrap_resamples': 300}


# ------------------------------------------------------------------ dữ liệu tổng hợp
def make_frames(n_symbols=25, n_days=620, seed=0, signal=0.0, market_vol=0.008, idio_vol=0.015):
    """signal > 0: mỗi mã có drift riêng BỀN VỮNG (độ lệch chuẩn = signal /ngày) → động lượng dự báo được."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2021-01-04', periods=n_days)
    market = rng.normal(0, market_vol, n_days)
    frames = {}
    for i in range(n_symbols):
        drift = rng.normal(0, signal) if signal else 0.0
        logret = market + drift + rng.normal(0, idio_vol, n_days)
        close = 25 * np.exp(np.cumsum(logret))
        opens = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.002, n_days))
        frames[f'S{i:02d}'] = pd.DataFrame({
            'time': dates, 'open': opens, 'high': np.maximum(opens, close) * (1 + np.abs(rng.normal(0, 0.004, n_days))),
            'low': np.minimum(opens, close) * (1 - np.abs(rng.normal(0, 0.004, n_days))), 'close': close,
            'volume': (1e6 * (1 + rng.uniform(-0.3, 0.6, n_days))).astype(int)})
    return frames


@pytest.fixture(scope='module')
def noise_frames():
    return make_frames(seed=1)


@pytest.fixture(scope='module')
def signal_frames():
    return make_frames(seed=2, signal=0.0012)


# ================================================================== purged split
class TestPurgedSplit:
    def _dates(self, n=300, symbols=5):
        d = pd.bdate_range('2022-01-03', periods=n)
        return pd.Series(np.tile(d, symbols)), d

    def test_train_label_windows_end_before_test(self):
        dates, cal = self._dates()
        train, test = purged_time_split(dates, horizon=20, test_size=0.2)
        pos = {d: i for i, d in enumerate(cal)}
        p = dates.map(pos).to_numpy()
        assert p[train].max() + 20 < p[test].min()
        assert train.sum() > 0 and test.sum() > 0 and not (train & test).any()

    def test_whole_dates_stay_on_one_side(self):
        dates, _ = self._dates()
        train, test = purged_time_split(dates, 20, 0.2)
        assert set(dates[train]).isdisjoint(set(dates[test]))        # không rò rỉ chéo mã trong cùng ngày

    def test_purge_removes_exactly_horizon_dates(self):
        dates, cal = self._dates(n=300, symbols=1)
        train, test = purged_time_split(dates, 20, 0.2)
        assert test.sum() == 60 and train.sum() == 240 - 20

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            purged_time_split(pd.Series(pd.bdate_range('2022-01-03', periods=15)), horizon=20)

    def test_walk_forward_folds_are_purged_expanding_and_disjoint(self):
        dates, cal = self._dates(n=400, symbols=3)
        pos = dates.map({d: i for i, d in enumerate(cal)}).to_numpy()
        folds = list(PurgedWalkForward(4, 20, 150).split(dates))
        assert len(folds) == 4
        prev_end, prev_train = -1, 0
        for tr, te in folds:
            assert pos[tr].max() + 20 < pos[te].min()
            assert pos[te].min() > prev_end                          # khối test liên tiếp, không chồng
            assert len(tr) > prev_train                              # train mở rộng dần
            prev_end, prev_train = pos[te].max(), len(tr)
        assert prev_end == 399                                       # phủ tới ngày cuối

    def test_walk_forward_rejects_insufficient_history(self):
        dates, _ = self._dates(n=160, symbols=2)
        with pytest.raises(ValueError):
            list(PurgedWalkForward(5, 20, 150).split(dates))


# ================================================================== đặc trưng / panel
class TestFeaturesAndPanel:
    def test_features_are_scale_invariant(self, noise_frames):
        df = noise_frames['S00']
        scaled = df.copy()
        for c in ('open', 'high', 'low', 'close'):
            scaled[c] = scaled[c] * 1000
        a, _ = research.stationary_features(df)
        b, _ = research.stationary_features(scaled)
        pd.testing.assert_frame_equal(a, b)

    def test_features_are_point_in_time(self, noise_frames):
        df = noise_frames['S00']
        cut = 400
        full, _ = research.stationary_features(df)
        trunc, _ = research.stationary_features(df.iloc[:cut + 1])
        pd.testing.assert_series_equal(full.iloc[cut], trunc.iloc[cut], check_names=False)

    def test_changing_the_future_does_not_change_past_features(self, noise_frames):
        df = noise_frames['S00'].copy()
        base, _ = research.stationary_features(df)
        df.loc[df.index[450:], ['open', 'high', 'low', 'close']] *= 3
        changed, _ = research.stationary_features(df)
        pd.testing.assert_frame_equal(base.iloc[:450], changed.iloc[:450])

    def test_panel_labels_ranks_and_neutrality(self, noise_frames):
        panel = research.build_panel(noise_frames, horizon=20, min_symbols=10)
        assert panel[research.RANK_COLS].min().min() > 0 and panel[research.RANK_COLS].max().max() <= 1
        med = panel.groupby('date')['excess'].median()
        assert med.abs().max() < 1e-9                               # trung hòa thị trường theo ngày
        row = panel.iloc[1000]
        close = noise_frames[row['symbol']].set_index(pd.to_datetime(noise_frames[row['symbol']]['time']))['close']
        i = close.index.get_loc(row['date'])
        assert row['fwd_ret'] == pytest.approx(close.iloc[i + 20] / close.iloc[i] - 1)

    def test_unlabeled_panel_keeps_latest_dates_labeled_drops_them(self, noise_frames):
        last = noise_frames['S00']['time'].max()
        un = research.build_panel(noise_frames, 20, 10, labeled=False)
        lab = research.build_panel(noise_frames, 20, 10, labeled=True)
        assert un['date'].max() == last and lab['date'].max() < last

    def test_get_latest_features_uses_todays_data(self, tmp_path, noise_frames):
        raw = tmp_path / 'raw'
        raw.mkdir()
        noise_frames['S00'].to_csv(raw / 'S00_price.csv', index=False)
        eng = FeatureEngineer(data_dir=str(raw))
        latest = eng.get_latest_features('S00')
        frame = eng._build_feature_frame(eng.load_price_data('S00'))
        assert latest is not None
        pd.testing.assert_series_equal(latest, frame[latest.index].iloc[-1], check_names=False)
        # Lỗi cũ: bộ dữ liệu huấn luyện bỏ `horizon` dòng cuối → dòng "mới nhất" của nó cũ hơn
        assert eng.prepare_ml_dataset('S00', horizon=5)['time'].max() < noise_frames['S00']['time'].max()

    def test_get_latest_features_none_when_history_too_short(self, tmp_path, noise_frames):
        raw = tmp_path / 'raw'
        raw.mkdir()
        noise_frames['S00'].head(30).to_csv(raw / 'S00_price.csv', index=False)
        assert FeatureEngineer(data_dir=str(raw)).get_latest_features('S00') is None


# ================================================================== TrendClassifier
class TestTrendClassifier:
    def _datasets(self, tmp_path, frames, horizon=5):
        raw = tmp_path / 'raw'
        raw.mkdir(exist_ok=True)
        for s, df in frames.items():
            df.to_csv(raw / f'{s}_price.csv', index=False)
        eng = FeatureEngineer(data_dir=str(raw))
        data = eng.prepare_batch_datasets(list(frames), horizon=horizon, threshold=0.02)
        return data, eng.get_feature_names()

    def test_time_column_triggers_purged_split(self, tmp_path):
        frames = make_frames(n_symbols=10, n_days=450, seed=3)
        data, names = self._datasets(tmp_path, frames)
        clf = TrendClassifier()
        m = clf.train_multi_symbol(data, names, test_size=0.2, horizon=5)
        total = sum(len(d) for d in data.values())
        assert m['split'] == 'purged_time'
        assert m['train_samples'] + m['test_samples'] < total       # có dòng bị purge bỏ
        assert m['test_samples'] == pytest.approx(total * 0.2, rel=0.1)

    def test_without_time_falls_back_to_random_and_says_so(self, tmp_path):
        frames = make_frames(n_symbols=6, n_days=450, seed=4)
        data, names = self._datasets(tmp_path, frames)
        df = pd.concat(data.values(), ignore_index=True).drop(columns=['time'])
        assert TrendClassifier().train(df, names)['split'] == 'random_leaky'

    def test_report_survives_missing_class_in_test_period(self, tmp_path):
        frames = make_frames(n_symbols=6, n_days=450, seed=5)
        data, names = self._datasets(tmp_path, frames)
        df = pd.concat(data.values(), ignore_index=True)
        df.loc[df['time'] > df['time'].quantile(0.8), 'target'] = 0      # test chỉ còn 1 lớp
        m = TrendClassifier().train(df, names, horizon=5)
        assert m['classification_report']['UP']['support'] == 0

    def test_random_split_inflates_accuracy_versus_purged(self, tmp_path):
        # Dữ liệu NHIỄU THUẦN: không có gì để học → độ chính xác thật ~ tỷ lệ lớp. Chia ngẫu nhiên làm thổi phồng.
        frames = make_frames(n_symbols=20, n_days=600, seed=6)
        data, names = self._datasets(tmp_path, frames, horizon=5)
        df = pd.concat(data.values(), ignore_index=True)
        purged = TrendClassifier().train(df, names, horizon=5)['test_accuracy']
        leaky = TrendClassifier().train(df.drop(columns=['time']), names)['test_accuracy']
        assert leaky - purged > 0.05, f'leaky={leaky:.3f} purged={purged:.3f}'


# ================================================================== thống kê
class TestStats:
    def test_block_bootstrap_mean(self):
        x = np.random.default_rng(0).normal(0.5, 1.0, 300)
        r = research.block_bootstrap_mean(x, 10, 500)
        assert r['ci_lower'] < r['mean'] < r['ci_upper'] and r['ci_lower'] > 0
        assert r == research.block_bootstrap_mean(x, 10, 500)
        assert research.block_bootstrap_mean(x[:20], 10, 100) is None

    def test_round_trip_cost_matches_backtest_params(self):
        assert research.round_trip_cost() == pytest.approx(0.006)

    def test_daily_cross_section_ic_sign(self):
        rng = np.random.default_rng(1)
        rows = []
        for d in pd.bdate_range('2024-01-01', periods=40):
            score = rng.uniform(size=20)
            for s, e in zip(score, score + rng.normal(0, 0.2, 20)):
                rows.append({'date': d, 'score': s, 'excess': e})
        cs = research.daily_cross_section(pd.DataFrame(rows), 'score', 0.2, 10)
        assert cs['ic'].mean() > 0.5 and cs['top_excess'].mean() > 0


def summary(ic_mean=0.05, ic_lo=0.02, ic_hi=0.08, top=0.02, top_lo=0.01, n=300):
    return {'n_dates': n, 'ic': {'mean': ic_mean, 'ci_lower': ic_lo, 'ci_upper': ic_hi, 'n': n},
            'top_excess': {'mean': top, 'ci_lower': top_lo, 'ci_upper': top * 2, 'n': n}}


class TestDecision:
    cfg = {**config.ML_VALIDATION}
    cost = 0.006

    def test_all_pass_is_has_edge(self):
        v, _ = research.decide(summary(), summary(ic_mean=0.03), self.cfg, self.cost)
        assert v == 'HAS_EDGE'

    def test_ic_not_above_zero_is_no_edge(self):
        v, _ = research.decide(summary(ic_mean=-0.01, ic_lo=-0.04, ic_hi=-0.001, top=-0.005, top_lo=-0.01),
                               summary(), self.cfg, self.cost)
        assert v == 'NO_EDGE'

    def test_edge_not_covering_costs_is_not_has_edge(self):
        v, checks = research.decide(summary(top=0.004, top_lo=0.003), summary(ic_mean=0.03), self.cfg, self.cost)
        assert v != 'HAS_EDGE'
        assert next(c for c in checks if c['name'].startswith('Lợi suất vượt'))['status'] == 'FAIL'

    def test_not_beating_momentum_baseline_is_not_has_edge(self):
        v, _ = research.decide(summary(ic_mean=0.04), summary(ic_mean=0.06), self.cfg, self.cost)
        assert v != 'HAS_EDGE'

    def test_too_few_oos_dates_is_inconclusive(self):
        v, _ = research.decide(summary(n=100), summary(ic_mean=0.03, n=100), self.cfg, self.cost)
        assert v == 'INCONCLUSIVE'

    def test_missing_statistics_is_inconclusive(self):
        v, _ = research.decide({'n_dates': 10, 'ic': None, 'top_excess': None}, {'ic': None}, self.cfg, self.cost)
        assert v == 'INCONCLUSIVE'


# ================================================================== end-to-end trên dữ liệu tổng hợp
class TestValidationEndToEnd:
    @pytest.mark.parametrize('seed', [11, 12, 13])
    def test_pure_noise_never_yields_edge(self, seed):
        report = research.run_validation(make_frames(seed=seed), cfg=FAST)
        assert report['verdict'] != 'HAS_EDGE'
        ic = report['ml']['ic']
        assert ic['ci_lower'] <= 0.0 <= ic['ci_upper'] or ic['ci_lower'] < 0.05      # không có IC dương ý nghĩa

    def test_planted_persistent_signal_is_detected(self, signal_frames):
        report = research.run_validation(signal_frames, cfg=FAST)
        ml, rnd = report['ml'], report['random_baseline']
        assert ml['ic']['ci_lower'] > 0
        assert ml['top_excess']['ci_lower'] > research.round_trip_cost()
        assert ml['ic']['mean'] > rnd['ic']['mean'] + 0.05
        assert report['momentum_baseline']['ic']['ci_lower'] > 0
        assert report['auc_oos'] > 0.55

    def test_report_structure_and_file(self, noise_frames, tmp_path):
        out = tmp_path / 'ml' / 'validation_report.json'
        report = research.run_validation(noise_frames, cfg={**FAST, 'report_file': str(out)}, write=True)
        saved = json.loads(out.read_text(encoding='utf-8'))
        assert saved['verdict'] == report['verdict'] and saved['caveats']
        assert len(saved['folds']) == 3 and saved['horizon'] == 20

    def test_fold_boundaries_never_overlap_label_windows(self, noise_frames):
        report = research.run_validation(noise_frames, cfg=FAST)
        cal = sorted(noise_frames['S00']['time'])
        pos = {d.strftime('%Y-%m-%d'): i for i, d in enumerate(cal)}
        for f in report['folds']:
            assert pos[f['train_end']] + 20 < pos[f['test_start']]

    def test_too_little_history_raises_instead_of_guessing(self):
        with pytest.raises(ValueError):
            research.run_validation(make_frames(n_days=330), cfg=FAST)


class TestConfig:
    def test_defaults_match_strategy(self):
        assert config.ML_VALIDATION['horizon'] == 20
        assert config.ML_VALIDATION['bootstrap_block'] == config.ML_VALIDATION['horizon']
