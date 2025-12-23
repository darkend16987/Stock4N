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
    def __init__(self, processed_dir=config.PROCESSED_DIR):
        self.processed_dir = processed_dir

        # Load config
        self.portfolio_config = config.PORTFOLIO_CONFIG
        self.risk_config = config.RISK_MANAGEMENT
        self.price_unit_config = config.PRICE_UNIT_CONFIG

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

    def generate_recommendation(self, total_capital=100000000):
        """
        Generate portfolio allocation recommendations

        Args:
            total_capital: Total capital in VND (default: 100M)
        """
        logger.info(f"Generating portfolio recommendations with capital: {total_capital:,.0f} VND")

        report_path = os.path.join(self.processed_dir, "analysis_report.csv")
        if not os.path.exists(report_path):
            logger.error(f"Analysis report not found: {report_path}. Run 'analyze' command first.")
            return

        df = pd.read_csv(report_path)

        # 1. Filter BUY recommendations
        buy_list = df[df['Recommendation'].str.contains('MUA', case=False, na=False)].copy()

        if buy_list.empty:
            logger.warning("=" * 60)
            logger.warning("⚠️ MARKET RISK WARNING")
            logger.warning("No stocks meet BUY criteria in current scan")
            logger.warning("💡 Recommendation: Hold 100% CASH")
            logger.warning("=" * 60)
            return

        logger.info(f"Found {len(buy_list)} stocks with BUY recommendations")

        # 2. Calculate allocation
        total_buy_score = buy_list['Total_Score'].sum()

        recommendations = []

        # Available cash (can configure to keep some reserve)
        cash_reserve_pct = self.portfolio_config.get('cash_reserve_pct', 0)
        available_cash = total_capital * (1 - cash_reserve_pct)

        logger.info(f"Available for investment: {available_cash:,.0f} VND ({(1-cash_reserve_pct)*100:.0f}%)")

        for index, row in buy_list.iterrows():
            symbol = row['Symbol']
            score = row['Total_Score']
            price_raw = row['Price']

            # Auto-detect price unit
            price = self._detect_price_unit(price_raw)

            if price == 0:
                logger.warning(f"Skipping {symbol}: Invalid price (0)")
                continue

            # Calculate weight
            raw_weight = score / total_buy_score

            # Apply max position limit
            max_position_pct = self.portfolio_config['max_position_pct']
            weight = min(max_position_pct, raw_weight)

            # Special case: only 1 stock → max 40%, keep 60% cash
            if len(buy_list) == 1:
                weight = max_position_pct
                logger.info(f"Single position detected, capping at {max_position_pct*100}%")

            amount = available_cash * weight

            # Round to lot of 100 shares
            shares = int(amount / price / 100) * 100

            if shares == 0:
                logger.warning(f"Skipping {symbol}: Insufficient capital for 1 lot (price={price:,.0f})")
                continue

            # Actual amount and weight
            actual_amount = shares * price
            actual_weight = actual_amount / total_capital

            # 3. Risk Management
            stop_loss_pct = self.risk_config['stop_loss_pct']
            target_profit_pct = self.risk_config['target_profit_pct']

            stop_loss_price = round(price * (1 - stop_loss_pct), 0)
            target_price = round(price * (1 + target_profit_pct), 0)

            risk_reward = f"1:{self.risk_config['risk_reward_ratio']}"

            recommendations.append({
                'Symbol': symbol,
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
            display_cols = ['Symbol', 'Action', 'Weight_%', 'Volume_Shares', 'Entry_Price', 'Stop_Loss', 'Target']
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
