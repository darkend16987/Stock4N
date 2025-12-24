#!/usr/bin/env python3
"""
Script tự động đồng bộ db.json từ backend sang frontend
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

# Đường dẫn
BASE_DIR = Path(__file__).parent.parent
BACKEND_DB = BASE_DIR / "data" / "export" / "db.json"
FRONTEND_DB = BASE_DIR / "frontend" / "public" / "data" / "db.json"

def sync_db_json():
    """Copy db.json từ backend sang frontend"""
    try:
        # Kiểm tra file backend tồn tại
        if not BACKEND_DB.exists():
            print(f"❌ Backend db.json không tồn tại: {BACKEND_DB}")
            return False

        # Tạo thư mục frontend nếu chưa có
        FRONTEND_DB.parent.mkdir(parents=True, exist_ok=True)

        # Lấy kích thước file
        backend_size = BACKEND_DB.stat().st_size

        # Copy file
        shutil.copy2(BACKEND_DB, FRONTEND_DB)

        # Xác nhận
        frontend_size = FRONTEND_DB.stat().st_size

        print(f"✓ Đã sync db.json thành công!")
        print(f"  Backend:  {BACKEND_DB} ({backend_size:,} bytes)")
        print(f"  Frontend: {FRONTEND_DB} ({frontend_size:,} bytes)")
        print(f"  Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return True

    except Exception as e:
        print(f"❌ Lỗi khi sync db.json: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 ĐỒNG BỘ DỮ LIỆU BACKEND → FRONTEND")
    print("=" * 60)

    success = sync_db_json()

    if success:
        print("\n✅ Hoàn tất! Frontend sẽ có dữ liệu mới.")
    else:
        print("\n❌ Thất bại! Kiểm tra lại đường dẫn.")

    print("=" * 60)
