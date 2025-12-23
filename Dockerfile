# Sử dụng Python 3.10 slim (nhẹ, ổn định)
FROM python:3.10-slim

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Ho_Chi_Minh

# Cài đặt các gói hệ thống cần thiết
# Thêm wget để tải source code TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# --- CÀI ĐẶT THƯ VIỆN C CỦA TA-LIB (QUAN TRỌNG) ---
# Bước này biên dịch thư viện gốc để Python có thể sử dụng
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
# Nâng cấp pip và cài đặt thư viện
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Mở port mặc định của Streamlit (cho Phase 2)
EXPOSE 8501

# Lệnh mặc định: Giữ container chạy để ta vào gõ lệnh
CMD ["tail", "-f", "/dev/null"]