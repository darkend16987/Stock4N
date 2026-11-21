"""
Rule Gate - Áp dụng QUY TẮC CỨNG của nhà đầu tư lên khuyến nghị MUA.

Trước đây các quy tắc này (ROE, P/E, Nợ/Vốn, breadth, penny) chỉ nằm trong prompt của AI
và hàm pre_screen() không ai gọi → hệ thống vẫn khuyến nghị mua mã vi phạm quy tắc.

Nguyên tắc:
  - Chỉ HẠ khuyến nghị (MUA → THEO DÕI), không bao giờ nâng.
  - Thiếu dữ liệu ROE → không thể xác minh chất lượng → KHÔNG mua (fail-closed).
  - Thiếu P/E hoặc Nợ/Vốn (mã phi tài chính) → cảnh báo, ghi vào Gate_Warnings, chưa chặn
    (thiếu dữ liệu phụ thường do định dạng nguồn đổi; calculator đã log độ phủ dữ liệu).
  - Nhóm tài chính (ngân hàng, chứng khoán, bảo hiểm) không áp trần Nợ/Vốn.
"""
import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.units import price_to_vnd

logger = get_logger(__name__)


class RuleGate:
    """Kiểm tra từng mã theo config.HARD_RULES + bối cảnh thị trường (breadth)."""

    def __init__(self, rules=None, sector_map=None, financial_sectors=None):
        self.rules = rules if rules is not None else config.HARD_RULES
        self.sector_map = sector_map if sector_map is not None else config.SECTOR_MAP
        self.financial_sectors = (financial_sectors if financial_sectors is not None
                                  else config.FINANCIAL_SECTORS)

    def sector_of(self, symbol):
        return self.sector_map.get(symbol, 'Khác')

    def evaluate(self, row, market_filter=None):
        """
        Args:
            row: dict/Series có Symbol, Price, ROE, PE, Debt_Equity, Total_Score
            market_filter: output của MarketBreadthAnalyzer.get_market_filter() (hoặc None)

        Returns:
            {'passed': bool, 'reasons': [str], 'warnings': [str]}
            reasons = lý do bị chặn; warnings = dữ liệu thiếu nhưng chưa chặn.
        """
        r = self.rules
        symbol = row.get('Symbol', '?')
        sector = self.sector_of(symbol)
        is_financial = sector in self.financial_sectors
        reasons, warnings = [], []

        # 1. Điểm tổng
        score = row.get('Total_Score')
        if score is not None and pd.notna(score) and score < r['min_score']:
            reasons.append(f"Điểm {score:.1f} < {r['min_score']}")

        # 2. ROE (bắt buộc)
        roe = row.get('ROE')
        if roe is None or pd.isna(roe):
            reasons.append("Thiếu ROE - không xác minh được chất lượng")
        elif roe < r['min_roe']:
            reasons.append(f"ROE {roe:.1f}% < {r['min_roe']}%")

        # 3. P/E
        pe = row.get('PE')
        if pe is None or pd.isna(pe):
            warnings.append("Thiếu P/E (lỗ TTM hoặc thiếu dữ liệu)")
        elif pe > r['max_pe']:
            reasons.append(f"P/E {pe:.1f} > {r['max_pe']}")

        # 4. Nợ/Vốn (bỏ qua nhóm tài chính)
        if not is_financial:
            de = row.get('Debt_Equity')
            if de is None or pd.isna(de):
                warnings.append("Thiếu Nợ/Vốn")
            else:
                cap = r.get('max_debt_equity_by_sector', {}).get(sector, r['max_debt_equity'])
                if de > cap:
                    reasons.append(f"Nợ/Vốn {de:.2f} > {cap}")

        # 5. Penny stock
        price = row.get('Price')
        if price is not None and pd.notna(price) and price > 0:
            price_vnd = price_to_vnd(price)
            if price_vnd < r['min_price_vnd']:
                reasons.append(f"Penny stock (giá {price_vnd:,.0f} < {r['min_price_vnd']:,})")

        # 6. Breadth thị trường
        if market_filter:
            if not market_filter.get('allow_new_buys', True):
                reasons.append(f"Thị trường {market_filter.get('sentiment', '?')} - không mua mới")
            pct = market_filter.get('pct_above_both')
            if pct is not None and pct < r['min_breadth']:
                reasons.append(f"Breadth {pct:.0%} < {r['min_breadth']:.0%}")

        return {'passed': not reasons, 'reasons': reasons, 'warnings': warnings}
