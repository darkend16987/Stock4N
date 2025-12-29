@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chỉ chạy Portfolio Manager
REM ==========================================

echo.
echo ==========================================
echo [4] Portfolio Manager - Tạo danh mục đầu tư
echo ==========================================
echo.

docker-compose up -d
docker exec stock4n_app python src/main.py portfolio

echo.
echo ✓ Hoàn tất! Danh mục đã được lưu vào data/processed/
echo.
pause
