"""
BacktestEngineV2 - backtest point-in-time, sát quy tắc giao dịch HOSE.

Khác engine cũ (BacktestEngine):
  - KHÔNG dùng điểm của hôm nay để mua trong quá khứ: mỗi ngày quét tín hiệu chỉ dùng dữ liệu <= ngày đó
    (giá, báo cáo tài chính có độ trễ công bố, breadth, tương quan)
  - Tín hiệu chốt cuối phiên t → khớp lệnh tại GIÁ MỞ CỬA phiên t+1
  - Dùng CHUNG đường chấm điểm/RuleGate/chọn danh mục/chia vốn với bản live
    (StockScorer.score_symbol, PortfolioManager.select_candidates/compute_allocation)
  - T+2: mua phiên N được bán từ phiên N+2, tiền bán về sau N+2
  - Biên độ ±7% (không mua tại trần, không bán tại sàn), bước giá, lô 100, phí 0.15%/chiều, thuế bán 0.10%, trượt giá 0.1%
  - Stop -7% / target +15% kiểm tra bằng high/low trong ngày; cùng ngày chạm cả hai → tính stop (bảo thủ)
  - Chia chung một vốn cho cả danh mục (engine cũ chạy từng mã tuần tự)

Hạn chế đã biết (xem validation.py và báo cáo): universe = VN100 hiện tại (thiên lệch sống sót), độ trễ công bố
báo cáo là giả định, số cổ phiếu cho P/E là ước lượng, chỉ mô phỏng HOSE.
"""
import json
import os
import sys
from dataclasses import dataclass, field

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.analysis.scorer import StockScorer
from modules.portfolio.manager import PortfolioManager
from modules.processing.calculator import FinancialCalculator
from modules.simulation import validation
from modules.simulation.point_in_time import PriceBook
from modules.simulation.vn_market import CostModel, price_band, round_up_to_tick
from modules.utils.logger import get_logger

logger = get_logger(__name__)

_EPS = 1e-6


@dataclass
class BacktestResult:
    equity: pd.Series
    invested: pd.Series
    trades: pd.DataFrame
    rebalances: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    cash: pd.Series = None     # tiền mặt đã về tài khoản (chưa gồm tiền bán chờ T+2), dùng để kiểm tra sổ sách


class BacktestEngineV2:
    def __init__(self, raw_dir=config.RAW_DIR, symbols=None, params=None, cost_model=None,
                 price_book=None, scorer=None, calculator=None):
        self.raw_dir = raw_dir
        self.params = {**config.BACKTEST_V2, **(params or {})}
        self.cost = cost_model or CostModel(
            fee_rate=self.params['fee_rate'], sell_tax_rate=self.params['sell_tax_rate'],
            slippage=self.params['slippage'], lot_size=self.params['lot_size'])
        self.symbols = symbols if symbols is not None else config.VN100_SYMBOLS
        self.book = price_book or PriceBook(raw_dir, self.symbols)
        self.scorer = scorer or StockScorer(data_dir=raw_dir)
        self.calculator = calculator or FinancialCalculator(data_dir=raw_dir, cache_raw=True)
        self.risk = config.RISK_MANAGEMENT
        self.portfolio_cfg = config.PORTFOLIO_CONFIG

        self._as_of = None
        self.manager = PortfolioManager(
            raw_dir=raw_dir,
            returns_provider=lambda sym: self.book.returns(sym, self._as_of,
                                                           self.portfolio_cfg.get('correlation_lookback', 60)))

    # ------------------------------------------------------------------ signals
    def _generate_signals(self, date, positions, cash_next, equity, held_value):
        """Quét tín hiệu CUỐI phiên `date` → danh sách lệnh mua sẽ khớp ở phiên kế tiếp."""
        info = {'date': str(date.date()), 'n_scored': 0, 'n_buy': 0, 'n_orders': 0, 'sentiment': None}

        mf = self.book.market_filter(date)
        if mf is None:
            info['note'] = 'no_breadth'
            return [], info
        info['sentiment'] = mf['sentiment']
        info['pct_above_both'] = mf['pct_above_both']
        if not mf.get('allow_new_buys', True):
            info['note'] = 'market_blocks_buys'
            return [], info

        rows = []
        for symbol in self.book.symbols:
            if symbol in positions:
                continue
            if self.book.bar(symbol, date) is None:        # không giao dịch hôm nay
                continue
            history = self.book.history(symbol, date)
            if history is None or len(history) < 50:
                continue
            metrics = self.calculator.calculate_metrics(symbol, as_of=date)
            if metrics is None:
                continue
            rows.append(self.scorer.score_symbol(metrics, mf, price_df=history))
        info['n_scored'] = len(rows)
        if not rows:
            return [], info

        scored = pd.DataFrame(rows)
        buy_list = (scored[scored['Recommendation'].str.contains('MUA', na=False)]
                    .drop_duplicates('Symbol').sort_values('Total_Score', ascending=False))
        info['n_buy'] = int(len(buy_list))
        if buy_list.empty:
            return [], info

        reserve = self.portfolio_cfg.get('cash_reserve_pct', 0)
        investable = equity * (1 - reserve) * mf.get('risk_multiplier', 1.0)
        budget = min(investable - held_value, cash_next)
        if budget <= 0:
            info['note'] = 'no_budget'
            return [], info

        self._as_of = date
        selected = self.manager.select_candidates(buy_list, investable, held_symbols=list(positions))
        if not selected:
            return [], info

        orders, remaining = [], budget
        for alloc in self.manager.compute_allocation(pd.DataFrame(selected), investable):
            amount = min(alloc['amount'], remaining)
            if amount < alloc['price'] * self.cost.lot_size:
                continue
            remaining -= amount
            orders.append({'symbol': alloc['symbol'], 'amount': amount, 'score': float(alloc['score']),
                           'sector': alloc['row'].get('Sector') if 'Sector' in alloc['row'] else None})
        info['n_orders'] = len(orders)
        return orders, info

    # ------------------------------------------------------------------ execution
    def _try_buy(self, order, date, idx, cash, positions):
        """Khớp lệnh mua tại giá mở cửa. Trả (cash còn lại, bản ghi lệnh hoặc None nếu không khớp)."""
        symbol = order['symbol']
        bar = self.book.bar(symbol, date)
        ref = self.book.prev_close(symbol, date)
        if bar is None or ref is None or symbol in positions:
            return cash, None
        fill = self.cost.buy_fill_price(float(bar['open']))
        _, ceiling = price_band(ref, self.params['price_limit'])
        if fill >= ceiling - _EPS:                         # mở cửa tại trần: không mua được
            return cash, None
        budget = min(order['amount'], cash)
        shares = self.cost.max_affordable_shares(budget, fill)
        if shares <= 0:
            return cash, None
        cost = self.cost.buy_cost(shares, fill)
        positions[symbol] = {
            'shares': shares, 'entry_price': fill, 'entry_idx': idx, 'entry_date': date,
            'settle_idx': idx + self.params['settlement_sessions'],
            'cost_total': cost, 'stop_pending': False, 'score': order['score'],
            'sector': order.get('sector'),
        }
        trade = {'date': date, 'symbol': symbol, 'action': 'BUY', 'price': fill, 'shares': shares,
                 'gross': shares * fill, 'fees': cost - shares * fill, 'pnl': 0.0, 'return_pct': 0.0,
                 'hold_sessions': 0, 'reason': f"Score={order['score']:.1f}", 'score': order['score'],
                 'sector': order.get('sector')}
        return cash - cost, trade

    def _exit_decision(self, pos, symbol, bar, ref_close, idx):
        """
        Quyết định bán tại phiên hiện tại (chỉ gọi khi đã qua T+2).
        Trả (giá khớp, lý do) hoặc None. Giá bán đã gồm trượt giá; bị chặn nếu khớp tại sàn.
        """
        entry = pos['entry_price']
        stop = entry * (1 - self.risk['stop_loss_pct'])
        target_limit = round_up_to_tick(entry * (1 + self.risk['target_profit_pct']))
        o, h, low = float(bar['open']), float(bar['high']), float(bar['low'])

        price, reason, ref_px = None, None, None
        if pos['stop_pending'] or o <= stop:                 # stop kích hoạt trước/qua đêm → bán thị trường tại mở cửa
            ref_px, reason = o, 'STOP_LOSS'
            price = self.cost.sell_fill_price(ref_px)
        elif low <= stop:                                    # chạm stop trong ngày
            ref_px, reason = stop, 'STOP_LOSS'
            price = self.cost.sell_fill_price(ref_px)
        elif o >= target_limit:                              # gap lên qua target: khớp tại mở cửa
            ref_px, reason = o, 'TAKE_PROFIT'
            price = int(o)
        elif h >= target_limit:                              # lệnh limit tại target
            ref_px, reason = target_limit, 'TAKE_PROFIT'
            price = target_limit
        elif idx - pos['entry_idx'] >= self.params['max_hold_sessions']:
            ref_px, reason = o, 'MAX_HOLD'
            price = self.cost.sell_fill_price(ref_px)
        if price is None:
            return None

        floor, ceiling = price_band(ref_close, self.params['price_limit'])
        if ref_px <= floor + _EPS:                           # thị trường nằm sàn: không có người mua → chưa bán được
            pos['stop_pending'] = pos['stop_pending'] or reason == 'STOP_LOSS'
            return None
        return min(max(price, floor), ceiling), reason       # trượt giá không đẩy giá bán xuống dưới sàn

    def _sell(self, symbol, pos, price, date, idx, reason):
        proceeds = self.cost.sell_proceeds(pos['shares'], price)
        pnl = proceeds - pos['cost_total']
        trade = {'date': date, 'symbol': symbol, 'action': 'SELL', 'price': price, 'shares': pos['shares'],
                 'gross': pos['shares'] * price, 'fees': pos['shares'] * price - proceeds, 'pnl': pnl,
                 'return_pct': pnl / pos['cost_total'] * 100, 'hold_sessions': idx - pos['entry_idx'],
                 'reason': reason, 'score': pos['score'], 'sector': pos['sector']}
        return proceeds, trade

    # ------------------------------------------------------------------ main loop
    def run(self, start_date=None, end_date=None):
        p = self.params
        calendar = [d for d in self.book.calendar
                    if (start_date is None or d >= pd.Timestamp(start_date))
                    and (end_date is None or d <= pd.Timestamp(end_date))]
        if len(calendar) <= p['warmup_sessions'] + 2:
            raise ValueError(f"Chỉ có {len(calendar)} phiên, cần > warmup ({p['warmup_sessions']}) + 2")

        cash = float(p['initial_capital'])
        pending_cash = []            # (phiên được dùng, số tiền)
        positions, orders = {}, []
        trades, equity, invested, rebalances, cash_series = [], {}, {}, [], {}

        for i, date in enumerate(calendar):
            # 1. Tiền bán đã về tài khoản
            released = [x for x in pending_cash if x[0] <= i]
            cash += sum(a for _, a in released)
            pending_cash = [x for x in pending_cash if x[0] > i]

            # 2. Xử lý vị thế hiện có (bán / đánh dấu stop khi còn bị khoá T+2)
            for symbol in list(positions):
                pos = positions[symbol]
                bar = self.book.bar(symbol, date)
                if bar is None:
                    continue
                if i < pos['settle_idx']:
                    if float(bar['low']) <= pos['entry_price'] * (1 - self.risk['stop_loss_pct']):
                        pos['stop_pending'] = True
                    continue
                decision = self._exit_decision(pos, symbol, bar, self.book.prev_close(symbol, date), i)
                if decision:
                    price, reason = decision
                    proceeds, trade = self._sell(symbol, pos, price, date, i, reason)
                    pending_cash.append((i + p['settlement_sessions'], proceeds))
                    trades.append(trade)
                    del positions[symbol]

            # 3. Khớp lệnh mua đã đặt cuối phiên trước tại giá mở cửa
            for order in orders:
                cash, trade = self._try_buy(order, date, i, cash, positions)
                if trade:
                    trades.append(trade)
            orders = []

            # 4. Định giá cuối phiên
            held_value = sum(pos['shares'] * (self.book.last_close(sym, date) or pos['entry_price'])
                             for sym, pos in positions.items())
            pending_total = sum(a for _, a in pending_cash)
            total_equity = cash + pending_total + held_value
            equity[date] = total_equity
            cash_series[date] = cash
            invested[date] = held_value / total_equity if total_equity > 0 else 0.0

            # 5. Quét tín hiệu cuối phiên (khớp ở phiên kế tiếp)
            is_last = i == len(calendar) - 1
            if (not is_last and i >= p['warmup_sessions']
                    and (i - p['warmup_sessions']) % p['rebalance_every'] == 0):
                cash_next = cash + sum(a for u, a in pending_cash if u <= i + 1)
                orders, info = self._generate_signals(date, positions, cash_next, total_equity, held_value)
                rebalances.append(info)

        # Đóng toàn bộ vị thế ở phiên cuối (có phí/thuế/trượt giá, bỏ qua khoá T+2) để kết quả sạch
        last_date, last_idx = calendar[-1], len(calendar) - 1
        for symbol in list(positions):
            pos = positions[symbol]
            close = self.book.last_close(symbol, last_date) or pos['entry_price']
            price = self.cost.sell_fill_price(close)
            proceeds, trade = self._sell(symbol, pos, price, last_date, last_idx, 'END_OF_BACKTEST')
            cash += proceeds
            trades.append(trade)
            del positions[symbol]
        equity[last_date] = cash + sum(a for _, a in pending_cash)
        cash_series[last_date] = cash
        invested[last_date] = 0.0

        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame(
            columns=['date', 'symbol', 'action', 'price', 'shares', 'gross', 'fees', 'pnl', 'return_pct',
                     'hold_sessions', 'reason', 'score', 'sector'])
        meta = {'universe_requested': len(self.symbols), 'universe_with_prices': len(self.book.symbols),
                'sessions': len(calendar), 'params': p,
                'fee_rate': self.cost.fee_rate, 'sell_tax_rate': self.cost.sell_tax_rate,
                'slippage': self.cost.slippage}
        return BacktestResult(equity=pd.Series(equity), invested=pd.Series(invested), trades=trades_df,
                              rebalances=rebalances, meta=meta, cash=pd.Series(cash_series))

    # ------------------------------------------------------------------ validation suite
    def run_suite(self, start_date=None, end_date=None, output_dir=None, write=True):
        """Chạy base + kiểm tra chịu chi phí x2, tính chỉ số, bootstrap, Monte Carlo, walk-forward, nghiệm thu."""
        p = self.params
        base = self.run(start_date, end_date)
        bench, bench_label = self.book.benchmark()

        metrics = validation.compute_metrics(base.equity, base.trades, bench, base.invested,
                                             rf_annual=p['risk_free_annual'])
        metrics['benchmark'] = bench_label
        bootstrap = validation.block_bootstrap_sharpe(
            base.equity.pct_change().dropna(), p['risk_free_annual'], p['bootstrap_resamples'],
            p['bootstrap_block'], p['seed'])
        mc = validation.monte_carlo_drawdown(base.trades, p['initial_capital'], p['mc_resamples'], p['seed'])
        metrics['walk_forward'] = validation.walk_forward(base.equity, bench, p['walk_forward_windows'])

        mult = config.BACKTEST_ACCEPTANCE['cost_stress_multiplier']
        stress_engine = BacktestEngineV2(
            raw_dir=self.raw_dir, symbols=self.symbols, params=self.params, cost_model=self.cost.stressed(mult),
            price_book=self.book, scorer=self.scorer, calculator=self.calculator)
        stress = stress_engine.run(start_date, end_date)
        stress_return = float(stress.equity.iloc[-1] / stress.equity.iloc[0] - 1)

        acceptance = validation.evaluate_acceptance(metrics, bootstrap, mc, stress_return)
        report = {'metrics': metrics, 'bootstrap': bootstrap, 'monte_carlo': mc,
                  'cost_stress': {'multiplier': mult, 'total_return': stress_return},
                  'acceptance': acceptance, 'meta': base.meta,
                  'limitations': self.limitations(bench_label, base.meta)}

        if write:
            self._write_report(report, base, output_dir or os.path.join(config.DATA_DIR, 'backtest'))
        return report, base

    @staticmethod
    def limitations(bench_label, meta):
        notes = [
            "Universe là danh sách VN100 HIỆN TẠI: thiên lệch sống sót (mã đã rớt khỏi VN100/hủy niêm yết không có trong mẫu) → kết quả lạc quan.",
            f"Độ trễ công bố báo cáo là GIẢ ĐỊNH ({config.REPORTING_LAG_DAYS}), chưa đối chiếu ngày công bố thực.",
            "Số cổ phiếu cho P/E, P/B ước lượng = vốn góp / 10,000đ (bỏ qua cổ phiếu quỹ, phát hành mới).",
            "Ngưỡng chấm điểm trong config có thể đã được chọn khi nhìn dữ liệu → có rủi ro overfit không kiểm soát được ở đây.",
            "Chỉ mô phỏng HOSE; khớp lệnh tại giá mở cửa + trượt giá cố định, không mô phỏng thanh khoản/khối lượng.",
            "Phí môi giới/thuế là mặc định trong config.BACKTEST_V2, cần đối chiếu biểu phí thực tế.",
        ]
        if bench_label != 'VNINDEX':
            notes.append("Benchmark là chỉ số cân bằng của universe (chưa có VNINDEX_price.csv) - yếu hơn VN-Index.")
        if meta['universe_with_prices'] < meta['universe_requested']:
            notes.append(f"Chỉ có dữ liệu giá cho {meta['universe_with_prices']}/{meta['universe_requested']} mã.")
        return notes

    @staticmethod
    def _write_report(report, base, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        stamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        base.trades.to_csv(os.path.join(out_dir, f'v2_trades_{stamp}.csv'), index=False)
        base.equity.rename('equity').to_csv(os.path.join(out_dir, f'v2_equity_{stamp}.csv'),
                                            index_label='date')
        with open(os.path.join(out_dir, f'v2_report_{stamp}.json'), 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=lambda o: None if o != o else str(o))
        logger.info(f"Đã ghi báo cáo backtest v2 vào {out_dir} (v2_*_{stamp})")
