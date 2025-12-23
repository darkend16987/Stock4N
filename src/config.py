import os
from datetime import datetime

# --- CẤU HÌNH ĐƯỜNG DẪN ---
# Vì code chạy trong Docker tại /app/src, nên data sẽ nằm ở /app/data
# os.path.dirname lấy thư mục chứa file config.py (là /app/src)
# os.path.dirname(...) lần nữa để ra root (/app)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Tạo thư mục nếu chưa tồn tại
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# --- DANH SÁCH CỔ PHIẾU (VN100 MẪU) ---
VN100_SYMBOLS = [
    'VCB', 'HPG', 'VHM', 'MWG', 'FPT', 'TCB', 'VPB', 'MBB', 'ACB', 'MSN',
    'VIC', 'VRE', 'VNM', 'GAS', 'SAB', 'GVR', 'BID', 'CTG', 'SSI', 'VND',
    'DGW', 'FRT', 'PNJ', 'REE', 'VHC', 'NVL', 'PDR', 'DIG', 'DXG', 'KDH'
]

# --- CẤU HÌNH THỜI GIAN ---
TODAY = datetime.now().strftime('%Y-%m-%d')
START_DATE = "2023-01-01"