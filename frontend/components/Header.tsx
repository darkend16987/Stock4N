'use client'

import { useState, useEffect } from 'react'
import { checkHealth } from '@/lib/api'

interface HeaderProps {
  lastUpdated: string
  onRefresh: () => void
  refreshing: boolean
}

export function Header({ lastUpdated, onRefresh, refreshing }: HeaderProps) {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    checkHealth().then(setApiOnline)
    const interval = setInterval(() => checkHealth().then(setApiOnline), 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="border-b border-slate-800/80 bg-[#0a0f1c]/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="container mx-auto max-w-7xl px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">
                Stock<span className="text-blue-400">4N</span>
              </h1>
              <p className="text-[10px] text-slate-500 -mt-0.5">VN Stock Intelligent Advisor</p>
            </div>
          </div>

          {/* Right side: Status indicators */}
          <div className="flex items-center gap-4">
            {/* API Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/40">
              <div className={`w-1.5 h-1.5 rounded-full ${
                apiOnline === null ? 'bg-slate-500' :
                apiOnline ? 'bg-emerald-400 animate-pulse-dot' : 'bg-red-400'
              }`} />
              <span className="text-xs text-slate-400">
                {apiOnline === null ? 'Checking...' : apiOnline ? 'API Online' : 'API Offline'}
              </span>
            </div>

            {/* Last Updated */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/40">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs text-slate-400">
                {new Date(lastUpdated).toLocaleString('vi-VN')}
              </span>
            </div>

            {/* Refresh button */}
            <button
              onClick={onRefresh}
              disabled={refreshing}
              className="p-2 rounded-lg bg-slate-800/60 border border-slate-700/40 text-slate-400 hover:text-white hover:bg-slate-700/60 transition-colors disabled:opacity-50"
              title="Refresh data"
            >
              <svg className={`w-4 h-4 ${refreshing ? 'animate-spin-slow' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
