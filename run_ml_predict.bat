@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - ML Prediction
REM Generate predictions using trained model
REM ==========================================

echo.
echo ============================================
echo    Stock4N - ML Prediction
echo ============================================
echo.
echo Generating trend predictions for all stocks...
echo.

REM Generate predictions
echo [1/1] Predicting trends...
docker exec stock4n_app python src/main.py ml_predict --ml-mode predict

echo.
echo ============================================
echo    Hoàn tất!
echo ============================================
echo.
echo Predictions đã được lưu tại:
echo   - data/processed/ml_predictions.csv
echo.
pause
