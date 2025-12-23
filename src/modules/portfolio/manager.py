import pandas as pd
import os
import sys

# Hack import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class PortfolioManager:
    """
    Module quản lý danh mục: Phân bổ vốn & Quản trị rủi ro.
    """
    def __init__(self, processed_dir=config.PROCESSED_DIR):
        self.processed_dir = processed_dir
        
    def generate_recommendation(self, total_capital=100000000): # Mặc định vốn giả lập 100tr VND
        print(f"💼 [Portfolio] Đang xây dựng danh mục khuyến nghị (Vốn giả lập: {total_capital:,.0f} VND)...")
        
        report_path = os.path.join(self.processed_dir, "analysis_report.csv")
        if not os.path.exists(report_path):
            print("❌ Chưa có file analysis_report.csv. Hãy chạy lệnh 'analyze' trước.")
            return

        df = pd.read_csv(report_path)
        
        # 1. Lọc các mã có khuyến nghị MUA
        # (Chứa từ 'MUA' trong cột Recommendation)
        buy_list = df[df['Recommendation'].str.contains('MUA', case=False, na=False)].copy()
        
        if buy_list.empty:
            print("⚠️ Thị trường rủi ro: Không có mã nào đạt tiêu chuẩn MUA trong đợt quét này.")
            print("💡 Khuyến nghị: Giữ 100% Tiền mặt.")
            return

        # 2. Tính toán tỷ trọng (Allocation)
        # Logic: Tổng điểm các mã mua
        total_buy_score = buy_list['Total_Score'].sum()
        
        recommendations = []
        
        # Tiền khả dụng để mua (Giả sử dành 100% cash cho các mã đạt chuẩn)
        # Trong thực tế có thể chỉ dành 70% cash nếu thị trường chung yếu
        available_cash = total_capital 

        for index, row in buy_list.iterrows():
            symbol = row['Symbol']
            score = row['Total_Score']
            price = row['Price'] * 1000 # Giá trong file csv đang là đơn vị nghìn đồng (ví dụ 27.0) -> nhân 1000
            
            if price == 0: continue

            # Tỷ trọng thô = Điểm / Tổng điểm
            raw_weight = score / total_buy_score
            
            # Rule: Max 40% cho 1 mã để đa dạng hóa
            weight = min(0.40, raw_weight) 
            
            # Nếu chỉ có 1 mã thì cho max 40%, còn lại giữ tiền
            if len(buy_list) == 1:
                weight = 0.40

            amount = available_cash * weight
            # Làm tròn lô 100 cổ phiếu
            shares = int(amount / price / 100) * 100
            
            # Tính lại số tiền thực tế
            actual_amount = shares * price
            actual_weight = actual_amount / total_capital

            # 3. Quản trị rủi ro (Risk Management)
            # Stoploss: -7% (Quy tắc cắt lỗ kinh điển)
            stop_loss_price = round(price * 0.93, 0)
            
            # Target: +15% (R:R ~ 1:2)
            target_price = round(price * 1.15, 0)
            
            if shares > 0:
                recommendations.append({
                    'Symbol': symbol,
                    'Action': row['Recommendation'],
                    'Score': score,
                    'Entry_Price': f"{price:,.0f}",
                    'Weight_%': f"{actual_weight*100:.1f}%",
                    'Capital_VND': f"{actual_amount:,.0f}",
                    'Volume_Shares': shares,
                    'Stop_Loss': f"{stop_loss_price:,.0f}",
                    'Target': f"{target_price:,.0f}",
                    'Risk/Reward': "1:2"
                })
            
        # Xuất file
        if recommendations:
            df_rec = pd.DataFrame(recommendations)
            output_path = os.path.join(self.processed_dir, "portfolio_recommendation.csv")
            df_rec.to_csv(output_path, index=False)
            
            print(f"✅ Đã tạo khuyến nghị phân bổ vốn tại: {output_path}")
            print("\n💰 DANH MỤC KHUYẾN NGHỊ CHI TIẾT:")
            print(df_rec[['Symbol', 'Action', 'Weight_%', 'Volume_Shares', 'Stop_Loss', 'Target']].to_string())
            
            remaining_cash = total_capital - df_rec['Capital_VND'].str.replace(',','').astype(float).sum()
            print(f"\n💵 Tiền mặt còn lại: {remaining_cash:,.0f} VND")
        else:
            print("⚠️ Không đủ vốn để mua lô tối thiểu (100cp) cho các mã khuyến nghị.")