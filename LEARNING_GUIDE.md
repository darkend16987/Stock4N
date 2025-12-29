# 🧠 Phase 2: Learning & Optimization Module

Hướng dẫn sử dụng module học patterns và tối ưu hóa tham số chiến lược.

---

## 📋 Tổng Quan

Phase 2 bổ sung khả năng **tự động học** từ dữ liệu lịch sử:

- **Pattern Analysis**: Phát hiện chu kỳ, momentum, support/resistance
- **Weight Optimization**: Tìm trọng số tối ưu cho scoring (Fund vs Tech)
- **Parameter Management**: Lưu/load tham số đã học

---

## 🚀 Sử Dụng

### Cách 1: Batch File (Windows)

```bash
run_learning.bat
```

### Cách 2: Docker CLI

```bash
# Chạy tất cả (patterns + optimization)
docker exec stock4n_app python src/main.py learn

# Chỉ phân tích patterns
docker exec stock4n_app python src/main.py learn --learn-mode patterns

# Chỉ tối ưu weights
docker exec stock4n_app python src/main.py learn --learn-mode optimize

# Tùy chỉnh lookback period
docker exec stock4n_app python src/main.py learn --days 730
```

---

## 📊 Pattern Analysis

### 1. **Seasonality Detection**

Phát hiện chu kỳ theo tháng/quý:

- **Monthly Returns**: Tháng nào thường tăng/giảm
- **Quarterly Returns**: Quý nào performance tốt nhất
- **Best/Worst Months**: Top 3 tháng tốt/xấu nhất

**Ví dụ kết quả**:
```json
{
  "symbol": "VCB",
  "monthly_returns": {
    "1": 2.5,   // Tháng 1 trung bình +2.5%
    "2": -1.2,  // Tháng 2 trung bình -1.2%
    ...
  },
  "best_months": [1, 3, 11],
  "best_quarter": 1
}
```

### 2. **Price Momentum**

Đà tăng/giảm qua các khung thời gian (5, 10, 20, 60 ngày):

```json
{
  "5": 3.2,   // +3.2% trong 5 ngày
  "10": 5.1,  // +5.1% trong 10 ngày
  "20": -2.3, // -2.3% trong 20 ngày
  "60": 10.5  // +10.5% trong 60 ngày
}
```

### 3. **Support & Resistance**

Mức hỗ trợ/kháng cự tự động:

```json
{
  "current_price": 85000,
  "nearest_support": 82000,
  "nearest_resistance": 88000,
  "support_levels": [75000, 78000, 82000],
  "resistance_levels": [88000, 92000, 95000]
}
```

### 4. **Trading Signals**

Tín hiệu tổng hợp từ patterns:

```json
{
  "seasonality_signal": 1,    // 1 = bullish, 0 = neutral, -1 = bearish
  "momentum_signal": 1,
  "support_resistance_signal": 0,
  "combined_signal": 1,
  "confidence": 0.67
}
```

---

## ⚖️ Weight Optimization

Tự động tìm trọng số tối ưu cho scoring formula.

### Cách Hoạt Động

1. **Grid Search**: Test nhiều tổ hợp trọng số (Fund vs Tech)
2. **Backtest**: Chạy backtest cho mỗi tổ hợp
3. **Evaluate**: Đánh giá theo Sharpe Ratio (hoặc metrics khác)
4. **Select**: Chọn trọng số có performance tốt nhất

### Ví Dụ Kết Quả

```
=== WEIGHT OPTIMIZATION SUMMARY ===

Total combinations tested: 5

Best Performance:
  Fund Weight: 0.60
  Tech Weight: 0.40

  Total Return: 15.30%
  Sharpe Ratio: 1.85
  Max Drawdown: -8.20%
  Win Rate: 62.5%
  Total Trades: 24
  Profit Factor: 2.15

Top 5 Combinations (by Sharpe Ratio):

  0.60/0.40 → Return: 15.3%, Sharpe: 1.85
  0.50/0.50 → Return: 14.1%, Sharpe: 1.72
  0.70/0.30 → Return: 13.8%, Sharpe: 1.68
  0.40/0.60 → Return: 12.5%, Sharpe: 1.55
  0.30/0.70 → Return: 11.2%, Sharpe: 1.42

===================================
```

### Cấu Hình Optimization

Mặc định:
- **Weight Range**: 0.3 - 0.7 (đảm bảo cả Fund và Tech đều có ảnh hưởng)
- **Step Size**: 0.1
- **Optimization Metric**: Sharpe Ratio
- **Lookback**: 365 ngày

---

## 💾 Parameter Management

Tất cả tham số đã học được lưu tự động.

### Cấu Trúc File

```
data/learned_params/
├── patterns_latest.json          # Patterns mới nhất
├── weights_latest.json           # Weights mới nhất
├── patterns_v20250129_143022.json  # Versioned patterns
├── weights_v20250129_143022.json   # Versioned weights
└── all_parameters.json           # Export tất cả params
```

### Load Learned Parameters

```python
from modules.learning.parameter_manager import ParameterManager

pm = ParameterManager()

# Load latest weights
weights = pm.load_weights('latest')
print(weights['fund_weight'])  # 0.60
print(weights['tech_weight'])  # 0.40

# Load latest patterns
patterns = pm.load_patterns('latest')
print(patterns['VCB']['seasonality'])

# Load specific version
weights_v1 = pm.load_weights('20250129_143022')
```

### Apply Learned Weights

Sau khi tối ưu, bạn có thể apply weights mới vào scoring:

```python
# Trong modules/analysis/scorer.py
weights = pm.load_weights('latest')

total_score = (
    fund_score * weights['fund_weight'] +
    tech_score * weights['tech_weight']
)
```

---

## 📂 Output Files

### 1. **Patterns**
- `data/learned_params/patterns_latest.json`
- Chứa: seasonality, momentum, support/resistance cho mỗi symbol

### 2. **Weights**
- `data/learned_params/weights_latest.json`
- Chứa: fund_weight, tech_weight, performance metrics

### 3. **Optimization Results**
- `data/processed/optimization_results.csv`
- Chứa: Tất cả combinations đã test với performance

---

## 🎯 Use Cases

### Use Case 1: Tìm Mã Theo Seasonality

```python
from modules.learning.parameter_manager import ParameterManager
import datetime

pm = ParameterManager()
patterns = pm.load_patterns('latest')

current_month = datetime.datetime.now().month

# Tìm mã có seasonality tốt tháng này
good_symbols = []
for symbol, data in patterns.items():
    if data and data['seasonality']:
        if current_month in data['seasonality']['best_months']:
            good_symbols.append(symbol)

print(f"Symbols có seasonality tốt tháng {current_month}: {good_symbols}")
```

### Use Case 2: Apply Optimized Weights

```python
from modules.learning.parameter_manager import ParameterManager
import pandas as pd

pm = ParameterManager()
weights = pm.load_weights('latest')

# Load analysis scores
df = pd.read_csv('data/processed/analysis_report.csv')

# Recalculate với weights mới
df['Total_Score_Optimized'] = (
    df['Fund_Score'] * weights['fund_weight'] +
    df['Tech_Score'] * weights['tech_weight']
)

# So sánh
print(df[['Symbol', 'Total_Score', 'Total_Score_Optimized']].head())
```

---

## ⚙️ Tùy Chỉnh

### Thay Đổi Optimization Metric

Trong `src/modules/learning/weight_optimizer.py`:

```python
# Thay vì optimize theo Sharpe Ratio
best_weights = optimizer.optimize_weights(
    ...,
    optimization_metric='total_return'  # hoặc 'win_rate', 'profit_factor'
)
```

### Thay Đổi Weight Range

```python
# Test weights từ 0.2 - 0.8 với bước 0.05
combinations = optimizer.generate_weight_combinations(
    weight_range=(0.2, 0.8),
    step=0.05
)
```

---

## 🔍 Troubleshooting

### Lỗi "Analysis file not found"

**Nguyên nhân**: Chưa chạy analysis trước khi optimize weights

**Giải pháp**:
```bash
docker exec stock4n_app python src/main.py analysis
docker exec stock4n_app python src/main.py learn
```

### Optimization quá lâu

**Nguyên nhân**: Quá nhiều combinations hoặc lookback period dài

**Giải pháp**:
- Giảm lookback: `--days 180`
- Hoặc chỉ chạy patterns: `--learn-mode patterns`

### Không có patterns cho một số symbols

**Nguyên nhân**: Symbol không có đủ dữ liệu giá lịch sử

**Giải pháp**: Chấp nhận được - patterns sẽ là `null` cho symbols đó

---

## 📈 Next Steps

Sau khi có learned parameters:

1. **Integrate vào scoring**: Update `StockScorer` để dùng optimized weights
2. **Backtest lại**: So sánh performance với weights cũ
3. **Deploy**: Apply weights mới vào production
4. **Monitor**: Theo dõi performance, re-optimize định kỳ (monthly/quarterly)

---

## 💡 Best Practices

1. **Re-optimize định kỳ**: Market thay đổi → weights tối ưu cũng thay đổi
2. **A/B Testing**: So sánh strategy cũ vs mới trước khi deploy
3. **Version Control**: Git commit learned parameters để rollback nếu cần
4. **Validation**: Test trên out-of-sample data

---

## 📞 Tham Khảo

- [BACKTESTING_GUIDE.md](BACKTESTING_GUIDE.md) - Hướng dẫn backtest
- Source code: `src/modules/learning/`
- Output: `data/learned_params/`

---

**⚠️ Lưu Ý**: Learned parameters dựa trên dữ liệu lịch sử. Past performance không đảm bảo future results!
