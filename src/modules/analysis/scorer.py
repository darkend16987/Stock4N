import pandas as pd
import numpy as np
import os
import sys
import talib # Thư viện Phân tích kỹ thuật chuyên dụng

# Hack import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class StockScorer:
    """
    Module chấm điểm cổ phiếu dựa trên kết hợp Cơ bản & Kỹ thuật.
    """
    
    def __init__(self, data_dir=config.RAW_DIR, processed_dir=config.PROCESSED_DIR):
        self.data_dir = data_dir
        self.processed_dir = processed_dir
        
    def load_price_data(self, symbol):
        """Đọc dữ liệu giá để phân tích kỹ thuật"""
        try:
            p_path = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if os.path.exists(p_path):
                df = pd.read_csv(p_path)
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')
                return df
        except Exception:
            pass
        return None

    def calculate_technical_score(self, symbol):
        """
        Tính điểm kỹ thuật (0-10)
        - Xu hướng (Trend): MA50, MA200
        - Động lượng (Momentum): RSI
        """
        df = self.load_price_data(symbol)
        if df is None or len(df) < 50:
            return 0, "No Data"

        # Lấy mảng giá đóng cửa (dạng numpy array cho talib)
        closes = df['close'].values.astype(float)
        
        # 1. Tính chỉ báo
        rsi = talib.RSI(closes, timeperiod=14)[-1]
        ma50 = talib.SMA(closes, timeperiod=50)[-1]
        ma200 = talib.SMA(closes, timeperiod=200)[-1] if len(closes) > 200 else 0
        current_price = closes[-1]
        
        score = 0
        reasons = []

        # 2. Chấm điểm Xu hướng (Trend) - Trọng số cao
        if current_price > ma50:
            score += 3
            reasons.append("Price > MA50 (Uptrend ngắn hạn)")
        else:
            reasons.append("Price < MA50 (Yếu)")
            
        if ma200 > 0 and current_price > ma200:
            score += 2
            reasons.append("Price > MA200 (Uptrend dài hạn)")

        # 3. Chấm điểm Động lượng (RSI)
        if 40 <= rsi <= 60:
            score += 3
            reasons.append(f"RSI Neutral ({rsi:.1f}) - Vùng mua an toàn")
        elif 30 <= rsi < 40:
            score += 2
            reasons.append(f"RSI Oversold nhẹ ({rsi:.1f}) - Canh hồi phục")
        elif rsi < 30:
            score += 1
            reasons.append(f"RSI Quá bán ({rsi:.1f}) - Bắt đáy mạo hiểm")
        elif rsi > 70:
            score -= 1
            reasons.append(f"RSI Quá mua ({rsi:.1f}) - Cẩn trọng điều chỉnh")
            
        # 4. Volume (Đơn giản)
        # Lấy volume trung bình 20 phiên
        avg_vol = np.mean(df['volume'].values[-20:])
        cur_vol = df['volume'].values[-1]
        if cur_vol > avg_vol * 1.2:
            score += 2
            reasons.append("Volume đột biến (>120% TB)")

        # Normalize score (Max 10)
        final_score = min(10, max(0, score))
        return final_score, "; ".join(reasons)

    def calculate_fundamental_score(self, metrics_row):
        """
        Tính điểm cơ bản (0-10) dựa trên ROE và Tăng trưởng
        """
        score = 0
        reasons = []
        
        # 1. ROE (Hiệu quả sử dụng vốn)
        roe = metrics_row.get('ROE')
        if pd.notna(roe):
            if roe > 20: score += 4; reasons.append(f"ROE Rất cao ({roe}%)")
            elif roe > 15: score += 3; reasons.append(f"ROE Tốt ({roe}%)")
            elif roe > 10: score += 2; reasons.append(f"ROE Khá ({roe}%)")
            else: reasons.append(f"ROE Thấp ({roe}%)")
        
        # 2. Tăng trưởng Lợi nhuận (Growth)
        growth = metrics_row.get('Profit_Growth_YoY')
        if pd.notna(growth):
            if growth > 20: score += 4; reasons.append(f"Tăng trưởng mạnh ({growth}%)")
            elif growth > 10: score += 3; reasons.append(f"Tăng trưởng tốt ({growth}%)")
            elif growth > 0: score += 1; reasons.append("Tăng trưởng dương")
            elif growth < -20: score -= 2; reasons.append("Suy thoái nghiêm trọng")
            else: reasons.append("Tăng trưởng âm")
            
        final_score = min(10, max(0, score))
        return final_score, "; ".join(reasons)

    def run_analysis(self):
        print("🧠 [Analysis] Đang phân tích & chấm điểm cổ phiếu...")
        
        # 1. Load dữ liệu metrics từ Phase 2
        metrics_path = os.path.join(self.processed_dir, "financial_metrics.csv")
        if not os.path.exists(metrics_path):
            print("❌ Chưa có file financial_metrics.csv. Hãy chạy lệnh 'process' trước.")
            return

        df_metrics = pd.read_csv(metrics_path)
        results = []

        for index, row in df_metrics.iterrows():
            symbol = row['Symbol']
            # print(f"Analyzing {symbol}...", end=" ")
            
            # Tính điểm
            f_score, f_reason = self.calculate_fundamental_score(row)
            t_score, t_reason = self.calculate_technical_score(symbol)
            
            # Tổng hợp (Trọng số: 60% Cơ bản - 40% Kỹ thuật cho khẩu vị Trung hạn)
            total_score = round(f_score * 0.6 + t_score * 0.4, 2)
            
            # Khuyến nghị
            recommendation = "THEO DÕI"
            if total_score >= 7.5: recommendation = "MUA MẠNH"
            elif total_score >= 6.0: recommendation = "MUA THĂM DÒ"
            elif total_score <= 4.0: recommendation = "BÁN / CƠ CẤU"

            results.append({
                'Symbol': symbol,
                'Total_Score': total_score,
                'Recommendation': recommendation,
                'Fund_Score': f_score,
                'Tech_Score': t_score,
                'Fund_Reason': f_reason,
                'Tech_Reason': t_reason,
                'Price': row['Price']
            })
            # print(f"Score: {total_score} ({recommendation})")

        # Xuất báo cáo
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by='Total_Score', ascending=False)
        
        output_path = os.path.join(self.processed_dir, "analysis_report.csv")
        df_results.to_csv(output_path, index=False)
        
        print(f"✅ Đã lưu báo cáo phân tích vào: {output_path}")
        print("\n🏆 TOP CỔ PHIẾU TIỀM NĂNG:")
        print(df_results[['Symbol', 'Total_Score', 'Recommendation', 'Fund_Score', 'Tech_Score']].head(10).to_string())