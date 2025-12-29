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

def main():
    parser = argparse.ArgumentParser(description="VN-Stock Intelligent Advisor CLI")
    parser.add_argument(
        'mode',
        choices=['ingestion', 'processing', 'analysis', 'portfolio', 'export', 'backtest', 'all'],
        help="Chế độ chạy"
    )
    parser.add_argument('--days', type=int, default=365, help="Backtest lookback days (default: 365)")
    parser.add_argument('--score', type=float, default=6.0, help="Min score to buy (default: 6.0)")
    parser.add_argument('--capital', type=int, default=100000000, help="Initial capital (default: 100M)")

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
    elif args.mode == 'all':
        run_ingestion()
        run_processing()
        run_analysis()
        run_portfolio()
        run_export()

if __name__ == "__main__":
    main()