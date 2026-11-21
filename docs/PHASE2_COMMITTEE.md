# Phase 2 - Hội đồng đầu tư LLM (veto-only, shadow-first)

Mục tiêu: dùng Gemini như một lớp **cẩn trọng bổ sung** lên các mã mà hệ thống định lượng đã chọn MUA.
LLM KHÔNG tạo ra khuyến nghị mới và KHÔNG được nâng khuyến nghị. Đây là quyết định thiết kế của dự án
(không phải sao chép từ TradingAgents/Vibe-Trading: `investment_committee` của Vibe-Trading không có quyền veto,
PM là LLM có thể bỏ qua CRO).

## Vì sao veto-only và shadow-first

- Nghiên cứu tham khảo: agent giao dịch dùng LLM thường mất lợi thế khi kiểm soát nhìn-trước-tương-lai.
- TradingAgents tự thừa nhận tin tức/mạng xã hội không được lưu trữ nên backtest lịch sử chỉ mang tính tham khảo.
  → **Không thể backtest LLM trên lịch sử một cách đáng tin.** Cách duy nhất là forward-test: ghi lại quyết định
  hôm nay, đối chiếu với kết quả thực sau này.
- Do đó mặc định `mode='shadow'`: hội đồng chạy, ghi nhật ký, KHÔNG đổi khuyến nghị. Chỉ bật `enforce` khi có bằng chứng.

## Luồng

```
analysis_report.csv (đã qua RuleGate)
   └─ chỉ các mã đang MUA, điểm cao trước, tối đa 15 mã
        ├─ Bảng dữ kiện (code tính, F01..Fnn) ──┐
        ├─ Bull  (ủng hộ)      ─ độc lập ───────┤
        ├─ Bear  (phản biện)   ─ độc lập ───────┤→ Risk Officer → Portfolio Manager → APPROVE | VETO
        └─ ghi ledger (JSONL) cho forward-test
enforce: VETO hạ MUA → THEO DÕI.   shadow: chỉ ghi committee_report.csv
```

4 lần gọi LLM / mã (Flash). Chạy: `python src/main.py committee` (shadow) hoặc `--committee-mode enforce`.
Chưa thêm vào `all` để tránh phát sinh chi phí API ngoài ý muốn.

## Các lớp chống ảo giác (kiểm tra bằng code, không tin LLM)

| Lớp | Cơ chế | Vi phạm → |
|---|---|---|
| Dữ kiện | Mọi số do code tính; LLM không có tin tức, không có dữ liệu ngoài | - |
| Schema | Enum chặt; **không có trường giá/khối lượng/mục tiêu** (trường lạ bị từ chối) | thử lại 1 lần |
| Trích dẫn | Mỗi lập luận phải có `fact_ids` tồn tại trong bảng dữ kiện | thử lại 1 lần |
| Bịa số | Mọi con số trong lập luận phải khớp một dữ kiện hoặc hằng số quy tắc hoặc là số đếm nhỏ | thử lại 1 lần |
| Bất biến | `apply_verdicts` assert: không dòng nào được nâng bậc | lỗi chương trình |
| Lỗi LLM | Hết quota/JSON hỏng sau retry → `LLM_ERROR`/`INVALID`, **không đổi gì** (fail-open) | ghi nhận trong báo cáo |

Hạn chế đã biết của kiểm tra bịa số: hằng số quy tắc (vd 35 = breadth tối thiểu) được phép xuất hiện ở bất cứ đâu,
nên đây là lưới an toàn thô, không thay thế việc đọc lập luận. Có test ghi lại hạn chế này.

Fail-open khi LLM lỗi là lựa chọn có chủ đích: hệ thống định lượng (đã kiểm chứng ở Phase 1) tự đứng được; LLM chỉ thêm
sự cẩn trọng. Đổi lại, khi API sập ở chế độ enforce, mã vẫn có thể được mua mà không qua veto.

## Nhật ký (ledger)

`data/committee/committee_ledger.jsonl` (append-only): ngày dữ liệu, dữ kiện đưa vào, từng vai trò nói gì, quyết định,
khuyến nghị hệ thống lúc đó, giá, mô hình, nhiệt độ, mode. Idempotent theo (ngày, mã, prompt_version, dữ kiện):
chạy lại cùng ngày không tốn thêm lượt gọi. Đây là đầu vào cho Phase 3 (settle và rút kinh nghiệm).

## Tiêu chí đề xuất để chuyển sang `enforce` (cần bạn duyệt; Phase 3 sẽ có công cụ settle)

1. Ít nhất 60 quyết định đã settle (20 phiên sau quyết định) trong ≥ 3 tháng.
2. Nhóm bị VETO có lợi suất vượt VN-Index thấp hơn nhóm APPROVE, với khoảng tin cậy 95% của chênh lệch không chứa 0.
3. ≥ 95% output hợp lệ (không INVALID/LLM_ERROR); tỷ lệ VETO ≤ 40% (veto quá nhiều = phá chiến lược).
4. Đọc tay 20 lập luận VETO ngẫu nhiên: không có lập luận dựa trên tin đồn hay dữ liệu không có trong bảng.

## Mô hình: Gemini 3.8 Flash

Mặc định `gemini-3.8-flash` (đổi bằng `AI_MODEL` trong `.env`; `COMMITTEE_MODEL` nếu muốn tách riêng hội đồng).
Python giờ tự nạp `.env` (không cần python-dotenv); biến đã có trong môi trường được ưu tiên.
Theo tài liệu Gemini 3.8 (aistudio.google.com/docs/whats-new-gemini-3.8):
- Cần bỏ `temperature`, `top_p`, `top_k` → client không gửi chúng cho Gemini ≥ 3 (`modules/utils/gemini_params.py`);
  Gemini 2.x vẫn dùng `temperature` 0.2. Tài liệu không nói gửi lên sẽ lỗi hay bị bỏ qua.
- Mặc định "suy nghĩ" mức `medium`; tài liệu không nói token suy nghĩ có tính vào giới hạn đầu ra không
  → `max_output_tokens` nâng lên 8192 để JSON không bị cắt.
- Tài liệu không nêu rõ SDK `google-generativeai` (cũ) còn hỗ trợ; ví dụ của họ dùng `google-genai`.

Kiểm tra thật ngày 2026-11-21 bằng key trong `.env`:
- `gemini-2.5-flash` trả 404 "no longer available to new users, use gemini-3.8-flash" → bắt buộc đổi.
- `gemini-3.8-flash` trả **503 "high demand"** ở 3/4 lần gọi và treo > 45s ở lần còn lại. Chưa có lần nào trả nội dung,
  nên **chưa kiểm chứng được** JSON mode và SDK cũ với mô hình này. Lỗi do phía Google quá tải, không phải do code.
- Client giờ có timeout 90s/lượt, tự thử lại 3 lần (chờ 5/15/40s) với lỗi 503/504/429, và cầu chì dừng sớm nếu
  2 mã liên tiếp lỗi API (các mã còn lại giữ nguyên khuyến nghị).
- Gói `google-generativeai` đã **ngừng hỗ trợ** (cảnh báo chính thức khi import, khuyên chuyển sang `google-genai`).
  Chưa chuyển vì không kiểm chứng được lúc API quá tải; nên làm khi API ổn định.

## Chưa kiểm chứng

- `GeminiClient` chưa gọi API thật (máy dev không có khoá và gói google-generativeai). `response_mime_type` có thể không
  được phiên bản thư viện của bạn hỗ trợ (đã có fallback); lần chạy đầu cần xem log.
- Chưa có nguồn tin tức: vnstock có tin tức hay không chưa được kiểm chứng. Hội đồng hiện không dùng tin tức và được dặn
  không suy đoán tin tức. Thêm tin tức = thay đổi lớn về rủi ro ảo giác, nên làm riêng sau.
- Prompt `v1` chưa được tinh chỉnh bằng dữ liệu thật; mọi thay đổi prompt phải tăng `prompt_version`.
