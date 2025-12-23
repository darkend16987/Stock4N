import { PortfolioPosition } from '@/lib/data'

interface PortfolioTableProps {
  data: PortfolioPosition[]
}

export function PortfolioTable({ data }: PortfolioTableProps) {
  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-slate-600 dark:text-slate-400">
        <p className="text-lg">⚠️ No portfolio positions available</p>
        <p className="mt-2 text-sm">Market conditions may not meet buy criteria at the moment.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50 dark:bg-slate-700">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Symbol</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Action</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Score</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Entry Price</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Weight</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Shares</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Capital</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Stop Loss</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Target</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          {data.map((position, index) => (
            <tr key={index} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
              <td className="px-4 py-3">
                <span className="font-bold text-lg text-blue-600 dark:text-blue-400">{position.Symbol}</span>
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-semibold ${
                  position.Action.includes('MUA MẠNH')
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                }`}>
                  {position.Action}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <span className="font-semibold text-slate-800 dark:text-white">{position.Score.toFixed(1)}</span>
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-slate-700 dark:text-slate-300">
                {position.Entry_Price}
              </td>
              <td className="px-4 py-3 text-right">
                <span className="font-semibold text-purple-600 dark:text-purple-400">{position['Weight_%']}</span>
              </td>
              <td className="px-4 py-3 text-right text-slate-700 dark:text-slate-300">
                {position.Volume_Shares.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-slate-700 dark:text-slate-300">
                {position.Capital_VND}
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-red-600 dark:text-red-400">
                {position.Stop_Loss}
              </td>
              <td className="px-4 py-3 text-right font-mono text-sm text-green-600 dark:text-green-400">
                {position.Target}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
