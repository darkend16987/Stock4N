# 🚀 Vnstock 3.4.0 Upgrade Guide

## Tổng quan Update

Vnstock 3.4.0 mang đến **3 cải tiến lớn**:
1. **KBS Data Source** — Nguồn dữ liệu mới, mạnh nhất (thay thế VCI)
2. **API Key Authentication** — 60 req/min FREE (vs 20 guest), 8 kỳ tài chính (vs 4)
3. **Standardized Reports** — Dữ liệu chuẩn hoá, dễ xử lý hơn

---

## 📋 Checklist Nâng cấp

### ✅ Phase 1: Cập nhật Code (Done)

- [x] `requirements.txt` → vnstock 3.4.0 beta
- [x] `config.py` → KBS first priority, VNSTOCK_CONFIG
- [x] `.env.example` → VNSTOCK_API_KEY template
- [x] `vnstock_register.py` → Helper script

### 🔄 Phase 2: Deploy & Configure

```bash
# 1. Rebuild Docker container
docker-compose down
docker-compose build --no-cache

# 2. Register FREE API key
docker-compose run --rm stock-advisor python vnstock_register.py

# Hoặc add trực tiếp vào .env:
echo "VNSTOCK_API_KEY=vnstock_YOUR_KEY_HERE" >> .env

# 3. Restart services
docker-compose up -d
```

### 🧪 Phase 3: Test & Verify

```bash
# Test data ingestion với KBS
docker exec stock4n_app python src/main.py ingestion

# Verify performance improvement
# - Trước: ~20 req/min → 50 mã = ~2.5 phút
# - Sau: ~60 req/min → 50 mã = ~50 giây (3x nhanh hơn!)
```

---

## 🎁 Benefits Sau Khi Upgrade

| Metric | Before (Guest) | After (Free API) | Gain |
|--------|---------------|------------------|------|
| **Rate Limit** | 20 req/min | 60 req/min | **+200%** |
| **Financial Data** | 4 quarters | 8 quarters | **+100%** |
| **Data Source** | VCI, TCBS | **KBS**, VCI, TCBS | New source |
| **Standardization** | Basic | Enhanced | Better quality |

### Cải thiện Performance

**Ingestion Phase (50 mã):**
- **Trước**: 20 req/min → ~2.5 phút
- **Sau**: 60 req/min → ~50 giây
- **Time saved**: ~70 giây/lần chạy

**Financial Data:**
- **Trước**: 4 kỳ = 1 năm data
- **Sau**: 8 kỳ = 2 năm data
- **More context** cho fundamental analysis

---

## 🔑 Lấy API Key (FREE)

1. **Truy cập**: https://vnstocks.com/login
2. **Đăng nhập**: Google account
3. **Copy API key** từ dashboard
4. **Chọn 1 trong 2 cách**:

### Cách 1: Script tự động (Recommended)
```bash
docker exec -it stock4n_app python vnstock_register.py
# Paste API key khi được yêu cầu
```

### Cách 2: Manual config
```bash
# Thêm vào .env
echo "VNSTOCK_API_KEY=vnstock_abc123..." >> .env

# Restart container
docker-compose restart stock-advisor
```

---

## 🐛 Troubleshooting

### Issue 1: "API key not recognized"
```bash
# Verify API key format
cat .env | grep VNSTOCK

# Should start with 'vnstock_'
# Re-register if needed
```

### Issue 2: "Rate limit exceeded"
```bash
# Check if API key is loaded
docker exec stock4n_app python -c "import os; print(os.environ.get('VNSTOCK_API_KEY'))"

# If None → API key not loaded, restart container
docker-compose restart stock-advisor
```

### Issue 3: "KBS source unavailable"
```bash
# Fallback to VCI automatically (priority #2)
# Check logs:
docker logs stock4n_app --tail 50
```

---

## 📚 References

- [Vnstock 3.4.0 Changelog](https://github.com/thinh-vu/vnstock/blob/main/CHANGELOG.md)
- [Vnstock Documentation](https://vnstocks.com/docs)
- [API Key Dashboard](https://vnstocks.com/login)
- [GitHub Issues](https://github.com/thinh-vu/vnstock/issues)

---

## 🎯 Next Steps

Sau khi upgrade xong:

1. **Test pipeline**: `run_all.bat` và verify KBS data
2. **Monitor performance**: Ingestion speed should be ~3x faster
3. **Check data quality**: Financial reports should have 8 quarters
4. **Update docs**: Document new rate limits in team wiki

Happy trading! 📈
