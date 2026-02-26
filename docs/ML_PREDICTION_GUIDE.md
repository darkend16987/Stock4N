# 🤖 Phase 3: ML Prediction Module

Hướng dẫn sử dụng Machine Learning để dự đoán xu hướng cổ phiếu.

---

## 📋 Tổng Quan

Phase 3 sử dụng **Machine Learning** để tự động dự đoán xu hướng giá cổ phiếu dựa trên dữ liệu lịch sử.

**Capabilities**:
- **Trend Classification**: Phân loại xu hướng (UP/NEUTRAL/DOWN)
- **Feature Engineering**: Tự động tạo 50+ technical features
- **Model Management**: Lưu/load models với versioning
- **Confidence Scores**: Probability cho mỗi prediction

**Models**:
- Random Forest Classifier (default)
- Gradient Boosting Classifier

**Output**: Dự đoán xu hướng 5 ngày tới cho tất cả stocks

---

## 🚀 Quick Start

### 1. Train Model

```bash
# Windows - Batch file (easiest)
run_ml_train.bat

# Docker CLI
docker exec stock4n_app python src/main.py ml_predict --ml-mode train
```

**Kết quả**: Model được lưu tại `data/ml_models/trend_classifier/latest/`

### 2. Generate Predictions

```bash
# Windows - Batch file
run_ml_predict.bat

# Docker CLI
docker exec stock4n_app python src/main.py ml_predict --ml-mode predict
```

**Kết quả**: Predictions saved to `data/processed/ml_predictions.csv`

---

## 📊 How It Works

### Pipeline Flow

```
Raw Price Data
    ↓
Feature Engineering (50+ features)
    ↓
Train ML Model (Random Forest)
    ↓
Saved Model
    ↓
Generate Predictions
    ↓
ml_predictions.csv
```

### 1. Feature Engineering

Tự động tạo technical indicators:

**Price-Based Features**:
- Returns: 1d, 5d, 10d, 20d
- Volatility: 5d, 20d
- High-Low range

**Moving Averages**:
- SMA: 5, 10, 20, 50
- Price vs SMA ratios
- MA crossovers (SMA5 vs SMA20, SMA20 vs SMA50)

**Momentum Indicators**:
- RSI (14 periods)
- MACD + MACD Signal
- Price momentum (5, 10, 20 days)

**Volume Features**:
- Volume change
- Volume vs MA
- Volume MA (5 periods)

**Lag Features**:
- Lagged values (1, 2, 3, 5 days) for:
  - Returns
  - RSI
  - MACD diff
  - Volume change

**Rolling Statistics**:
- Mean, Std, Min, Max for:
  - Returns (windows: 5, 10, 20)
  - Volume (windows: 5, 10, 20)

**Total**: 50+ features automatically generated!

### 2. Target Variable

Phân loại xu hướng dựa trên future returns:

- **UP (1)**: Future return > +2% trong 5 ngày
- **NEUTRAL (0)**: Future return trong [-2%, +2%]
- **DOWN (-1)**: Future return < -2% trong 5 ngày

### 3. Model Training

**Algorithm**: Random Forest Classifier
- 100 trees
- Max depth: 10
- Min samples split: 20
- Min samples leaf: 10

**Training**:
- Pooled data từ tất cả 50 stocks
- Train/test split: 80/20
- Stratified sampling (giữ tỷ lệ classes)

**Evaluation**:
- Accuracy (train & test)
- Precision, Recall, F1-score per class
- Feature importance ranking

### 4. Prediction

Cho mỗi stock:
- Extract latest features từ giá hiện tại
- Feed vào trained model
- Get prediction + probabilities
- Return: UP/NEUTRAL/DOWN + confidence

---

## 🎯 Usage Examples

### Train với Custom Parameters

```bash
# Gradient Boosting instead of Random Forest
docker exec stock4n_app python src/main.py ml_predict \
  --ml-mode train \
  --model-type gradient_boosting

# Longer forecast horizon (10 days)
docker exec stock4n_app python src/main.py ml_predict \
  --ml-mode train \
  --horizon 10 \
  --threshold 0.03

# Higher threshold for classification (3% instead of 2%)
docker exec stock4n_app python src/main.py ml_predict \
  --ml-mode train \
  --threshold 0.03
```

### Load và Sử Dụng Model

```python
from modules.ml_prediction.model_manager import ModelManager
from modules.ml_prediction.feature_engineer import FeatureEngineer

# Load model
manager = ModelManager()
model = manager.load_model('trend_classifier', 'latest')

# Get latest features
engineer = FeatureEngineer()
features = engineer.get_latest_features('VCB')

# Predict
prediction = model.predict_single(features)

print(f"Prediction: {prediction['prediction_label']}")
print(f"Confidence: {prediction['confidence']:.2%}")
print(f"Probabilities: {prediction['probabilities']}")
```

**Output**:
```
Prediction: UP
Confidence: 78.5%
Probabilities: {
  'UP': 0.785,
  'NEUTRAL': 0.150,
  'DOWN': 0.065
}
```

---

## 📁 Output Files

### 1. Trained Models

```
data/ml_models/trend_classifier/
├── latest/                          # Symlink to latest version
│   ├── model.pkl                   # Trained model
│   ├── metadata.json               # Model info & metrics
│   └── feature_importance.csv      # Feature rankings
├── 20250129_153045/                # Versioned models
│   ├── model.pkl
│   ├── metadata.json
│   └── feature_importance.csv
└── 20250129_120000/
    └── ...
```

### 2. Predictions

`data/processed/ml_predictions.csv`:

| Symbol | Prediction | Confidence | P(UP) | P(NEUTRAL) | P(DOWN) |
|--------|-----------|-----------|-------|-----------|---------|
| VCB    | UP        | 78.5%     | 78.5% | 15.0%     | 6.5%    |
| BID    | NEUTRAL   | 65.2%     | 20.1% | 65.2%     | 14.7%   |
| VHM    | DOWN      | 72.3%     | 12.5% | 15.2%     | 72.3%   |

### 3. Metadata

`data/ml_models/trend_classifier/latest/metadata.json`:

```json
{
  "model_name": "trend_classifier",
  "version": "20250129_153045",
  "saved_at": "2025-01-29T15:30:45",
  "model_type": "random_forest",
  "horizon": 5,
  "threshold": 0.02,
  "symbols": ["VCB", "BID", "VHM", ...],
  "n_symbols": 50,
  "feature_names": ["return_1d", "rsi_14", ...],
  "metrics": {
    "train_accuracy": 0.682,
    "test_accuracy": 0.645,
    "train_samples": 12450,
    "test_samples": 3113,
    "classification_report": {
      "UP": {"precision": 0.68, "recall": 0.71, "f1-score": 0.69},
      "NEUTRAL": {"precision": 0.61, "recall": 0.55, "f1-score": 0.58},
      "DOWN": {"precision": 0.66, "recall": 0.69, "f1-score": 0.67}
    }
  }
}
```

---

## 🔍 Model Performance

### Expected Accuracy

**Baseline** (Random Forest, 5-day horizon, 2% threshold):
- **Train Accuracy**: ~68%
- **Test Accuracy**: ~64-65%

**Per-Class Performance**:
- **UP**: Precision ~68%, Recall ~71%
- **NEUTRAL**: Precision ~61%, Recall ~55% (hardest class)
- **DOWN**: Precision ~66%, Recall ~69%

### Interpretation

- **64% accuracy** on 3-class classification >> 33% random baseline
- Model learns patterns from technical indicators
- UP/DOWN classes easier than NEUTRAL
- Higher confidence predictions more reliable

### Feature Importance

Top features thường là:
1. `return_20d` - 20-day returns
2. `rsi_14` - RSI indicator
3. `price_vs_sma20` - Price vs SMA20 ratio
4. `macd_diff` - MACD histogram
5. `momentum_10` - 10-day momentum

---

## 💡 Use Cases

### Use Case 1: Filter Stocks với ML Predictions

```python
import pandas as pd

# Load predictions
pred_df = pd.read_csv('data/processed/ml_predictions.csv')

# Filter UP predictions với high confidence
high_conf_up = pred_df[
    (pred_df['Prediction'] == 'UP') &
    (pred_df['Confidence'].str.rstrip('%').astype(float) > 70)
]

print(f"High confidence UP predictions: {len(high_conf_up)}")
print(high_conf_up[['Symbol', 'Confidence', 'P(UP)']])
```

### Use Case 2: Combine với Stock Scoring

```python
# Load analysis scores
scores_df = pd.read_csv('data/processed/analysis_report.csv')

# Merge với ML predictions
merged = scores_df.merge(pred_df, on='Symbol')

# Filter: High score AND ML predicts UP
candidates = merged[
    (merged['Total_Score'] >= 7.0) &
    (merged['Prediction'] == 'UP') &
    (merged['Confidence'].str.rstrip('%').astype(float) > 65)
]

print(f"Strong buy candidates: {len(candidates)}")
print(candidates[['Symbol', 'Total_Score', 'Prediction', 'Confidence']])
```

### Use Case 3: Backtesting ML Strategy

```python
# Backtest strategy:
# - Buy: ML predicts UP với confidence > 70%
# - Hold for 5 days (horizon period)
# - Evaluate accuracy

correct_predictions = 0
total_predictions = 0

for symbol in candidates['Symbol']:
    # Get actual price movement after 5 days
    # Compare with ML prediction
    # Track accuracy
    pass

accuracy = correct_predictions / total_predictions
print(f"ML Strategy Accuracy: {accuracy:.2%}")
```

### Use Case 4: Model Comparison

```python
from modules.ml_prediction.model_manager import ModelManager

manager = ModelManager()

# Compare all trained versions
comparison = manager.compare_versions('trend_classifier')

print(comparison)
```

**Output**:
```
         version             saved_at  train_accuracy  test_accuracy  ...
0  20250129_153045  2025-01-29T15:30:45           0.682          0.645
1  20250129_120000  2025-01-29T12:00:00           0.675          0.638
2  20250128_180000  2025-01-28T18:00:00           0.691          0.652
```

---

## ⚙️ Advanced Configuration

### Custom Model Parameters

Modify trong `src/modules/ml_prediction/trend_classifier.py`:

```python
# Random Forest
self.model = RandomForestClassifier(
    n_estimators=200,      # More trees
    max_depth=15,          # Deeper trees
    min_samples_split=10,  # Split easier
    random_state=42
)

# Gradient Boosting
self.model = GradientBoostingClassifier(
    n_estimators=150,
    max_depth=7,
    learning_rate=0.05,    # Slower learning
    random_state=42
)
```

### Custom Features

Add trong `src/modules/ml_prediction/feature_engineer.py`:

```python
def create_technical_features(self, df):
    # ... existing features ...

    # Add new feature
    df['custom_indicator'] = (
        df['close'].rolling(10).mean() /
        df['close'].rolling(30).mean()
    )

    return df
```

### Custom Classification Thresholds

```python
# Asymmetric thresholds
df['target'] = 0  # neutral

df.loc[df['future_return'] > 0.03, 'target'] = 1   # UP: +3%
df.loc[df['future_return'] < -0.015, 'target'] = -1  # DOWN: -1.5%
```

---

## 🔧 Model Management

### List All Versions

```python
from modules.ml_prediction.model_manager import ModelManager

manager = ModelManager()

versions = manager.list_versions('trend_classifier')

for version, saved_at, test_acc in versions:
    print(f"{version}: {test_acc:.3f} (saved: {saved_at})")
```

### Get Best Model

```python
best_version, model, metadata = manager.get_best_model(
    model_name='trend_classifier',
    metric='test_accuracy'
)

print(f"Best model: {best_version}")
print(f"Test accuracy: {metadata['metrics']['test_accuracy']:.3f}")
```

### Export Model

```python
# Export to zip file
zip_path = manager.export_model(
    model_name='trend_classifier',
    version='latest',
    output_file='/path/to/export/model_v1'
)

print(f"Exported to: {zip_path}")
```

### Import Model

```python
# Import from zip
success = manager.import_model(
    zip_file='/path/to/model_v1.zip',
    model_name='trend_classifier',
    version='imported_v1'
)
```

---

## 🚨 Troubleshooting

### Lỗi "No trained model found"

**Nguyên nhân**: Chưa train model

**Giải pháp**:
```bash
run_ml_train.bat
```

### Model accuracy quá thấp (<50%)

**Nguyên nhân**: Không đủ dữ liệu hoặc features không informative

**Giải pháp**:
- Increase data collection period
- Add more features
- Try different model_type (gradient_boosting)
- Adjust horizon or threshold

### Memory error khi training

**Nguyên nhân**: Too many samples or features

**Giải pháp**:
- Reduce số symbols (train trên subset)
- Reduce feature count (remove redundant features)
- Use simpler model (lower max_depth)

### Predictions all NEUTRAL

**Nguyên nhân**: Threshold quá cao hoặc market sideways

**Giải pháp**:
- Lower threshold: `--threshold 0.015`
- Check market conditions
- Try shorter horizon: `--horizon 3`

---

## 📈 Performance Tips

### 1. Feature Selection

Remove redundant features:
```python
# Keep only top N important features
top_features = classifier.get_feature_importance(top_n=30)
feature_names = top_features['feature'].tolist()
```

### 2. Ensemble Models

Combine predictions từ nhiều models:
```python
# Train multiple models
model_rf = TrendClassifier('random_forest')
model_gb = TrendClassifier('gradient_boosting')

# Average predictions
pred_rf = model_rf.predict_proba(X)
pred_gb = model_gb.predict_proba(X)

ensemble_pred = (pred_rf + pred_gb) / 2
```

### 3. Retrain Periodically

```bash
# Schedule monthly retraining
# Cron job (Linux) or Task Scheduler (Windows)
# Run: docker exec stock4n_app python src/main.py ml_predict --ml-mode train
```

### 4. Validate on Recent Data

```python
# Test model on most recent month
recent_df = df[df['time'] >= '2025-01-01']

metrics = classifier.evaluate_on_new_data(recent_df, feature_names)
print(f"Recent accuracy: {metrics['accuracy']:.3f}")
```

---

## 📊 Metrics Explained

### Accuracy
- **Definition**: % predictions chính xác
- **Good**: >60% (3-class), >70% (2-class)
- **Limitation**: Không account for class imbalance

### Precision
- **Definition**: Trong số predictions UP, bao nhiêu % đúng?
- **Use**: Quan trọng khi muốn tránh false positives
- **Good**: >65%

### Recall
- **Definition**: Trong số stocks thực tế UP, bao nhiêu % model catch được?
- **Use**: Quan trọng khi không muốn miss opportunities
- **Good**: >65%

### F1-Score
- **Definition**: Harmonic mean của Precision và Recall
- **Use**: Balanced metric
- **Good**: >0.65

### Confidence
- **Definition**: Max probability trong prediction
- **Use**: Filter low-confidence predictions
- **Threshold**: >70% for reliable predictions

---

## 🎓 Best Practices

1. **Retrain regularly**: Monthly hoặc khi market conditions thay đổi
2. **Validate predictions**: So sánh với actual results
3. **Use confidence threshold**: Chỉ trade high-confidence predictions (>70%)
4. **Combine signals**: ML + Scoring + Patterns = stronger signal
5. **Track performance**: Log predictions và outcomes
6. **A/B test**: Compare old vs new models trước khi deploy
7. **Version control**: Commit trained models vào git LFS
8. **Monitor drift**: Check if test accuracy giảm theo thời gian

---

## 📚 References

- **scikit-learn**: https://scikit-learn.org/
- **Random Forest**: https://en.wikipedia.org/wiki/Random_forest
- **Feature Engineering**: https://www.kaggle.com/learn/feature-engineering
- **Technical Indicators**: https://www.investopedia.com/

---

## 🚀 Next Steps

Sau khi train model:

1. **Generate predictions**: Run `run_ml_predict.bat`
2. **Integrate vào analysis**: Merge predictions với stock scores
3. **Backtest**: Validate predictions trên historical data
4. **Monitor**: Track prediction accuracy over time
5. **Iterate**: Add features, tune parameters, retrain

---

**⚠️ Disclaimer**: ML predictions dựa trên historical patterns. Past performance does not guarantee future results. Luôn kết hợp với fundamental analysis và risk management!
