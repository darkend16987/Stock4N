@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Chạy Learning Module
REM Phân tích patterns và tối ưu weights
REM ==========================================

echo.
echo ============================================
echo    Stock4N - Learning & Optimization
echo ============================================
echo.
echo Chức năng:
echo   - Phân tích patterns (seasonality, momentum, S/R)
echo   - Tối ưu weights cho scoring
echo   - Lưu learned parameters
echo.

REM Chạy learning mode (patterns + optimization)
echo [1/1] Chạy learning module...
docker exec stock4n_app python src/main.py learn --days 365

echo.
echo ============================================
echo    Hoàn tất!
echo ============================================
echo.
echo Kết quả được lưu tại:
echo   - data/learned_params/patterns_latest.json
echo   - data/learned_params/weights_latest.json
echo   - data/processed/optimization_results.csv
echo.
pause
