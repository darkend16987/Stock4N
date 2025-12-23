import pandas as pd
import json
import os
import sys

# Hack import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class DataExporter:
    """
    Module chuyển đổi dữ liệu CSV sang JSON để phục vụ Web Frontend (Next.js/Vercel)
    """
    def __init__(self, processed_dir=config.PROCESSED_DIR, raw_dir=config.RAW_DIR):
        self.processed_dir = processed_dir
        self.raw_dir = raw_dir
        self.export_dir = os.path.join(config.DATA_DIR, "export")
        os.makedirs(self.export_dir, exist_ok=True)

    def export_all(self):
        print(f"📦 [Exporter] Đang xuất dữ liệu sang JSON tại: {self.export_dir}")
        data_store = {
            "last_updated": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            "analysis": [],
            "portfolio": [],
            "charts": {}
        }

        # 1. Export Analysis Report (Bảng xếp hạng)
        analysis_path = os.path.join(self.processed_dir, "analysis_report.csv")
        if os.path.exists(analysis_path):
            df = pd.read_csv(analysis_path)
            data_store["analysis"] = df.to_dict(orient="records")
        
        # 2. Export Portfolio (Danh mục khuyến nghị)
        portfolio_path = os.path.join(self.processed_dir, "portfolio_recommendation.csv")
        if os.path.exists(portfolio_path):
            df = pd.read_csv(portfolio_path)
            data_store["portfolio"] = df.to_dict(orient="records")

        # 3. Export Price History (Biểu đồ) cho các mã trong Analysis
        # Chỉ lấy top mã để giảm dung lượng file JSON
        if "analysis" in data_store:
            top_symbols = [item['Symbol'] for item in data_store["analysis"]]
            
            for symbol in top_symbols:
                price_path = os.path.join(self.raw_dir, f"{symbol}_price.csv")
                if os.path.exists(price_path):
                    df = pd.read_csv(price_path)
                    # Giảm tải: Chỉ lấy 100 phiên gần nhất
                    df = df.tail(100)
                    data_store["charts"][symbol] = df.to_dict(orient="records")

        # Lưu file JSON chính
        output_file = os.path.join(self.export_dir, "db.json")
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(data_store, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Đã xuất file {output_file} thành công!")

if __name__ == "__main__":
    exporter = DataExporter()
    exporter.export_all()