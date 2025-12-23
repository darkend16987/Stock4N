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
    return sum + parseFloat(p.Capital_VND.replace(/,/g, ''))
  }, 0)

  const stats = [
    {
      title: 'Total Stocks Analyzed',
      value: analysis.length,
      icon: '📈',
      color: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600'
    },
    {
      title: 'Buy Signals',
      value: buySignals,
      icon: '✅',
      color: 'bg-green-50 dark:bg-green-900/20 text-green-600'
    },
    {
      title: 'Strong Buy',
      value: strongBuy,
      icon: '🚀',
      color: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600'
    },
    {
      title: 'Portfolio Positions',
      value: positions,
      icon: '💼',
      color: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600'
    },
    {
      title: 'Capital Allocated',
      value: `${(totalCapital / 1000000).toFixed(1)}M`,
      icon: '💰',
      color: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600'
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {stats.map((stat, index) => (
        <div key={index} className="bg-white dark:bg-slate-800 rounded-lg shadow-md p-4">
          <div className={`inline-flex items-center justify-center w-12 h-12 rounded-lg mb-3 ${stat.color}`}>
            <span className="text-2xl">{stat.icon}</span>
          </div>
          <h3 className="text-sm text-slate-600 dark:text-slate-400 mb-1">{stat.title}</h3>
          <p className="text-2xl font-bold text-slate-800 dark:text-white">{stat.value}</p>
        </div>
      ))}
    </div>
  )
}
