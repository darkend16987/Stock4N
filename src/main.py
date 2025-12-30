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

def run_analysis():
    print("🧠 [MODE] Market Analysis")
    scorer = StockScorer()
    scorer.run_analysis()

def run_portfolio():
    print("💼 [MODE] Portfolio Manager")
    manager = PortfolioManager()
    manager.generate_recommendation(total_capital=100000000)

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
        choices=['ingestion', 'processing', 'analysis', 'portfolio', 'export', 'backtest', 'learn', 'ml_predict', 'all'],
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

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    if args.mode == 'ingestion': run_ingestion()
    elif args.mode == 'processing': run_processing()
    elif args.mode == 'analysis': run_analysis()
    elif args.mode == 'portfolio': run_portfolio()
    elif args.mode == 'export': run_export()
    elif args.mode == 'backtest': run_backtest(args.days, args.score, args.capital)
    elif args.mode == 'learn': run_learning(args.learn_mode, args.optimize_weights, args.days)
    elif args.mode == 'ml_predict': run_ml_predict(args.ml_mode, args.model_type, args.horizon, args.threshold)
    elif args.mode == 'all':
        run_ingestion()
        run_processing()
        run_analysis()
        run_portfolio()
        run_export()

if __name__ == "__main__":
    main()