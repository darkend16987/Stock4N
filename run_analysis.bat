@echo off
REM ==========================================
REM Stock4N - Chỉ chạy Market Analysis
REM ==========================================

echo.
echo ==========================================
echo [3] Market Analysis - Phân tích và chấm điểm
echo ==========================================
echo.

docker-compose up -d
docker exec stock4n_app python src/main.py analysis

echo.
echo ✓ Hoàn tất! Phân tích đã được lưu vào data/processed/
echo.
pause
