"""
Stock Option Skill — Bộ quy tắc chiến lược đầu tư cho AI Reasoner.

Mã hoá toàn bộ khẩu vị, chiến lược và quy trình lọc cổ phiếu
phù hợp với profile: NHÀ ĐẦU TƯ TRUNG HẠN, ƯA AN TOÀN.

AI Reasoner sẽ dùng context từ module này để:
  1. Lọc sơ bộ trước khi phân tích sâu (pre-screen)
  2. Đánh giá opportunity theo đúng khẩu vị rủi ro
  3. Gợi ý hành động phù hợp (mua / giữ / bán)
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class StockOptionSkill:
    """
    Skill đầu tư trung hạn, an toàn cho thị trường VN.

    Workflow:
        1. pre_screen()     → Lọc sơ bộ theo hard rules
        2. evaluate()       → Chấm điểm cơ hội
        3. get_ai_context() → Cung cấp context cho AI Reasoner
        4. suggest_action() → Đề xuất hành động cụ thể
    """

    # ── Investor Profile ──────────────────────────────
    PROFILE = {
        'name': 'Nhà đầu tư trung hạn an toàn',
        'horizon': '3-6 tháng',
        'risk_appetite': 'Thấp - Trung bình (Conservative)',
        'focus': 'Blue-chip VN30 + Mid-cap chất lượng',
        'strategy': 'Fundamental-first, Technical timing',
        'weight_fundamental': 0.65,
        'weight_technical': 0.35,
    }

    # ── Hard Rules (không thoả = loại ngay) ───────────
    HARD_RULES = {
        'min_score': 6.5,          # Điểm tổng tối thiểu
        'min_roe': 10,             # ROE tối thiểu 10%
        'max_pe': 30,              # P/E tối đa 30x
        'max_debt_equity': 2.0,    # Nợ/vốn tối đa 2.0
        'min_breadth': 0.35,       # Market breadth tối thiểu 35%
        'max_position_pct': 0.20,  # Tối đa 20% 1 vị thế
        'max_positions': 8,        # Tối đa 8 mã
        'cash_reserve': 0.25,      # Giữ 25% tiền mặt
    }

    # ── Scoring Preferences ───────────────────────────
    PREFERENCES = {
        'stop_loss_pct': 0.05,     # Cắt lỗ 5%
        'target_profit_pct': 0.12, # Chốt lời 12%
        'min_risk_reward': 2.0,    # R:R tối thiểu 1:2
        'prefer_dividend': True,   # Ưu tiên cổ tức
        'avoid_penny': True,       # Tránh penny stock (< 10k)
        'prefer_high_volume': True, # Ưu tiên thanh khoản cao
    }

    # ── Strategy Steps ────────────────────────────────
    STRATEGY_STEPS = [
        "B1: Kiểm tra Market Breadth — nếu < 35% thì KHÔNG MUA MỚI, chỉ giữ/cắt lỗ",
        "B2: Lọc sơ bộ — ROE >= 10%, P/E <= 30, Nợ/Vốn <= 2.0",
        "B3: Chấm điểm tổng (Fundamental 65% + Technical 35%) — chỉ xét mã >= 6.5/10",
        "B4: Kiểm tra xu hướng — RSI 40-65 (neutral-bullish), giá trên MA50",
        "B5: Xác nhận Volume — volume trung bình 20 phiên phải đủ thanh khoản",
        "B6: Phân bổ vốn — tối đa 20%/mã, giữ 25% tiền mặt, tối đa 8 mã",
        "B7: Đặt Stop Loss -5% và Target +12%, R:R >= 1:2",
        "B8: Review hàng tuần — cắt lỗ nghiêm túc, không trung bình giá xuống",
    ]

    # ── AI Context Prompt ─────────────────────────────
    AI_CONTEXT_TEMPLATE = """
## Hồ sơ Nhà đầu tư
- Phong cách: {profile_name}
- Tầm nhìn: {horizon}
- Khẩu vị rủi ro: {risk}
- Chiến lược: Phân tích cơ bản {w_fund}% + Kỹ thuật {w_tech}%

## Quy tắc cứng
- Chỉ mua khi Market Breadth > 35%
- Điểm tổng >= 6.5/10
- ROE >= 10% | P/E <= 30 | Nợ/Vốn <= 2.0
- Stop Loss: -5% | Target: +12% | R:R >= 1:2
- Tối đa 8 vị thế, mỗi vị thế <= 20%, giữ 25% cash

## Quy trình 8 bước
{steps}

## Yêu cầu phân tích
- Đánh giá theo đúng khẩu vị AN TOÀN trên
- Nêu rõ MUA / GIỮ / BÁN kèm lý do
- Cảnh báo rủi ro cụ thể (nếu có)
- Gợi ý mức giá entry, stop loss, target
"""

    def get_ai_context(self) -> str:
        """Trả về context string để prepend vào prompt của AI Reasoner."""
        steps = "\n".join(f"  {s}" for s in self.STRATEGY_STEPS)
        return self.AI_CONTEXT_TEMPLATE.format(
            profile_name=self.PROFILE['name'],
            horizon=self.PROFILE['horizon'],
            risk=self.PROFILE['risk_appetite'],
            w_fund=int(self.PROFILE['weight_fundamental'] * 100),
            w_tech=int(self.PROFILE['weight_technical'] * 100),
            steps=steps,
        )

    def pre_screen(self, stock_data: dict) -> dict:
        """
        Lọc sơ bộ theo hard rules.

        Args:
            stock_data: dict chứa score, roe, pe_ratio, debt_equity, ...

        Returns:
            {'passed': bool, 'reasons': list[str]}
        """
        reasons = []
        passed = True

        score = stock_data.get('score', 0)
        if score < self.HARD_RULES['min_score']:
            reasons.append(f"Điểm {score:.1f} < {self.HARD_RULES['min_score']} (quá thấp)")
            passed = False

        roe = stock_data.get('roe')
        if roe is not None and roe < self.HARD_RULES['min_roe']:
            reasons.append(f"ROE {roe:.1f}% < {self.HARD_RULES['min_roe']}%")
            passed = False

        pe = stock_data.get('pe_ratio')
        if pe is not None and pe > self.HARD_RULES['max_pe']:
            reasons.append(f"P/E {pe:.1f} > {self.HARD_RULES['max_pe']} (quá đắt)")
            passed = False

        de = stock_data.get('debt_equity')
        if de is not None and de > self.HARD_RULES['max_debt_equity']:
            reasons.append(f"Nợ/Vốn {de:.2f} > {self.HARD_RULES['max_debt_equity']}")
            passed = False

        price = stock_data.get('price', 0)
        if self.PREFERENCES['avoid_penny'] and 0 < price < 10000:
            reasons.append(f"Penny stock (giá {price:,.0f} < 10,000)")
            passed = False

        if not reasons:
            reasons.append("Thoả tất cả điều kiện sơ bộ")

        return {'passed': passed, 'reasons': reasons}

    def evaluate_opportunity(self, stock_data: dict, market_breadth: float = 0.5) -> dict:
        """
        Đánh giá cơ hội đầu tư.

        Returns:
            {
                'action': 'MUA' | 'GIỮ' | 'THEO DÕI' | 'BÁN',
                'confidence': float 0-1,
                'entry_zone': str,
                'stop_loss': float,
                'target': float,
                'reasons': list[str]
            }
        """
        screen = self.pre_screen(stock_data)
        score = stock_data.get('score', 0)
        price = stock_data.get('price', 0)
        rsi = stock_data.get('rsi', 50)

        # Market breadth check
        if market_breadth < self.HARD_RULES['min_breadth']:
            return {
                'action': 'THEO DÕI',
                'confidence': 0.3,
                'entry_zone': 'Chưa phù hợp (thị trường yếu)',
                'stop_loss': 0,
                'target': 0,
                'reasons': [f"Market breadth {market_breadth:.0%} < {self.HARD_RULES['min_breadth']:.0%}"]
            }

        if not screen['passed']:
            return {
                'action': 'THEO DÕI' if score >= 5.0 else 'BÁN',
                'confidence': 0.4,
                'entry_zone': 'Không đủ điều kiện',
                'stop_loss': 0,
                'target': 0,
                'reasons': screen['reasons']
            }

        # Calculate levels
        stop_loss = price * (1 - self.PREFERENCES['stop_loss_pct']) if price else 0
        target = price * (1 + self.PREFERENCES['target_profit_pct']) if price else 0

        # Determine action
        if score >= 7.5 and 35 <= rsi <= 65:
            action = 'MUA MẠNH'
            confidence = min(0.9, score / 10)
        elif score >= 6.5:
            action = 'MUA THĂM DÒ'
            confidence = min(0.75, score / 10)
        elif score >= 5.0:
            action = 'GIỮ'
            confidence = 0.5
        else:
            action = 'BÁN'
            confidence = 0.6

        reasons = screen['reasons']
        if rsi and rsi > 70:
            reasons.append(f"RSI={rsi:.0f} quá mua — cân nhắc chờ điều chỉnh")
            confidence *= 0.8
        if rsi and rsi < 30:
            reasons.append(f"RSI={rsi:.0f} quá bán — cơ hội nếu cơ bản tốt")

        return {
            'action': action,
            'confidence': round(confidence, 2),
            'entry_zone': f"{price:,.0f}" if price else "N/A",
            'stop_loss': round(stop_loss),
            'target': round(target),
            'reasons': reasons,
        }

    def get_position_size(self, capital: float, num_current_positions: int) -> dict:
        """
        Tính position size phù hợp.

        Args:
            capital: Tổng vốn (VND)
            num_current_positions: Số vị thế hiện tại

        Returns:
            {'available_capital': float, 'max_per_position': float, 'can_open_new': bool}
        """
        investable = capital * (1 - self.HARD_RULES['cash_reserve'])
        can_open = num_current_positions < self.HARD_RULES['max_positions']
        max_per = investable * self.HARD_RULES['max_position_pct']

        return {
            'available_capital': round(investable),
            'max_per_position': round(max_per),
            'can_open_new': can_open,
            'remaining_slots': max(0, self.HARD_RULES['max_positions'] - num_current_positions),
        }
