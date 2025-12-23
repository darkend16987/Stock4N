import pandas as pd
import numpy as np
import os
import sys

# Hack để import config từ thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.exceptions import InsufficientDataException, MissingColumnException
from modules.utils.validator import DataValidator

logger = get_logger(__name__)


class FinancialCalculator:
    """
    Module tính toán các chỉ số tài chính từ dữ liệu thô.
    Mục tiêu: Tạo ra một bản tóm tắt sức khỏe (Health Check) cho từng mã.
    """

    def __init__(self, data_dir=config.RAW_DIR, output_dir=config.PROCESSED_DIR):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.validator = DataValidator()

        # Mapping các tên cột từ file CSV (Do vnstock trả về tiếng Việt/Anh lộn xộn)
        self.col_map = {
            'profit': ['Lợi nhuận sau thuế của Cổ đông công ty mẹ (đồng)', 'Lợi nhuận sau thuế (đồng)', 'post_tax_profit', 'net_income'],
            'revenue': ['Doanh thu thuần (đồng)', 'net_revenue', 'revenue'],
            'equity': ['VỐN CHỦ SỞ HỮU (đồng)', 'owners_equity', 'equity', 'vốn chủ sở hữu'],
            'assets': ['TỔNG CỘNG TÀI SẢN (đồng)', 'total_assets', 'assets'],
            'year': ['Năm', 'year', 'Year'],
            'quarter': ['Kỳ', 'quarter', 'Quarter', 'Quý']
        }

    def _find_col(self, df, keywords):
        """Tìm tên cột chính xác trong DataFrame dựa trên từ khóa"""
        for col in df.columns:
            for kw in keywords:
                if kw.lower() in col.lower():
                    return col
        return None

    def _get_quarter_value_safely(self, df, year_col, quarter_col, target_year, target_quarter, value_col):
        """
        Lấy giá trị của một quý cụ thể một cách an toàn

        Args:
            df: DataFrame chứa dữ liệu tài chính
            year_col: Tên cột năm
            quarter_col: Tên cột quý
            target_year: Năm cần tìm
            target_quarter: Quý cần tìm
            value_col: Cột giá trị cần lấy

        Returns:
            Giá trị hoặc None nếu không tìm thấy
        """
        try:
            matching_rows = df[
                (df[year_col] == target_year) &
                (df[quarter_col] == target_quarter)
            ]

            if not matching_rows.empty:
                value = matching_rows.iloc[0][value_col]
                return value if pd.notna(value) else None

        except Exception as e:
            logger.debug(f"Error getting quarter value: {e}")

        return None

    def _calculate_yoy_growth(self, df, year_col, quarter_col, value_col):
        """
        Tính tăng trưởng YoY (Year over Year) một cách chính xác

        So sánh quý hiện tại với cùng quý năm trước

        Returns:
            float: Growth percentage hoặc None
        """
        try:
            if df.empty or len(df) < 2:
                return None

            # Sort để đảm bảo thứ tự
            df_sorted = df.sort_values(by=[year_col, quarter_col], ascending=True)

            # Lấy quý gần nhất
            latest_row = df_sorted.iloc[-1]
            current_year = latest_row[year_col]
            current_quarter = latest_row[quarter_col]
            current_value = latest_row[value_col]

            if pd.isna(current_value) or current_value == 0:
                return None

            # Tìm cùng quý năm trước
            prev_year = current_year - 1
            prev_value = self._get_quarter_value_safely(
                df_sorted, year_col, quarter_col,
                prev_year, current_quarter, value_col
            )

            if prev_value is None or prev_value == 0:
                logger.debug(f"Cannot calculate YoY growth: missing Q{current_quarter}/{prev_year} data")
                return None

            # Tính growth
            growth = ((current_value - prev_value) / abs(prev_value)) * 100

            logger.debug(f"YoY Growth: Q{current_quarter}/{current_year} vs Q{current_quarter}/{prev_year} = {growth:.2f}%")

            return round(growth, 2)

        except Exception as e:
            logger.warning(f"Error calculating YoY growth: {e}")
            return None

    def load_data(self, symbol):
        """Đọc dữ liệu thô từ CSV"""
        data = {}
        try:
            # Load Price
            p_path = os.path.join(self.data_dir, f"{symbol}_price.csv")
            if os.path.exists(p_path):
                data['price'] = pd.read_csv(p_path)
                logger.debug(f"Loaded price data for {symbol}: {len(data['price'])} rows")

            # Load Financials
            for r_type in ['BalanceSheet', 'IncomeStatement']:
                f_path = os.path.join(self.data_dir, f"{symbol}_fin_{r_type}.csv")
                if os.path.exists(f_path):
                    data[r_type] = pd.read_csv(f_path)
                    logger.debug(f"Loaded {r_type} for {symbol}: {len(data[r_type])} rows")

        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")

        return data

    def calculate_metrics(self, symbol):
        """Tính toán các chỉ số cơ bản"""
        data = self.load_data(symbol)

        # 1. Kiểm tra dữ liệu tối thiểu
        if 'price' not in data or 'IncomeStatement' not in data:
            logger.warning(f"Insufficient data for {symbol}: missing price or income statement")
            return None

        try:
            # Lấy giá đóng cửa mới nhất
            if data['price'].empty:
                logger.warning(f"Empty price data for {symbol}")
                return None

            # Đảm bảo sort theo thời gian
            data['price']['time'] = pd.to_datetime(data['price']['time'])
            data['price'] = data['price'].sort_values('time')
            latest_price = data['price'].iloc[-1]['close']

            # Xử lý Báo cáo KQKD (Income Statement)
            inc_df = data['IncomeStatement'].copy()

            # Find column names
            year_col = self._find_col(inc_df, self.col_map['year'])
            quarter_col = self._find_col(inc_df, self.col_map['quarter'])
            profit_col = self._find_col(inc_df, self.col_map['profit'])
            rev_col = self._find_col(inc_df, self.col_map['revenue'])

            if not year_col or not quarter_col:
                logger.warning(f"Missing year/quarter columns for {symbol}")
                return None

            # Sort: Năm tăng dần, Kỳ (Quý) tăng dần
            inc_df = inc_df.sort_values(by=[year_col, quarter_col], ascending=True)

            # Xử lý Bảng CĐKT (Balance Sheet) - Để lấy Vốn chủ sở hữu
            bs_df = data.get('BalanceSheet')
            equity_col = None
            if bs_df is not None and not bs_df.empty:
                bs_df = bs_df.copy()
                bs_year_col = self._find_col(bs_df, self.col_map['year'])
                bs_quarter_col = self._find_col(bs_df, self.col_map['quarter'])

                if bs_year_col and bs_quarter_col:
                    bs_df = bs_df.sort_values(by=[bs_year_col, bs_quarter_col], ascending=True)

                equity_col = self._find_col(bs_df, self.col_map['equity'])

            # --- BẮT ĐẦU TÍNH TOÁN ---
            metrics = {
                'Symbol': symbol,
                'Price': latest_price,
                'PE': None,
                'PB': None,
                'ROE': None,
                'Revenue_Growth_YoY': None,
                'Profit_Growth_YoY': None,
                'Net_Profit_TTM': None
            }

            # 1. Tính EPS & P/E (Dùng TTM - Trailing 12 Months)
            if profit_col:
                # Lấy 4 quý gần nhất
                last_4_quarters = inc_df.tail(4)
                if len(last_4_quarters) == 4:
                    # Filter out null values
                    valid_profits = last_4_quarters[profit_col].dropna()
                    if len(valid_profits) >= 3:  # Accept if at least 3 quarters have data
                        net_profit_ttm = valid_profits.sum()
                        metrics['Net_Profit_TTM'] = net_profit_ttm
                        logger.debug(f"{symbol} TTM Profit: {net_profit_ttm:,.0f}")
                    else:
                        logger.debug(f"{symbol}: Insufficient TTM data (only {len(valid_profits)} valid quarters)")

                # Tính Tăng trưởng Lợi nhuận YoY (cải tiến)
                if len(inc_df) >= 5:  # Need at least 5 quarters to compare
                    profit_growth = self._calculate_yoy_growth(
                        inc_df, year_col, quarter_col, profit_col
                    )
                    if profit_growth is not None:
                        metrics['Profit_Growth_YoY'] = profit_growth

            # 2. Tính P/B & ROE
            if equity_col and bs_df is not None and not bs_df.empty:
                latest_equity = bs_df.iloc[-1][equity_col]

                # ROE = Profit TTM / Equity
                if metrics['Net_Profit_TTM'] and pd.notna(latest_equity) and latest_equity > 0:
                    metrics['ROE'] = round((metrics['Net_Profit_TTM'] / latest_equity) * 100, 2)
                    logger.debug(f"{symbol} ROE: {metrics['ROE']}%")

            # 3. Tính Tăng trưởng Doanh thu YoY (cải tiến)
            if rev_col and len(inc_df) >= 5:
                revenue_growth = self._calculate_yoy_growth(
                    inc_df, year_col, quarter_col, rev_col
                )
                if revenue_growth is not None:
                    metrics['Revenue_Growth_YoY'] = revenue_growth

            # Validate metrics before returning
            is_valid, message = self.validator.validate_metrics(metrics, symbol)
            if not is_valid:
                logger.warning(f"Metrics validation failed for {symbol}: {message}")
                return None

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics for {symbol}: {e}", exc_info=True)
            return None

    def run_processing(self, symbols):
        """Process all symbols and generate metrics report"""
        logger.info(f"Starting processing for {len(symbols)} symbols...")

        results = []
        success_count = 0
        failed_count = 0

        for idx, symbol in enumerate(symbols):
            logger.info(f"[{idx+1}/{len(symbols)}] Processing {symbol}...")

            metrics = self.calculate_metrics(symbol)
            if metrics:
                results.append(metrics)
                success_count += 1
                logger.info(f"✓ {symbol}: Metrics calculated successfully")
            else:
                failed_count += 1
                logger.warning(f"⏩ {symbol}: Skipped (insufficient data or errors)")

        # Lưu kết quả tổng hợp
        if results:
            df_result = pd.DataFrame(results)
            output_path = os.path.join(self.output_dir, "financial_metrics.csv")
            df_result.to_csv(output_path, index=False)

            logger.info("=" * 60)
            logger.info("PROCESSING SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total: {len(symbols)} symbols")
            logger.info(f"Success: {success_count} ({success_count/len(symbols)*100:.1f}%)")
            logger.info(f"Failed: {failed_count} ({failed_count/len(symbols)*100:.1f}%)")
            logger.info(f"Output saved to: {output_path}")
            logger.info("=" * 60)

            # Hiển thị preview
            logger.info("\nPREVIEW - Top 10 Results:")
            preview_cols = ['Symbol', 'Price', 'ROE', 'Revenue_Growth_YoY', 'Profit_Growth_YoY']
            print(df_result[preview_cols].head(10).to_string())

            return df_result

        else:
            logger.error("No results to save. All symbols failed processing.")
            return pd.DataFrame()
