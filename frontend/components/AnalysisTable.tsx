'use client'

import { useState } from 'react'
import { StockAnalysis, getRecommendationColor, getScoreColor } from '@/lib/data'

interface AnalysisTableProps {
  data: StockAnalysis[]
}

export function AnalysisTable({ data }: AnalysisTableProps) {
  const [filter, setFilter] = useState<string>('all')

  const filteredData = data.filter(stock => {
    if (filter === 'all') return true
    if (filter === 'buy') return stock.Recommendation.includes('MUA')
    if (filter === 'watch') return stock.Recommendation.includes('THEO DÕI')
    if (filter === 'sell') return stock.Recommendation.includes('BÁN')
    return true
  }).slice(0, 20) // Show top 20

  const filters = [
    { id: 'all', label: 'All', count: data.length },
    { id: 'buy', label: 'Buy Signals', count: data.filter(s => s.Recommendation.includes('MUA')).length },
    { id: 'watch', label: 'Watch List', count: data.filter(s => s.Recommendation.includes('THEO DÕI')).length },
    { id: 'sell', label: 'Sell/Rebalance', count: data.filter(s => s.Recommendation.includes('BÁN')).length },
  ]

  return (
    <div>
      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              filter === f.id
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
            }`}
          >
            {f.label} ({f.count})
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Rank</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Symbol</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Score</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Recommendation</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Fund</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Tech</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Price</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Analysis</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {filteredData.map((stock, index) => (
              <tr key={index} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                <td className="px-4 py-3 text-slate-600 dark:text-slate-400">#{index + 1}</td>
                <td className="px-4 py-3">
                  <span className="font-bold text-lg text-blue-600 dark:text-blue-400">{stock.Symbol}</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={`text-xl font-bold ${getScoreColor(stock.Total_Score)}`}>
                    {stock.Total_Score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getRecommendationColor(stock.Recommendation)}`}>
                    {stock.Recommendation}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-purple-600 dark:text-purple-400 font-semibold">{stock.Fund_Score}/10</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-orange-600 dark:text-orange-400 font-semibold">{stock.Tech_Score}/10</span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm text-slate-700 dark:text-slate-300">
                  {(stock.Price * 1000).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400 max-w-xs truncate">
                  {stock.Fund_Reason.substring(0, 50)}...
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
