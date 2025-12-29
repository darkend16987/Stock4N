"""
Weight Optimizer - Tối ưu hóa trọng số scoring
Sử dụng kết quả backtest để tìm trọng số tối ưu
"""
import pandas as pd
import numpy as np
from itertools import product
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config
from modules.simulation.backtest_engine import BacktestEngine
from modules.simulation.performance import PerformanceMetrics
from modules.utils.logger import get_logger

logger = get_logger(__name__)


class WeightOptimizer:
    """
    Tối ưu hóa trọng số cho scoring strategy
    """

    def __init__(self, data_dir=config.RAW_DIR):
        self.data_dir = data_dir
        self.best_weights = None
        self.optimization_results = []

    def generate_weight_combinations(self, weight_range=(0.3, 0.7), step=0.1):
        """
        Tạo các tổ hợp trọng số để test

        Args:
            weight_range: (min, max) for fund_weight
            step: Bước nhảy

        Returns:
            list: [(fund_weight, tech_weight), ...]
        """
        fund_weights = np.arange(weight_range[0], weight_range[1] + step, step)
        combinations = []

        for fund_w in fund_weights:
            tech_w = 1.0 - fund_w
            if tech_w >= 0.3 and tech_w <= 0.7:  # Ensure both weights reasonable
                combinations.append((round(fund_w, 2), round(tech_w, 2)))

        logger.info(f"Generated {len(combinations)} weight combinations")
        return combinations

    def test_weight_combination(
        self,
        fund_weight,
        tech_weight,
        scores_df,
        start_date,
        end_date,
        initial_capital=100_000_000,
        min_score=6.0
    ):
        """
        Test một tổ hợp trọng số bằng backtest

        Returns:
            dict: Performance metrics
        """
        # Recalculate total score with new weights
        scores_df_adj = scores_df.copy()
        scores_df_adj['Total_Score'] = (
            scores_df_adj['Fund_Score'] * fund_weight +
            scores_df_adj['Tech_Score'] * tech_weight
        )

        # Run backtest
        engine = BacktestEngine(
            data_dir=self.data_dir,
            initial_capital=initial_capital,
            max_positions=10,
            position_size_pct=0.10,
            stop_loss_pct=0.07,
            take_profit_pct=0.15
        )

        trades_df = engine.run_backtest(
            scores_df=scores_df_adj,
            start_date=start_date,
            end_date=end_date,
            min_score=min_score
        )

        if trades_df.empty:
            return None

        # Calculate metrics
        metrics = PerformanceMetrics(trades_df, initial_capital=initial_capital)

        result = {
            'fund_weight': fund_weight,
            'tech_weight': tech_weight,
            'total_return': metrics.total_return(),
            'sharpe_ratio': metrics.sharpe_ratio(),
            'max_drawdown': metrics.max_drawdown(),
            'win_rate': metrics.win_rate(),
            'total_trades': len(trades_df),
            'profit_factor': metrics.profit_factor()
        }

        return result

    def optimize_weights(
        self,
        scores_df,
        start_date,
        end_date,
        initial_capital=100_000_000,
        min_score=6.0,
        optimization_metric='sharpe_ratio'
    ):
        """
        Tìm trọng số tối ưu bằng grid search

        Args:
            optimization_metric: Metric to optimize ('sharpe_ratio', 'total_return', 'win_rate')

        Returns:
            dict: Best weights and their performance
        """
        logger.info("Starting weight optimization...")

        weight_combinations = self.generate_weight_combinations()

        results = []

        for fund_w, tech_w in weight_combinations:
            logger.info(f"Testing weights: Fund={fund_w}, Tech={tech_w}")

            result = self.test_weight_combination(
                fund_weight=fund_w,
                tech_weight=tech_w,
                scores_df=scores_df,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                min_score=min_score
            )

            if result:
                results.append(result)
                logger.info(
                    f"  → Return: {result['total_return']:.2f}%, "
                    f"Sharpe: {result['sharpe_ratio']:.2f}, "
                    f"Win Rate: {result['win_rate']:.1f}%"
                )

        if not results:
            logger.warning("No valid optimization results!")
            return None

        # Find best weights
        results_df = pd.DataFrame(results)
        self.optimization_results = results_df

        # Sort by optimization metric
        if optimization_metric not in results_df.columns:
            optimization_metric = 'sharpe_ratio'

        best_result = results_df.loc[results_df[optimization_metric].idxmax()]

        self.best_weights = {
            'fund_weight': best_result['fund_weight'],
            'tech_weight': best_result['tech_weight'],
            'performance': {
                'total_return': best_result['total_return'],
                'sharpe_ratio': best_result['sharpe_ratio'],
                'max_drawdown': best_result['max_drawdown'],
                'win_rate': best_result['win_rate'],
                'total_trades': int(best_result['total_trades']),
                'profit_factor': best_result['profit_factor']
            }
        }

        logger.info(
            f"\n✅ Best weights found: "
            f"Fund={self.best_weights['fund_weight']}, "
            f"Tech={self.best_weights['tech_weight']}"
        )
        logger.info(f"Performance: {self.best_weights['performance']}")

        return self.best_weights

    def save_optimization_results(self, output_dir=config.PROCESSED_DIR):
        """
        Lưu kết quả optimization ra file

        Saves:
            - optimization_results.csv: All tested combinations
            - best_weights.json: Best weights and performance
        """
        if self.optimization_results.empty:
            logger.warning("No optimization results to save")
            return

        os.makedirs(output_dir, exist_ok=True)

        # Save all results
        results_file = os.path.join(output_dir, 'optimization_results.csv')
        self.optimization_results.to_csv(results_file, index=False)
        logger.info(f"Saved optimization results to {results_file}")

        # Save best weights
        if self.best_weights:
            import json
            weights_file = os.path.join(output_dir, 'best_weights.json')
            with open(weights_file, 'w', encoding='utf-8') as f:
                json.dump(self.best_weights, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved best weights to {weights_file}")

    def get_optimization_summary(self):
        """
        Tạo summary của quá trình optimization

        Returns:
            str: Formatted summary
        """
        if self.optimization_results.empty:
            return "No optimization results available"

        df = self.optimization_results

        summary = f"""
=== WEIGHT OPTIMIZATION SUMMARY ===

Total combinations tested: {len(df)}

Best Performance:
  Fund Weight: {self.best_weights['fund_weight']:.2f}
  Tech Weight: {self.best_weights['tech_weight']:.2f}

  Total Return: {self.best_weights['performance']['total_return']:.2f}%
  Sharpe Ratio: {self.best_weights['performance']['sharpe_ratio']:.2f}
  Max Drawdown: {self.best_weights['performance']['max_drawdown']:.2f}%
  Win Rate: {self.best_weights['performance']['win_rate']:.1f}%
  Total Trades: {self.best_weights['performance']['total_trades']}
  Profit Factor: {self.best_weights['performance']['profit_factor']:.2f}

Top 5 Combinations (by Sharpe Ratio):
"""
        top5 = df.nlargest(5, 'sharpe_ratio')
        for idx, row in top5.iterrows():
            summary += f"\n  {row['fund_weight']:.2f}/{row['tech_weight']:.2f} → "
            summary += f"Return: {row['total_return']:.1f}%, Sharpe: {row['sharpe_ratio']:.2f}"

        summary += "\n\n==================================="

        return summary
