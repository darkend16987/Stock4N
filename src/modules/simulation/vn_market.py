"""
Quy tắc thị trường HOSE dùng cho backtest: bước giá, biên độ, chi phí giao dịch.

Chỉ mô phỏng sàn HOSE (VN100 gồm các mã niêm yết HOSE). Mọi giá ở đây tính bằng VND (không phải nghìn đồng).
Phí môi giới/thuế là giá trị mặc định trong config.BACKTEST_V2 - cần đối chiếu biểu phí công ty chứng khoán.
"""
import math
import os
import sys
from dataclasses import dataclass, replace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

# (giá từ, bước giá): <10,000: 10đ | 10,000 - <50,000: 50đ | >= 50,000: 100đ
HOSE_TICK_TABLE = ((0, 10), (10_000, 50), (50_000, 100))

_EPS = 1e-9


def tick_size(price):
    step = HOSE_TICK_TABLE[0][1]
    for lower, tick in HOSE_TICK_TABLE:
        if price >= lower:
            step = tick
    return step


def round_down_to_tick(price):
    tick = tick_size(price)
    return math.floor(price / tick + _EPS) * tick


def round_up_to_tick(price):
    tick = tick_size(price)
    return math.ceil(price / tick - _EPS) * tick


def price_band(ref_price, limit=None):
    """
    Biên độ ngày theo giá tham chiếu (đóng cửa phiên trước).
    Trần làm tròn xuống, sàn làm tròn lên bước giá. limit None/0 → không giới hạn.
    """
    limit = config.BACKTEST_V2['price_limit'] if limit is None else limit
    if not limit:
        return 0.0, float('inf')
    ceiling = round_down_to_tick(ref_price * (1 + limit))
    floor = round_up_to_tick(ref_price * (1 - limit))
    return floor, ceiling


@dataclass(frozen=True)
class CostModel:
    fee_rate: float = config.BACKTEST_V2['fee_rate']
    sell_tax_rate: float = config.BACKTEST_V2['sell_tax_rate']
    slippage: float = config.BACKTEST_V2['slippage']
    lot_size: int = config.BACKTEST_V2['lot_size']

    def buy_fill_price(self, reference_price):
        """Giá mua khớp: giá tham chiếu trượt lên, làm tròn lên bước giá."""
        return round_up_to_tick(reference_price * (1 + self.slippage))

    def sell_fill_price(self, reference_price):
        """Giá bán khớp: giá tham chiếu trượt xuống, làm tròn xuống bước giá."""
        return round_down_to_tick(reference_price * (1 - self.slippage))

    def buy_cost(self, shares, price):
        """Tổng tiền phải trả khi mua (gồm phí)."""
        return shares * price * (1 + self.fee_rate)

    def sell_proceeds(self, shares, price):
        """Tiền thực nhận khi bán (đã trừ phí và thuế)."""
        return shares * price * (1 - self.fee_rate - self.sell_tax_rate)

    def max_affordable_shares(self, cash, price):
        """Số cổ (bội của lô) mua được với `cash` sau phí."""
        per_share = price * (1 + self.fee_rate)
        if per_share <= 0:
            return 0
        return int(cash / per_share // self.lot_size) * self.lot_size

    def stressed(self, multiplier):
        """Bản nhân đôi (hoặc nhân k) phí, thuế, trượt giá - dùng cho kiểm tra độ bền."""
        return replace(self,
                       fee_rate=self.fee_rate * multiplier,
                       sell_tax_rate=self.sell_tax_rate * multiplier,
                       slippage=self.slippage * multiplier)
