@echo off
chcp 65001 >nul
REM ==========================================
REM Stock4N - Install ML Dependencies
REM Cài đặt scikit-learn và joblib
REM ==========================================

echo.
echo ============================================
echo    Stock4N - Installing ML Dependencies
echo ============================================
echo.
echo Đang cài đặt scikit-learn và joblib...
echo.

docker exec stock4n_app pip install scikit-learn>=1.3.0 joblib

echo.
echo ============================================
echo    Hoàn tất!
echo ============================================
echo.
echo ML dependencies đã được cài đặt.
echo Giờ bạn có thể chạy:
echo   - run_all.bat
echo   - run_ml_train.bat
echo   - run_ml_predict.bat
echo.
pause
