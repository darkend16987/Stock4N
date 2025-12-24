@echo off
REM ==========================================
REM Stock4N - Setup Python Virtual Environment
REM ==========================================

echo.
echo ==========================================
echo Stock4N - Setup Environment
echo ==========================================
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python chưa được cài đặt!
    echo Vui lòng cài Python từ: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Tạo virtual environment...
if exist venv (
    echo ✓ Virtual environment đã tồn tại
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Không thể tạo virtual environment!
        pause
        exit /b 1
    )
    echo ✓ Đã tạo virtual environment
)
echo.

echo [2/4] Kích hoạt virtual environment...
call venv\Scripts\activate.bat
echo.

echo [3/4] Cài đặt dependencies...
echo Đang cài: pandas, streamlit, plotly...
pip install -q pandas streamlit plotly openpyxl
if errorlevel 1 (
    echo ERROR: Không thể cài đặt packages!
    pause
    exit /b 1
)
echo ✓ Đã cài đặt tất cả dependencies
echo.

echo [4/4] Kiểm tra cài đặt...
python -c "import streamlit; import pandas; import plotly; print('✓ All packages OK')"
echo.

echo ==========================================
echo ✅ SETUP HOÀN TẤT!
echo ==========================================
echo.
echo Bây giờ bạn có thể:
echo 1. Chạy Streamlit dashboard: run_dashboard_venv.bat
echo 2. Hoặc tự kích hoạt venv: venv\Scripts\activate.bat
echo.
pause
