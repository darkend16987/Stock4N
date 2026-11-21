# Phase 4 - ML: kiểm định ngoài mẫu có purge, mục tiêu 20 phiên

Mục tiêu: trả lời trung thực "ML có dự báo được mã nào vượt thị trường trong 20 phiên tới, đủ bù chi phí, ngoài mẫu,
và tốt hơn baseline động lượng đơn giản không?". Cho tới khi verdict = `HAS_EDGE`, ML chỉ là thông tin tham khảo và
**không được** đưa vào điểm số, quy tắc cứng hay danh mục.

## Lỗi tìm thấy trong ML cũ (đã đọc code, đã kiểm chứng)

| # | Lỗi | Hậu quả | Xử lý |
|---|---|---|---|
| 1 | `get_latest_features()` gọi `prepare_ml_dataset()` rồi `dropna()` → bỏ `horizon` dòng cuối (chưa có nhãn) | Dự đoán "mới nhất" dùng đặc trưng cũ hàng tuần (trên dữ liệu thật: dòng cuối 2026-01-23 thay vì 2026-02-27 khi horizon 20) | Tính đặc trưng trực tiếp đến hôm nay |
| 2 | `train_test_split` ngẫu nhiên + `stratify` trên dữ liệu chuỗi thời gian gộp nhiều mã | Nhãn các ngày kề nhau chồng lấn; các mã cùng ngày chịu chung cú sốc → độ chính xác bị thổi phồng | Chia theo thời gian có purge (`purged_cv.py`); chia ngẫu nhiên chỉ còn khi không có cột `time`, kèm cảnh báo |
| 3 | Đặc trưng phụ thuộc mức giá (`sma_*`, `momentum_*` dạng hiệu giá, `volume_*` tuyệt đối) | Giá/khối lượng tuyệt đối làm lộ danh tính mã và thời kỳ | Bộ đặc trưng mới của `research.py` toàn tỷ lệ, rồi xếp hạng theo ngày |
| 4 | Horizon mặc định 5 phiên, ngưỡng 2% | Lệch với chiến lược nắm giữ 1-3 tháng | Mặc định `--horizon 20 --threshold 0.05` |
| 5 | `classification_report` giả định đủ 3 lớp | Lỗi khi tập test thiếu lớp (xảy ra khi chia theo thời gian) | `labels` cố định, `zero_division=0` |

Bộ đặc trưng cũ (dùng cho model đã lưu) giữ nguyên để không phá `ml_predict`; chỉ sửa lỗi 1, 2, 4, 5.
Mô hình cũ nên huấn luyện lại (`ml_predict --ml-mode train`) vì cách chia và horizon đã đổi.

## Kiểm định (`python src/main.py ml_validate`)

- Panel ngày × mã; đặc trưng = tỷ lệ không phụ thuộc mức giá → **xếp hạng phần trăm theo từng ngày** (loại chế độ chung).
- Nhãn = lợi suất 20 phiên trừ trung vị universe cùng ngày (trung hòa thị trường), `y = vượt trung vị`.
- Walk-forward mở rộng dần, 5 khối test, **purge 20 phiên** giữa train và test.
- Chỉ số: Spearman IC theo ngày; lợi suất vượt của nhóm 20% mã xếp cao nhất; KTC 95% bằng block bootstrap (block 20).
- So với baseline động lượng (`ret_60`) và ngẫu nhiên.

Điều kiện `HAS_EDGE` (đề xuất, `config.ML_VALIDATION`), tất cả phải đạt:
1. ≥ 250 ngày ngoài mẫu (≥ ~1 năm test), ≥ 10 mã/ngày.
2. Cận dưới KTC95 của IC trung bình > 0.
3. Cận dưới KTC95 của lợi suất vượt nhóm top **> chi phí khứ hồi** (0,6% = 2×phí + thuế + 2×trượt giá).
4. IC trung bình của ML > IC của baseline động lượng.

`NO_EDGE` khi IC không dương rõ ràng; thiếu mẫu/số liệu → `INCONCLUSIVE`. Báo cáo: `data/ml_models/validation_report.json`.
`ml_predict --ml-mode predict` in cảnh báo "CHƯA ĐƯỢC XÁC THỰC" nếu verdict khác `HAS_EDGE`.

## Kiểm tra bằng dữ liệu tổng hợp (trong test)

| Kịch bản | Kết quả |
|---|---|
| Nhiễu thuần (3 seed) | không bao giờ ra `HAS_EDGE`; KTC của IC chứa 0 hoặc gần 0 |
| Có tín hiệu bền vững cài sẵn | ML IC ≈ +0,19 [+0,11, +0,26], top vượt TB ≈ +1,7%, `HAS_EDGE` |
| Chia ngẫu nhiên cũ vs purge, trên nhiễu | ngẫu nhiên cho độ chính xác cao hơn rõ rệt (rò rỉ) |

Quan sát đáng chú ý: ngay trên nhiễu thuần, IC của baseline động lượng có lúc đạt +0,10 do ngẫu nhiên. Đó là lý do
bắt buộc dùng KTC thay vì so điểm số.

## Hạn chế

- Universe là VN100 hiện tại (thiên lệch sống sót); chỉ dùng giá/khối lượng, không có dữ liệu cơ bản point-in-time.
- 5 khối test và nhãn 20 phiên chồng lấn: KTC là ước lượng thô. Cần ≥ 250 ngày ngoài mẫu mới kết luận được.
- `HAS_EDGE` chỉ là dấu hiệu ngoài mẫu trên dữ liệu đã thấy, không đảm bảo tương lai; nên theo dõi tiếp bằng forward-test.
- Máy dev chỉ có giá của 30 mã (từ 2023-01) nên chưa thể chạy kiểm định thật (cần đủ ~98 mã).
