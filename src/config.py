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

# --- DANH SÁCH CỔ PHIẾU (VN TOP 50 - Blue Chip & Mid-Cap Uy Tín) ---
# Danh sách dựa trên VN30 (30 mã) + VNMidCap top (20 mã) theo vốn hóa và thanh khoản
# Nguồn: HOSE VN30 Index (kỳ 1/2025) + Top vốn hóa thị trường 2025
VN100_SYMBOLS = [
    # === VN30 - Blue Chip Stocks (30 mã) ===
    # Ngân hàng (15 mã)
    'VCB', 'BID', 'CTG', 'TCB', 'MBB', 'VPB', 'ACB', 'HDB', 'STB', 'TPB',
    'VIB', 'SHB', 'SSB', 'LPB', 'EIB',
    # Bất động sản & Tập đoàn (5 mã)
    'VIC', 'VHM', 'VRE', 'BCM', 'VGI',
    # Năng lượng & Công nghiệp (4 mã)
    'GAS', 'PLX', 'HPG', 'GVR',
    # Hàng tiêu dùng & Bán lẻ (4 mã)
    'VNM', 'MSN', 'MWG', 'SAB',
    # Chứng khoán & Tài chính (1 mã)
    'SSI',
    # Công nghệ (1 mã)
    'FPT',

    # === VN MidCap & Large Cap - Top 20 mã bổ sung ===
    # Bất động sản & Xây dựng (6 mã)
    'KDH', 'DXG', 'NVL', 'PDR', 'DIG', 'BCG',
    # Năng lượng & Công nghiệp (5 mã)
    'POW', 'REE', 'DGW', 'NT2', 'BSR',
    # Hàng tiêu dùng & Dịch vụ (4 mã)
    'PNJ', 'FRT', 'VHC', 'DGC',
    # Hàng không & Logistics (2 mã)
    'VJC', 'HVN',
    # Nông nghiệp & Thủy sản (2 mã)
    'VND', 'HNG',
    # Công nghệ & Viễn thông (1 mã)
    'VGC'
]

# --- CẤU HÌNH THỜI GIAN ---
TODAY = datetime.now().strftime('%Y-%m-%d')
START_DATE = "2023-01-01"

# --- CẤU HÌNH DATA INGESTION ---
# Cache expiry (days)
CACHE_EXPIRY = {
    'price': 0,        # Daily update for price data
    'financial': 30,   # Monthly update for financial reports
    'profile': 90      # Quarterly update for company profile
}

# API retry configuration
API_RETRY = {
    'max_attempts': 3,
    'initial_wait': 2,       # seconds
    'max_wait': 10,          # seconds
    'exponential_base': 2    # wait time = initial_wait * (base ** attempt)
}

# Rate limiting
RATE_LIMIT = {
    'request_delay_min': 1,  # Min seconds between requests
    'request_delay_max': 3,  # Max seconds between requests
    'cooldown_on_limit': 60  # Cooldown seconds when rate limited
}

# Data sources priority
DATA_SOURCES = {
    'price': ['VCI', 'TCBS', 'MSN'],       # Priority order for price data (vnstock v3.x compatible)
    'financial': ['VCI', 'TCBS']            # Priority order for financial data
}

# Parallel data fetching (Priority 3 improvement)
PARALLEL_FETCHING = {
    'enabled': True,           # Enable parallel fetching by default
    'max_workers': 3,          # Max 3 concurrent workers (to avoid rate limiting)
    'timeout': 60              # Timeout per symbol (seconds)
}

# --- CẤU HÌNH SCORING ---
# Weight distribution between fundamental and technical analysis
SCORING_WEIGHTS = {
    'fundamental': 0.6,  # 60% weight for fundamental analysis
    'technical': 0.4     # 40% weight for technical analysis
}

# Fundamental scoring thresholds
FUNDAMENTAL_THRESHOLDS = {
    'roe': {
        'excellent': 20,    # ROE > 20%: +4 points
        'good': 15,         # ROE > 15%: +3 points
        'fair': 10          # ROE > 10%: +2 points
    },
    'profit_growth': {
        'strong': 20,       # Growth > 20%: +4 points
        'good': 10,         # Growth > 10%: +3 points
        'weak': -20         # Growth < -20%: -2 points
    },
    'revenue_growth': {
        'strong': 15,       # Growth > 15%: +3 points
        'good': 5           # Growth > 5%: +1 point
    }
}

# Technical scoring thresholds
TECHNICAL_THRESHOLDS = {
    'rsi': {
        'overbought': 70,      # RSI > 70: Overbought (caution)
        'neutral_high': 60,    # 40-60: Neutral zone (safe)
        'neutral_low': 40,
        'oversold': 30         # RSI < 30: Oversold (risky buy)
    },
    'volume_surge': 1.2,       # Volume > 120% of average
    'ma_periods': {
        'short': 50,           # Short-term moving average
        'long': 200            # Long-term moving average
    }
}

# Score to recommendation mapping
RECOMMENDATION_THRESHOLDS = {
    'strong_buy': 7.5,      # Score >= 7.5: MUA MẠNH
    'buy': 6.0,             # Score >= 6.0: MUA THĂM DÒ
    'sell': 4.0             # Score <= 4.0: BÁN / CƠ CẤU
}

# --- CẤU HÌNH PORTFOLIO ---
# Position sizing
PORTFOLIO_CONFIG = {
    'max_position_pct': 0.40,     # Max 40% per position (diversification)
    'min_position_pct': 0.05,     # Min 5% per position (meaningful size)
    'max_positions': 10,          # Max number of positions
    'cash_reserve_pct': 0.20      # Keep 20% cash reserve
}

# Risk management
RISK_MANAGEMENT = {
    'stop_loss_pct': 0.07,        # -7% stop loss
    'target_profit_pct': 0.15,    # +15% target profit
    'risk_reward_ratio': 2.0,     # 1:2 risk/reward
    'max_drawdown_pct': 0.15      # Max 15% portfolio drawdown
}

# Price unit detection
PRICE_UNIT_CONFIG = {
    'threshold': 100,             # If price < 100, assume it's in thousands VND
    'multiplier': 1000            # Multiply by 1000 to get actual price
}

# --- CẤU HÌNH DATA VALIDATION ---
DATA_QUALITY = {
    'min_price_rows': 30,         # Minimum 30 days of price data
    'min_financial_quarters': 4,   # Minimum 4 quarters of financial data
    'max_null_ratio': 0.1,        # Max 10% null values allowed
    'quality_threshold': 0.7       # Minimum data quality score (0-1)
}

# --- CẤU HÌNH LOGGING ---
LOGGING_CONFIG = {
    'log_dir': os.path.join(BASE_DIR, 'logs'),
    'days_to_keep': 7,            # Keep logs for 7 days
    'level': 'INFO'               # Default log level
}

# --- CẤU HÌNH EXPORT ---
EXPORT_CONFIG = {
    'chart_history_limit': 100,   # Only export last 100 days for charts
    'export_dir': os.path.join(DATA_DIR, 'export')
}

# Create export directory
os.makedirs(EXPORT_CONFIG['export_dir'], exist_ok=True)
os.makedirs(LOGGING_CONFIG['log_dir'], exist_ok=True)