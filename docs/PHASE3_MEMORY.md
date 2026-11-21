# Phase 3 - Đối chiếu kết quả, bài học thống kê, kiểm tra sẵn sàng `enforce`

Biến sổ nhật ký của hội đồng (Phase 2) thành bằng chứng: mỗi quyết định được đối chiếu với kết quả thực sau 20 phiên,
so với benchmark, rồi quyết định có nên bật `enforce` hay không.

## Chạy

```
python src/main.py committee           # hằng ngày/tuần (shadow) → ghi ledger
python src/main.py committee_settle    # định kỳ: settle các quyết định đủ 20 phiên + báo cáo sẵn sàng
```

Kết quả: `data/committee/committee_outcomes.jsonl`, `committee_readiness.json`.

## Thiết kế (đã đối chiếu code TradingAgents, có điều chỉnh)

| Điểm | TradingAgents (đọc từ code) | Dự án này |
|---|---|---|
| Chu kỳ settle | 5 phiên vs SPY | **20 phiên** vs VN-Index (nếu có `VNINDEX_price.csv`) vì nắm giữ 1-3 tháng |
| "Bài học" | LLM viết 2-4 câu phản tư | **Thống kê tính bằng code** (n, vượt benchmark TB, % vượt) theo quyết định và cờ rủi ro; chỉ hiện khi đủ mẫu |
| Chống nhìn trước | lọc theo `resolved` ≤ ngày quyết định | giống: chỉ dùng outcome có `resolved_on` ≤ ngày quyết định |
| Ai thấy bài học | chỉ Portfolio Manager | chỉ Portfolio Manager; **cấm trích số** (kiểm tra chống bịa số sẽ từ chối) |

Lý do không dùng LLM viết bài học: dễ kể chuyện từ vài trường hợp và thêm ảo giác; thống kê có cỡ mẫu thì kiểm chứng được.
Ngưỡng hiện bài học: ≥ 20 quyết định đã settle và mỗi nhóm ≥ 8 (`lessons_min_total`, `lessons_min_group`).
`prompt_version` đã tăng lên `v2` vì PM nhận thêm ngữ cảnh.

## Quy ước đo

Đo chất lượng quyết định (không mô phỏng giao dịch): đóng cửa ngày dữ liệu → đóng cửa sau 20 phiên của mã; benchmark đo
cùng cửa sổ. Bỏ phí/khớp lệnh vì nhóm VETO và APPROVE chịu cùng sai lệch. Cũng ghi MAE/MFE (đáy/đỉnh trong cửa sổ)
để xem stop -7% và target +15% sẽ kích hoạt hay không. Cửa sổ chưa đủ 20 phiên → vẫn pending.

## Kiểm tra sẵn sàng `enforce` (`config.COMMITTEE_READINESS`, đề xuất)

Verdict: `NOT_READY` | `INCONCLUSIVE` | `READY_PENDING_MANUAL`. **Không bao giờ tự trả READY** vì tiêu chí đọc tay
(20 lập luận VETO ngẫu nhiên, không có tin đồn/dữ liệu ngoài bảng) không tự động hoá được.

| Tiêu chí | Ngưỡng |
|---|---|
| Quyết định đã settle | ≥ 60, trải dài ≥ 90 ngày |
| Mã VETO và mã APPROVE đã settle | mỗi nhóm ≥ 10 |
| Output hợp lệ | ≥ 95% (ledger ghi cả lần lỗi để tính) |
| Tỷ lệ VETO | ≤ 40% |
| Chênh lệch (VETO − APPROVE) lợi suất vượt benchmark | cận trên KTC 95% < 0 (bootstrap theo cụm ngày, vì các mã cùng ngày tương quan và cửa sổ chồng lấn) |
| Đọc tay | MANUAL |

## Hạn chế

- Cần vài tháng chạy shadow mới có đủ mẫu; trước đó verdict luôn INCONCLUSIVE (đúng chủ ý).
- Nếu thiếu `VNINDEX_price.csv`, benchmark là chỉ số cân bằng của universe và được ghi trong từng outcome.
- Chênh lệch VETO − APPROVE chỉ cho thấy veto có "hay" hơn không; không chứng minh nhân quả hay lợi thế tuyệt đối.
- Mẫu nhỏ và nhiều mã trùng chu kỳ làm KTC rộng; đây là lý do ngưỡng mẫu được đặt cao.
