'use client'

import { StockAnalysis, PortfolioPosition } from '@/lib/data'

interface StatsCardsProps {
  analysis: StockAnalysis[]
  portfolio: PortfolioPosition[]
}

export function StatsCards({ analysis, portfolio }: StatsCardsProps) {
  const buySignals = analysis.filter(a => a.Recommendation.includes('MUA')).length
  const strongBuy = analysis.filter(a => a.Recommendation === 'MUA MẠNH').length
  const positions = portfolio.length

  const totalCapital = portfolio.reduce((sum, p) => {
    const val = p.Capital_VND?.replace(/,/g, '')
    return sum + (parseFloat(val) || 0)
  }, 0)

  const avgScore = analysis.length > 0
    ? analysis.reduce((s, a) => s + a.Total_Score, 0) / analysis.length
    : 0

  const stats = [
    {
      title: 'Analyzed',
      value: analysis.length,
      suffix: 'stocks',
      color: 'blue',
      iconPath: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
    },
    {
      title: 'Buy Signals',
      value: buySignals,
      suffix: '',
      color: 'cyan',
      iconPath: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    },
    {
      title: 'Strong Buy',
      value: strongBuy,
      suffix: '',
      color: 'emerald',
      iconPath: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    },
    {
      title: 'Portfolio',
      value: positions,
      suffix: 'positions',
      color: 'violet',
      iconPath: 'M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    },
    {
      title: 'Capital',
      value: totalCapital > 0 ? `${(totalCapital / 1000000).toFixed(0)}M` : '0',
      suffix: 'VND',
      color: 'amber',
      iconPath: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    },
    {
      title: 'Avg Score',
      value: avgScore.toFixed(1),
      suffix: '/10',
      color: avgScore >= 6.5 ? 'emerald' : avgScore >= 5.0 ? 'amber' : 'red',
      iconPath: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z',
    },
  ]

  const colorMap: Record<string, { bg: string; icon: string; text: string }> = {
    blue:    { bg: 'bg-blue-500/10',    icon: 'text-blue-400',    text: 'text-blue-400' },
    cyan:    { bg: 'bg-cyan-500/10',    icon: 'text-cyan-400',    text: 'text-cyan-400' },
    emerald: { bg: 'bg-emerald-500/10', icon: 'text-emerald-400', text: 'text-emerald-400' },
    violet:  { bg: 'bg-violet-500/10',  icon: 'text-violet-400',  text: 'text-violet-400' },
    amber:   { bg: 'bg-amber-500/10',   icon: 'text-amber-400',   text: 'text-amber-400' },
    red:     { bg: 'bg-red-500/10',     icon: 'text-red-400',     text: 'text-red-400' },
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6">
      {stats.map((stat, index) => {
        const c = colorMap[stat.color] || colorMap.blue
        return (
          <div
            key={index}
            className="bg-slate-800/40 rounded-xl border border-slate-700/40 p-4 hover:border-slate-600/60 transition-colors"
          >
            <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center mb-3`}>
              <svg className={`w-4 h-4 ${c.icon}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={stat.iconPath} />
              </svg>
            </div>
            <div className="text-xs text-slate-500 mb-1">{stat.title}</div>
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold text-white">{stat.value}</span>
              {stat.suffix && <span className="text-xs text-slate-500">{stat.suffix}</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
