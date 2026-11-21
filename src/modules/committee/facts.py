"""
Bảng dữ kiện (fact sheet) cho hội đồng LLM.

TOÀN BỘ dữ kiện được tính bằng code từ dữ liệu hệ thống; LLM không được tự tính hay tự thêm số.
Mỗi dữ kiện có mã (F01, F02, ...) để lập luận trích dẫn và để kiểm tra chống bịa số.
Dữ kiện thiếu được liệt kê riêng (không điền giá trị đoán).
"""
import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config


def _num(x):
    """float hợp lệ hoặc None (loại NaN/inf/chuỗi)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


class FactSheet:
    def __init__(self, symbol, as_of):
        self.symbol = symbol
        self.as_of = str(as_of)
        self.facts = {}          # id -> {'label', 'value', 'unit'}
        self.missing = []        # nhãn các dữ kiện không có
        self._n = 0

    def add(self, label, value, unit='', digits=2):
        """Thêm dữ kiện; value None/NaN → ghi vào danh sách thiếu."""
        if isinstance(value, str):
            if not value.strip():
                self.missing.append(label)
                return None
            stored = value.strip()
        else:
            v = _num(value)
            if v is None:
                self.missing.append(label)
                return None
            stored = round(v, digits)
        self._n += 1
        fid = f"F{self._n:02d}"
        self.facts[fid] = {'label': label, 'value': stored, 'unit': unit}
        return fid

    def numeric_values(self):
        return [f['value'] for f in self.facts.values() if isinstance(f['value'], (int, float))]

    def to_prompt_text(self):
        lines = [f"Mã: {self.symbol} | Ngày dữ liệu: {self.as_of}", "BẢNG DỮ KIỆN:"]
        for fid, f in self.facts.items():
            unit = f" {f['unit']}" if f['unit'] else ''
            lines.append(f"  {fid} | {f['label']} = {f['value']}{unit}")
        if self.missing:
            lines.append("DỮ LIỆU KHÔNG CÓ (không được suy đoán): " + "; ".join(self.missing))
        return "\n".join(lines)

    def fingerprint(self):
        payload = json.dumps({'facts': self.facts, 'missing': self.missing, 'as_of': self.as_of},
                             sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

    def to_dict(self):
        return {'symbol': self.symbol, 'as_of': self.as_of, 'facts': self.facts, 'missing': self.missing}


def price_stats(price_df, as_of=None):
    """
    Thống kê giá/thanh khoản từ lịch sử giá (đã cắt đến as_of nếu có). Giá trả về là VND.
    Trả về dict (khoá thiếu nếu không đủ dữ liệu) và ngày dữ liệu cuối.
    """
    out = {}
    if price_df is None or price_df.empty:
        return out, None
    df = price_df.copy()
    df['time'] = pd.to_datetime(df['time']).dt.normalize()
    df = df.drop_duplicates('time', keep='last').sort_values('time')
    if as_of is not None:
        df = df[df['time'] <= pd.Timestamp(as_of).normalize()]
    df = df.dropna(subset=['close'])
    if df.empty:
        return out, None

    # đơn vị: nghìn đồng → VND (quyết định theo trung vị cả chuỗi)
    if df['close'].median() < config.PRICE_UNIT_CONFIG['threshold']:
        for col in ('open', 'high', 'low', 'close'):
            if col in df:
                df[col] = df[col] * config.PRICE_UNIT_CONFIG['multiplier']

    close = df['close'].astype(float).reset_index(drop=True)
    last_date = df['time'].iloc[-1]
    out['price_vnd'] = float(close.iloc[-1])
    if len(close) > 20:
        out['ret_20d'] = float(close.iloc[-1] / close.iloc[-21] - 1) * 100
    if len(close) > 60:
        out['ret_60d'] = float(close.iloc[-1] / close.iloc[-61] - 1) * 100
    if len(close) >= 50:
        out['dist_ma50'] = float(close.iloc[-1] / close.tail(50).mean() - 1) * 100
    if len(close) > 15:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] > 0 else np.inf
        out['rsi14'] = float(100 - 100 / (1 + rs)) if np.isfinite(rs) else 100.0
    if len(close) > 20:
        out['vol_20d'] = float(close.pct_change().tail(20).std() * 100)
    if 'volume' in df and len(df) >= 20:
        vol = df['volume'].astype(float).reset_index(drop=True)
        out['liquidity_bn'] = float((close.tail(20) * vol.tail(20)).mean() / 1e9)
    if len(close) >= 120:
        window = df.tail(252)
        hi = float(window['high'].max()) if 'high' in window else float(close.tail(252).max())
        lo = float(window['low'].min()) if 'low' in window else float(close.tail(252).min())
        if hi > lo:
            out['range_pos'] = (out['price_vnd'] - lo) / (hi - lo) * 100
            out['from_high'] = (out['price_vnd'] / hi - 1) * 100
    return out, last_date


def build_fact_sheet(symbol, row, price_df, market_filter=None, same_sector_in_shortlist=None, as_of=None):
    """
    Args:
        row: dict/Series gộp analysis_report + financial_metrics (Total_Score, Fund_Score, Tech_Score,
             ROE, PE, PB, Debt_Equity, Profit_Growth_YoY, Revenue_Growth_YoY, Sector, Gate_Warnings)
        price_df: lịch sử giá thô (cột time, open, high, low, close, volume)
        same_sector_in_shortlist: số mã MUA cùng ngành trong danh sách đang xét (kể cả mã này)
    """
    stats, data_date = price_stats(price_df, as_of)
    sheet = FactSheet(symbol, (data_date.date() if data_date is not None else as_of) or 'unknown')
    g = row.get if hasattr(row, 'get') else (lambda k, d=None: d)

    sheet.add('Điểm tổng hệ thống', g('Total_Score'), '/10', 1)
    sheet.add('Điểm cơ bản', g('Fund_Score'), '/10', 1)
    sheet.add('Điểm kỹ thuật', g('Tech_Score'), '/10', 1)
    sheet.add('ROE (TTM)', g('ROE'), '%', 1)
    sheet.add('P/E', g('PE'), 'x', 1)
    sheet.add('P/B', g('PB'), 'x', 2)
    sheet.add('Nợ phải trả / Vốn chủ', g('Debt_Equity'), 'x', 2)
    sheet.add('Tăng trưởng lợi nhuận YoY', g('Profit_Growth_YoY'), '%', 1)
    sheet.add('Tăng trưởng doanh thu YoY', g('Revenue_Growth_YoY'), '%', 1)

    sheet.add('Giá hiện tại', stats.get('price_vnd'), 'VND', 0)
    sheet.add('Lợi suất 20 phiên', stats.get('ret_20d'), '%', 1)
    sheet.add('Lợi suất 60 phiên', stats.get('ret_60d'), '%', 1)
    sheet.add('Giá so với MA50', stats.get('dist_ma50'), '%', 1)
    sheet.add('RSI 14', stats.get('rsi14'), '', 1)
    sheet.add('Biến động ngày (độ lệch chuẩn 20 phiên)', stats.get('vol_20d'), '%', 2)
    sheet.add('Thanh khoản TB 20 phiên', stats.get('liquidity_bn'), 'tỷ VND/ngày', 1)
    sheet.add('Vị trí trong biên giá 52 tuần', stats.get('range_pos'), '% (0=đáy, 100=đỉnh)', 0)
    sheet.add('Cách đỉnh 52 tuần', stats.get('from_high'), '%', 1)

    if market_filter:
        sheet.add('Breadth thị trường (mã trên SMA10&20)', _num(market_filter.get('pct_above_both')) * 100
                  if _num(market_filter.get('pct_above_both')) is not None else None, '%', 0)
        sheet.add('Trạng thái thị trường', market_filter.get('sentiment'))
    sheet.add('Ngành', g('Sector'))
    if same_sector_in_shortlist is not None:
        sheet.add('Số mã MUA cùng ngành trong danh sách xét', same_sector_in_shortlist, '', 0)
    warnings = g('Gate_Warnings')
    if isinstance(warnings, str) and warnings.strip():
        sheet.add('Cảnh báo dữ liệu của hệ thống', warnings)
    return sheet
