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

def main():
    parser = argparse.ArgumentParser(description="VN-Stock Intelligent Advisor CLI")
    parser.add_argument(
        'mode',
        choices=['ingestion', 'processing', 'analysis', 'portfolio', 'export', 'backtest', 'learn', 'all'],
        help="Chế độ chạy"
    )
    parser.add_argument('--days', type=int, default=365, help="Backtest/Learning lookback days (default: 365)")
    parser.add_argument('--score', type=float, default=6.0, help="Min score to buy (default: 6.0)")
    parser.add_argument('--capital', type=int, default=100000000, help="Initial capital (default: 100M)")
    parser.add_argument('--learn-mode', type=str, default='all', choices=['patterns', 'optimize', 'all'],
                        help="Learning mode: patterns, optimize, or all (default: all)")
    parser.add_argument('--optimize-weights', action='store_true', help="Run weight optimization in learning mode")

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
    elif args.mode == 'all':
        run_ingestion()
        run_processing()
        run_analysis()
        run_portfolio()
        run_export()

if __name__ == "__main__":
    main()