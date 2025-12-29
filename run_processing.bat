@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chỉ chạy Data Processing
REM ==========================================

echo.
echo ==========================================
echo [2] Data Processing - Tính toán chỉ số tài chính
echo ==========================================
echo.

docker-compose up -d
docker exec stock4n_app python src/main.py processing

echo.
echo ✓ Hoàn tất! Dữ liệu đã được xử lý vào data/processed/
echo.
pause
