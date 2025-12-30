@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - ML Model Training
REM Train machine learning models
REM ==========================================

echo.
echo ============================================
echo    Stock4N - ML Model Training
echo ============================================
echo.
echo Training Random Forest model to predict trends...
echo.

REM Train model
echo [1/1] Training model...
docker exec stock4n_app python src/main.py ml_predict --ml-mode train --model-type random_forest --horizon 5 --threshold 0.02

echo.
echo ============================================
echo    Hoàn tất!
echo ============================================
echo.
echo Model đã được lưu tại:
echo   - data/ml_models/trend_classifier/latest/
echo.
echo Để generate predictions, chạy:
echo   run_ml_predict.bat
echo.
pause
