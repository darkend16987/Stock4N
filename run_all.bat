@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chạy toàn bộ pipeline
REM ==========================================

echo.
echo ==========================================
echo Stock4N - VN Stock Intelligent Advisor
echo ==========================================
echo.

REM Bước 1: Khởi động Docker container
echo [1/6] Khởi động Docker container...
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Không thể khởi động Docker!
    pause
    exit /b 1
)
echo ✓ Docker container đã khởi động
echo.

REM Bước 2: Chạy data pipeline
echo [2/6] Đang chạy data pipeline (ingestion, processing, analysis)...
docker exec stock4n_app python src/main.py all
if errorlevel 1 (
    echo ERROR: Pipeline thất bại!
    pause
    exit /b 1
)
echo ✓ Data pipeline hoàn tất
echo.

REM Bước 3: Đồng bộ db.json sang frontend
echo [3/6] Đồng bộ db.json sang frontend...
python scripts/sync_data.py
if errorlevel 1 (
    echo ERROR: Không thể đồng bộ dữ liệu!
    pause
    exit /b 1
)
echo ✓ Dữ liệu đã được đồng bộ
echo.

REM Bước 4: Git add
echo [4/6] Chuẩn bị commit thay đổi...
git add frontend/public/data/db.json
git add data/export/db.json
echo ✓ Đã add các file cần thiết
echo.

REM Bước 5: Git commit
echo [5/6] Commit thay đổi...
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a:%%b)
git commit -m "Update data: %mydate% %mytime%"
echo ✓ Đã commit
echo.

REM Bước 6: Git push
echo [6/6] Đẩy lên GitHub...
git push
if errorlevel 1 (
    echo WARNING: Push thất bại. Vui lòng kiểm tra kết nối mạng.
    echo Bạn có thể thử lại bằng lệnh: git push
)
echo.

echo ==========================================
echo ✅ HOÀN TẤT!
echo ==========================================
echo.
echo Tiếp theo:
echo 1. Vercel sẽ tự động deploy frontend mới (khoảng 1-2 phút)
echo 2. Truy cập website để xem dữ liệu cập nhật
echo.
echo Các lệnh riêng lẻ:
echo - run_ingestion.bat    : Chỉ lấy dữ liệu
echo - run_analysis.bat     : Chỉ phân tích
echo - run_sync.bat         : Chỉ đồng bộ frontend
echo.
pause
