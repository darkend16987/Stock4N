# 📚 Stock4N Documentation

Advanced guides và technical documentation cho Stock4N.

---

## 📖 **Table of Contents**

### **Getting Started**
- [Quick Start Guide](../QUICK_START.md) — Hướng dẫn bắt đầu nhanh
- [Configuration Guide](../CONFIGURATION.md) — Chi tiết cấu hình hệ thống
- [Vnstock Upgrade](../VNSTOCK_UPGRADE_GUIDE.md) — Nâng cấp vnstock 3.4.0

### **Advanced Features**
- [Backtesting Guide](BACKTESTING_GUIDE.md) — Kiểm tra chiến lược với dữ liệu lịch sử
- [Learning Guide](LEARNING_GUIDE.md) — Pattern detection & weight optimization
- [ML Prediction Guide](ML_PREDICTION_GUIDE.md) — Machine Learning models

### **Operations**
- [Deployment Strategy](DEPLOYMENT_STRATEGY.md) — Production deployment
- [Troubleshooting](TROUBLESHOOTING.md) — Xử lý lỗi thường gặp

### **Reference**
- [Project Blueprint](PROJECT_BLUEPRINT.md) — Thiết kế kiến trúc ban đầu
- [Encoding Fix](ENCODING_FIX.md) — Fix encoding issues

---

## 🚀 **Quick Navigation**

### **I Want To...**

**Learn the basics**
→ Start with [Quick Start](../QUICK_START.md)

**Understand the configuration**
→ Read [Configuration Guide](../CONFIGURATION.md)

**Test my strategy**
→ See [Backtesting Guide](BACKTESTING_GUIDE.md)

**Use machine learning**
→ Follow [ML Prediction Guide](ML_PREDICTION_GUIDE.md)

**Improve performance**
→ Check [Learning Guide](LEARNING_GUIDE.md)

**Deploy to production**
→ Use [Deployment Strategy](DEPLOYMENT_STRATEGY.md)

**Fix an issue**
→ Browse [Troubleshooting](TROUBLESHOOTING.md)

---

## 📋 **Documentation Structure**

### **Root Level** (Main docs)
```
Stock4N/
├── README.md                    # Main overview
├── QUICK_START.md              # Getting started
├── CONFIGURATION.md            # System config
└── VNSTOCK_UPGRADE_GUIDE.md   # Vnstock 3.4.0
```

### **docs/** (Advanced guides)
```
docs/
├── README.md                   # This file
├── BACKTESTING_GUIDE.md       # Strategy testing
├── LEARNING_GUIDE.md          # Adaptive learning
├── ML_PREDICTION_GUIDE.md     # Machine learning
├── DEPLOYMENT_STRATEGY.md     # Production setup
├── TROUBLESHOOTING.md         # Error fixes
├── PROJECT_BLUEPRINT.md       # Original design
└── ENCODING_FIX.md            # Technical fix
```

---

## 🎯 **Documentation by Role**

### **Beginner Investor**
1. [Quick Start](../QUICK_START.md) — Setup system
2. [Configuration](../CONFIGURATION.md) — Understand settings
3. [Troubleshooting](TROUBLESHOOTING.md) — Fix common issues

### **Advanced Trader**
1. [Backtesting](BACKTESTING_GUIDE.md) — Test strategies
2. [Learning](LEARNING_GUIDE.md) — Optimize parameters
3. [ML Prediction](ML_PREDICTION_GUIDE.md) — Use AI models

### **Developer**
1. [Project Blueprint](PROJECT_BLUEPRINT.md) — Architecture
2. [Deployment](DEPLOYMENT_STRATEGY.md) — Production setup
3. Main [README](../README.md) — Development guide

---

## 📝 **Documentation Standards**

### **Guide Template**

Each guide should include:
- **Overview** — What & Why
- **Prerequisites** — Requirements
- **Usage** — Step-by-step instructions
- **Examples** — Real code examples
- **Troubleshooting** — Common issues
- **Next Steps** — What to read next

### **Code Examples**

Always include:
```bash
# Command with description
docker exec stock4n_app python src/main.py all

# Expected output
✓ Ingestion completed (100 stocks)
✓ Analysis completed
```

### **Cross-References**

Link to related docs:
- [See also: Configuration](../CONFIGURATION.md)
- [Related: Backtesting](BACKTESTING_GUIDE.md)

---

## 🔄 **Document Maintenance**

### **Update Frequency**

| Document | Update When |
|----------|-------------|
| README.md | Major feature changes |
| QUICK_START.md | Setup process changes |
| CONFIGURATION.md | Config schema changes |
| Guides (docs/) | Feature enhancements |

### **Version Control**

All docs are versioned with git:
```bash
# Check doc history
git log -- docs/BACKTESTING_GUIDE.md

# View changes
git diff HEAD~1 docs/LEARNING_GUIDE.md
```

---

## 🆘 **Need Help?**

**Can't find what you need?**

1. **Search docs**: Use GitHub search or `grep`
   ```bash
   grep -r "your-keyword" docs/
   ```

2. **Check Issues**: [GitHub Issues](https://github.com/your-username/Stock4N/issues)

3. **Ask Community**: [GitHub Discussions](https://github.com/your-username/Stock4N/discussions)

---

## 📊 **Documentation Stats**

- **Total Guides**: 8
- **Lines of Documentation**: ~5,000+
- **Code Examples**: 50+
- **Last Updated**: 2026-02-25

---

**Happy Reading!** 📖

[⬆ Back to Main README](../README.md)
