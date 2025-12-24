#!/bin/bash
# ==========================================
# Stock4N - Chạy toàn bộ pipeline
# ==========================================

echo ""
echo "=========================================="
echo "Stock4N - VN Stock Intelligent Advisor"
echo "=========================================="
echo ""

# Bước 1: Khởi động Docker container
echo "[1/6] Khởi động Docker container..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "ERROR: Không thể khởi động Docker!"
    exit 1
fi
echo "✓ Docker container đã khởi động"
echo ""

# Bước 2: Chạy data pipeline
echo "[2/6] Đang chạy data pipeline (ingestion, processing, analysis)..."
docker exec stock4n_app python src/main.py all
if [ $? -ne 0 ]; then
    echo "ERROR: Pipeline thất bại!"
    exit 1
fi
echo "✓ Data pipeline hoàn tất"
echo ""

# Bước 3: Đồng bộ db.json sang frontend
echo "[3/6] Đồng bộ db.json sang frontend..."
python3 scripts/sync_data.py
if [ $? -ne 0 ]; then
    echo "ERROR: Không thể đồng bộ dữ liệu!"
    exit 1
fi
echo "✓ Dữ liệu đã được đồng bộ"
echo ""

# Bước 4: Git add
echo "[4/6] Chuẩn bị commit thay đổi..."
git add frontend/public/data/db.json
git add data/export/db.json
echo "✓ Đã add các file cần thiết"
echo ""

# Bước 5: Git commit
echo "[5/6] Commit thay đổi..."
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
git commit -m "Update data: $TIMESTAMP"
echo "✓ Đã commit"
echo ""

# Bước 6: Git push (với retry)
echo "[6/6] Đẩy lên GitHub..."
MAX_RETRIES=4
RETRY_COUNT=0
WAIT_TIME=2

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    git push
    if [ $? -eq 0 ]; then
        echo "✓ Push thành công!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Push thất bại. Thử lại lần $RETRY_COUNT sau $WAIT_TIME giây..."
            sleep $WAIT_TIME
            WAIT_TIME=$((WAIT_TIME * 2))
        else
            echo "❌ Push thất bại sau $MAX_RETRIES lần thử. Vui lòng kiểm tra kết nối mạng."
        fi
    fi
done
echo ""

echo "=========================================="
echo "✅ HOÀN TẤT!"
echo "=========================================="
echo ""
echo "Tiếp theo:"
echo "1. Vercel sẽ tự động deploy frontend mới (khoảng 1-2 phút)"
echo "2. Truy cập website để xem dữ liệu cập nhật"
echo ""
echo "Các lệnh riêng lẻ:"
echo "- ./run_ingestion.sh    : Chỉ lấy dữ liệu"
echo "- ./run_analysis.sh     : Chỉ phân tích"
echo "- ./run_sync.sh         : Chỉ đồng bộ frontend"
echo ""
