@echo off
REM ==========================================
REM Stock4N - Streamlit Interactive Dashboard
REM ==========================================

echo.
echo ==========================================
echo Stock4N - Streamlit Dashboard
echo ==========================================
echo.
echo Đang khởi động dashboard...
echo Dashboard sẽ tự động mở trên browser: http://localhost:8501
echo.
echo Để dừng: Nhấn Ctrl+C
echo.

REM Khởi động Docker trước
docker-compose up -d

REM Chạy Streamlit
streamlit run app_streamlit.py --server.port 8501 --server.headless false
