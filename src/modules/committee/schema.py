"""
Schema và kiểm tra output của hội đồng LLM (không phụ thuộc pydantic).

Chống ảo giác bằng 3 lớp kiểm tra cứng (vi phạm → output bị coi là không hợp lệ, thử lại, rồi bỏ):
  1. Cấu trúc/enum đúng schema, không có trường lạ (đặc biệt: không có trường giá/khối lượng/mục tiêu)
  2. Mỗi lập luận phải trích dẫn >= 1 fact_id, và fact_id phải TỒN TẠI trong bảng dữ kiện
  3. Mọi con số trong lập luận phải khớp một dữ kiện (hoặc hằng số quy tắc đã biết) - không được bịa số
"""
import json
import math
import re

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

RISK_FLAGS = ('LIQUIDITY', 'VOLATILITY', 'VALUATION', 'LEVERAGE', 'SECTOR_CONCENTRATION',
              'MARKET_REGIME', 'DATA_QUALITY', 'OVEREXTENDED', 'MOMENTUM_WEAK', 'OTHER')
CRO_VERDICTS = ('SUPPORT', 'CONDITIONAL', 'OPPOSE')
PM_ACTIONS = ('APPROVE', 'VETO')

MAX_ARGUMENTS = 4
MAX_CLAIM_CHARS = 280


class SchemaError(ValueError):
    """Output của LLM không hợp lệ; thông điệp được đưa lại cho LLM khi thử lại."""


# ----------------------------------------------------------------------------- JSON
def extract_json(text):
    """Lấy object JSON từ phản hồi (chịu được ```json fence và chữ thừa quanh JSON)."""
    if text is None:
        raise SchemaError("Phản hồi rỗng")
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    start, end = cleaned.find('{'), cleaned.rfind('}')
    if start == -1 or end <= start:
        raise SchemaError("Không tìm thấy object JSON")
    try:
        data = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as e:
        raise SchemaError(f"JSON sai cú pháp: {e}")
    if not isinstance(data, dict):
        raise SchemaError("JSON gốc phải là object")
    return data


# ----------------------------------------------------------------------------- numbers
_NUM_RE = re.compile(r"(?<![\w.])-?\d[\d.,]*\d|\d")


def _to_float(token):
    """'1,234.5' / '1.234,5' / '18,5' → float; None nếu không đọc được."""
    t = token.strip().rstrip('.,')
    if not t:
        return None
    if ',' in t and '.' in t:
        if t.rfind(',') > t.rfind('.'):      # kiểu VN: 1.234,5
            t = t.replace('.', '').replace(',', '.')
        else:                                 # kiểu US: 1,234.5
            t = t.replace(',', '')
    elif ',' in t:
        parts = t.split(',')
        t = t.replace(',', '') if all(len(p) == 3 for p in parts[1:]) else t.replace(',', '.')
    elif t.count('.') > 1:
        t = t.replace('.', '')
    try:
        return float(t)
    except ValueError:
        return None


def _rule_constants():
    """Hằng số quy tắc hệ thống mà lập luận được phép nhắc tới (ngưỡng, không phải dữ kiện thị trường)."""
    r, p, k = config.HARD_RULES, config.PORTFOLIO_CONFIG, config.RISK_MANAGEMENT
    values = {r['min_score'], r['min_roe'], r['max_pe'], r['max_debt_equity'], r['min_price_vnd'],
              r['min_breadth'] * 100, r['min_breadth'], p['max_position_pct'] * 100, p['max_positions'],
              p['cash_reserve_pct'] * 100, p['max_sector_pct'] * 100, p['max_correlation'],
              k['stop_loss_pct'] * 100, k['target_profit_pct'] * 100}
    values.update(r.get('max_debt_equity_by_sector', {}).values())
    return {float(v) for v in values}


def numbers_in(text):
    out = []
    for m in _NUM_RE.finditer(text or ''):
        v = _to_float(m.group(0))
        if v is not None and not math.isnan(v):
            out.append(v)
    return out


def _matches(n, candidates):
    for c in candidates:
        tol = max(0.05, abs(c) * 0.005)
        if abs(abs(n) - abs(c)) <= tol:
            return True
    return False


def find_invented_numbers(text, fact_values):
    """Các số trong `text` không khớp dữ kiện nào, không phải hằng số quy tắc, và không phải số đếm nhỏ."""
    constants = _rule_constants()
    allowed = list(fact_values)
    bad = []
    for n in numbers_in(text):
        if abs(n) <= 12 and float(n).is_integer():      # số đếm nhỏ: "2 mã", "3 phiên"
            continue
        # đơn vị tỷ đồng/triệu: cho phép số đã quy đổi từ dữ kiện (VND → tỷ)
        scaled = [v / 1e9 for v in allowed] + [v / 1e6 for v in allowed] + [v * 100 for v in allowed]
        if _matches(n, allowed) or _matches(n, scaled) or _matches(n, constants):
            continue
        bad.append(n)
    return bad


# ----------------------------------------------------------------------------- validation
def _check_keys(obj, allowed, where):
    extra = set(obj) - set(allowed)
    if extra:
        raise SchemaError(f"{where}: trường không được phép {sorted(extra)} "
                          f"(chỉ cho phép {sorted(allowed)}; KHÔNG được đề xuất giá/khối lượng/mục tiêu)")
    missing = set(allowed) - set(obj)
    if missing:
        raise SchemaError(f"{where}: thiếu trường {sorted(missing)}")


def _validate_arguments(args, sheet, where):
    if not isinstance(args, list) or not (1 <= len(args) <= MAX_ARGUMENTS):
        raise SchemaError(f"{where}: cần danh sách 1-{MAX_ARGUMENTS} lập luận")
    fact_values = sheet.numeric_values()
    cleaned = []
    for i, a in enumerate(args):
        if not isinstance(a, dict):
            raise SchemaError(f"{where}[{i}]: mỗi lập luận phải là object {{claim, fact_ids}}")
        _check_keys(a, ('claim', 'fact_ids'), f"{where}[{i}]")
        claim, ids = a['claim'], a['fact_ids']
        if not isinstance(claim, str) or not claim.strip():
            raise SchemaError(f"{where}[{i}].claim phải là chuỗi không rỗng")
        if len(claim) > MAX_CLAIM_CHARS:
            raise SchemaError(f"{where}[{i}].claim quá dài (> {MAX_CLAIM_CHARS} ký tự)")
        if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
            raise SchemaError(f"{where}[{i}].fact_ids phải là danh sách >= 1 mã dữ kiện")
        unknown = [x for x in ids if x not in sheet.facts]
        if unknown:
            raise SchemaError(f"{where}[{i}]: fact_id không tồn tại {unknown}; "
                              f"chỉ được dùng {sorted(sheet.facts)}")
        invented = find_invented_numbers(claim, fact_values)
        if invented:
            raise SchemaError(f"{where}[{i}]: con số không có trong bảng dữ kiện {invented}; "
                              f"chỉ được nêu số có trong dữ kiện")
        cleaned.append({'claim': claim.strip(), 'fact_ids': list(ids)})
    return cleaned


def _validate_flags(flags, where):
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        raise SchemaError(f"{where}: risk_flags phải là danh sách chuỗi")
    bad = [f for f in flags if f not in RISK_FLAGS]
    if bad:
        raise SchemaError(f"{where}: risk_flags không hợp lệ {bad}; chỉ cho phép {list(RISK_FLAGS)}")
    return list(dict.fromkeys(flags))


def validate_argument_role(data, sheet):
    """Bull / Bear: {"arguments": [...]}"""
    _check_keys(data, ('arguments',), 'output')
    return {'arguments': _validate_arguments(data['arguments'], sheet, 'arguments')}


def validate_risk_officer(data, sheet):
    _check_keys(data, ('verdict', 'risk_flags', 'arguments'), 'output')
    if data['verdict'] not in CRO_VERDICTS:
        raise SchemaError(f"verdict phải thuộc {list(CRO_VERDICTS)}")
    return {'verdict': data['verdict'],
            'risk_flags': _validate_flags(data['risk_flags'], 'risk_flags'),
            'arguments': _validate_arguments(data['arguments'], sheet, 'arguments')}


def validate_portfolio_manager(data, sheet):
    _check_keys(data, ('action', 'confidence', 'risk_flags', 'arguments'), 'output')
    if data['action'] not in PM_ACTIONS:
        raise SchemaError(f"action phải thuộc {list(PM_ACTIONS)}")
    conf = data['confidence']
    if isinstance(conf, bool) or not isinstance(conf, int) or not 1 <= conf <= 5:
        raise SchemaError("confidence phải là số nguyên 1-5")
    flags = _validate_flags(data['risk_flags'], 'risk_flags')
    args = _validate_arguments(data['arguments'], sheet, 'arguments')
    if data['action'] == 'VETO' and not flags:
        raise SchemaError("VETO phải kèm ít nhất 1 risk_flag")
    return {'action': data['action'], 'confidence': conf, 'risk_flags': flags, 'arguments': args}


VALIDATORS = {
    'bull': validate_argument_role,
    'bear': validate_argument_role,
    'risk_officer': validate_risk_officer,
    'portfolio_manager': validate_portfolio_manager,
}
