@echo off
REM ==========================================
REM Stock4N - Chỉ đồng bộ db.json sang frontend
REM ==========================================

echo.
echo ==========================================
echo [6] Sync Data - Đồng bộ db.json sang frontend
echo ==========================================
echo.

python scripts/sync_data.py

echo.
echo ✓ Hoàn tất! Frontend đã có dữ liệu mới.
echo   Nhớ commit và push để deploy lên Vercel:
echo   git add frontend/public/data/db.json
echo   git commit -m "Update data"
echo   git push
echo.
pause
