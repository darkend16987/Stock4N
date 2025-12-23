import pandas as pd
import time
import os
import random
from datetime import datetime
import sys
import vnstock 

# Thêm đường dẫn src vào system path để import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class VNStockLoader:
    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir
        self.use_legacy = hasattr(vnstock, 'stock_historical_data')
        
        if not self.use_legacy:
            print("ℹ️ Phát hiện vnstock v3.x (OOP Mode)")
        else:
            print("ℹ️ Phát hiện vnstock v2.x (Legacy Mode)")

    def _get_file_path(self, symbol, data_type):
        return os.path.join(self.data_dir, f"{symbol}_{data_type}.csv")

    def _load_from_cache(self, file_path, max_age_days=1):
        if os.path.exists(file_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            age = (datetime.now() - file_time).days
            if age < max_age_days:
                return pd.read_csv(file_path)
        return None

    def _save_to_cache(self, df, file_path):
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False)

    def get_price_data(self, symbol):
        """
        Lấy dữ liệu giá với cơ chế Fallback đa nguồn: DNSE -> VCI -> TCBS
        """
        file_path = self._get_file_path(symbol, "price")
        # Price check mỗi ngày (max_age=0)
        cached = self._load_from_cache(file_path, max_age_days=0)
        if cached is not None: return cached

        if self.use_legacy:
            try:
                df = vnstock.stock_historical_data(symbol=symbol, start_date=config.START_DATE, end_date=config.TODAY, resolution='1D', type='stock')
                if df is not None and not df.empty:
                    self._save_to_cache(df, file_path)
                    return df
            except Exception as e:
                print(f"  ❌ Legacy fetch failed: {e}")
                return None
        else:
            from vnstock import Vnstock
            # Danh sách nguồn ưu tiên cho GIÁ
            sources = ['DNSE', 'VCI', 'TCBS']
            
            for source in sources:
                try:
                    # print(f"  Trying source: {source}...")
                    stock = Vnstock().stock(symbol=symbol, source=source)
                    df = stock.quote.history(start=config.START_DATE, end=config.TODAY, interval='1D')
                    
                    if df is not None and not df.empty:
                        # print(f"  ✅ Success with {source}")
                        self._save_to_cache(df, file_path)
                        return df
                except Exception as e:
                    time.sleep(1) # Nghỉ nhẹ trước khi thử nguồn khác
            
            print(f"  ❌ Failed to fetch price for {symbol} from all sources.")
            return None

    def get_financial_report(self, symbol, report_type='BalanceSheet'):
        file_path = self._get_file_path(symbol, f"fin_{report_type}")
        # BCTC check 30 ngày 1 lần
        cached = self._load_from_cache(file_path, max_age_days=30)
        if cached is not None: return cached

        try:
            df = None
            if self.use_legacy:
                df = vnstock.financial_report(symbol=symbol, report_type=report_type, frequency='Quarterly')
            else:
                from vnstock import Vnstock
                # Ưu tiên nguồn VCI vì TCBS chặn public API
                finance_sources = ['VCI', 'TCBS']
                
                for source in finance_sources:
                    try:
                        stock = Vnstock().stock(symbol=symbol, source=source)
                        
                        if report_type == 'BalanceSheet':
                            df = stock.finance.balance_sheet(period='quarter', lang='vi')
                        elif report_type == 'IncomeStatement':
                            df = stock.finance.income_statement(period='quarter', lang='vi')
                        elif report_type == 'CashFlow':
                            df = stock.finance.cash_flow(period='quarter', lang='vi')
                        
                        if df is not None and not df.empty:
                            self._save_to_cache(df, file_path)
                            return df
                    except Exception as e:
                        time.sleep(1)
                        continue
            
            if df is not None and not df.empty:
                self._save_to_cache(df, file_path)
                return df
        except Exception as e:
            # Xử lý riêng lỗi Rate Limit
            if "Rate limit" in str(e) or "429" in str(e):
                print(f"  ⛔ RATE LIMIT HIT for {symbol}. Cooling down for 60s...")
                time.sleep(60) 
            elif "404" in str(e) or "Not Found" in str(e):
                # Không in lỗi 404 để tránh rác log, chỉ ghi nhận thiếu data
                pass
            else:
                print(f"  [Error] FinReport {symbol} - {report_type}: {e}")
        return None

    def run_ingestion(self, symbols):
        # Đã loại bỏ TEST MODE limit. Chạy full danh sách đầu vào.
        print(f"🚀 [Docker] Bắt đầu tải dữ liệu cho {len(symbols)} mã vào: {self.data_dir}")
        print("ℹ️ Lưu ý: Quá trình này sẽ mất thời gian do áp dụng rate-limit để tránh bị chặn IP.")
        
        results = []
        for idx, symbol in enumerate(symbols):
            print(f"[{idx+1}/{len(symbols)}] Processing {symbol}...", end=" ", flush=True)
            
            # CHIẾN THUẬT: Random Sleep
            pre_sleep = random.uniform(1, 3) 
            time.sleep(pre_sleep)
            
            # 1. Lấy giá (Quan trọng nhất)
            price = self.get_price_data(symbol)
            
            # 2. Lấy BCTC (Nếu giá OK mới lấy tiếp để tiết kiệm request)
            bs = None
            inc = None
            if price is not None:
                # Nghỉ giữa các request tài chính
                time.sleep(random.uniform(1, 2))
                bs = self.get_financial_report(symbol, 'BalanceSheet')
                
                if bs is not None:
                    time.sleep(random.uniform(1, 2))
                    inc = self.get_financial_report(symbol, 'IncomeStatement')
            
            # Đánh giá trạng thái
            if price is None:
                status = "❌ NO PRICE"
            elif bs is None:
                status = "⚠️ PRICE ONLY" # Có giá nhưng thiếu BCTC -> Vẫn trade kỹ thuật được
            else:
                status = "✅ FULL DATA"

            print(status)
            
            results.append({'Symbol': symbol, 'Status': status})
            
        return pd.DataFrame(results)