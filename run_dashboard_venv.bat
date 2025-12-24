@echo off
REM ==========================================
REM Stock4N - Streamlit Dashboard (với venv)
REM ==========================================

echo.
echo ==========================================
echo Stock4N - Streamlit Dashboard
echo ==========================================
echo.

REM Kiểm tra venv tồn tại
if not exist venv (
    echo ⚠️  Virtual environment chưa được tạo!
    echo Đang chạy setup...
    call setup_venv.bat
    if errorlevel 1 (
        echo ERROR: Setup thất bại!
        pause
        exit /b 1
    )
)

REM Kích hoạt venv
echo [1/2] Kích hoạt virtual environment...
call venv\Scripts\activate.bat
echo.

REM Khởi động Docker
echo [2/2] Khởi động Docker container...
docker-compose up -d
echo.

REM Chạy Streamlit
echo ==========================================
echo ✓ Đang khởi động Streamlit Dashboard...
echo ==========================================
echo.
echo Dashboard sẽ mở tại: http://localhost:8501
echo Để dừng: Nhấn Ctrl+C
echo.
streamlit run app_streamlit.py --server.port 8501 --server.headless false

pause
