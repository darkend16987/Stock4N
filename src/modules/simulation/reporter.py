"""
Backtest Reporter - Generate beautiful reports
"""
import pandas as pd
import os
from datetime import datetime


class BacktestReporter:
    """Generate backtest reports"""

    def __init__(self, trades_df, performance_metrics, output_dir='data/backtest'):
        self.trades = trades_df
        self.metrics = performance_metrics
        self.output_dir = output_dir

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def print_summary(self):
        """In tổng kết ra terminal"""
        summary = self.metrics.summary()

        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS SUMMARY")
        print("=" * 60)

        # Capital & Returns
        print(f"\n💰 CAPITAL & RETURNS:")
        print(f"  Initial Capital:     {summary['initial_capital']:>15,} VND")
        print(f"  Final Capital:       {summary['final_capital']:>15,} VND")
        print(f"  Total P&L:           {summary['total_pnl']:>15,} VND")
        print(f"  Total Return:        {summary['total_return_pct']:>14.2f} %")

        # Risk Metrics
        print(f"\n📈 RISK METRICS:")
        print(f"  Sharpe Ratio:        {summary['sharpe_ratio']:>15.2f}")
        print(f"  Max Drawdown:        {summary['max_drawdown_pct']:>14.2f} %")
        print(f"  Profit Factor:       {summary['profit_factor']:>15.2f}")

        # Trading Stats
        print(f"\n📊 TRADING STATISTICS:")
        print(f"  Total Trades:        {summary['total_trades']:>15}")
        print(f"  Winning Trades:      {summary['winning_trades']:>15} ({summary['win_rate_pct']:.1f}%)")
        print(f"  Losing Trades:       {summary['losing_trades']:>15}")
        print(f"  Win Rate:            {summary['win_rate_pct']:>14.1f} %")

        # Win/Loss
        print(f"\n💵 WIN/LOSS ANALYSIS:")
        print(f"  Average Win:         {summary['avg_win']:>15,} VND")
        print(f"  Average Loss:        {summary['avg_loss']:>15,} VND")

        print("\n" + "=" * 60)

    def print_top_performers(self, top_n=10):
        """In top cổ phiếu hoạt động tốt nhất"""
        if self.trades.empty:
            return

        # Get sell trades with P&L
        sells = self.trades[self.trades['action'] == 'SELL'].copy()

        if sells.empty:
            print("\n⚠️  No completed trades to analyze")
            return

        # Sort by P&L
        sells = sells.sort_values('pnl', ascending=False)

        print(f"\n🏆 TOP {top_n} BEST PERFORMERS:")
        print("-" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Return %':<12}{'P&L (VND)':<15}{'Reason':<20}")
        print("-" * 80)

        for i, (_, row) in enumerate(sells.head(top_n).iterrows(), 1):
            print(
                f"{i:<6}"
                f"{row['symbol']:<10}"
                f"{row.get('return_pct', 0):>10.2f}%"
                f"{row['pnl']:>15,.0f}"
                f"  {row.get('reason', 'N/A'):<20}"
            )

        print("\n❌ TOP 5 WORST PERFORMERS:")
        print("-" * 80)

        for i, (_, row) in enumerate(sells.tail(5).iterrows(), 1):
            print(
                f"{i:<6}"
                f"{row['symbol']:<10}"
                f"{row.get('return_pct', 0):>10.2f}%"
                f"{row['pnl']:>15,.0f}"
                f"  {row.get('reason', 'N/A'):<20}"
            )

    def save_to_csv(self):
        """Lưu kết quả ra CSV"""
        if self.trades.empty:
            print("⚠️  No trades to save")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.output_dir, f'backtest_{timestamp}.csv')

        self.trades.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ Backtest results saved to: {filename}")

        # Save summary
        summary_file = os.path.join(self.output_dir, f'summary_{timestamp}.txt')
        summary = self.metrics.summary()

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("BACKTEST RESULTS SUMMARY\n")
            f.write("=" * 60 + "\n\n")

            f.write("CAPITAL & RETURNS:\n")
            f.write(f"  Initial Capital:     {summary['initial_capital']:,} VND\n")
            f.write(f"  Final Capital:       {summary['final_capital']:,} VND\n")
            f.write(f"  Total P&L:           {summary['total_pnl']:,} VND\n")
            f.write(f"  Total Return:        {summary['total_return_pct']:.2f}%\n\n")

            f.write("RISK METRICS:\n")
            f.write(f"  Sharpe Ratio:        {summary['sharpe_ratio']:.2f}\n")
            f.write(f"  Max Drawdown:        {summary['max_drawdown_pct']:.2f}%\n")
            f.write(f"  Profit Factor:       {summary['profit_factor']:.2f}\n\n")

            f.write("TRADING STATISTICS:\n")
            f.write(f"  Total Trades:        {summary['total_trades']}\n")
            f.write(f"  Winning Trades:      {summary['winning_trades']} ({summary['win_rate_pct']:.1f}%)\n")
            f.write(f"  Losing Trades:       {summary['losing_trades']}\n")
            f.write(f"  Win Rate:            {summary['win_rate_pct']:.1f}%\n")

        print(f"✅ Summary saved to: {summary_file}")

        return filename

    def generate_full_report(self):
        """Tạo báo cáo đầy đủ"""
        self.print_summary()
        self.print_top_performers()
        self.save_to_csv()
