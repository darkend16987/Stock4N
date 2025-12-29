@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chỉ chạy Data Export
REM ==========================================

echo.
echo ==========================================
echo [5] Data Export - Xuất db.json cho web
echo ==========================================
echo.

docker-compose up -d
docker exec stock4n_app python src/main.py export

echo.
echo ✓ Hoàn tất! db.json đã được xuất vào data/export/
echo.
pause
