'use client'

import { PortfolioPosition } from '@/lib/data'

interface PortfolioTableProps {
  data: PortfolioPosition[]
}

export function PortfolioTable({ data }: PortfolioTableProps) {
  if (data.length === 0) {
    return (
      <div className="text-center py-16 px-6">
        <div className="w-12 h-12 rounded-xl bg-slate-700/50 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        </div>
        <p className="text-slate-400 text-sm font-medium">No portfolio positions available</p>
        <p className="text-slate-600 text-xs mt-1">Run the pipeline to generate recommendations</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700/50">
            <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Symbol</th>
            <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Action</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Score</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Entry</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Weight</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Shares</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Capital</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Stop Loss</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Target</th>
            <th className="px-4 py-3 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">R/R</th>
          </tr>
        </thead>
        <tbody>
          {data.map((p, index) => (
            <tr
              key={index}
              className="border-b border-slate-800/50 hover:bg-slate-700/20 transition-colors"
            >
              <td className="px-4 py-3">
                <span className="text-sm font-bold text-blue-400">{p.Symbol}</span>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold ${
                  p.Action.includes('MUA MẠNH')
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : p.Action.includes('MUA')
                      ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                }`}>
                  {p.Action}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <span className={`text-sm font-bold ${
                  p.Score >= 7.5 ? 'text-emerald-400' : p.Score >= 6.5 ? 'text-blue-400' : 'text-amber-400'
                }`}>
                  {p.Score?.toFixed(1)}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs text-slate-300">{p.Entry_Price}</td>
              <td className="px-4 py-3 text-right">
                <span className="text-xs font-semibold text-violet-400">{p['Weight_%']}</span>
              </td>
              <td className="px-4 py-3 text-right text-xs text-slate-400">{p.Volume_Shares?.toLocaleString()}</td>
              <td className="px-4 py-3 text-right font-mono text-xs text-slate-300">{p.Capital_VND}</td>
              <td className="px-4 py-3 text-right font-mono text-xs text-red-400">{p.Stop_Loss}</td>
              <td className="px-4 py-3 text-right font-mono text-xs text-emerald-400">{p.Target}</td>
              <td className="px-4 py-3 text-right text-xs text-slate-400">{p['Risk/Reward']}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
