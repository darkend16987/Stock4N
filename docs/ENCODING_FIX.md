# 🔧 Fix Encoding Tiếng Việt - Windows CMD

## ✅ Đã Fix

Tất cả file `.bat` đã được cập nhật với UTF-8 encoding:

```batch
@echo off
chcp 65001 >nul    ← Dòng này fix encoding
```

## 📊 Kết Quả

### ❌ Trước khi fix:
```
Khß╗ƒi ─æß╗Öng Docker container...
Γ£ô Docker container ─æ├ú khß╗ƒi ─æß╗Öng
─Éang chß║íy data pipeline
Γ£ô Data pipeline ho├án tß║Ñt
```

### ✅ Sau khi fix:
```
Khởi động Docker container...
✓ Docker container đã khởi động
Đang chạy data pipeline
✓ Data pipeline hoàn tất
```

## 🚀 Cách Sử Dụng

### Option 1: Pull Code Mới (Khuyên dùng)

```bash
# Trên branch main
git pull origin main

# Hoặc nếu đang ở branch khác, merge PR này
```

### Option 2: Test Ngay

Chạy bất kỳ file `.bat` nào:

```bash
run_all.bat
run_dashboard.bat
run_ingestion.bat
```

Bạn sẽ thấy tiếng Việt hiển thị đúng!

## 📝 Technical Details

### Cách Fix Hoạt Động

```batch
chcp 65001 >nul
```

- `chcp` = Change Code Page (thay đổi bảng mã)
- `65001` = UTF-8 encoding
- `>nul` = Ẩn output (không hiển thị "Active code page: 65001")

### Các File Đã Fix

- ✅ `run_all.bat`
- ✅ `run_ingestion.bat`
- ✅ `run_processing.bat`
- ✅ `run_analysis.bat`
- ✅ `run_portfolio.bat`
- ✅ `run_export.bat`
- ✅ `run_sync.bat`
- ✅ `run_dashboard.bat`
- ✅ `run_dashboard_venv.bat`
- ✅ `setup_venv.bat`

## 🐛 Nếu Vẫn Lỗi

### Kiểm tra CMD Settings

1. Right-click trên CMD title bar → **Properties**
2. Vào tab **Font**
3. Chọn **Consolas** hoặc **Lucida Console**
4. OK và restart CMD

### Kiểm tra Windows Settings

```batch
# Check current code page
chcp

# Nên thấy: Active code page: 65001
```

### Alternative: Dùng Windows Terminal

Windows Terminal (PowerShell) hỗ trợ UTF-8 mặc định, không cần `chcp`.

Download: https://aka.ms/terminal

## ✨ Bonus: English Version

Nếu vẫn không được, tôi có thể tạo phiên bản tiếng Anh của tất cả `.bat` files.

## 📚 Tham Khảo

- [Microsoft Docs - chcp](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/chcp)
- [UTF-8 Code Page](https://en.wikipedia.org/wiki/UTF-8)

---

**Last Updated**: 2025-12-29
**Commit**: 9685ff6
