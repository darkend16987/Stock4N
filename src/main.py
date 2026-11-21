import argparse
import sys
import os
import subprocess

# Thêm đường dẫn root vào system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.ingestion.loader import VNStockLoader
    from modules.processing.calculator import FinancialCalculator
    from modules.analysis.scorer import StockScorer
    from modules.portfolio.manager import PortfolioManager
    from modules.utils.exporter import DataExporter
    from modules.simulation.backtest_engine import BacktestEngine
    from modules.simulation.performance import PerformanceMetrics
    from modules.simulation.reporter import BacktestReporter
    from modules.learning.pattern_analyzer import PatternAnalyzer
    from modules.learning.weight_optimizer import WeightOptimizer
    from modules.learning.parameter_manager import ParameterManager
    from modules.ml_prediction.feature_engineer import FeatureEngineer
    from modules.ml_prediction.trend_classifier import TrendClassifier
    from modules.ml_prediction.model_manager import ModelManager
    from modules.analysis.breadth_analyzer import MarketBreadthAnalyzer
    from modules.analysis.adaptive_params import AdaptiveParamManager
    from modules.analysis.ai_reasoner import AIReasoner
    from modules.analysis.price_filter_scanner import PriceFilterScanner
    import config
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)

def run_ingestion():
    print("🚀 [MODE] Data Ingestion")
    loader = VNStockLoader()
    loader.run_ingestion(config.VN100_SYMBOLS)

def run_processing():
    print("⚙️ [MODE] Data Processing")
    calculator = FinancialCalculator()
    calculator.run_processing(config.VN100_SYMBOLS)

def get_market_filter():
    """Market breadth filter dùng chung cho analysis (RuleGate) và portfolio (risk multiplier)."""
    breadth = MarketBreadthAnalyzer()
    market_filter = breadth.get_market_filter(config.VN100_SYMBOLS)
    print(f"  {market_filter['summary']}")
    return market_filter

def run_analysis(use_adaptive=False):
    print("🧠 [MODE] Market Analysis")

    # Market breadth check (runs before individual scoring) → chặn MUA mới khi thị trường yếu
    print("\n📊 Checking market breadth...")
    market_filter = get_market_filter()

    # Adaptive param optimization (optional)
    if use_adaptive:
        print("\n⚙️  Running adaptive parameter optimization...")
        apm = AdaptiveParamManager()
        adaptive_params = apm.run_all(config.VN100_SYMBOLS)
        df_params = apm.get_summary_df(adaptive_params)
        params_file = os.path.join(config.PROCESSED_DIR, 'adaptive_params.csv')
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)
        df_params.to_csv(params_file, index=False)
        print(f"  ✓ Saved adaptive params to {params_file}")

    scorer = StockScorer()
    scorer.run_analysis(market_filter=market_filter)

def run_breadth():
    """Standalone breadth/sentiment check."""
    print("📊 [MODE] Market Breadth / Sentiment")
    analyzer = MarketBreadthAnalyzer()
    analyzer.print_breadth_report(config.VN100_SYMBOLS)

def run_portfolio():
    print("💼 [MODE] Portfolio Manager")
    manager = PortfolioManager()
    print("\n📊 Checking market breadth...")
    manager.generate_recommendation(total_capital=100000000, market_filter=get_market_filter())

def run_export():
    """Xuất dữ liệu sang JSON cho Web App"""
    print("📦 [MODE] Exporting Data for Web")
    exporter = DataExporter()
    exporter.export_all()

def run_backtest(lookback_days=365, min_score=6.0, capital=100000000):
    """
    Chạy backtest chiến lược

    Args:
        lookback_days: Số ngày quay lại để test (mặc định 365 = 1 năm)
        min_score: Điểm tối thiểu để mua (mặc định 6.0)
        capital: Vốn ban đầu (mặc định 100M)
    """
    print("🔬 [MODE] Backtesting Strategy")
    print("⚠️  Engine CŨ: dùng điểm của HÔM NAY để mua trong quá khứ (nhìn trước tương lai), không tính phí/T+2. "
          "Kết quả KHÔNG đáng tin cho quyết định tiền thật → dùng 'backtest_v2'.")
    print(f"Parameters: Lookback={lookback_days} days, Min Score={min_score}, Capital={capital:,}")

    from datetime import datetime, timedelta
    import pandas as pd

    # Define backtest period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    print(f"Period: {start_date.date()} to {end_date.date()}")

    # Load latest analysis scores
    analysis_file = os.path.join(config.PROCESSED_DIR, 'analysis_report.csv')
    if not os.path.exists(analysis_file):
        print("❌ Analysis file not found! Run 'analyze' first.")
        return

    scores_df = pd.read_csv(analysis_file)

    # Initialize backtest engine
    engine = BacktestEngine(
        data_dir=config.RAW_DIR,
        initial_capital=capital,
        max_positions=10,
        position_size_pct=0.10,
        stop_loss_pct=0.07,
        take_profit_pct=0.15
    )

    # Run backtest
    trades_df = engine.run_backtest(
        scores_df=scores_df,
        start_date=start_date,
        end_date=end_date,
        min_score=min_score
    )

    if trades_df.empty:
        print("⚠️  No trades executed. Try lowering min_score.")
        return

    # Calculate performance
    metrics = PerformanceMetrics(trades_df, initial_capital=capital)

    # Generate report
    reporter = BacktestReporter(trades_df, metrics)
    reporter.generate_full_report()

    print("\n✅ Backtest completed!")

def run_backtest_v2(lookback_days=None, capital=None):
    """
    Backtest point-in-time (BacktestEngineV2) + kiểm định thống kê + ngưỡng nghiệm thu.

    Args:
        lookback_days: chỉ lấy N ngày gần nhất (None = toàn bộ dữ liệu giá hiện có)
        capital: vốn ban đầu (None = config.BACKTEST_V2['initial_capital'])
    """
    print("🔬 [MODE] Backtest V2 (point-in-time, quy tắc HOSE)")
    import pandas as pd
    from modules.simulation.backtest_v2 import BacktestEngineV2

    params = {'initial_capital': capital} if capital else None
    engine = BacktestEngineV2(params=params)
    start = None
    if lookback_days:
        start = engine.book.calendar[-1] - pd.Timedelta(days=lookback_days)

    report, _ = engine.run_suite(start_date=start)
    m, acc = report['metrics'], report['acceptance']

    def pct(v):
        return 'n/a' if v is None else f"{v:.1%}"

    print(f"\nKỳ: {m['start']} → {m['end']} ({m['sessions']} phiên) | Benchmark: {m['benchmark']}")
    print(f"Tổng lãi {pct(m['total_return'])} | CAGR {pct(m['cagr'])} | Max DD {pct(m['max_drawdown'])} | "
          f"Sharpe {m['sharpe'] if m['sharpe'] is None else round(m['sharpe'], 2)}")
    print(f"Số lệnh {m['n_trades']} | Win rate {pct(m['win_rate'])} | Profit factor {m['profit_factor']}")
    print(f"\nNGHIỆM THU: {acc['verdict']}")
    for c in acc['checks']:
        print(f"  [{c['status']:>4}] {c['name']}: {c['value']} (yêu cầu {c['rule']} {c['threshold']})")
    print("\nHẠN CHẾ:")
    for note in report['limitations']:
        print(f"  - {note}")


def run_committee(mode=None):
    """
    Hội đồng đầu tư LLM (Bull/Bear/Risk/PM) trên các mã đang được khuyến nghị MUA. CHỈ CÓ QUYỀN PHỦ QUYẾT.
    shadow (mặc định): chỉ ghi committee_report.csv + ledger để forward-test, KHÔNG đổi analysis_report.csv.
    enforce: veto hạ MUA → THEO DÕI trong analysis_report.csv (bản gốc được sao lưu).
    """
    print("🏛️ [MODE] Investment Committee (veto-only)")
    import pandas as pd
    from datetime import datetime
    from modules.committee.committee import InvestmentCommittee
    from modules.committee.llm import GeminiClient

    mode = mode or config.COMMITTEE_CONFIG['mode']
    report_path = os.path.join(config.PROCESSED_DIR, 'analysis_report.csv')
    if not os.path.exists(report_path):
        print("❌ Chưa có analysis_report.csv - chạy 'analysis' trước.")
        return

    client = GeminiClient()
    if not client.available:
        print("❌ Thiếu GOOGLE_API_KEY hoặc gói google-generativeai → hội đồng không chạy, khuyến nghị giữ nguyên.")
        return

    report = pd.read_csv(report_path)
    if 'Pre_Committee_Recommendation' in report.columns:          # chạy lại: khôi phục khuyến nghị gốc
        report['Recommendation'] = report['Pre_Committee_Recommendation']
        report = report.drop(columns=[c for c in report.columns if c.startswith('Committee_')
                                      or c == 'Pre_Committee_Recommendation'])
    metrics_path = os.path.join(config.PROCESSED_DIR, 'financial_metrics.csv')
    metrics = pd.read_csv(metrics_path) if os.path.exists(metrics_path) else None

    print("\n📊 Checking market breadth...")
    from modules.committee.memory import OutcomeStore, build_lessons
    store = OutcomeStore()
    committee = InvestmentCommittee(client, lessons_provider=lambda as_of: build_lessons(store.read(), as_of))
    out, verdicts = committee.run(report, metrics, get_market_filter(), mode)

    out.to_csv(os.path.join(config.PROCESSED_DIR, 'committee_report.csv'), index=False)
    if mode == 'enforce':
        backup = os.path.join(config.PROCESSED_DIR, f"analysis_report.pre_committee_{datetime.now():%Y%m%d_%H%M%S}.csv")
        report.to_csv(backup, index=False)
        out.to_csv(report_path, index=False)
        print(f"  ✓ Đã cập nhật analysis_report.csv (bản gốc: {backup})")

    ok = [v for v in verdicts if v['status'] == 'OK']
    vetoes = [v for v in ok if v['action'] == 'VETO']
    print(f"\nChế độ: {mode.upper()} | Đã xét {len(verdicts)} mã | hợp lệ {len(ok)} | "
          f"lỗi/không hợp lệ {len(verdicts) - len(ok)} | VETO {len(vetoes)} | LLM calls {committee.calls}")
    for v in verdicts:
        tag = v['action'] if v['status'] == 'OK' else v['status']
        print(f"  {v['symbol']:<6} {tag:<10} {','.join(v['risk_flags'])}")
    if mode == 'shadow':
        print("\n(shadow: chưa ảnh hưởng khuyến nghị. Ledger: " + config.COMMITTEE_CONFIG['ledger_file'] + ")")


def run_committee_settle():
    """
    Đối chiếu các quyết định của hội đồng đã đủ 20 phiên với kết quả thực (so với benchmark),
    rồi đánh giá đã đủ bằng chứng để chuyển hội đồng sang 'enforce' hay chưa.
    """
    print("🧾 [MODE] Committee Settlement & Readiness")
    import json
    from modules.committee.ledger import Ledger
    from modules.committee.memory import OutcomeStore, evaluate_readiness, settle_pending
    from modules.simulation.point_in_time import PriceBook

    entries = Ledger().entries()
    if not entries:
        print("ℹ️  Ledger trống - chạy 'committee' (shadow) vài tháng trước.")
        return
    book = PriceBook(config.RAW_DIR, config.VN100_SYMBOLS)
    benchmark, label = book.benchmark()
    store = OutcomeStore()
    new = settle_pending(entries, store, book, benchmark, label)
    outcomes = store.read()
    print(f"  Benchmark: {label} | settle mới: {len(new)} | tổng đã settle: {len(outcomes)}")

    report = evaluate_readiness(outcomes, entries)
    print(f"\nSẴN SÀNG ENFORCE? → {report['verdict']}")
    for c in report['checks']:
        print(f"  [{c['status']:>6}] {c['name']}: {c['value']} (yêu cầu {c['rule']} {c['threshold']})")
    path = os.path.join(config.DATA_DIR, 'committee', 'committee_readiness.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Báo cáo: {path}")


def run_learning(mode='patterns', optimize_weights=False, lookback_days=365):
    """
    Chạy learning module - Phân tích patterns và tối ưu weights

    Args:
        mode: 'patterns' or 'optimize' or 'all'
        optimize_weights: Có tối ưu weights hay không
        lookback_days: Số ngày dữ liệu để học
    """
    print("🧠 [MODE] Learning & Optimization")

    param_manager = ParameterManager()

    # Pattern Analysis
    if mode in ['patterns', 'all']:
        print("\n📊 Analyzing patterns...")
        analyzer = PatternAnalyzer()

        patterns = analyzer.analyze_all_patterns(config.VN100_SYMBOLS)

        # Save patterns
        param_manager.save_patterns(patterns)
        print(f"✅ Analyzed patterns for {len(patterns)} symbols")

        # Print some insights
        print("\n📈 Pattern Insights:")
        for symbol in list(patterns.keys())[:5]:  # Show first 5
            if patterns[symbol]:
                signal = analyzer.get_trading_signals(symbol)
                print(f"  {symbol}: Combined Signal={signal['combined_signal']}, "
                      f"Confidence={signal['confidence']}")

    # Weight Optimization
    if mode in ['optimize', 'all'] or optimize_weights:
        print("\n⚖️  Optimizing weights...")

        # Load analysis scores
        import pandas as pd
        from datetime import datetime, timedelta

        analysis_file = os.path.join(config.PROCESSED_DIR, 'analysis_report.csv')
        if not os.path.exists(analysis_file):
            print("❌ Analysis file not found! Run 'analysis' first.")
            return

        scores_df = pd.read_csv(analysis_file)

        # Define optimization period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        optimizer = WeightOptimizer()

        best_weights = optimizer.optimize_weights(
            scores_df=scores_df,
            start_date=start_date,
            end_date=end_date,
            initial_capital=100_000_000,
            min_score=6.0,
            optimization_metric='sharpe_ratio'
        )

        if best_weights:
            # Save results
            optimizer.save_optimization_results()
            param_manager.save_weights(best_weights)

            # Print summary
            print("\n" + optimizer.get_optimization_summary())
        else:
            print("⚠️  Weight optimization failed")

    # Print overall summary
    print("\n" + param_manager.get_summary())
    print("\n✅ Learning completed!")

def run_price_filter():
    """Quét toàn bộ thị trường lọc cổ phiếu theo tiêu chí giá/khối lượng/PE/PB."""
    print("🔍 [MODE] Price Filter Scanner")
    print("Conditions: Close < SMA200, Avg Vol 20 >= 500K, PE < 20, PB < 5")
    print("This scan covers ALL listed stocks and may take a long time due to API rate limits.")
    print("Progress is saved automatically - you can resume if interrupted.\n")

    scanner = PriceFilterScanner()
    results = scanner.run_scan()

    if not results.empty:
        print(f"\n✅ Found {len(results)} matching stocks!")
        print(results.to_string(index=False))
    else:
        print("\n⚠️  No stocks matched all criteria.")


def run_ml_predict(mode='train', model_type='random_forest', horizon=5, threshold=0.02):
    """
    Chạy ML prediction - Train model hoặc predict trends

    Args:
        mode: 'train' or 'predict'
        model_type: 'random_forest' or 'gradient_boosting'
        horizon: Forecast horizon (days)
        threshold: Classification threshold (%)
    """
    print("🤖 [MODE] ML Prediction")

    model_manager = ModelManager()

    if mode == 'train':
        print(f"\n🎓 Training {model_type} model...")
        print(f"Forecast horizon: {horizon} days, Threshold: {threshold*100}%")

        # Feature engineering
        print("\n📊 Creating features...")
        engineer = FeatureEngineer()

        datasets = engineer.prepare_batch_datasets(
            symbols=config.VN100_SYMBOLS,
            horizon=horizon,
            threshold=threshold
        )

        if not datasets:
            print("❌ No datasets prepared!")
            return

        print(f"✓ Prepared {len(datasets)} datasets")

        # Get feature names
        feature_names = engineer.get_feature_names()
        print(f"✓ Generated {len(feature_names)} features")

        # Train model
        print("\n🧠 Training model...")
        classifier = TrendClassifier(model_type=model_type)

        metrics = classifier.train_multi_symbol(
            datasets=datasets,
            feature_names=feature_names,
            test_size=0.2
        )

        # Save model
        print("\n💾 Saving model...")
        metadata = {
            'horizon': horizon,
            'threshold': threshold,
            'symbols': list(datasets.keys()),
            'n_symbols': len(datasets)
        }

        model_manager.save_model(
            model=classifier,
            model_name='trend_classifier',
            metadata=metadata
        )

        # Print summary
        print("\n" + classifier.get_model_summary())

        print("\n✅ Training completed!")

    elif mode == 'predict':
        print("\n🔮 Generating predictions...")

        # Load latest model
        model = model_manager.load_model('trend_classifier', 'latest')
        if model is None:
            print("❌ No trained model found! Run 'train' first.")
            return

        metadata = model_manager.load_metadata('trend_classifier', 'latest')
        print(f"✓ Loaded model (trained: {metadata.get('saved_at', 'N/A')})")

        # Get latest features for all symbols
        print("\n📊 Extracting latest features...")
        engineer = FeatureEngineer()

        predictions = []

        for symbol in config.VN100_SYMBOLS:
            try:
                features = engineer.get_latest_features(symbol)
                if features is not None:
                    pred = model.predict_single(features)

                    predictions.append({
                        'Symbol': symbol,
                        'Prediction': pred['prediction_label'],
                        'Confidence': f"{pred['confidence']:.2%}",
                        'P(UP)': f"{pred['probabilities']['UP']:.2%}",
                        'P(NEUTRAL)': f"{pred['probabilities']['NEUTRAL']:.2%}",
                        'P(DOWN)': f"{pred['probabilities']['DOWN']:.2%}"
                    })

                    print(f"  ✓ {symbol}: {pred['prediction_label']} ({pred['confidence']:.2%})")

            except Exception as e:
                print(f"  ⚠️  Error predicting {symbol}: {e}")

        # Save predictions
        import pandas as pd
        pred_df = pd.DataFrame(predictions)

        output_file = os.path.join(config.PROCESSED_DIR, 'ml_predictions.csv')
        pred_df.to_csv(output_file, index=False)

        print(f"\n✓ Generated {len(predictions)} predictions")
        print(f"✓ Saved to {output_file}")

        # Summary
        print("\n📊 Prediction Summary:")
        pred_counts = pred_df['Prediction'].value_counts()
        for pred, count in pred_counts.items():
            print(f"  {pred}: {count} stocks")

        # Top confident predictions
        print("\n🎯 Top 10 Confident Predictions:")
        pred_df['Confidence_num'] = pred_df['Confidence'].str.rstrip('%').astype(float)
        top10 = pred_df.nlargest(10, 'Confidence_num')[['Symbol', 'Prediction', 'Confidence']]
        print(top10.to_string(index=False))

        print("\n✅ Prediction completed!")

    else:
        print(f"❌ Unknown mode: {mode}")

def main():
    parser = argparse.ArgumentParser(description="VN-Stock Intelligent Advisor CLI")
    parser.add_argument(
        'mode',
        choices=['ingestion', 'processing', 'analysis', 'portfolio', 'export',
                 'backtest', 'backtest_v2', 'committee', 'committee_settle', 'learn', 'ml_predict', 'breadth', 'price_filter', 'all'],
        help="Chế độ chạy"
    )
    parser.add_argument('--days', type=int, default=365, help="Backtest/Learning lookback days (default: 365)")
    parser.add_argument('--score', type=float, default=6.0, help="Min score to buy (default: 6.0)")
    parser.add_argument('--capital', type=int, default=100000000, help="Initial capital (default: 100M)")
    parser.add_argument('--learn-mode', type=str, default='all', choices=['patterns', 'optimize', 'all'],
                        help="Learning mode: patterns, optimize, or all (default: all)")
    parser.add_argument('--optimize-weights', action='store_true', help="Run weight optimization in learning mode")
    parser.add_argument('--ml-mode', type=str, default='train', choices=['train', 'predict'],
                        help="ML mode: train or predict (default: train)")
    parser.add_argument('--model-type', type=str, default='random_forest',
                        choices=['random_forest', 'gradient_boosting'],
                        help="ML model type (default: random_forest)")
    parser.add_argument('--horizon', type=int, default=5, help="Forecast horizon in days (default: 5)")
    parser.add_argument('--threshold', type=float, default=0.02, help="Classification threshold (default: 0.02 = 2%)")
    parser.add_argument('--adaptive', action='store_true', help="Use adaptive parameter optimization in analysis")
    parser.add_argument('--committee-mode', type=str, default=None, choices=['shadow', 'enforce'],
                        help="Committee mode: shadow (log only, default from config) or enforce (veto downgrades BUY)")

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.mode == 'ingestion': run_ingestion()
    elif args.mode == 'processing': run_processing()
    elif args.mode == 'analysis': run_analysis(use_adaptive=args.adaptive)
    elif args.mode == 'portfolio': run_portfolio()
    elif args.mode == 'export': run_export()
    elif args.mode == 'breadth': run_breadth()
    elif args.mode == 'backtest': run_backtest(args.days, args.score, args.capital)
    elif args.mode == 'backtest_v2':
        # --days không truyền → dùng toàn bộ lịch sử giá (mặc định 365 chỉ áp cho backtest cũ)
        run_backtest_v2(args.days if '--days' in sys.argv else None, args.capital)
    elif args.mode == 'committee': run_committee(args.committee_mode)
    elif args.mode == 'committee_settle': run_committee_settle()
    elif args.mode == 'learn': run_learning(args.learn_mode, args.optimize_weights, args.days)
    elif args.mode == 'ml_predict': run_ml_predict(args.ml_mode, args.model_type, args.horizon, args.threshold)
    elif args.mode == 'price_filter': run_price_filter()
    elif args.mode == 'all':
        run_ingestion()
        run_processing()
        run_analysis(use_adaptive=args.adaptive)
        run_breadth()
        run_portfolio()
        run_export()

if __name__ == "__main__":
    main()