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

# --- DANH SÁCH CỔ PHIẾU (VN100 - Top 100 theo vốn hóa & thanh khoản) ---
# Danh sách dựa trên VN100 Index (HOSE) - cập nhật Q1/2026
# Nguồn: VN30 (30 mã) + VNMidCap (70 mã) theo FTSE Russell classification
# Ưu tiên: Blue chips > Large cap > Mid cap theo thanh khoản
VN100_SYMBOLS = [
    # ════════════════════════════════════════════════════════════════
    # VN30 - Blue Chip Stocks (30 mã) - Top tier
    # ════════════════════════════════════════════════════════════════

    # Ngân hàng (15 mã) - Banking sector dominance
    'VCB', 'BID', 'CTG', 'TCB', 'MBB', 'VPB', 'ACB', 'HDB', 'STB', 'TPB',
    'VIB', 'SHB', 'SSB', 'LPB', 'EIB',

    # Bất động sản & Tập đoàn (5 mã) - Real estate & conglomerates
    'VIC', 'VHM', 'VRE', 'BCM', 'VGI',

    # Năng lượng & Công nghiệp (4 mã) - Energy & industrials
    'GAS', 'PLX', 'HPG', 'GVR',

    # Hàng tiêu dùng & Bán lẻ (4 mã) - Consumer & retail
    'VNM', 'MSN', 'MWG', 'SAB',

    # Chứng khoán & Tài chính (1 mã) - Securities
    'SSI',

    # Công nghệ (1 mã) - Technology
    'FPT',

    # ════════════════════════════════════════════════════════════════
    # VN MidCap & Large Cap - 70 mã bổ sung
    # ════════════════════════════════════════════════════════════════

    # Bất động sản & Xây dựng (15 mã) - Real estate & construction
    'KDH', 'DXG', 'NVL', 'PDR', 'DIG', 'BCG', 'HDG', 'CEO', 'SZC', 'NLG',
    'IDC', 'KBC', 'IJC', 'HDC', 'CII',

    # Ngân hàng & Tài chính bổ sung (10 mã) - Additional banking & finance
    'BVH', 'VCI', 'HCM', 'AGR', 'BSI', 'FTS', 'MBS', 'VDS', 'ORS', 'CTS',

    # Năng lượng & Điện lực (8 mã) - Energy & power
    'POW', 'NT2', 'REE', 'DGW', 'BSR', 'PVD', 'PVS', 'PVT',

    # Công nghiệp & Vật liệu (10 mã) - Industrials & materials
    'DCM', 'DPM', 'DGC', 'BMP', 'CSV', 'DHC', 'NKG', 'PHR', 'AAA', 'GMD',

    # Hàng tiêu dùng & Dịch vụ (8 mã) - Consumer & services
    'PNJ', 'FRT', 'VHC', 'VCF', 'ASM', 'MSH', 'PHC', 'TLG',

    # Hàng không, Logistics & Vận tải (5 mã) - Aviation, logistics & transport
    'VJC', 'HVN', 'GMD', 'VSC', 'TCL',

    # Nông nghiệp & Thủy sản (6 mã) - Agriculture & seafood
    'VND', 'HNG', 'HAG', 'ANV', 'BAF', 'VHG',

    # Công nghệ & Viễn thông (5 mã) - Tech & telecom
    'VGC', 'CMG', 'VGI', 'ITD', 'ELC',

    # Y tế & Dược phẩm (3 mã) - Healthcare & pharma
    'DHG', 'DMC', 'IMP'
]

# Một số mã xuất hiện ở 2 nhóm (GMD, VGI) → loại trùng, giữ nguyên thứ tự
# (trùng làm ra dòng lặp trong báo cáo và mua 2 lần cùng 1 mã)
VN100_SYMBOLS = list(dict.fromkeys(VN100_SYMBOLS))

# --- PHÂN NGÀNH (phục vụ trần ngành, bỏ qua D/E cho nhóm tài chính) ---
# LƯU Ý: phân loại thô, cần rà soát thủ công. Mã không có trong map → 'Khác'.
_SECTOR_GROUPS = {
    'Ngân hàng': ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'VPB', 'ACB', 'HDB', 'STB', 'TPB',
                  'VIB', 'SHB', 'SSB', 'LPB', 'EIB'],
    'Chứng khoán': ['SSI', 'VCI', 'HCM', 'AGR', 'BSI', 'FTS', 'MBS', 'VDS', 'ORS', 'CTS', 'VND'],
    'Bảo hiểm': ['BVH'],
    'Bất động sản': ['VIC', 'VHM', 'VRE', 'BCM', 'KDH', 'DXG', 'NVL', 'PDR', 'DIG', 'NLG',
                     'HDC', 'CEO', 'IDC', 'KBC', 'SZC', 'IJC'],
    'Xây dựng & Hạ tầng': ['BCG', 'CII', 'PHC'],
    'Năng lượng & Điện': ['POW', 'NT2', 'REE', 'HDG'],
    'Dầu khí': ['GAS', 'PLX', 'BSR', 'PVD', 'PVS'],
    'Vật liệu & Công nghiệp': ['HPG', 'GVR', 'DCM', 'DPM', 'DGC', 'BMP', 'CSV', 'DHC', 'NKG',
                               'PHR', 'AAA', 'VGC'],
    'Tiêu dùng & Bán lẻ': ['VNM', 'MSN', 'MWG', 'SAB', 'PNJ', 'FRT', 'VCF', 'MSH', 'TLG', 'DGW'],
    'Vận tải & Logistics': ['VJC', 'HVN', 'GMD', 'VSC', 'TCL', 'PVT'],
    'Nông nghiệp & Thủy sản': ['VHC', 'ASM', 'HNG', 'HAG', 'ANV', 'BAF', 'VHG'],
    'Công nghệ & Viễn thông': ['FPT', 'CMG', 'VGI', 'ITD', 'ELC'],
    'Y tế & Dược': ['DHG', 'DMC', 'IMP'],
}
SECTOR_MAP = {sym: sector for sector, syms in _SECTOR_GROUPS.items() for sym in syms}
# Nhóm tài chính: đòn bẩy cao là đặc thù ngành → không áp trần Nợ/Vốn
FINANCIAL_SECTORS = {'Ngân hàng', 'Chứng khoán', 'Bảo hiểm'}

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

# Rate limiting (optimized for vnstock 3.4.0)
# API Limits:
#   - Guest mode: 20 requests/min
#   - Free API key: 60 requests/min
#   - Silver tier: 300 requests/min ← current plan
#   - Sponsor: 180-300 requests/min
# Strategy: Faster delays for Silver tier, RateLimiter handles throttling
RATE_LIMIT = {
    'request_delay_min': 0.15,  # Min seconds between requests (Silver: 300 req/min = 5 req/s)
    'request_delay_max': 0.5,   # Max seconds between requests
    'cooldown_on_limit': 30     # Cooldown seconds when rate limited
}
# Expected performance (100 stocks, 3 API calls each):
#   - Total requests: ~300
#   - With Silver 300 req/min: ~1-2 minutes
#   - With Free 60 req/min: ~5-6 minutes

# Data sources priority
# VNSTOCK 3.4.0: KBS là nguồn mới nhất, ưu tiên #1
# KBS có dữ liệu tương đương VCI, chuẩn hoá tốt hơn
DATA_SOURCES = {
    'price': ['KBS', 'VCI', 'TCBS', 'MSN'],       # Priority: KBS first (vnstock 3.4.0+)
    'financial': ['KBS', 'VCI', 'TCBS']           # KBS supports 8 quarters with free API key
}

# Vnstock API Configuration (v3.4.0+)
# Silver tier: 300 req/min, 8 quarters financial data
VNSTOCK_CONFIG = {
    'api_key': os.environ.get('VNSTOCK_API_KEY'),  # Set in .env
    'auto_register': True,                          # Auto-register API key on startup
    'rate_limit_buffer': 2,                         # Buffer seconds between requests
}

# Parallel data fetching (optimized for Silver tier - 300 req/min)
# Strategy: More workers, shorter delays → 5 req/sec target
# Math: 8 workers × avg 0.3s delay = ~4-5 req/sec = ~270 req/min (safe buffer)
PARALLEL_FETCHING = {
    'enabled': True,           # Enable parallel fetching by default
    'max_workers': 8,          # 8 concurrent workers (Silver: 300 req/min)
    'timeout': 60              # Timeout per symbol
}

# --- CẤU HÌNH SCORING ---
# Weight distribution between fundamental and technical analysis
# Profile: NHÀ ĐẦU TƯ TRUNG HẠN, ƯA THÍCH AN TOÀN
#   → Ưu tiên cơ bản 65% (chất lượng doanh nghiệp, lợi nhuận bền vững)
#   → Kỹ thuật 35% (timing, momentum hỗ trợ ra quyết định)
SCORING_WEIGHTS = {
    'fundamental': 0.65,  # 65% weight — ưu tiên nền tảng vững chắc
    'technical': 0.35     # 35% weight — hỗ trợ timing entry/exit
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
# Nâng ngưỡng mua lên 6.5 → chỉ mua mã thực sự chất lượng
RECOMMENDATION_THRESHOLDS = {
    'strong_buy': 7.5,      # Score >= 7.5: MUA MẠNH (cơ bản + kỹ thuật đều tốt)
    'buy': 6.5,             # Score >= 6.5: MUA THĂM DÒ (nâng từ 6.0 → an toàn hơn)
    'sell': 4.5             # Score <= 4.5: BÁN / CƠ CẤU (nâng từ 4.0)
}

# --- CẤU HÌNH PORTFOLIO ---
# Position sizing — TRUNG HẠN, AN TOÀN
# Phân bổ đều, không dồn quá nhiều vào 1 mã
PORTFOLIO_CONFIG = {
    'max_position_pct': 0.20,     # Max 20% mỗi vị thế (giảm từ 40% → đa dạng hóa)
    'min_position_pct': 0.05,     # Min 5% (đủ ý nghĩa)
    'max_positions': 8,           # Tối đa 8 mã (giảm từ 10 → quản lý dễ hơn)
    'cash_reserve_pct': 0.25,     # Giữ 25% tiền mặt (tăng từ 20% → an toàn hơn)
    'max_sector_pct': 0.40,       # Tối đa 40% mỗi ngành (→ tối đa 2 mã/ngành khi mỗi mã ≤ 20%)
    'max_correlation': 0.70,      # Bỏ mã có tương quan lợi suất > 0.7 với mã đã chọn
    'correlation_lookback': 60,   # Số phiên tính tương quan
}

# --- QUY TẮC CỨNG (single source of truth) ---
# Mã không thoả → không được khuyến nghị MUA. Dùng bởi RuleGate (analysis),
# StockOptionSkill (prompt AI) và PortfolioManager.
HARD_RULES = {
    'min_score': RECOMMENDATION_THRESHOLDS['buy'],  # Điểm tổng tối thiểu (= ngưỡng 'buy')
    'min_roe': 10,             # ROE tối thiểu 10%
    'max_pe': 30,              # P/E tối đa 30x
    'max_debt_equity': 2.0,    # Nợ phải trả / Vốn chủ sở hữu tối đa 2.0 (bỏ qua nhóm tài chính)
    # Trần riêng theo ngành: BĐS có "người mua trả tiền trước" trong nợ phải trả nên nới nhẹ.
    # Vẫn đủ chặt để loại các chủ đầu tư đòn bẩy cao (NVL, DXG, PDR... thường > 3).
    'max_debt_equity_by_sector': {'Bất động sản': 2.5},
    'min_breadth': 0.35,       # Tỷ lệ mã trên SMA10 & SMA20 tối thiểu để mua mới
    'min_price_vnd': 10000,    # Tránh penny stock (< 10,000 VND)
    'max_position_pct': PORTFOLIO_CONFIG['max_position_pct'],
    'max_positions': PORTFOLIO_CONFIG['max_positions'],
    'cash_reserve': PORTFOLIO_CONFIG['cash_reserve_pct'],
}

# Investment horizon
HOLDING_PERIOD = {
    'min_months': 1,              # Tối thiểu 1 tháng
    'target_months': 3,           # Trung bình 3 tháng
    'max_months': 6,              # Tối đa 6 tháng
    'expected_return': (0.10, 0.15)  # Lợi nhuận mong đợi 10-15%
}

# Risk management — AN TOÀN, phù hợp với ĐẶC ĐIỂM THỊ TRƯỜNG VN
# VN market biến động cao, có "lái" và manipulation
# → Stop loss 7% (không quá chặt) để tránh bị shake out
# → Target 15% upper range để match kỳ vọng 1-6 tháng
RISK_MANAGEMENT = {
    'stop_loss_pct': 0.07,        # -7% stop loss (điều chỉnh từ 5% → phù hợp VN volatility)
    'target_profit_pct': 0.15,    # +15% target (tăng từ 12% → upper range 10-15%)
    'risk_reward_ratio': 2.14,    # 1:2.14 risk/reward (7% risk → 15% reward)
    'max_drawdown_pct': 0.10      # Max 10% drawdown danh mục (siết từ 15%)
}

# Price unit detection
# Dữ liệu giá vnstock tính theo NGHÌN đồng (VD 29.3 = 29,300đ). Không mã nào trên HOSE
# giá dưới 1,000đ, nên giá < 1000 chắc chắn là đơn vị nghìn đồng.
# (Ngưỡng cũ 100 làm các mã giá 100-999 nghìn như FRT 167, PNJ 121 bị coi là 167đ/121đ
#  → khuyến nghị mua hàng chục nghìn cổ phiếu.)
PRICE_UNIT_CONFIG = {
    'threshold': 1000,            # If price < 1000, assume it's in thousands VND
    'multiplier': 1000            # Multiply by 1000 to get actual price
}

# Mệnh giá cổ phiếu VN (đồng) — ước lượng số cổ phiếu = Vốn góp / mệnh giá
PAR_VALUE_VND = 10000

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