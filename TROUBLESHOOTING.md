# 🚨 Hướng Dẫn Khắc Phục - Troubleshooting

## ❌ Vấn Đề 1: Vercel Vẫn Hiển Thị 0 Data

### Nguyên Nhân
- Vercel đang deploy (cần 1-3 phút)
- Vercel cache chưa clear
- Deployment không tự động trigger

### ✅ Giải Pháp

#### Bước 1: Kiểm tra Vercel Deployment

1. Mở Vercel Dashboard: https://vercel.com/dashboard
2. Chọn project **Stock4N**
3. Xem tab **Deployments**
4. Kiểm tra deployment mới nhất:
   - ✅ **Ready** = Deploy thành công
   - 🔄 **Building** = Đang deploy (đợi thêm)
   - ❌ **Failed** = Deploy thất bại (xem logs)

#### Bước 2: Force Redeploy (Nếu Cần)

```bash
# Tạo commit trống để trigger deploy
git commit --allow-empty -m "Trigger Vercel redeploy"
git push origin main
```

#### Bước 3: Clear Browser Cache

- **Chrome/Edge**: `Ctrl + Shift + R` (Hard Refresh)
- **Firefox**: `Ctrl + F5`
- Hoặc mở **Incognito/Private Mode**

#### Bước 4: Kiểm tra File Trực Tiếp

Mở URL này trong browser để xem db.json:
```
https://YOUR-VERCEL-URL/data/db.json
```

Thay `YOUR-VERCEL-URL` bằng URL Vercel của bạn (vd: `stock4n.vercel.app`)

**Kết quả mong đợi**:
- File JSON hiển thị với `"last_updated": "2025-12-24 10:27:06"`
- `"analysis"` array có 50 items
- `"portfolio"` array có 11 items

**Nếu thấy file cũ (timestamp cũ hoặc empty)**:
→ Vercel chưa deploy version mới → Force redeploy (Bước 2)

---

## ❌ Vấn Đề 2: Streamlit Dashboard Không Chạy

### Nguyên Nhân
- Streamlit chưa được cài đặt ở máy local Windows
- Python dependencies thiếu

### ✅ Giải Pháp

#### Cách 1: Dùng Setup Script (Khuyên Dùng)

```bash
# Bước 1: Chạy setup (chỉ 1 lần)
setup_venv.bat

# Bước 2: Chạy dashboard
run_dashboard_venv.bat
```

#### Cách 2: Cài Đặt Thủ Công

```bash
# 1. Tạo virtual environment
python -m venv venv

# 2. Kích hoạt
venv\Scripts\activate.bat

# 3. Cài packages
pip install streamlit pandas plotly openpyxl

# 4. Chạy dashboard
streamlit run app_streamlit.py
```

#### Cách 3: Dùng Docker (Nếu Không Muốn Setup Local)

```bash
# Tạo Dockerfile mới cho Streamlit
# (Tôi có thể tạo nếu bạn muốn)
```

---

## ❌ Vấn Đề 3: Import Error "No module named 'streamlit'"

### Giải Pháp

```bash
# Đảm bảo venv đã được kích hoạt
venv\Scripts\activate.bat

# Kiểm tra pip đang dùng
where pip

# Nên thấy: D:\GitHub\Stock4N\venv\Scripts\pip.exe

# Cài lại streamlit
pip install --upgrade streamlit
```

---

## ❌ Vấn đề 4: "ERR_EMPTY_RESPONSE" khi mở localhost:8501

### Nguyên Nhân
- Streamlit server chưa start
- Port 8501 đang bị chiếm

### Giải Pháp

```bash
# 1. Kiểm tra port 8501 có bị chiếm không
netstat -ano | findstr :8501

# 2. Nếu có process, kill nó
taskkill /PID <PID_NUMBER> /F

# 3. Chạy lại dashboard
run_dashboard_venv.bat
```

---

## 🔍 Debug Checklist

### Kiểm tra Docker
```bash
docker ps
# Phải thấy: stock4n_app (Up X minutes)
```

### Kiểm tra Data Files
```bash
# Backend có db.json không?
dir data\export\db.json

# Frontend có db.json không?
dir frontend\public\data\db.json

# Kích thước file phải ~800KB
```

### Kiểm tra Git Branch
```bash
# Đang ở branch nào?
git branch

# Main branch có commit mới nhất không?
git log origin/main --oneline -3
```

---

## 🚀 Quick Fixes

### Fix 1: Vercel Không Cập Nhật
```bash
# Trigger redeploy
git commit --allow-empty -m "Redeploy"
git push origin main
```

### Fix 2: Streamlit Không Chạy
```bash
# Setup lại từ đầu
setup_venv.bat
run_dashboard_venv.bat
```

### Fix 3: Dữ Liệu Không Đồng Bộ
```bash
# Sync lại frontend
run_sync.bat

# Commit và push
git add frontend/public/data/db.json
git commit -m "Update db.json"
git push origin main
```

---

## 📞 Nếu Vẫn Không Được

### Thu Thập Thông Tin Debug

```bash
# 1. Kiểm tra Python version
python --version

# 2. Kiểm tra pip version
pip --version

# 3. Kiểm tra streamlit
streamlit --version

# 4. Kiểm tra db.json content
python -c "import json; print(json.load(open('frontend/public/data/db.json'))['metadata'])"

# 5. Kiểm tra git status
git status
git log --oneline -3
```

### Check Vercel Logs

1. Vào Vercel Dashboard → Project → Deployments
2. Click vào deployment mới nhất
3. Xem tab **Build Logs**
4. Tìm errors (nếu có)

---

## ✅ Expected Results

### Streamlit Dashboard
- URL: `http://localhost:8501`
- Hiển thị: Dashboard với 50 stocks, 11 portfolio positions
- Có nút: "Chạy Tất Cả", "Ingestion", "Processing", etc.

### Vercel Website
- URL: `https://YOUR-DOMAIN.vercel.app`
- Last Updated: `2025-12-24 10:27:06` (hoặc mới hơn)
- Total Stocks: **50**
- Buy Signals: **15**
- Portfolio Positions: **11**

---

## 💡 Tips

1. **Luôn check Vercel deployment status** trước khi báo lỗi
2. **Hard refresh browser** (`Ctrl + Shift + R`) sau mỗi lần deploy
3. **Dùng Streamlit dashboard** cho local testing (nhanh hơn Vercel)
4. **Chạy `run_all.bat`** hàng ngày để cập nhật dữ liệu
5. **Commit và push** sau khi có dữ liệu mới để trigger Vercel deploy

---

## 🎯 Test Cases

### Test 1: Backend Pipeline
```bash
run_all.bat
# Expected: Success 50/50 symbols
```

### Test 2: Frontend Sync
```bash
run_sync.bat
# Expected: File size ~800KB
```

### Test 3: Streamlit
```bash
run_dashboard_venv.bat
# Expected: Open http://localhost:8501
```

### Test 4: Vercel
```
https://YOUR-DOMAIN.vercel.app/data/db.json
# Expected: JSON with 50 analysis items
```

---

**Last Updated**: 2025-12-24
