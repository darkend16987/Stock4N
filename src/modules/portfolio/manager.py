import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.utils.logger import get_logger
from modules.utils.exceptions import InsufficientCapitalException, NoValidPositionException

logger = get_logger(__name__)


class PortfolioManager:
    """
    Module quản lý danh mục: Phân bổ vốn & Quản trị rủi ro.
    """
    def __init__(self, processed_dir=config.PROCESSED_DIR, raw_dir=config.RAW_DIR, returns_provider=None):
        """
        Args:
            returns_provider: callable(symbol) -> pandas.Series lợi suất ngày (hoặc None). Backtest dùng
                để cấp dữ liệu point-in-time cho bộ lọc tương quan; None = đọc file giá mới nhất.
        """
        self.processed_dir = processed_dir
        self.raw_dir = raw_dir
        self._returns_provider = returns_provider

        # Load config
        self.portfolio_config = config.PORTFOLIO_CONFIG
        self.risk_config = config.RISK_MANAGEMENT
        self.price_unit_config = config.PRICE_UNIT_CONFIG

        self._returns_cache = {}

        logger.info(f"PortfolioManager initialized: Max position={self.portfolio_config['max_position_pct']*100}%, Stop loss={self.risk_config['stop_loss_pct']*100}%")

    def _detect_price_unit(self, price):
        """
        Auto-detect price unit (VND vs thousands VND)

        Args:
            price: Price value

        Returns:
            Actual price in VND
        """
        threshold = self.price_unit_config['threshold']
        multiplier = self.price_unit_config['multiplier']

        if price < threshold:
            # Assume it's in thousands VND
            actual_price = price * multiplier
            logger.debug(f"Price {price} detected as thousands VND → {actual_price} VND")
            return actual_price
        else:
            # Already in VND
            return price

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _load_returns(self, symbol):
        """Lợi suất ngày gần nhất (correlation_lookback phiên) của 1 mã; None nếu thiếu dữ liệu."""
        if self._returns_provider is not None:
            return self._returns_provider(symbol)

        if symbol in self._returns_cache:
            return self._returns_cache[symbol]

        returns = None
        path = os.path.join(self.raw_dir, f"{symbol}_price.csv")
        try:
            if os.path.exists(path):
                df = pd.read_csv(path)
                df['time'] = pd.to_datetime(df['time']).dt.normalize()
                closes = df.drop_duplicates('time').sort_values('time').set_index('time')['close']
                lookback = self.portfolio_config.get('correlation_lookback', 60)
                returns = closes.pct_change().dropna().tail(lookback)
        except Exception as e:
            logger.warning(f"Cannot load returns for {symbol}: {e}")

        self._returns_cache[symbol] = returns
        return returns

    def _max_correlation_with(self, symbol, selected_symbols):
        """
        Tương quan lợi suất cao nhất giữa `symbol` và các mã đã chọn.
        Returns (corr, other_symbol) hoặc (None, None) nếu không đủ dữ liệu để kiểm tra.
        """
        r1 = self._load_returns(symbol)
        if r1 is None or len(r1) < 20:
            return None, None

        worst, worst_sym = None, None
        for other in selected_symbols:
            r2 = self._load_returns(other)
            if r2 is None:
                continue
            joined = pd.concat([r1, r2], axis=1, join='inner').dropna()
            if len(joined) < 20:
                continue
            corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
            if pd.notna(corr) and (worst is None or corr > worst):
                worst, worst_sym = corr, other
        return worst, worst_sym

    def select_candidates(self, buy_list, available_cash, held_symbols=None, slots=None):
        """
        Chọn tối đa max_positions mã từ buy_list (đã sắp theo điểm giảm dần), tôn trọng:
          - số vị thế tối đa
          - tối đa N mã / ngành, với N = max_sector_pct // max_position_pct
            (mỗi mã ≤ max_position_pct → tổng 1 ngành ≤ max_sector_pct)
          - tương quan lợi suất ≤ max_correlation với các mã đã chọn
          - đủ tiền mua ít nhất 1 lô (100 cổ) trong mức tối đa của 1 vị thế

        Args:
            held_symbols: các mã ĐANG nắm giữ (backtest/tái cân bằng): tính vào trần ngành và
                bộ lọc tương quan; không được chọn lại.
            slots: số vị thế mới tối đa (mặc định max_positions - số mã đang giữ).

        Returns:
            list[pandas.Series] đã chọn
        """
        cfg = self.portfolio_config
        held_symbols = list(held_symbols or [])
        max_positions = cfg['max_positions']
        if slots is None:
            slots = max_positions - len(held_symbols)
        slots = max(0, min(slots, max_positions - len(held_symbols)))
        max_per_sector = max(1, int(cfg.get('max_sector_pct', 1.0) // cfg['max_position_pct']))
        max_corr = cfg.get('max_correlation', 1.0)
        max_amount = available_cash * cfg['max_position_pct']

        selected = []
        sector_count = {}
        for held in held_symbols:
            sec = config.SECTOR_MAP.get(held, 'Khác')
            sector_count[sec] = sector_count.get(sec, 0) + 1

        for _, row in buy_list.iterrows():
            if len(selected) >= slots:
                break

            symbol = row['Symbol']
            if symbol in held_symbols:
                continue
            sector = row.get('Sector') if pd.notna(row.get('Sector', None)) else config.SECTOR_MAP.get(symbol, 'Khác')

            price = self._detect_price_unit(row['Price'])
            if price <= 0 or price * 100 > max_amount:
                logger.info(f"  ⏩ {symbol}: bỏ qua - 1 lô ({price*100:,.0f} VND) vượt mức tối đa 1 vị thế ({max_amount:,.0f})")
                continue

            if sector_count.get(sector, 0) >= max_per_sector:
                logger.info(f"  ⏩ {symbol}: bỏ qua - ngành '{sector}' đã đủ {max_per_sector} mã")
                continue

            corr, other = self._max_correlation_with(
                symbol, held_symbols + [s['Symbol'] for s in selected])
            if corr is not None and corr > max_corr:
                logger.info(f"  ⏩ {symbol}: bỏ qua - tương quan {corr:.2f} với {other} > {max_corr}")
                continue

            selected.append(row)
            sector_count[sector] = sector_count.get(sector, 0) + 1

        return selected

    def compute_allocation(self, selected_df, available_cash):
        """
        Chia `available_cash` cho các mã đã chọn theo tỷ lệ điểm, mỗi mã ≤ max_position_pct,
        làm tròn xuống lô 100. Dùng chung cho khuyến nghị live và backtest.

        Returns:
            list[dict]: row, symbol, score, price (VND), weight, shares, amount (VND)
        """
        selected_df = pd.DataFrame(selected_df)
        if selected_df.empty:
            return []

        max_position_pct = self.portfolio_config['max_position_pct']
        total_buy_score = selected_df['Total_Score'].sum()
        result = []

        for _, row in selected_df.iterrows():
            symbol = row['Symbol']
            score = row['Total_Score']

            # Auto-detect price unit
            price = self._detect_price_unit(row['Price'])

            if price == 0:
                logger.warning(f"Skipping {symbol}: Invalid price (0)")
                continue

            # Calculate weight, apply max position limit
            raw_weight = score / total_buy_score
            weight = min(max_position_pct, raw_weight)

            # Special case: only 1 stock → max position, keep rest cash
            if len(selected_df) == 1:
                weight = max_position_pct
                logger.info(f"Single position detected, capping at {max_position_pct*100}%")

            amount = available_cash * weight

            # Round to lot of 100 shares
            shares = int(amount / price / 100) * 100

            if shares == 0:
                logger.warning(f"Skipping {symbol}: Insufficient capital for 1 lot (price={price:,.0f})")
                continue

            result.append({'row': row, 'symbol': symbol, 'score': score, 'price': price,
                           'weight': weight, 'shares': shares, 'amount': shares * price})

        return result

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------

    def generate_recommendation(self, total_capital=100000000, market_filter=None):
        """
        Generate portfolio allocation recommendations

        Args:
            total_capital: Total capital in VND (default: 100M)
            market_filter: output của MarketBreadthAnalyzer.get_market_filter().
                Nếu có: không mua mới khi thị trường yếu, và vốn đầu tư được nhân
                với risk_multiplier (thị trường kém khả quan → đầu tư ít hơn).
        """
        logger.info(f"Generating portfolio recommendations with capital: {total_capital:,.0f} VND")

        report_path = os.path.join(self.processed_dir, "analysis_report.csv")
        if not os.path.exists(report_path):
            logger.error(f"Analysis report not found: {report_path}. Run 'analyze' command first.")
            return

        df = pd.read_csv(report_path)

        # 0. Market regime
        risk_multiplier = 1.0
        if market_filter:
            risk_multiplier = market_filter.get('risk_multiplier', 1.0)
            logger.info(f"Market filter: {market_filter.get('sentiment')} | "
                        f"allow_new_buys={market_filter.get('allow_new_buys')} | risk_multiplier={risk_multiplier}")
            if not market_filter.get('allow_new_buys', True):
                logger.warning("=" * 60)
                logger.warning("⚠️ MARKET RISK WARNING - thị trường yếu, không mua mới")
                logger.warning("💡 Recommendation: Hold 100% CASH")
                logger.warning("=" * 60)
                return

        # 1. Filter BUY recommendations (đã qua RuleGate ở bước analysis), điểm cao trước
        buy_list = df[df['Recommendation'].str.contains('MUA', case=False, na=False)].copy()
        buy_list = buy_list.drop_duplicates('Symbol').sort_values('Total_Score', ascending=False)

        if buy_list.empty:
            logger.warning("=" * 60)
            logger.warning("⚠️ MARKET RISK WARNING")
            logger.warning("No stocks meet BUY criteria in current scan")
            logger.warning("💡 Recommendation: Hold 100% CASH")
            logger.warning("=" * 60)
            return

        logger.info(f"Found {len(buy_list)} stocks with BUY recommendations")

        # Available cash (can configure to keep some reserve)
        cash_reserve_pct = self.portfolio_config.get('cash_reserve_pct', 0)
        available_cash = total_capital * (1 - cash_reserve_pct) * risk_multiplier

        logger.info(f"Available for investment: {available_cash:,.0f} VND "
                    f"({(1-cash_reserve_pct)*risk_multiplier*100:.0f}%)")

        # 2. Select candidates (max positions, sector cap, correlation, lot affordability)
        selected = self.select_candidates(buy_list, available_cash)
        if not selected:
            logger.warning("Không mã nào qua bộ lọc danh mục → Hold 100% CASH")
            return

        selected_df = pd.DataFrame(selected)
        logger.info(f"Selected {len(selected_df)}/{len(buy_list)} stocks "
                    f"(max {self.portfolio_config['max_positions']})")

        # 3. Calculate allocation
        max_position_pct = self.portfolio_config['max_position_pct']
        recommendations = []

        for alloc in self.compute_allocation(selected_df, available_cash):
            row = alloc['row']
            symbol = alloc['symbol']
            score = alloc['score']
            price = alloc['price']
            shares = alloc['shares']
            actual_amount = alloc['amount']
            actual_weight = actual_amount / total_capital

            # Risk Management
            stop_loss_pct = self.risk_config['stop_loss_pct']
            target_profit_pct = self.risk_config['target_profit_pct']

            stop_loss_price = round(price * (1 - stop_loss_pct), 0)
            target_price = round(price * (1 + target_profit_pct), 0)

            risk_reward = f"1:{self.risk_config['risk_reward_ratio']}"

            recommendations.append({
                'Symbol': symbol,
                'Sector': row.get('Sector') if pd.notna(row.get('Sector', None)) else config.SECTOR_MAP.get(symbol, 'Khác'),
                'Action': row['Recommendation'],
                'Score': score,
                'Entry_Price': f"{price:,.0f}",
                'Weight_%': f"{actual_weight*100:.1f}%",
                'Capital_VND': f"{actual_amount:,.0f}",
                'Volume_Shares': shares,
                'Stop_Loss': f"{stop_loss_price:,.0f}",
                'Target': f"{target_price:,.0f}",
                'Risk/Reward': risk_reward
            })

            logger.info(f"✓ {symbol}: {shares} shares @ {price:,.0f} = {actual_amount:,.0f} VND ({actual_weight*100:.1f}%)")

        # 4. Save recommendations
        if recommendations:
            df_rec = pd.DataFrame(recommendations)
            output_path = os.path.join(self.processed_dir, "portfolio_recommendation.csv")
            df_rec.to_csv(output_path, index=False)

            # Calculate totals
            total_invested = sum([
                float(rec['Capital_VND'].replace(',',''))
                for rec in recommendations
            ])
            remaining_cash = total_capital - total_invested
            invested_pct = (total_invested / total_capital) * 100

            logger.info("=" * 60)
            logger.info("PORTFOLIO ALLOCATION")
            logger.info("=" * 60)
            logger.info(f"Total capital: {total_capital:,.0f} VND")
            logger.info(f"Invested: {total_invested:,.0f} VND ({invested_pct:.1f}%)")
            logger.info(f"Cash reserve: {remaining_cash:,.0f} VND ({100-invested_pct:.1f}%)")
            logger.info(f"Number of positions: {len(recommendations)}")
            logger.info(f"Output saved to: {output_path}")
            logger.info("=" * 60)

            logger.info("\nPORTFOLIO DETAILS:")
            display_cols = ['Symbol', 'Sector', 'Action', 'Weight_%', 'Volume_Shares', 'Entry_Price', 'Stop_Loss', 'Target']
            print(df_rec[display_cols].to_string())

            # Risk summary
            logger.info("\nRISK SUMMARY:")
            logger.info(f"Stop Loss: -{stop_loss_pct*100:.1f}% per position")
            logger.info(f"Target Profit: +{target_profit_pct*100:.1f}% per position")
            logger.info(f"Risk/Reward Ratio: {risk_reward}")
            logger.info(f"Max position size: {max_position_pct*100:.1f}%")

            return df_rec
        else:
            logger.error("No valid positions could be created (insufficient capital for minimum lots)")
            raise NoValidPositionException("Cannot create any positions with current capital and prices")
