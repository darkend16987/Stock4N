# Phase 1 - BacktestEngineV2 (point-in-time, quy tắc HOSE)

Mục tiêu: có một thước đo ĐÁNG TIN để trả lời "chiến lược chấm điểm + quy tắc cứng hiện tại có lợi thế thật
sau chi phí không?" trước khi giao thêm trí thông minh (LLM, ML) cho hệ thống. Tiền thật → ngưỡng nghiệm thu chặt.

## Chạy

```
python src/main.py backtest_v2                 # toàn bộ lịch sử giá hiện có
python src/main.py backtest_v2 --days 730      # 2 năm gần nhất
```

Kết quả ghi vào `data/backtest/`: `v2_trades_*.csv`, `v2_equity_*.csv`, `v2_report_*.json`
(chỉ số, bootstrap, Monte Carlo, walk-forward, từng điều kiện nghiệm thu, danh sách hạn chế).
Engine cũ (`backtest`) vẫn còn nhưng KHÔNG đáng tin (xem bảng dưới).

## Khác biệt so với engine cũ

| Vấn đề của engine cũ (`modules/simulation/backtest_engine.py`) | Engine mới |
|---|---|
| Mua đầu kỳ bằng điểm của HÔM NAY (nhìn trước tương lai) | Mỗi ngày quét lại, chỉ dùng dữ liệu đến hết phiên đó |
| Báo cáo tài chính mới nhất áp cho quá khứ | Báo cáo chỉ dùng sau (hết quý + độ trễ công bố) |
| Số cổ tính theo giá nghìn đồng (phóng đại 1000 lần) | Giá chuẩn hoá về VND |
| Không phí, không thuế, không T+2, không biên độ | Phí 0.15%/chiều, thuế bán 0.10%, trượt giá 0.1%, T+2, ±7%, bước giá, lô 100 |
| Mỗi mã chạy riêng, vốn không chung | Một danh mục chung vốn, tối đa 8 mã, trần ngành, lọc tương quan |
| Không qua quy tắc cứng, breadth | Dùng đúng `StockScorer.score_symbol` + RuleGate + breadth point-in-time như bản live |

## Quy ước khớp lệnh

- Tín hiệu chốt cuối phiên t; lệnh mua khớp ở **giá mở cửa phiên t+1** + trượt giá, làm tròn bước giá.
- Không mua nếu giá khớp ≥ trần. Không bán nếu thị trường nằm sàn (lệnh nhớ trạng thái, thử lại hôm sau).
- Mua phiên N → bán được từ phiên N+2; tiền bán về sau N+2.
- Stop -7% / target +15% dùng high/low trong ngày. Stop khớp tại mức stop (trượt giá), nếu mở cửa gap qua stop thì khớp
  tại giá mở cửa (xấu hơn stop). Target là lệnh limit. Stop chạm khi còn bị khoá T+2 → bán ở lần đầu bán được.
- Tối đa 6 tháng (126 phiên). Cuối kỳ đóng toàn bộ vị thế (có phí/thuế) để kết quả sạch.

## Lưới kiểm tra (checkpoint)

| # | Hạng mục | Cách kiểm | Trạng thái |
|---|---|---|---|
| 1 | Không nhìn trước giá | Đổi mạnh mọi giá sau ngày D → kết quả đến D không đổi | test `TestNoLookAhead` |
| 2 | Không nhìn trước báo cáo | Đổi báo cáo chưa công bố tại D → không ảnh hưởng | test `TestNoLookAhead`, `TestCalculatorPointInTime` |
| 3 | Bộ kiểm đủ nhạy | Cố tình rò rỉ lịch sử → test phát hiện | `test_detector_catches_a_deliberate_leak` |
| 4 | Sổ sách | Vốn cuối = vốn đầu + Σ lãi/lỗ ròng; tiền không âm | `TestEngineRun` |
| 5 | T+2, biên độ, bước giá | Từng kịch bản khớp lệnh | `TestExecution`, `TestMarketRules` |
| 6 | Quy tắc cứng được tôn trọng | Mã ROE thấp / Nợ-Vốn cao không bao giờ được mua | `test_hard_rule_violators_never_bought` |
| 7 | Breadth chặn mua | Thị trường giảm → 0 lệnh mua | `test_bear_market_produces_no_buys` |
| 8 | Breadth PIT khớp bản live | So với `MarketBreadthAnalyzer` trên dữ liệu cắt | `test_breadth_matches_live_analyzer...` |
| 9 | Kết quả tái lập | Chạy 2 lần cho cùng đường vốn | `test_deterministic` |
| 10 | Chi phí có tác dụng | Bỏ phí → lãi cao hơn; chi phí x2 không tốt hơn base | `test_costs_reduce_return`, `TestSuite` |

## Ngưỡng nghiệm thu (ĐỀ XUẤT - sửa ở `config.BACKTEST_ACCEPTANCE`)

Verdict: **PASS** chỉ khi đạt tất cả; **FAIL** nếu một chỉ số rủi ro/hiệu suất không đạt;
**INCONCLUSIVE** nếu thiếu mẫu hoặc thiếu số liệu (không bao giờ tính là PASS).

| Điều kiện | Ngưỡng |
|---|---|
| Số phiên | ≥ 504 (~2 năm) |
| Số lệnh đóng | ≥ 40 |
| Sharpe, cận dưới KTC 95% (block bootstrap) | > 0 |
| CAGR vượt benchmark, sau chi phí | > 0 |
| Max drawdown thực tế | ≤ 10% (theo `RISK_MANAGEMENT.max_drawdown_pct`) |
| Max drawdown Monte Carlo (đảo thứ tự lệnh), p95 | ≤ 15% |
| Profit factor | ≥ 1.3 |
| Cửa sổ walk-forward có lãi | ≥ 60% (6 cửa sổ) |
| Chi phí+thuế+trượt giá nhân đôi | vẫn có lãi |

## Giả định CHƯA kiểm chứng (cần bạn xác nhận)

1. **Độ trễ công bố báo cáo**: Q1-Q3 = 45 ngày, Q4 = 90 ngày (`config.REPORTING_LAG_DAYS`). Dữ liệu thô không có ngày công bố.
2. **Phí 0.15%/chiều, thuế 0.10%**: đối chiếu biểu phí công ty chứng khoán của bạn.
3. **Lãi tiền gửi 4%/năm** dùng cho Sharpe (`risk_free_annual`): ước lượng.
4. **Số cổ phiếu** cho P/E, P/B ước lượng = vốn góp / 10,000đ.
5. **Cột báo cáo tài chính KBS** hiện tại chưa được kiểm chứng với dữ liệu thật đầy đủ.

## Hạn chế KHÔNG thể sửa bằng code

- **Thiên lệch sống sót**: universe là VN100 hiện tại. Cần danh sách thành phần theo thời kỳ để khắc phục.
- **Overfit ngưỡng**: các ngưỡng chấm điểm trong config có thể đã chọn khi nhìn dữ liệu.
- Chưa có `VNINDEX_price.csv` → benchmark tạm là chỉ số cân bằng của universe (yếu hơn VN-Index).
- Chỉ mô phỏng HOSE; không mô phỏng thanh khoản/khối lượng khớp.

## Dữ liệu cần để có kết luận thật

- Giá + báo cáo tài chính của đủ ~98 mã (máy dev chỉ có giá của 30 mã và báo cáo của 3 mã → kết quả vô nghĩa).
- `data/raw/VNINDEX_price.csv` (cột `time, close`) để có benchmark chuẩn.
- Ít nhất 2 năm giá + 6 quý báo cáo trước ngày bắt đầu giao dịch.
