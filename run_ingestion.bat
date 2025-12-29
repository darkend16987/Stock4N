@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chỉ chạy Data Ingestion
REM ==========================================

echo.
echo ==========================================
echo [1] Data Ingestion - Lấy dữ liệu từ vnstock
echo ==========================================
echo.

docker-compose up -d
docker exec stock4n_app python src/main.py ingestion

echo.
echo ✓ Hoàn tất! Dữ liệu đã được lưu vào data/raw/
echo.
pause
