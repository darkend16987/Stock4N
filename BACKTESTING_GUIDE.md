# 🔬 Hướng Dẫn Backtesting - Stock4N

## 📚 Giới Thiệu

**Backtesting** là quá trình kiểm tra chiến lược đầu tư trên dữ liệu lịch sử để đánh giá hiệu quả. Module này giúp bạn:

✅ Đo lường performance của chiến lược scoring
✅ Tìm ra mã cổ phiếu hoạt động tốt
✅ Tối ưu hóa tham số (stop loss, take profit, etc.)
✅ Ra quyết định đầu tư dựa trên số liệu thực tế

---

## 🚀 Cách Sử Dụng

### **Option 1: Chạy Batch File** (Đơn Giản Nhất)

```bash
# Double-click hoặc chạy trong CMD:
run_backtest.bat
```

### **Option 2: Chạy Docker Command**

```bash
# Backtest 1 năm với score >= 6.0
docker exec stock4n_app python src/main.py backtest

# Custom parameters
docker exec stock4n_app python src/main.py backtest --days 180 --score 7.0 --capital 200000000
```

### **Option 3: Chạy Python Trực Tiếp**

```bash
cd src
python main.py backtest --days 365 --score 6.0
```

---

## ⚙️ Tham Số

| Parameter | Mặc Định | Mô Tả |
|-----------|----------|-------|
| `--days` | 365 | Số ngày quay lại để test (365 = 1 năm) |
| `--score` | 6.0 | Điểm tối thiểu để mua (6.0 = MUA THĂM DÒ trở lên) |
| `--capital` | 100000000 | Vốn ban đầu (VND) |

---

## 📊 Chiến Lược Được Test

### **Buy Signal**
- Điều kiện: `Total_Score >= min_score` VÀ `Recommendation` chứa "MUA"
- Mua tại giá đầu tiên có sẵn
- Số lượng: 10% vốn hiện tại / giá (làm tròn lot 100)
- Tối đa 10 vị thế cùng lúc

### **Sell Signal**
Bán khi đạt một trong các điều kiện:
- **Stop Loss**: Giá giảm >= 7% so với giá mua
- **Take Profit**: Giá tăng >= 15% so với giá mua
- **End of Period**: Kết thúc kỳ backtest (close tất cả positions)

---

## 📈 Metrics Được Đo

### **Capital & Returns**
- **Initial Capital**: Vốn ban đầu
- **Final Capital**: Vốn cuối kỳ
- **Total P&L**: Lời/lỗ tổng cộng (VND)
- **Total Return**: Lợi nhuận % (so với vốn ban đầu)

### **Risk Metrics**
- **Sharpe Ratio**: Tỷ lệ lợi nhuận/rủi ro (>1 = tốt, >2 = rất tốt)
- **Max Drawdown**: Sụt giảm lớn nhất từ đỉnh (%)
- **Profit Factor**: Tổng win / Tổng loss (>1 = profitable)

### **Trading Statistics**
- **Total Trades**: Tổng số giao dịch
- **Winning Trades**: Số giao dịch thắng
- **Losing Trades**: Số giao dịch thua
- **Win Rate**: Tỷ lệ thắng (%)

### **Win/Loss Analysis**
- **Average Win**: Lời trung bình mỗi giao dịch thắng
- **Average Loss**: Lỗ trung bình mỗi giao dịch thua

---

## 📁 Output Files

Sau khi chạy backtest, kết quả được lưu tại `data/backtest/`:

```
data/backtest/
├── backtest_20251229_093755.csv      # Chi tiết từng giao dịch
└── summary_20251229_093755.txt       # Tổng kết metrics
```

### **File CSV Columns**
- `date`: Ngày giao dịch
- `symbol`: Mã cổ phiếu
- `action`: BUY hoặc SELL
- `price`: Giá giao dịch
- `shares`: Số lượng cổ phiếu
- `pnl`: Profit & Loss (VND)
- `reason`: Lý do (STOP_LOSS, TAKE_PROFIT, END_OF_PERIOD)
- `return_pct`: Lợi nhuận % (chỉ có khi SELL)

---

## 🎯 Ví Dụ Output

```
============================================================
📊 BACKTEST RESULTS SUMMARY
============================================================

💰 CAPITAL & RETURNS:
  Initial Capital:       100,000,000 VND
  Final Capital:         118,450,000 VND
  Total P&L:              18,450,000 VND
  Total Return:                18.45 %

📈 RISK METRICS:
  Sharpe Ratio:                 1.24
  Max Drawdown:                12.30 %
  Profit Factor:                1.65

📊 TRADING STATISTICS:
  Total Trades:                   18
  Winning Trades:                 11 (61.1%)
  Losing Trades:                   7
  Win Rate:                     61.1 %

💵 WIN/LOSS ANALYSIS:
  Average Win:           2,450,000 VND
  Average Loss:          1,120,000 VND

============================================================

🏆 TOP 10 BEST PERFORMERS:
--------------------------------------------------------------------------------
Rank  Symbol    Return %    P&L (VND)      Reason
--------------------------------------------------------------------------------
1     CTG          32.50%      4,550,000    TAKE_PROFIT
2     HPG          28.20%      3,780,000    TAKE_PROFIT
3     SAB          22.10%      3,250,000    TAKE_PROFIT
```

---

## 💡 Tips & Best Practices

### 1. **Test Nhiều Tham Số**

```bash
# Test với score cao hơn (chỉ mua cổ phiếu rất tốt)
run_backtest.bat --score 7.5

# Test với vốn lớn hơn
run_backtest.bat --capital 500000000

# Test ngắn hạn (6 tháng)
run_backtest.bat --days 180
```

### 2. **So Sánh Kết Quả**

Chạy backtest với nhiều `--score` khác nhau để tìm ra điểm tối ưu:
- Score 6.0: Nhiều giao dịch, rủi ro cao
- Score 7.0: Trung bình
- Score 8.0: Ít giao dịch, an toàn hơn

### 3. **Kết Hợp Với Analysis**

```bash
# Luôn chạy analysis trước khi backtest
docker exec stock4n_app python src/main.py analysis
docker exec stock4n_app python src/main.py backtest
```

### 4. **Theo Dõi Các Mã Tốt**

Nhìn vào **Top Performers** để biết mã nào hoạt động tốt → Focus vào những mã này trong tương lai.

---

## 🐛 Troubleshooting

### Lỗi: "Analysis file not found"

**Nguyên nhân**: Chưa chạy analysis

**Giải pháp**:
```bash
docker exec stock4n_app python src/main.py analysis
docker exec stock4n_app python src/main.py backtest
```

---

### Lỗi: "No trades executed"

**Nguyên nhân**: `--score` quá cao, không có mã nào đủ điểm

**Giải pháp**: Giảm `--score` xuống (vd: từ 8.0 → 6.0)

---

### Lỗi: "No price data"

**Nguyên nhân**: Chưa chạy ingestion hoặc thiếu dữ liệu lịch sử

**Giải pháp**:
```bash
docker exec stock4n_app python src/main.py ingestion
```

---

## 🔮 Roadmap (Phase 2 & 3)

### Phase 2: Pattern Learning
- ✅ Detect seasonality (chu kỳ theo tháng/quý)
- ✅ Find recurring patterns
- ✅ Optimize scoring weights tự động
- ✅ Save/load learned parameters

### Phase 3: ML Prediction
- ✅ LSTM/GRU cho dự đoán giá
- ✅ Random Forest cho phân loại xu hướng
- ✅ Feature engineering tự động
- ✅ Model versioning & A/B testing

---

## 📞 Support

Nếu gặp vấn đề:
1. Check logs tại `logs/`
2. Đọc `TROUBLESHOOTING.md`
3. Mở issue trên GitHub

---

**Last Updated**: 2025-12-29
**Version**: 1.0 (Phase 1 - Basic Backtesting)
