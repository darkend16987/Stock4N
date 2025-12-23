import pandas as pd
import numpy as np
import os
import sys
import talib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.validator import DataValidator

logger = get_logger(__name__)


class StockScorer:
    """
    Module chấm điểm cổ phiếu dựa trên kết hợp Cơ bản & Kỹ thuật.
    """

    def __init__(self, data_dir=config.RAW_DIR, processed_dir=config.PROCESSED_DIR):
        self.data_dir = data_dir
        self.processed_dir = processed_dir
        self.validator = DataValidator()

        # Load thresholds from config
        self.fund_thresholds = config.FUNDAMENTAL_THRESHOLDS
        self.tech_thresholds = config.TECHNICAL_THRESHOLDS
        self.scoring_weights = config.SCORING_WEIGHTS
        self.rec_thresholds = config.RECOMMENDATION_THRESHOLDS

        logger.info(f"StockScorer initialized with weights: F={self.scoring_weights['fundamental']}, T={self.scoring_weights['technical']}")

    def load_price_data(self, symbol):
        """Đọc dữ liệu giá để phân tích kỹ thuật"""
        try:
            p_path = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if os.path.exists(p_path):
                df = pd.read_csv(p_path)
                df['time'] = pd.to_datetime(df['time'])
                df = df.sort_values('time')
                return df
        except Exception as e:
            logger.error(f"Error loading price data for {symbol}: {e}")
        return None

    def calculate_technical_score(self, symbol):
        """
        Tính điểm kỹ thuật (0-10)
        - Xu hướng (Trend): MA50, MA200
        - Động lượng (Momentum): RSI
        - Volume analysis
        """
        df = self.load_price_data(symbol)
        if df is None or len(df) < 50:
            logger.warning(f"Insufficient price data for technical analysis: {symbol}")
            return 0, "No Data"

        try:
            # Lấy mảng giá đóng cửa
            closes = df['close'].values.astype(float)

            # 1. Tính chỉ báo
            ma_short_period = self.tech_thresholds['ma_periods']['short']
            ma_long_period = self.tech_thresholds['ma_periods']['long']

            rsi = talib.RSI(closes, timeperiod=14)[-1]
            ma_short = talib.SMA(closes, timeperiod=ma_short_period)[-1]
            ma_long = talib.SMA(closes, timeperiod=ma_long_period)[-1] if len(closes) > ma_long_period else 0
            current_price = closes[-1]

            score = 0
            reasons = []

            # 2. Chấm điểm Xu hướng (Trend)
            if current_price > ma_short:
                score += 3
                reasons.append(f"Price > MA{ma_short_period} (Uptrend ngắn hạn)")
            else:
                reasons.append(f"Price < MA{ma_short_period} (Yếu)")

            if ma_long > 0 and current_price > ma_long:
                score += 2
                reasons.append(f"Price > MA{ma_long_period} (Uptrend dài hạn)")

            # 3. Chấm điểm RSI
            rsi_levels = self.tech_thresholds['rsi']
            if rsi_levels['neutral_low'] <= rsi <= rsi_levels['neutral_high']:
                score += 3
                reasons.append(f"RSI Neutral ({rsi:.1f}) - Vùng mua an toàn")
            elif rsi_levels['oversold'] <= rsi < rsi_levels['neutral_low']:
                score += 2
                reasons.append(f"RSI Oversold nhẹ ({rsi:.1f}) - Canh hồi phục")
            elif rsi < rsi_levels['oversold']:
                score += 1
                reasons.append(f"RSI Quá bán ({rsi:.1f}) - Bắt đáy mạo hiểm")
            elif rsi > rsi_levels['overbought']:
                score -= 1
                reasons.append(f"RSI Quá mua ({rsi:.1f}) - Cẩn trọng điều chỉnh")

            # 4. Volume analysis
            avg_vol = np.mean(df['volume'].values[-20:])
            cur_vol = df['volume'].values[-1]
            volume_threshold = self.tech_thresholds['volume_surge']

            if cur_vol > avg_vol * volume_threshold:
                score += 2
                reasons.append(f"Volume đột biến (>{volume_threshold*100:.0f}% TB)")

            # Normalize score
            final_score = min(10, max(0, score))
            logger.debug(f"{symbol} Technical Score: {final_score}/10 - {'; '.join(reasons)}")

            return final_score, "; ".join(reasons)

        except Exception as e:
            logger.error(f"Error calculating technical score for {symbol}: {e}")
            return 0, f"Error: {str(e)}"

    def calculate_fundamental_score(self, metrics_row):
        """
        Tính điểm cơ bản (0-10) dựa trên ROE và Tăng trưởng
        """
        symbol = metrics_row.get('Symbol', 'Unknown')
        score = 0
        reasons = []

        try:
            # 1. ROE (Hiệu quả sử dụng vốn)
            roe = metrics_row.get('ROE')
            roe_thresholds = self.fund_thresholds['roe']

            if pd.notna(roe):
                if roe > roe_thresholds['excellent']:
                    score += 4
                    reasons.append(f"ROE Rất cao ({roe}%)")
                elif roe > roe_thresholds['good']:
                    score += 3
                    reasons.append(f"ROE Tốt ({roe}%)")
                elif roe > roe_thresholds['fair']:
                    score += 2
                    reasons.append(f"ROE Khá ({roe}%)")
                else:
                    reasons.append(f"ROE Thấp ({roe}%)")

            # 2. Tăng trưởng Lợi nhuận
            growth = metrics_row.get('Profit_Growth_YoY')
            growth_thresholds = self.fund_thresholds['profit_growth']

            if pd.notna(growth):
                if growth > growth_thresholds['strong']:
                    score += 4
                    reasons.append(f"Tăng trưởng mạnh ({growth}%)")
                elif growth > growth_thresholds['good']:
                    score += 3
                    reasons.append(f"Tăng trưởng tốt ({growth}%)")
                elif growth > 0:
                    score += 1
                    reasons.append("Tăng trưởng dương")
                elif growth < growth_thresholds['weak']:
                    score -= 2
                    reasons.append(f"Suy thoái nghiêm trọng ({growth}%)")
                else:
                    reasons.append(f"Tăng trưởng âm ({growth}%)")

            final_score = min(10, max(0, score))
            logger.debug(f"{symbol} Fundamental Score: {final_score}/10 - {'; '.join(reasons)}")

            return final_score, "; ".join(reasons)

        except Exception as e:
            logger.error(f"Error calculating fundamental score for {symbol}: {e}")
            return 0, f"Error: {str(e)}"

    def run_analysis(self):
        """Run full analysis and generate scored recommendations"""
        logger.info("Starting stock analysis and scoring...")

        # 1. Load metrics từ Phase 2
        metrics_path = os.path.join(self.processed_dir, "financial_metrics.csv")
        if not os.path.exists(metrics_path):
            logger.error(f"Metrics file not found: {metrics_path}. Run 'process' command first.")
            return

        df_metrics = pd.read_csv(metrics_path)
        logger.info(f"Loaded {len(df_metrics)} symbols for analysis")

        results = []
        for index, row in df_metrics.iterrows():
            symbol = row['Symbol']
            logger.info(f"[{index+1}/{len(df_metrics)}] Analyzing {symbol}...")

            # Tính điểm
            f_score, f_reason = self.calculate_fundamental_score(row)
            t_score, t_reason = self.calculate_technical_score(symbol)

            # Tổng hợp với trọng số từ config
            total_score = round(
                f_score * self.scoring_weights['fundamental'] +
                t_score * self.scoring_weights['technical'],
                2
            )

            # Khuyến nghị từ config
            if total_score >= self.rec_thresholds['strong_buy']:
                recommendation = "MUA MẠNH"
            elif total_score >= self.rec_thresholds['buy']:
                recommendation = "MUA THĂM DÒ"
            elif total_score <= self.rec_thresholds['sell']:
                recommendation = "BÁN / CƠ CẤU"
            else:
                recommendation = "THEO DÕI"

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

            logger.info(f"✓ {symbol}: Score={total_score} → {recommendation}")

        # Xuất báo cáo
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by='Total_Score', ascending=False)

        # Validate report
        is_valid, message = self.validator.validate_analysis_report(df_results)
        if not is_valid:
            logger.error(f"Analysis report validation failed: {message}")
            return

        output_path = os.path.join(self.processed_dir, "analysis_report.csv")
        df_results.to_csv(output_path, index=False)

        logger.info("=" * 60)
        logger.info("ANALYSIS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total analyzed: {len(df_results)} symbols")
        logger.info(f"MUA MẠNH: {len(df_results[df_results['Recommendation'] == 'MUA MẠNH'])}")
        logger.info(f"MUA THĂM DÒ: {len(df_results[df_results['Recommendation'] == 'MUA THĂM DÒ'])}")
        logger.info(f"THEO DÕI: {len(df_results[df_results['Recommendation'] == 'THEO DÕI'])}")
        logger.info(f"BÁN / CƠ CẤU: {len(df_results[df_results['Recommendation'] == 'BÁN / CƠ CẤU'])}")
        logger.info(f"Output saved to: {output_path}")
        logger.info("=" * 60)

        logger.info("\nTOP 10 CỔ PHIẾU TIỀM NĂNG:")
        display_cols = ['Symbol', 'Total_Score', 'Recommendation', 'Fund_Score', 'Tech_Score']
        print(df_results[display_cols].head(10).to_string())

        return df_results
