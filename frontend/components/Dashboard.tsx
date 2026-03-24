'use client'

import { useState, useCallback } from 'react'
import { StockData } from '@/lib/data'
import { Header } from './Header'
import { StatsCards } from './StatsCards'
import { CommandCenter } from './CommandCenter'
import { PortfolioTable } from './PortfolioTable'
import { AnalysisTable } from './AnalysisTable'
import { PriceFilterTable } from './PriceFilterTable'

type TabId = 'portfolio' | 'analysis' | 'price_filter'

const tabs: { id: TabId; label: string; icon: string }[] = [
  { id: 'portfolio',     label: 'Danh Mục',    icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
  { id: 'analysis',      label: 'Phân Tích',   icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { id: 'price_filter',  label: 'Lọc Giá',     icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
]

export function Dashboard({ initialData }: { initialData: StockData }) {
  const [data, setData] = useState(initialData)
  const [activeTab, setActiveTab] = useState<TabId>('portfolio')
  const [refreshing, setRefreshing] = useState(false)

  const refreshData = useCallback(async () => {
    setRefreshing(true)
    try {
      const dataUrl = process.env.NEXT_PUBLIC_DATA_URL || '/data/db.json'
      const res = await fetch(dataUrl, { cache: 'no-store' })
      if (res.ok) {
        const newData = await res.json()
        setData(newData)
      }
    } catch (e) {
      console.error('Refresh failed:', e)
    } finally {
      setRefreshing(false)
    }
  }, [])

  return (
    <div className="min-h-screen">
      <Header lastUpdated={data.last_updated} onRefresh={refreshData} refreshing={refreshing} />

      <main className="container mx-auto px-4 pb-8 max-w-7xl space-y-6">
        {/* Stats Cards */}
        <StatsCards analysis={data.analysis} portfolio={data.portfolio} />

        {/* Command Center */}
        <CommandCenter onComplete={refreshData} />

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 bg-slate-800/60 p-1 rounded-xl border border-slate-700/50 w-fit">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
              </svg>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 overflow-hidden">
          {activeTab === 'portfolio' && (
            <div>
              <div className="px-6 py-4 border-b border-slate-700/50">
                <h2 className="text-lg font-semibold text-white">Portfolio Recommendations</h2>
                <p className="text-sm text-slate-400 mt-1">Stop Loss: -5% | Target: +12% | R:R 1:2.4 | Cash reserve: 25%</p>
              </div>
              <PortfolioTable data={data.portfolio} />
            </div>
          )}
          {activeTab === 'analysis' && (
            <div>
              <div className="px-6 py-4 border-b border-slate-700/50">
                <h2 className="text-lg font-semibold text-white">Market Analysis & Rankings</h2>
                <p className="text-sm text-slate-400 mt-1">Fundamental 65% + Technical 35% | Buy threshold: 6.5/10</p>
              </div>
              <AnalysisTable data={data.analysis} />
            </div>
          )}
          {activeTab === 'price_filter' && (
            <div>
              <div className="px-6 py-4 border-b border-slate-700/50">
                <h2 className="text-lg font-semibold text-white">Lọc Cổ Phiếu: Giá &lt; SMA200</h2>
                <p className="text-sm text-slate-400 mt-1">Quét toàn thị trường VN | Background scan với auto-resume</p>
              </div>
              <PriceFilterTable data={data.price_filter || []} />
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="text-center py-6 text-slate-500 text-xs space-y-1">
          <p>Stock4N - VN Stock Intelligent Advisor | AI-powered by Gemini</p>
          <p>
            Data: {new Date(data.last_updated).toLocaleString('vi-VN')}
          </p>
          <p className="text-slate-600">
            Disclaimer: This is not financial advice. Always do your own research.
          </p>
        </footer>
      </main>
    </div>
  )
}
