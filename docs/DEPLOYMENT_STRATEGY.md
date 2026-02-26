# Chiến Lược Deploy Frontend & Data Sync

## ❓ Vấn đề: Git với Generated Data

**Câu hỏi:** Có nên commit dữ liệu CSV, db.json lên git không?

**Trả lời ngắn gọn:**
- ❌ **CSV files** (`data/raw/*.csv`, `data/processed/*.csv`) → KHÔNG commit (đã ignore)
- ❌ **Log files** (`data/logs/*.log`) → KHÔNG commit (đã ignore)
- ✅ **config.py** → NÊN commit (đây là source code)
- ⚠️ **db.json** → TÙY CHIẾN LƯỢC (xem bên dưới)

## 🎯 Ba Chiến Lược Deploy với Vercel

### **Chiến Lược 1: Commit db.json vào Git (Đơn giản nhất)**

**Phù hợp:** MVP, demo, prototype, dự án cá nhân

**Ưu điểm:**
- ✅ Deploy đơn giản nhất
- ✅ Frontend luôn có data hiển thị
- ✅ Không cần infrastructure phức tạp
- ✅ Hoạt động ngay lập tức trên Vercel

**Nhược điểm:**
- ❌ Data bị "stale" (cũ) nếu không update thường xuyên
- ❌ Cần manual commit mỗi khi chạy algorithm
- ❌ History git lưu nhiều version của db.json

**Cách thực hiện:**

```bash
# 1. Sửa .gitignore - uncomment dòng này:
# !data/export/db.json

# 2. Copy db.json vào frontend
mkdir -p frontend/public/data/export
cp data/export/db.json frontend/public/data/export/

# 3. Commit và push
git add data/export/db.json frontend/public/data/export/db.json
git commit -m "Update analysis data"
git push

# 4. Vercel tự động rebuild
```

**Quy trình update:**
- Chạy algorithm hàng ngày/tuần
- Copy db.json mới vào frontend/public
- Commit và push
- Vercel auto-deploy (~ 2-3 phút)

---

### **Chiến Lược 2: GitHub Actions Auto-Update (Khuyến nghị)**

**Phù hợp:** Production, tự động hóa, update định kỳ

**Ưu điểm:**
- ✅ Hoàn toàn tự động
- ✅ Chạy theo schedule (mỗi ngày 5 PM)
- ✅ Data luôn fresh
- ✅ Không cần can thiệp thủ công

**Nhược điểm:**
- ⚠️ Phức tạp hơn một chút
- ⚠️ Phụ thuộc GitHub Actions (miễn phí 2000 phút/tháng)

**Cách thực hiện:**

Tạo file `.github/workflows/daily-analysis.yml`:

```yaml
name: Daily Stock Analysis & Deploy

on:
  schedule:
    # Chạy lúc 5 PM (17:00 UTC+7) mỗi ngày từ T2-T6
    - cron: '0 10 * * 1-5'  # 10:00 UTC = 17:00 UTC+7
  workflow_dispatch:  # Cho phép chạy manual

jobs:
  analyze-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Run Stock Analysis
        run: |
          docker-compose up --build

      - name: Copy Results to Frontend
        run: |
          mkdir -p frontend/public/data/export
          cp data/export/db.json frontend/public/data/export/

      - name: Commit and Push Results
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add frontend/public/data/export/db.json
          git commit -m "🤖 Auto-update analysis data $(date +'%Y-%m-%d %H:%M')" || exit 0
          git push

      # Vercel tự động deploy khi có commit mới
```

**Setup:**
```bash
# 1. Tạo workflow file
mkdir -p .github/workflows
# Copy YAML content vào đó

# 2. Commit workflow
git add .github/workflows/daily-analysis.yml
git commit -m "Add auto-update workflow"
git push

# 3. Xong! Sẽ tự chạy mỗi ngày lúc 5 PM
```

---

### **Chiến Lược 3: Backend API + Frontend Fetch (Advanced)**

**Phù hợp:** Production scale, real-time updates, nhiều clients

**Ưu điểm:**
- ✅ Data luôn real-time
- ✅ Không cần rebuild frontend
- ✅ Backend và frontend độc lập
- ✅ Có thể cache, optimize riêng

**Nhược điểm:**
- ❌ Phức tạp nhất
- ❌ Cần host backend riêng (AWS, DigitalOcean, etc.)
- ❌ Chi phí server

**Architecture:**

```
Backend (AWS/DO)        Frontend (Vercel)
┌──────────────┐       ┌──────────────┐
│ Python API   │◄──────┤ Next.js App  │
│ (FastAPI)    │ HTTPS │              │
│              │       │              │
│ /api/stocks  │       │ fetch() data │
│ /api/portfolio       │              │
└──────────────┘       └──────────────┘
      │
      ▼
  ┌─────────┐
  │ Database│
  │ (Postgres)
  └─────────┘
```

**Cách thực hiện:**

1. **Backend API** (Tạo FastAPI service):

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# CORS cho Vercel domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],
    allow_methods=["GET"],
)

@app.get("/api/stocks")
async def get_stocks():
    with open("/app/data/export/db.json") as f:
        return json.load(f)
```

2. **Frontend Update** (Fetch from API):

```typescript
// frontend/lib/data.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getStockData() {
  const res = await fetch(`${API_URL}/api/stocks`, {
    next: { revalidate: 3600 } // Cache 1 hour
  });
  return res.json();
}
```

3. **Deploy Backend:**
```bash
# AWS ECS, DigitalOcean App Platform, hoặc Railway
# Schedule cron job chạy analysis mỗi ngày
```

---

## 📊 So Sánh Các Chiến Lược

| Tiêu chí | Strategy 1<br>(Commit) | Strategy 2<br>(GitHub Actions) | Strategy 3<br>(API) |
|----------|------------------------|-------------------------------|---------------------|
| **Độ phức tạp** | ⭐ Dễ | ⭐⭐ Trung bình | ⭐⭐⭐ Khó |
| **Chi phí** | $0 | $0 | $5-20/tháng |
| **Data freshness** | Manual | Tự động (1x/ngày) | Real-time |
| **Setup time** | 5 phút | 30 phút | 2-4 giờ |
| **Maintenance** | Cao (manual) | Thấp (auto) | Trung bình |
| **Scalability** | Thấp | Trung bình | Cao |

## 🎯 Khuyến Nghị

**Cho dự án của bạn (Stock4N):**

1. **Bắt đầu với Strategy 1** (Commit db.json):
   - Deploy nhanh, test frontend
   - Uncomment `!data/export/db.json` trong .gitignore
   - Copy db.json vào `frontend/public/data/export/`
   - Commit và deploy lên Vercel

2. **Khi ổn định, chuyển sang Strategy 2** (GitHub Actions):
   - Setup workflow tự động
   - Update data mỗi ngày lúc 5 PM
   - Không cần thao tác manual

3. **Nếu scale lớn hơn, xem xét Strategy 3** (API):
   - Khi có nhiều users
   - Cần real-time data
   - Có budget cho infrastructure

## 🚀 Quick Start: Deploy Ngay Với Strategy 1

```bash
# 1. Uncomment dòng này trong .gitignore
# !data/export/db.json

# 2. Copy db.json vào frontend (nếu có)
mkdir -p frontend/public/data/export
cp data/export/db.json frontend/public/data/export/ 2>/dev/null || echo "Chạy algorithm trước để tạo db.json"

# 3. Commit tất cả
git add -A
git commit -m "Setup deployment with db.json"
git push

# 4. Deploy lên Vercel
# - Vào vercel.com
# - Import repo darkend16987/Stock4N
# - Root directory: frontend
# - Deploy!
```

## ❓ FAQ

**Q: Có ảnh hưởng gì nếu ignore db.json?**
A: Frontend sẽ không có data để hiển thị khi mới deploy. Cần sync data bằng 1 trong 3 strategies.

**Q: File nào NÊN commit?**
A:
- ✅ Source code (*.py, *.tsx, *.ts)
- ✅ Config files (config.py, package.json, tsconfig.json)
- ✅ Documentation (README.md, *.md)
- ✅ Infrastructure (Dockerfile, docker-compose.yml)
- ✅ Tests (tests/*.py)

**Q: File nào KHÔNG NÊN commit?**
A:
- ❌ Generated data (*.csv, logs)
- ❌ Dependencies (node_modules/, venv/)
- ❌ Build artifacts (.next/, dist/)
- ❌ Secrets (.env, *.pem, *.key)

**Q: db.json bao nhiêu MB? Có quá lớn không?**
A: Với 30 stocks, db.json thường ~50-200KB. Hoàn toàn OK để commit vào git.

**Q: Vercel có limit gì không?**
A:
- Free tier: 100GB bandwidth/tháng
- db.json ~100KB → có thể serve ~1M requests/tháng
- Đủ cho hầu hết use cases

---

**Tóm lại:**
- ✅ Ignore tất cả CSV files và logs
- ✅ COMMIT config.py (source code)
- ⚠️ db.json: Chọn 1 trong 3 strategies (khuyến nghị Strategy 1 để bắt đầu)
- 🚀 Không ảnh hưởng đến Vercel deployment!
