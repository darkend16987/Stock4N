# 📊 Stock4N - AI-Powered Vietnamese Stock Advisor

<div align="center">

**Hệ thống phân tích & tư vấn đầu tư chứng khoán Việt Nam thông minh**

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![vnstock](https://img.shields.io/badge/vnstock-3.4.0-green.svg)](https://github.com/thinh-vu/vnstock)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)

[Quick Start](#-quick-start) • [Features](#-features) • [Documentation](#-documentation) • [Architecture](#-architecture)

</div>

---

## 🎯 **Overview**

Stock4N phân tích **100 mã cổ phiếu VN100** (VN30 + VNMidcap) với chiến lược **Defensive Swing Trading** (1-3 tháng), kết hợp:

- **60% Fundamental Analysis**: ROE, profit growth, financial health
- **40% Technical Analysis**: RSI, SMA trends, volume patterns
- **AI-Powered Insights**: Market breadth, pattern recognition, ML predictions

**Target Audience**: Nhà đầu tư cá nhân với khẩu vị rủi ro thấp-trung bình, vốn 50-200 triệu VND.

---

## ✨ **Features**

### **Core Features**

✅ **100 Stock Universe** — VN100 Index coverage (95%+ market cap)
✅ **Multi-Source Data** — KBS, VCI, TCBS fallback (vnstock 3.4.0)
✅ **Dual Analysis** — 60% fundamental + 40% technical scoring
✅ **Smart Portfolio** — Top 8 stocks, 100M capital allocation
✅ **Risk Management** — -7% stop loss, +15% target (1:2 R/R)
✅ **Modern Dashboard** — Next.js web UI with real-time charts
✅ **Production Ready** — Docker, logging, validation, retry logic

### **Advanced Features**

🧠 **Market Breadth Analysis** — Advance/decline ratio, sector strength
📈 **Backtesting Engine** — Historical performance simulation
🤖 **ML Predictions** — Random Forest, Gradient Boosting models
🔄 **Adaptive Learning** — Pattern detection & weight optimization

---

## 🚀 **Quick Start**

### **Prerequisites**

- Docker & Docker Compose
- [FREE Vnstock API Key](https://vnstocks.com/login) (60 req/min)
- 8GB RAM, 2GB disk space

### **Setup (5 minutes)**

```bash
# 1. Clone repository
git clone https://github.com/your-username/Stock4N.git
cd Stock4N

# 2. Configure environment
cp .env.example .env
# Edit .env and add your VNSTOCK_API_KEY

# 3. Start services
docker-compose up -d

# 4. Register Vnstock API key
docker exec -it stock4n_app python vnstock_register.py
# Paste your API key when prompted

# 5. Run full pipeline
docker exec stock4n_app python src/main.py all
# Takes ~7-8 minutes for 100 stocks

# 6. Access dashboard
# Frontend: http://localhost:3000
```

### **One-Command Automation**

```bash
# Windows
run_all.bat

# Linux/Mac
./run_all.sh
```

This will:
1. Start Docker containers
2. Run data pipeline (ingestion → analysis → portfolio)
3. Export results to web dashboard
4. Git commit & push (optional)

---

## 📋 **Configuration**

### **Current Setup**

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Stock Universe** | 100 stocks | VN100 Index (VN30 + VNMidcap) |
| **Capital** | 100,000,000 VND | 100 triệu (configurable) |
| **Max Positions** | 8 stocks | 5-20% per position |
| **Cash Reserve** | 25% | 25 triệu buffer |
| **Holding Period** | 1-3 months | Swing trading |
| **Stop Loss** | -7% | Risk management |
| **Target** | +15% | Risk/reward 1:2.14 |

### **Data Sources (Priority Order)**

1. **KBS** — Primary (vnstock 3.4.0+)
2. **VCI** — Fallback #1
3. **TCBS** — Fallback #2
4. **MSN** — Fallback #3 (price only)

### **API Rate Limits**

| Tier | Requests/min | Financial Data | Cost |
|------|--------------|----------------|------|
| Guest | 20 | 4 quarters | Free |
| **Community** (recommended) | **60** | **8 quarters** | **Free** ✅ |
| Sponsor | 180-300 | Unlimited | Paid |

**Register FREE Community tier**: https://vnstocks.com/login

---

## 🏗️ **Architecture**

### **Pipeline Flow**

```
┌─────────────────────────────────────────────────┐
│         100 VN100 Stocks (HOSE)                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  1. INGESTION (~6 min)                          │
│  • Fetch price data (KBS/VCI/TCBS)              │
│  • Fetch financial reports (8 quarters)         │
│  • Cache & validate                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  2. PROCESSING (~30 sec)                        │
│  • Calculate ROE, ROA, EPS growth               │
│  • Debt/Equity, Asset growth                    │
│  • Technical indicators (RSI, SMA)              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  3. ANALYSIS (~45 sec)                          │
│  • Market breadth check (auto)                  │
│  • Fundamental scoring (60%)                    │
│  • Technical scoring (40%)                      │
│  • Total score: 0-10                            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  4. PORTFOLIO (~5 sec)                          │
│  • Select top 8 stocks (score >= 6.5)           │
│  • Allocate 100M capital                        │
│  • Position sizing (5-20%)                      │
│  • Risk management rules                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  5. EXPORT (~2 sec)                             │
│  • Generate db.json                             │
│  • Sync to frontend                             │
└─────────────────────────────────────────────────┘
```

**Total Pipeline Time**: ~7-8 minutes (with FREE API key)

### **Tech Stack**

**Backend**:
- Python 3.10 + pandas, numpy, TA-Lib
- vnstock 3.4.0 (KBS data source)
- Docker (stock-advisor service)

**Frontend**:
- Next.js 15 + React + TypeScript
- TailwindCSS + Recharts
- Static generation (SSG)

**Data**:
- CSV cache (local)
- JSON export (db.json)
- No database required

---

## 📚 **Documentation**

### **Root Documentation**

- [README.md](README.md) — This file (main overview)
- [QUICK_START.md](QUICK_START.md) — Getting started guide
- [CONFIGURATION.md](CONFIGURATION.md) — Detailed configuration
- [VNSTOCK_UPGRADE_GUIDE.md](VNSTOCK_UPGRADE_GUIDE.md) — Vnstock 3.4.0 upgrade

### **Advanced Guides** (`docs/`)

- [BACKTESTING_GUIDE.md](docs/BACKTESTING_GUIDE.md) — Strategy backtesting
- [LEARNING_GUIDE.md](docs/LEARNING_GUIDE.md) — Pattern learning & optimization
- [ML_PREDICTION_GUIDE.md](docs/ML_PREDICTION_GUIDE.md) — Machine learning models
- [DEPLOYMENT_STRATEGY.md](docs/DEPLOYMENT_STRATEGY.md) — Production deployment
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Common issues & fixes
- [PROJECT_BLUEPRINT.md](docs/PROJECT_BLUEPRINT.md) — Original architecture design

---

## 🔧 **Usage**

### **Command-Line Interface**

```bash
# Individual stages
python src/main.py ingestion    # Fetch data
python src/main.py processing   # Calculate metrics
python src/main.py analysis     # Score stocks
python src/main.py portfolio    # Generate recommendations
python src/main.py export       # Export JSON

# Full pipeline
python src/main.py all          # Run all stages

# Advanced
python src/main.py backtest --capital 100000000 --days 365
python src/main.py learn --learn-mode all
python src/main.py ml_predict --ml-mode train
```

### **Automation Scripts**

**Windows**:
```bash
run_all.bat          # Full pipeline + deploy
run_ingestion.bat    # Data only
run_analysis.bat     # Analysis only
```

**Linux/Mac**:
```bash
./run_all.sh         # Full pipeline + deploy
./run_ingestion.sh   # Data only
./run_analysis.sh    # Analysis only
```

---

## 📊 **Portfolio Example**

### **Sample Output (100M VND Capital)**

```
══════════════════════════════════════════════════════════
💼 STOCK4N PORTFOLIO RECOMMENDATION
══════════════════════════════════════════════════════════

Analysis Date: 2026-02-25
Total Capital: 100,000,000 VND
Market Breadth: ✅ POSITIVE (60/40 advance/decline)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top 8 Stocks (from 100 analyzed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Symbol  Score  Sector        Weight   Capital      Stop    Target
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VCB     7.8    Banking       12%      12,000,000   -7%     +15%
HPG     7.5    Steel         10%      10,000,000   -7%     +15%
FPT     7.3    Technology    10%      10,000,000   -7%     +15%
GAS     7.1    Energy         9%       9,000,000   -7%     +15%
VNM     6.9    Consumer       8%       8,000,000   -7%     +15%
VHM     6.8    Real Estate    8%       8,000,000   -7%     +15%
TCB     6.7    Banking        7%       7,000,000   -7%     +15%
MSN     6.6    Conglomerate   6%       6,000,000   -7%     +15%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Allocation:
  Invested:     70,000,000 VND (70%)
  Cash Reserve: 30,000,000 VND (30%)

Diversification: 6 sectors represented
Expected R/R: 1:2.14 (risk 7%, reward 15%)

══════════════════════════════════════════════════════════
```

---

## 🎓 **Trading Strategy**

### **Defensive Swing Trading**

**Philosophy**: Bảo toàn vốn > Tối đa lợi nhuận

**Entry Criteria**:
- ✅ Score >= 6.5 (6.5-7.0: Buy Probe, 7.0+: Strong Buy)
- ✅ Market breadth positive (advance/decline > 50%)
- ✅ Sector not overbought
- ✅ Technical confirmation (RSI, SMA crossover)

**Position Sizing**:
- Max 20% per position (diversification)
- Min 5% per position (meaningful allocation)
- 25% cash reserve (opportunities + safety)

**Exit Rules**:
- **Stop Loss**: -7% (protect capital)
- **Target**: +15% (lock profits)
- **Time-based**: Re-evaluate after 3 months
- **Score-based**: Sell if score drops below 5.0

**Risk Management**:
- Portfolio max drawdown: -10%
- Max correlation between positions: 0.7
- Sector max allocation: 40%

---

## 🛠️ **Development**

### **Project Structure**

```
Stock4N/
├── src/
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration
│   ├── modules/
│   │   ├── ingestion/             # Data fetching
│   │   ├── processing/            # Metrics calculation
│   │   ├── analysis/              # Stock scoring
│   │   ├── portfolio/             # Portfolio management
│   │   ├── simulation/            # Backtesting
│   │   ├── learning/              # ML & optimization
│   │   └── utils/                 # Utilities
├── frontend/                      # Next.js web app
├── data/                          # Data storage
│   ├── raw/                       # CSV cache
│   ├── processed/                 # Processed data
│   └── export/                    # db.json output
├── docs/                          # Advanced documentation
├── scripts/                       # Helper scripts
├── docker-compose.yml             # Docker orchestration
└── requirements.txt               # Python dependencies
```

### **Adding New Features**

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Implement in relevant module
# src/modules/your_module/

# 3. Add tests (if applicable)
# tests/test_your_module.py

# 4. Update documentation
# docs/YOUR_FEATURE_GUIDE.md

# 5. Test locally
docker-compose build --no-cache
docker exec stock4n_app python src/main.py all

# 6. Commit & push
git add .
git commit -m "feat: Your feature description"
git push origin feature/your-feature
```

---

## 🐛 **Troubleshooting**

### **Common Issues**

**1. API Rate Limit Exceeded**
```bash
# Solution: Register FREE API key
docker exec -it stock4n_app python vnstock_register.py
```

**2. Docker Build Fails**
```bash
# Clear cache and rebuild
docker-compose down
docker system prune -a
docker-compose build --no-cache
```

**3. Frontend Not Loading**
```bash
# Check if db.json exists
ls -lh frontend/public/data/db.json

# Re-export data
docker exec stock4n_app python src/main.py export
python scripts/sync_data.py
```

**4. Slow Ingestion (15+ minutes)**
```bash
# Verify API key is set
docker exec stock4n_app python -c "import os; print(os.environ.get('VNSTOCK_API_KEY'))"

# Should NOT be None
```

More troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 🤝 **Contributing**

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### **Code Style**

- Python: PEP 8 (use `black` formatter)
- JavaScript/TypeScript: Prettier + ESLint
- Commits: Conventional Commits format

---

## 📄 **License**

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **vnstock** by [@thinh-vu](https://github.com/thinh-vu) — Vietnamese stock data API
- **TA-Lib** — Technical analysis library
- **Next.js** — React framework
- **Vietnamese Stock Market Community** — Data sources & insights

---

## 📞 **Support**

- 📧 **Issues**: [GitHub Issues](https://github.com/your-username/Stock4N/issues)
- 📚 **Documentation**: [docs/](docs/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-username/Stock4N/discussions)

---

<div align="center">

**Made with ❤️ for Vietnamese Stock Market Investors**

[⬆ Back to Top](#-stock4n---ai-powered-vietnamese-stock-advisor)

</div>
