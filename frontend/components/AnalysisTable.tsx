'use client'

import { useState } from 'react'
import { StockAnalysis, getRecommendationColor, getScoreColor } from '@/lib/data'

interface AnalysisTableProps {
  data: StockAnalysis[]
}

export function AnalysisTable({ data }: AnalysisTableProps) {
  const [filter, setFilter] = useState<string>('all')
  const [showCount, setShowCount] = useState(20)

  const filteredData = data.filter(stock => {
    if (filter === 'all') return true
    if (filter === 'buy') return stock.Recommendation.includes('MUA')
    if (filter === 'watch') return stock.Recommendation.includes('THEO DÕI')
    if (filter === 'sell') return stock.Recommendation.includes('BÁN')
    return true
  })

  const displayData = filteredData.slice(0, showCount)

  const filters = [
    { id: 'all',   label: 'All',         count: data.length },
    { id: 'buy',   label: 'Buy',         count: data.filter(s => s.Recommendation.includes('MUA')).length },
    { id: 'watch', label: 'Watch',        count: data.filter(s => s.Recommendation.includes('THEO DÕI')).length },
    { id: 'sell',  label: 'Sell',         count: data.filter(s => s.Recommendation.includes('BÁN')).length },
  ]

  return (
    <div>
      {/* Filters */}
      <div className="flex items-center gap-2 px-6 py-3 border-b border-slate-700/50 overflow-x-auto">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => { setFilter(f.id); setShowCount(20); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150 ${
              filter === f.id
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            {f.label}
            <span className={`px-1.5 py-0.5 rounded text-[10px] ${
              filter === f.id ? 'bg-blue-500/50' : 'bg-slate-700/50'
            }`}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700/50">
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider w-12">#</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Symbol</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Score</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Recommendation</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Fund</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Tech</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Price</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Analysis</th>
            </tr>
          </thead>
          <tbody>
            {displayData.map((stock, index) => (
              <tr key={index} className="border-b border-slate-800/50 hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-2.5 text-xs text-slate-600">{index + 1}</td>
                <td className="px-4 py-2.5">
                  <span className="text-sm font-bold text-blue-400">{stock.Symbol}</span>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className={`text-base font-bold ${getScoreColor(stock.Total_Score)}`}>
                    {stock.Total_Score?.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex px-2.5 py-0.5 rounded text-[10px] font-semibold ${getRecommendationColor(stock.Recommendation)}`}>
                    {stock.Recommendation}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className="text-xs text-violet-400 font-semibold">{stock.Fund_Score?.toFixed(1)}</span>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className="text-xs text-orange-400 font-semibold">{stock.Tech_Score?.toFixed(1)}</span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-300">
                  {stock.Price ? (stock.Price * 1000).toLocaleString() : '-'}
                </td>
                <td className="px-4 py-2.5 text-[11px] text-slate-500 max-w-[200px] truncate">
                  {stock.Fund_Reason?.substring(0, 60)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Load more */}
      {filteredData.length > showCount && (
        <div className="text-center py-3 border-t border-slate-700/50">
          <button
            onClick={() => setShowCount(prev => prev + 20)}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium"
          >
            Show more ({filteredData.length - showCount} remaining)
          </button>
        </div>
      )}
    </div>
  )
}
