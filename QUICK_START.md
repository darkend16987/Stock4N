# 🚀 Hướng Dẫn Sử Dụng Nhanh Stock4N

## 📋 Tóm Tắt

Stock4N là hệ thống phân tích chứng khoán Việt Nam tự động với:
- **Backend**: Python + Docker (phân tích 50 mã top VN)
- **Frontend**: Next.js + Vercel (hiển thị kết quả)
- **Data**: Tự động lấy từ vnstock, xử lý và đồng bộ

---

## 🎯 Cách Sử Dụng - Đơn Giản Nhất

### Windows: Chỉ cần **Double-click** các file `.bat`

```
📁 Stock4N/
├── run_all.bat           ⭐ CHẠY TẤT CẢ (Khuyên dùng!)
├── run_ingestion.bat     📥 Chỉ lấy dữ liệu
├── run_processing.bat    ⚙️  Chỉ xử lý dữ liệu
├── run_analysis.bat      🧠 Chỉ phân tích
├── run_portfolio.bat     💼 Chỉ tạo danh mục
├── run_export.bat        📦 Chỉ xuất db.json
└── run_sync.bat          🔄 Chỉ đồng bộ frontend
```

### Linux/Mac: Chạy shell scripts

```bash
./run_all.sh              # Chạy tất cả
./run_ingestion.sh        # Chỉ lấy dữ liệu
./run_sync.sh             # Chỉ đồng bộ frontend
```

---

## ⚡ Quy Trình Tự Động (run_all.bat/sh)

```
[1] Khởi động Docker container
        ↓
[2] Chạy data pipeline (ingestion → processing → analysis → portfolio → export)
        ↓
[3] Đồng bộ db.json từ backend sang frontend
        ↓
[4] Git add các file thay đổi
        ↓
[5] Git commit với timestamp
        ↓
[6] Git push lên GitHub (với retry 4 lần)
        ↓
[7] Vercel tự động deploy frontend mới (1-2 phút)
```

**✅ Kết quả**: Website của bạn tự động cập nhật dữ liệu mới!

---

## 📊 Chi Tiết Các Bước

### 1️⃣ Lấy Dữ Liệu (Ingestion)

```bash
# Windows
run_ingestion.bat

# Linux/Mac
./run_ingestion.sh

# Hoặc thủ công
docker exec stock4n_app python src/main.py ingestion
```

**Output**: `data/raw/*.csv` (price, financial, profile cho 50 mã)

---

### 2️⃣ Xử Lý Dữ Liệu (Processing)

```bash
# Windows
run_processing.bat

# Hoặc thủ công
docker exec stock4n_app python src/main.py processing
```

**Output**: `data/processed/financial_metrics.csv` (ROE, growth, etc.)

---

### 3️⃣ Phân Tích & Chấm Điểm (Analysis)

```bash
# Windows
run_analysis.bat

# Hoặc thủ công
docker exec stock4n_app python src/main.py analysis
```

**Output**: `data/processed/analysis_report.csv` (điểm số, khuyến nghị)

---

### 4️⃣ Tạo Danh Mục Đầu Tư (Portfolio)

```bash
# Windows
run_portfolio.bat

# Hoặc thủ công
docker exec stock4n_app python src/main.py portfolio
```

**Output**: `data/processed/portfolio_recommendation.csv`

---

### 5️⃣ Xuất Dữ Liệu Web (Export)

```bash
# Windows
run_export.bat

# Hoặc thủ công
docker exec stock4n_app python src/main.py export
```

**Output**: `data/export/db.json` (492KB)

---

### 6️⃣ Đồng Bộ Frontend (Sync)

```bash
# Windows
run_sync.bat

# Linux/Mac
python3 scripts/sync_data.py
```

**Công việc**:
- Copy `data/export/db.json` → `frontend/public/data/db.json`
- Frontend (Vercel) sẽ đọc file này

---

## 🔧 Cấu Hình Nâng Cao

### Thay Đổi Danh Sách Cổ Phiếu

Mở file `src/config.py`:

```python
VN100_SYMBOLS = [
    # === VN30 - Blue Chip (30 mã) ===
    'VCB', 'BID', 'CTG', ...  # ← Sửa ở đây

    # === VN MidCap (20 mã) ===
    'KDH', 'DXG', 'NVL', ...  # ← Hoặc ở đây
]
```

---

### Thay Đổi Vốn Đầu Tư

Mở file `src/main.py`:

```python
# Thay đổi từ 100M → 200M
manager = PortfolioManager(capital=200_000_000)
```

---

### Thay Đổi Tỷ Lệ Stop Loss

Mở file `src/config.py`:

```python
RISK_MANAGEMENT = {
    'stop_loss_pct': 0.10,        # ← Đổi từ 7% → 10%
    'target_profit_pct': 0.20,    # ← Đổi từ 15% → 20%
}
```

---

## 🐛 Xử Lý Lỗi Thường Gặp

### ❌ Lỗi: "Docker không khởi động"

```bash
# Kiểm tra Docker đã chạy chưa
docker ps

# Nếu chưa có container, tạo mới
docker-compose up -d
```

---

### ❌ Lỗi: "db.json không có dữ liệu"

```bash
# 1. Kiểm tra file backend
ls -lh data/export/db.json

# 2. Nếu file < 1KB, chạy lại pipeline
run_all.bat

# 3. Sync lại frontend
run_sync.bat
```

---

### ❌ Lỗi: "Git push thất bại"

```bash
# Thử push thủ công
git push -u origin claude/fix-frontend-data-loading-N0OJg

# Nếu lỗi 403, kiểm tra branch name
git branch

# Branch phải bắt đầu với 'claude/' và kết thúc với session ID
```

---

### ❌ Lỗi: "Frontend vẫn không có dữ liệu sau khi push"

**Nguyên nhân**: Vercel đang deploy (1-2 phút)

**Giải pháp**:
1. Chờ 2 phút
2. Hard refresh: `Ctrl + Shift + R` (Windows) hoặc `Cmd + Shift + R` (Mac)
3. Kiểm tra Vercel dashboard: https://vercel.com/dashboard

---

## 📈 Danh Sách 50 Mã Cổ Phiếu Hiện Tại

### VN30 - Blue Chip (30 mã)

**Ngân hàng (15 mã)**:
VCB, BID, CTG, TCB, MBB, VPB, ACB, HDB, STB, TPB, VIB, SHB, SSB, LPB, EIB

**Bất động sản (5 mã)**:
VIC, VHM, VRE, BCM, VGI

**Năng lượng & Công nghiệp (4 mã)**:
GAS, PLX, HPG, GVR

**Hàng tiêu dùng (4 mã)**:
VNM, MSN, MWG, SAB

**Khác (2 mã)**:
SSI (Chứng khoán), FPT (Công nghệ)

### VN MidCap & Large Cap (20 mã)

**Bất động sản (6 mã)**:
KDH, DXG, NVL, PDR, DIG, BCG

**Năng lượng & Công nghiệp (5 mã)**:
POW, REE, DGW, NT2, BSR

**Hàng tiêu dùng & Dịch vụ (4 mã)**:
PNJ, FRT, VHC, DGC

**Hàng không (2 mã)**:
VJC, HVN

**Nông nghiệp (2 mã)**:
VND, HNG

**Công nghệ (1 mã)**:
VGC

---

## 📞 Hỗ Trợ

### Vấn Đề Backend
- Log file: `logs/*.log`
- Docker logs: `docker logs stock4n_app`

### Vấn Đề Frontend
- Vercel logs: https://vercel.com/dashboard
- Browser console: F12 → Console tab

### Vấn Đề Git
- Check branch: `git branch`
- Check remote: `git remote -v`
- Check status: `git status`

---

## 🎓 Tips & Tricks

### 1. Chạy Hàng Ngày Tự Động

**Windows Task Scheduler**:
1. Mở Task Scheduler
2. Create Task → Action → Start a program
3. Program: `D:\GitHub\Stock4N\run_all.bat`
4. Trigger: Daily at 9:00 AM

**Linux Cron**:
```bash
# Chạy mỗi ngày lúc 9:00 sáng
0 9 * * * cd /path/to/Stock4N && ./run_all.sh
```

---

### 2. Kiểm Tra Nhanh Dữ Liệu

```bash
# Xem số lượng mã đã lấy
ls -1 data/raw/*_price.csv | wc -l

# Xem top 10 cổ phiếu
docker exec stock4n_app python -c "
import pandas as pd
df = pd.read_csv('data/processed/analysis_report.csv')
print(df.nlargest(10, 'Total_Score')[['Symbol', 'Total_Score', 'Recommendation']])
"
```

---

### 3. Backup Dữ Liệu

```bash
# Backup db.json
cp data/export/db.json data/export/db_backup_$(date +%Y%m%d).json

# Backup tất cả processed data
tar -czf backup_$(date +%Y%m%d).tar.gz data/processed/
```

---

## ✅ Checklist Hàng Ngày

- [ ] Chạy `run_all.bat` để cập nhật dữ liệu
- [ ] Kiểm tra log có lỗi không
- [ ] Verify frontend đã cập nhật (check timestamp)
- [ ] Review danh mục đầu tư mới
- [ ] Backup dữ liệu quan trọng (optional)

---

**🎉 Chúc bạn đầu tư thành công!**
