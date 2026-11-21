"""
Hội đồng đầu tư LLM (Bull → Bear → Risk Officer → Portfolio Manager) - CHỈ CÓ QUYỀN PHỦ QUYẾT.

Nguyên tắc an toàn (tiền thật):
  - Veto-only: kết quả duy nhất có thể ảnh hưởng hệ thống là hạ MUA → THEO DÕI. Không bao giờ nâng khuyến nghị,
    không đặt giá/khối lượng/mục tiêu (schema cấm các trường đó).
  - Chỉ xét các mã hệ thống ĐÃ khuyến nghị MUA (đã qua RuleGate); các mã khác không bị đụng tới.
  - Mọi lập luận phải trích dẫn dữ kiện có thật và không được bịa số (xem schema.py).
  - LLM lỗi/không hợp lệ → KHÔNG thay đổi gì (hệ thống định lượng tự đứng được), ghi rõ trạng thái.
  - Mặc định mode 'shadow': chỉ ghi nhật ký để forward-test; 'enforce' chỉ bật sau khi có bằng chứng.
"""
import hashlib
import json
import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.committee import schema
from modules.committee.facts import build_fact_sheet
from modules.committee.ledger import Ledger
from modules.committee.llm import LLMUnavailable
from modules.utils.logger import get_logger

logger = get_logger(__name__)

# Thứ hạng để kiểm tra bất biến "chỉ hạ, không nâng"
REC_RANK = {'BÁN / CƠ CẤU': 0, 'THEO DÕI': 1, 'MUA THĂM DÒ': 2, 'MUA MẠNH': 3}

SYSTEM_PROMPT = """Bạn là thành viên hội đồng đầu tư của một nhà đầu tư cá nhân Việt Nam ưa an toàn, \
nắm giữ trung hạn 1-6 tháng, vốn nhỏ.
QUY TẮC BẮT BUỘC:
1. CHỈ dùng dữ kiện trong BẢNG DỮ KIỆN. Bạn KHÔNG có tin tức, KHÔNG có dữ liệu bên ngoài, KHÔNG biết sự kiện \
công ty. Không suy đoán tin tức hay tin đồn.
2. Mỗi lập luận gồm "claim" (tiếng Việt, ngắn gọn) và "fact_ids" (mã dữ kiện làm căn cứ, vd ["F04"]).
3. Chỉ nêu con số CÓ trong bảng dữ kiện. Không tự tính ra số mới. Không đề xuất giá mua/bán/mục tiêu/khối lượng.
4. Chỉ trả về MỘT object JSON đúng schema được yêu cầu, không thêm bất kỳ chữ nào ngoài JSON."""

ROLE_TASKS = {
    'bull': ("Vai trò: nhà phân tích ỦNG HỘ việc mua. Nêu 1-4 lý do mạnh nhất để mua mã này, chỉ dựa trên dữ kiện.\n"
             'Schema: {"arguments": [{"claim": "...", "fact_ids": ["F01"]}]}'),
    'bear': ("Vai trò: nhà phân tích PHẢN BIỆN. Nêu 1-4 rủi ro/điểm yếu nghiêm trọng nhất của việc mua mã này, "
             "chỉ dựa trên dữ kiện.\n"
             'Schema: {"arguments": [{"claim": "...", "fact_ids": ["F01"]}]}'),
    'risk_officer': ("Vai trò: Giám đốc rủi ro. Đọc lập luận ủng hộ và phản biện, đánh giá rủi ro thực sự của vị thế.\n"
                     f"risk_flags chỉ được chọn từ: {list(schema.RISK_FLAGS)}.\n"
                     'verdict: "SUPPORT" (rủi ro chấp nhận được) | "CONDITIONAL" | "OPPOSE" (rủi ro quá cao).\n'
                     'Schema: {"verdict": "...", "risk_flags": ["..."], "arguments": '
                     '[{"claim": "...", "fact_ids": ["F01"]}]}'),
    'portfolio_manager': (
        "Vai trò: Giám đốc danh mục, người quyết định cuối. Hệ thống định lượng ĐÃ chọn mã này sau khi qua các quy tắc "
        "cứng (ROE, P/E, nợ, penny, breadth, điểm tổng).\n"
        "Bạn CHỈ có quyền VETO (không mua). Chỉ VETO khi có rủi ro CỤ THỂ, được chứng minh bằng dữ kiện, mà hệ thống "
        "định lượng chưa xử lý - ví dụ: thanh khoản mỏng, giá đã tăng quá xa MA50 kèm RSI cao, biến động bất thường, "
        "thiếu dữ liệu quan trọng. KHÔNG VETO chỉ vì cảm giác hay vì không có tin tức. Mặc định là APPROVE.\n"
        f"risk_flags chỉ được chọn từ: {list(schema.RISK_FLAGS)}. VETO bắt buộc kèm ít nhất 1 risk_flag.\n"
        "confidence: số nguyên 1-5 (độ chắc chắn của quyết định).\n"
        'Schema: {"action": "APPROVE" | "VETO", "confidence": 3, "risk_flags": ["..."], '
        '"arguments": [{"claim": "...", "fact_ids": ["F01"]}]}'),
}


class InvestmentCommittee:
    def __init__(self, client, cfg=None, ledger=None, lessons_provider=None):
        """
        lessons_provider: callable(as_of) -> str thống kê bài học (memory.build_lessons); chỉ PM nhìn thấy.
        """
        self.client = client
        self.cfg = {**config.COMMITTEE_CONFIG, **(cfg or {})}
        self.ledger = ledger or Ledger(self.cfg['ledger_file'])
        self.lessons_provider = lessons_provider
        self.calls = 0

    # ------------------------------------------------------------------ một vai trò
    def _call_role(self, role, sheet, context=''):
        prompt = f"{sheet.to_prompt_text()}\n\n{context}{ROLE_TASKS[role]}"
        error = None
        for attempt in range(self.cfg['max_retries'] + 1):
            full = prompt if error is None else (
                f"{prompt}\n\nLẦN TRƯỚC OUTPUT BỊ TỪ CHỐI: {error}\nHãy sửa và chỉ trả về JSON hợp lệ.")
            raw = self.client.generate(SYSTEM_PROMPT, full)
            self.calls += 1
            try:
                return schema.VALIDATORS[role](schema.extract_json(raw), sheet)
            except schema.SchemaError as e:
                error = str(e)
                logger.warning(f"  [{sheet.symbol}/{role}] output bị từ chối (lần {attempt + 1}): {error}")
        raise schema.SchemaError(f"{role}: {error}")

    # ------------------------------------------------------------------ một mã
    def review(self, sheet, system_recommendation=None, score=None):
        """Chạy hội đồng cho 1 mã. Không bao giờ ném lỗi lên trên: trả về verdict có `status`."""
        key = {'as_of': sheet.as_of, 'symbol': sheet.symbol, 'prompt_version': self.cfg['prompt_version']}
        fingerprint = sheet.fingerprint()

        cached = self.ledger.find(facts_hash=fingerprint, **key)
        if cached:
            logger.info(f"  [{sheet.symbol}] dùng kết quả đã có trong ledger ({sheet.as_of})")
            return {**cached['verdict'], 'cached': True}

        verdict = {'symbol': sheet.symbol, 'as_of': sheet.as_of, 'status': 'OK', 'action': None,
                   'confidence': None, 'risk_flags': [], 'reasons': [], 'bull': None, 'bear': None,
                   'cro': None, 'cro_pm_disagree': None, 'error': None, 'cached': False}
        start_calls = self.calls
        try:
            bull = self._call_role('bull', sheet)
            bear = self._call_role('bear', sheet)
            debate = ("LẬP LUẬN ỦNG HỘ:\n" + json.dumps(bull, ensure_ascii=False) +
                      "\nLẬP LUẬN PHẢN BIỆN:\n" + json.dumps(bear, ensure_ascii=False) + "\n\n")
            cro = self._call_role('risk_officer', sheet, debate)
            lessons = self.lessons_provider(sheet.as_of) if self.lessons_provider else ''
            verdict['lessons_hash'] = hashlib.sha256(lessons.encode('utf-8')).hexdigest()[:12] if lessons else None
            pm_ctx = (lessons + debate + "Ý KIẾN GIÁM ĐỐC RỦI RO:\n" + json.dumps(cro, ensure_ascii=False) + "\n\n")
            pm = self._call_role('portfolio_manager', sheet, pm_ctx)
            verdict.update({'action': pm['action'], 'confidence': pm['confidence'],
                            'risk_flags': pm['risk_flags'], 'reasons': pm['arguments'],
                            'bull': bull, 'bear': bear, 'cro': cro,
                            'cro_pm_disagree': (cro['verdict'] == 'OPPOSE') != (pm['action'] == 'VETO')})
        except schema.SchemaError as e:
            verdict.update({'status': 'INVALID', 'error': str(e)})
        except LLMUnavailable as e:
            verdict.update({'status': 'LLM_ERROR', 'error': str(e)})
        except Exception as e:                     # không để lỗi bất ngờ làm sập pipeline
            logger.error(f"  [{sheet.symbol}] lỗi không mong đợi: {e}", exc_info=True)
            verdict.update({'status': 'LLM_ERROR', 'error': f"{type(e).__name__}: {e}"})
        verdict['calls'] = self.calls - start_calls

        if verdict['status'] != 'OK':
            # ghi cả lần thất bại để tính tỷ lệ output hợp lệ (không chặn lần chạy lại: find() chỉ lấy OK)
            self.ledger.append({**key, 'status': verdict['status'], 'error': verdict['error'],
                                'facts_hash': fingerprint, 'mode': self.cfg['mode'],
                                'logged_at': pd.Timestamp.now().isoformat(timespec='seconds')})
        else:
            facts = sheet.to_dict()
            self.ledger.append({
                **key, 'status': 'OK', 'facts_hash': fingerprint, 'model': self.cfg['model'],
                'temperature': self.cfg['temperature'], 'mode': self.cfg['mode'],
                'system_recommendation': system_recommendation, 'score': score,
                'price_vnd': next((f['value'] for f in facts['facts'].values() if f['label'] == 'Giá hiện tại'), None),
                'facts': facts, 'verdict': verdict,
                'logged_at': pd.Timestamp.now().isoformat(timespec='seconds')})
        return verdict

    # ------------------------------------------------------------------ cả danh sách
    def run(self, report_df, metrics_df=None, market_filter=None, mode=None, price_loader=None):
        """
        Duyệt các mã đang được khuyến nghị MUA (cao điểm trước, tối đa max_reviews).
        Trả về (DataFrame đã gắn cột hội đồng, danh sách verdict).
        """
        mode = mode or self.cfg['mode']
        if mode not in ('shadow', 'enforce'):
            raise ValueError(f"mode không hợp lệ: {mode}")
        price_loader = price_loader or default_price_loader
        self.cfg = {**self.cfg, 'mode': mode}          # ghi đúng mode vào ledger

        buys = report_df[report_df['Recommendation'].astype(str).str.startswith('MUA')]
        buys = buys.drop_duplicates('Symbol').sort_values('Total_Score', ascending=False)
        if len(buys) > self.cfg['max_reviews']:
            logger.warning(f"{len(buys)} mã MUA > max_reviews={self.cfg['max_reviews']}: chỉ duyệt top "
                           f"{self.cfg['max_reviews']}; phần còn lại giữ nguyên khuyến nghị")
            buys = buys.head(self.cfg['max_reviews'])

        metrics = {} if metrics_df is None else metrics_df.drop_duplicates('Symbol').set_index('Symbol').to_dict('index')
        sector_counts = buys['Sector'].value_counts().to_dict() if 'Sector' in buys else {}

        verdicts = []
        consecutive_api_errors = 0
        for _, row in buys.iterrows():
            symbol = row['Symbol']
            if consecutive_api_errors >= self.cfg['max_consecutive_api_errors']:
                # Cầu chì: API đang sập/quá tải → không gọi tiếp (mỗi mã có thể tốn nhiều phút chờ và thử lại)
                verdicts.append({'symbol': symbol, 'as_of': None, 'status': 'LLM_ERROR', 'action': None,
                                 'confidence': None, 'risk_flags': [], 'reasons': [], 'bull': None, 'bear': None,
                                 'cro': None, 'cro_pm_disagree': None, 'cached': False, 'calls': 0,
                                 'error': f"Bỏ qua: API lỗi liên tiếp {consecutive_api_errors} mã"})
                continue
            merged = {**metrics.get(symbol, {}), **row.to_dict()}
            sheet = build_fact_sheet(symbol, merged, price_loader(symbol), market_filter,
                                     same_sector_in_shortlist=sector_counts.get(row.get('Sector')))
            logger.info(f"Hội đồng xét {symbol} (điểm {row['Total_Score']}, {row['Recommendation']})...")
            verdict = self.review(sheet, row['Recommendation'], float(row['Total_Score']))
            consecutive_api_errors = consecutive_api_errors + 1 if verdict['status'] == 'LLM_ERROR' else 0
            verdicts.append(verdict)
        if consecutive_api_errors >= self.cfg['max_consecutive_api_errors']:
            logger.warning("Hội đồng dừng sớm vì API Gemini lỗi liên tiếp; các mã còn lại giữ nguyên khuyến nghị")

        return apply_verdicts(report_df, verdicts, mode), verdicts


def default_price_loader(symbol):
    path = os.path.join(config.RAW_DIR, f"{symbol}_price.csv")
    return pd.read_csv(path) if os.path.exists(path) else None


def apply_verdicts(report_df, verdicts, mode):
    """
    Gắn kết quả hội đồng vào báo cáo. Ở mode 'enforce', VETO hạ MUA → THEO DÕI.
    Bất biến được kiểm tra bằng assert: không dòng nào được nâng bậc, mã không bị xét không đổi.
    """
    out = report_df.copy()
    by_symbol = {v['symbol']: v for v in verdicts}
    out['Pre_Committee_Recommendation'] = out['Recommendation']
    out['Committee_Status'] = out['Symbol'].map(lambda s: by_symbol[s]['status'] if s in by_symbol else 'NOT_REVIEWED')
    out['Committee_Action'] = out['Symbol'].map(lambda s: by_symbol[s]['action'] if s in by_symbol else None)
    out['Committee_Flags'] = out['Symbol'].map(
        lambda s: ','.join(by_symbol[s]['risk_flags']) if s in by_symbol else '')
    out['Committee_Reasons'] = out['Symbol'].map(
        lambda s: ' | '.join(r['claim'] for r in by_symbol[s]['reasons']) if s in by_symbol else '')

    if mode == 'enforce':
        veto = (out['Committee_Status'] == 'OK') & (out['Committee_Action'] == 'VETO') \
               & out['Recommendation'].astype(str).str.startswith('MUA')
        out.loc[veto, 'Recommendation'] = 'THEO DÕI'

    before = out['Pre_Committee_Recommendation'].map(REC_RANK).fillna(-1)
    after = out['Recommendation'].map(REC_RANK).fillna(-1)
    assert (after <= before).all(), "Vi phạm veto-only: hội đồng không được phép nâng khuyến nghị"
    return out
