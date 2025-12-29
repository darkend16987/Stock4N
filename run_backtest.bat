@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Backtest Strategy
REM ==========================================

echo.
echo ==========================================
echo [Backtest] Test Chiến Lược Trên Lịch Sử
echo ==========================================
echo.

REM Khởi động Docker
docker-compose up -d

REM Chạy backtest
echo Đang chạy backtest...
echo Parameters:
echo - Lookback: 365 days (1 year)
echo - Min Score: 6.0
echo - Capital: 100,000,000 VND
echo.

docker exec stock4n_app python src/main.py backtest --days 365 --score 6.0 --capital 100000000

echo.
echo ✓ Hoàn tất! Kết quả đã được lưu vào data/backtest/
echo.
pause
