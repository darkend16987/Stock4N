import pandas as pd
import numpy as np
import os
import sys

# Hack để import config từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class FinancialCalculator:
    """
    Module tính toán các chỉ số tài chính từ dữ liệu thô.
    Mục tiêu: Tạo ra một bản tóm tắt sức khỏe (Health Check) cho từng mã.
    """
    
    def __init__(self, data_dir=config.RAW_DIR, output_dir=config.PROCESSED_DIR):
        self.data_dir = data_dir
        self.output_dir = output_dir
        # Mapping các tên cột từ file CSV (Do vnstock trả về tiếng Việt/Anh lộn xộn)
        self.col_map = {
            'profit': ['Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)', 'Lợi nhuận sau thuế (đồng)', 'post_tax_profit'],
            'revenue': ['Doanh thu thuần (đồng)', 'net_revenue'],
            'equity': ['VỐN CHỦ SỞ HỮU (đồng)', 'owners_equity'],
            'assets': ['TỔNG CỘNG TÀI SẢN (đồng)', 'total_assets']
        }

    def _find_col(self, df, keywords):
        """Tìm tên cột chính xác trong DataFrame dựa trên từ khóa"""
        for col in df.columns:
            for kw in keywords:
                if kw.lower() in col.lower():
                    return col
        return None

    def load_data(self, symbol):
        """Đọc dữ liệu thô từ CSV"""
        data = {}
        try:
            # Load Price
            p_path = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if os.path.exists(p_path):
                data['price'] = pd.read_csv(p_path)
            
            # Load Financials
            for r_type in ['BalanceSheet', 'IncomeStatement']:
                f_path = os.path.join(self.data_dir, f"{symbol}_fin_{r_type}.csv")
                if os.path.exists(f_path):
                    data[r_type] = pd.read_csv(f_path)
        except Exception as e:
            print(f"  ❌ Error loading data for {symbol}: {e}")
        return data

    def calculate_metrics(self, symbol):
        """Tính toán các chỉ số cơ bản"""
        data = self.load_data(symbol)
        
        # 1. Kiểm tra dữ liệu tối thiểu
        if 'price' not in data or 'IncomeStatement' not in data:
            return None

        try:
            # Lấy giá đóng cửa mới nhất
            if data['price'].empty: return None
            # Đảm bảo sort theo thời gian
            data['price']['time'] = pd.to_datetime(data['price']['time'])
            data['price'] = data['price'].sort_values('time')
            latest_price = data['price'].iloc[-1]['close']
            
            # Xử lý Báo cáo KQKD (Income Statement)
            inc_df = data['IncomeStatement']
            # Sort: Năm tăng dần, Kỳ (Quý) tăng dần
            if 'Năm' in inc_df.columns and 'Kỳ' in inc_df.columns:
                 inc_df = inc_df.sort_values(by=['Năm', 'Kỳ'], ascending=True)
            
            # Tìm cột Lợi nhuận & Doanh thu
            profit_col = self._find_col(inc_df, self.col_map['profit'])
            rev_col = self._find_col(inc_df, self.col_map['revenue'])

            # Xử lý Bảng CĐKT (Balance Sheet) - Để lấy Vốn chủ sở hữu
            bs_df = data.get('BalanceSheet')
            equity_col = None
            if bs_df is not None:
                if 'Năm' in bs_df.columns and 'Kỳ' in bs_df.columns:
                     bs_df = bs_df.sort_values(by=['Năm', 'Kỳ'], ascending=True)
                equity_col = self._find_col(bs_df, self.col_map['equity'])
            
            # --- BẮT ĐẦU TÍNH TOÁN ---
            metrics = {
                'Symbol': symbol,
                'Price': latest_price,
                'PE': None,
                'PB': None,
                'ROE': None,
                'Revenue_Growth_YoY': None,
                'Profit_Growth_YoY': None
            }

            # 1. Tính EPS & P/E (Dùng TTM - Trailing 12 Months)
            if profit_col:
                # Lấy 4 quý gần nhất
                last_4_quarters = inc_df.tail(4)
                if len(last_4_quarters) == 4:
                    net_profit_ttm = last_4_quarters[profit_col].sum()
                    
                    # Giả định số lượng cổ phiếu (Đây là điểm khó nếu không có data Profile)
                    # Tạm thời ta dùng MarketCap / Price nếu có, hoặc dùng NetProfit / PE nếu có nguồn khác
                    # Ở đây ta sẽ tính 'Earnings Yield Proxy' = NetProfit_TTM / MarketCap
                    # Nhưng để đơn giản cho Phase này, ta sẽ lưu Raw Profit để so sánh
                    metrics['Net_Profit_TTM'] = net_profit_ttm
                    
                    # Tính Tăng trưởng (So quý gần nhất với cùng kỳ năm trước)
                    if len(inc_df) >= 5:
                        current_q_profit = inc_df.iloc[-1][profit_col]
                        prev_year_q_profit = inc_df.iloc[-5][profit_col]
                        
                        if prev_year_q_profit != 0:
                            metrics['Profit_Growth_YoY'] = round((current_q_profit - prev_year_q_profit) / abs(prev_year_q_profit) * 100, 2)

            # 2. Tính P/B & ROE
            if equity_col and bs_df is not None and not bs_df.empty:
                latest_equity = bs_df.iloc[-1][equity_col]
                
                # ROE = Profit TTM / Equity
                if 'Net_Profit_TTM' in metrics and latest_equity > 0:
                    metrics['ROE'] = round((metrics['Net_Profit_TTM'] / latest_equity) * 100, 2)
                
                # P/B cần Market Cap. 
                # Ta có thể ước lượng định giá rẻ/đắt bằng cách so sánh Price biến động với Equity biến động? 
                # Không, cần số lượng cổ phiếu.
                # Tạm thời để trống P/B nếu không có SLCP.

            # 3. Tính Tăng trưởng Doanh thu
            if rev_col and len(inc_df) >= 5:
                current_q_rev = inc_df.iloc[-1][rev_col]
                prev_year_q_rev = inc_df.iloc[-5][rev_col]
                if prev_year_q_rev != 0:
                     metrics['Revenue_Growth_YoY'] = round((current_q_rev - prev_year_q_rev) / abs(prev_year_q_rev) * 100, 2)

            return metrics

        except Exception as e:
            print(f"  ⚠️ Error calculating for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def run_processing(self, symbols):
        print(f"⚙️ [Processing] Đang tính toán chỉ số cho {len(symbols)} mã...")
        results = []
        
        for symbol in symbols:
            print(f"Processing {symbol}...", end=" ", flush=True)
            metrics = self.calculate_metrics(symbol)
            if metrics:
                results.append(metrics)
                print("✅ Done")
            else:
                print("⏩ Skipped (Thiếu data)")
        
        # Lưu kết quả tổng hợp
        if results:
            df_result = pd.DataFrame(results)
            output_path = os.path.join(self.output_dir, "financial_metrics.csv")
            df_result.to_csv(output_path, index=False)
            print(f"\n✅ Đã lưu kết quả xử lý vào: {output_path}")
            
            # Hiển thị thử kết quả
            print("\n📊 PREVIEW KẾT QUẢ:")
            print(df_result[['Symbol', 'Price', 'ROE', 'Revenue_Growth_YoY', 'Profit_Growth_YoY']].to_string())
            
            return df_result
        return pd.DataFrame()