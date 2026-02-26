# **PROJECT BLUEPRINT: VN-STOCK INTELLIGENT ADVISOR**

## **1\. Tổng Quan Dự Án (Project Overview)**

### **1.1. Ý Tưởng & Mục Đích**

Xây dựng một hệ thống **Trợ lý đầu tư chứng khoán (Investment Advisor)** tự động, phục vụ nhà đầu tư cá nhân có khẩu vị rủi ro thấp/trung bình. Hệ thống tập trung vào **quản trị danh mục** và tìm kiếm cơ hội đầu tư **trung hạn (1-3 tháng)** dựa trên dữ liệu thực tế (Data-Driven) và các học thuyết kiểm chứng.

### **1.2. Đối Tượng Mục Tiêu**

* **Vốn hóa:** VN100 (VN30 \+ Midcap).  
* **Phong cách:** Defensive Swing Trading (Đầu tư phòng thủ).  
* **Kỳ vọng:** Lợi nhuận ổn định, ưu tiên bảo toàn vốn.

## **2\. Kiến Trúc Hệ Thống (System Architecture)**

Hệ thống thiết kế theo mô hình **Modular Monolith**, gồm 5 Module chính:

### **Module 1: Data Ingestion (Thu thập dữ liệu) \- *Core***

* **Công nghệ:** vnstock (v3.x).  
* **Nguồn dữ liệu:**  
  * *Giá/Volume:* TCBS/DNSE.  
  * *Tài chính (BCTC):* TCBS (chuẩn hóa).  
  * *Hồ sơ:* VCI.  
* **Chức năng:** Tải dữ liệu, Lưu cache cục bộ (CSV/Parquet), Kiểm tra lỗi (Data Validation).

### **Module 2: Data Processing (Xử lý & Làm sạch)**

* **Nhiệm vụ:** Tính toán chỉ số tài chính dẫn xuất (P/E lịch sử, Tăng trưởng kép), Xử lý dữ liệu thiếu (Imputation).

### **Module 3: Analysis Engine (Bộ não phân tích)**

* **Fundamental Scorer:** Piotroski F-Score (Modified), Magic Formula.  
* **Technical Scorer:** Trend (MA), Momentum (RSI), Volume Analysis.  
* **Confidence Scorer:** Đánh giá độ tin cậy của dữ liệu đầu vào.

### **Module 4: Portfolio Manager (Quản lý danh mục)**

* **Nhiệm vụ:** Phân bổ tỷ trọng (Position Sizing), Kiểm soát rủi ro (Risk Management), Cảnh báo sớm.

### **Module 5: Presentation (Giao diện)**

* **Output:** Báo cáo Terminal (Phase 1), Streamlit Dashboard (Phase 2), Telegram Alert.

## **3\. Logic Flow (Luồng Dữ Liệu)**

graph TD  
    A\[Start: List VN100\] \--\> B\[Module 1: Data Loader\]  
    B \--\>|Fetch & Cache| C\[Raw Data Store\]  
    C \--\> D\[Module 2: Processor\]  
    D \--\>|Clean & Calculate| E\[Structured Data\]  
    E \--\> F\[Module 3: Scoring Engine\]  
    F \--\>|Analyze| G{Score \> Threshold?}  
    G \-- Yes \--\> H\[Module 4: Portfolio logic\]  
    G \-- No \--\> I\[Discard/Watchlist\]  
    H \--\> J\[Final Recommendation\]

## **4\. Lộ Trình Thực Hiện (Step-by-Step)**

* **Bước 1 (Hôm nay):** Xây dựng **Module 1 (Data Ingestion)**.  
  * Tạo class VNStockLoader để quản lý việc gọi API.  
  * Tạo cơ chế lưu trữ file CSV để hạn chế gọi API nhiều lần.  
* **Bước 2:** Xây dựng Module 2 & 3 (Processing & Scoring).  
* **Bước 3:** Xây dựng Module 4 (Portfolio).  
* **Bước 4:** Tích hợp và chạy thử nghiệm (Backtest/Dry Run).