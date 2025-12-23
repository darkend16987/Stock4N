import { PortfolioTable } from '@/components/PortfolioTable'
import { AnalysisTable } from '@/components/AnalysisTable'
import { StatsCards } from '@/components/StatsCards'
import { Header } from '@/components/Header'
import { getStockData } from '@/lib/data'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export default async function Home() {
  const data = await getStockData()

  return (
    <main className="container mx-auto px-4 py-8 max-w-7xl">
      <Header lastUpdated={data.last_updated} />

      <StatsCards
        analysis={data.analysis}
        portfolio={data.portfolio}
      />

      <div className="grid gap-8 mt-8">
        {/* Portfolio Recommendations */}
        <section className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-slate-800 dark:text-white flex items-center">
            <span className="text-3xl mr-3">💼</span>
            Portfolio Recommendations
          </h2>
          <PortfolioTable data={data.portfolio} />
        </section>

        {/* Market Analysis */}
        <section className="bg-white dark:bg-slate-800 rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold mb-4 text-slate-800 dark:text-white flex items-center">
            <span className="text-3xl mr-3">📊</span>
            Market Analysis & Rankings
          </h2>
          <AnalysisTable data={data.analysis} />
        </section>
      </div>

      {/* Footer */}
      <footer className="mt-12 text-center text-slate-600 dark:text-slate-400 text-sm">
        <p>Stock4N - VN Stock Intelligent Advisor</p>
        <p className="mt-1">
          Data updated: {new Date(data.last_updated).toLocaleString('vi-VN')}
        </p>
        <p className="mt-2 text-xs text-slate-500">
          ⚠️ This is not financial advice. Always do your own research before investing.
        </p>
      </footer>
    </main>
  )
}
