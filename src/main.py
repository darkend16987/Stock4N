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

def main():
    parser = argparse.ArgumentParser(description="VN-Stock Intelligent Advisor CLI")
    parser.add_argument('mode', choices=['ingest', 'process', 'analyze', 'portfolio', 'export', 'all'], help="Chế độ chạy")
    
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    if args.mode == 'ingest': run_ingestion()
    elif args.mode == 'process': run_processing()
    elif args.mode == 'analyze': run_analysis()
    elif args.mode == 'portfolio': run_portfolio()
    elif args.mode == 'export': run_export()
    elif args.mode == 'all':
        run_ingestion()
        run_processing()
        run_analysis()
        run_portfolio()
        run_export()

if __name__ == "__main__":
    main()