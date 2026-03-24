'use client'

import { useState, useEffect, useCallback } from 'react'
import { PriceFilterResult } from '@/lib/data'
import { startScan, getScanStatus, getScanResults, stopScan, ScanStatus } from '@/lib/api'

interface PriceFilterTableProps {
  data: PriceFilterResult[]
}

export function PriceFilterTable({ data: initialData }: PriceFilterTableProps) {
  const [data, setData] = useState(initialData)
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null)
  const [polling, setPolling] = useState(false)
  const [sortKey, setSortKey] = useState<keyof PriceFilterResult>('Pct_Below_SMA200')
  const [sortAsc, setSortAsc] = useState(true)
  const [showCount, setShowCount] = useState(30)

  // Poll scan status while running
  useEffect(() => {
    if (!polling) return
    const interval = setInterval(async () => {
      const status = await getScanStatus()
      setScanStatus(status)
      if (status.status === 'completed' || status.status === 'error' || status.status === 'idle') {
        setPolling(false)
        // Fetch final results
        const results = await getScanResults()
        if (results.length > 0) setData(results)
      }
    }, 5000) // Poll every 5 seconds
    return () => clearInterval(interval)
  }, [polling])

  // Check scan status on mount
  useEffect(() => {
    getScanStatus().then(status => {
      setScanStatus(status)
      if (status.status === 'running') setPolling(true)
    })
  }, [])

  const handleStartScan = useCallback(async () => {
    const ok = await startScan()
    if (ok) {
      setPolling(true)
      setScanStatus({ status: 'running', started_at: new Date().toISOString(), error: '' })
    }
  }, [])

  const handleStopScan = useCallback(async () => {
    await stopScan()
    setPolling(false)
    setScanStatus(prev => prev ? { ...prev, status: 'idle' } : null)
  }, [])

  const handleRefreshResults = useCallback(async () => {
    const results = await getScanResults()
    if (results.length > 0) setData(results)
  }, [])

  // Sort data
  const sortedData = [...data].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (typeof av === 'number' && typeof bv === 'number') {
      return sortAsc ? av - bv : bv - av
    }
    return sortAsc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av))
  })

  const displayData = sortedData.slice(0, showCount)

  const handleSort = (key: keyof PriceFilterResult) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const isRunning = scanStatus?.status === 'running'

  const SortIcon = ({ col }: { col: keyof PriceFilterResult }) => {
    if (sortKey !== col) return <span className="text-slate-600 ml-1">&#8597;</span>
    return <span className="text-blue-400 ml-1">{sortAsc ? '&#9650;' : '&#9660;'}</span>
  }

  return (
    <div>
      {/* Scan controls */}
      <div className="px-6 py-4 border-b border-slate-700/50 space-y-3">
        <div className="flex items-center gap-3 flex-wrap">
          {!isRunning ? (
            <button
              onClick={handleStartScan}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-400 hover:to-purple-500 shadow-lg shadow-violet-500/25 transition-all"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Bắt Đầu Quét
            </button>
          ) : (
            <button
              onClick={handleStopScan}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-red-600/80 text-white hover:bg-red-500 transition-all"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Dừng Quét
            </button>
          )}

          <button
            onClick={handleRefreshResults}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-slate-700/50 text-slate-300 hover:bg-slate-700 hover:text-white transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Tải Lại KQ
          </button>

          <div className="flex-1" />
          <span className="text-xs text-slate-500">
            {data.length > 0 ? `${data.length} mã khớp điều kiện` : 'Chưa có kết quả'}
          </span>
        </div>

        {/* Scan progress */}
        {isRunning && scanStatus && (
          <div className="bg-violet-500/10 border border-violet-500/30 rounded-lg px-4 py-3">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-violet-400 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <div className="flex-1 text-sm">
                <span className="text-violet-300 font-medium">Đang quét thị trường...</span>
                <div className="text-xs text-slate-400 mt-1 flex gap-4 flex-wrap">
                  {scanStatus.processed !== undefined && (
                    <span>Đã xử lý: <strong className="text-slate-300">{scanStatus.processed}</strong> mã</span>
                  )}
                  {scanStatus.batch && (
                    <span>Batch: <strong className="text-slate-300">{scanStatus.batch}</strong></span>
                  )}
                  {scanStatus.matches !== undefined && (
                    <span>Khớp: <strong className="text-emerald-400">{scanStatus.matches}</strong></span>
                  )}
                  {scanStatus.last_update && (
                    <span>Cập nhật: {scanStatus.last_update.substring(11, 19)}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {scanStatus?.status === 'error' && scanStatus.error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-xs text-red-400">
            Lỗi: {scanStatus.error}
          </div>
        )}
      </div>

      {/* Conditions legend */}
      <div className="px-6 py-2 border-b border-slate-700/50 flex items-center gap-4 flex-wrap text-[10px] text-slate-500">
        <span className="px-2 py-0.5 rounded bg-slate-700/50">Close &lt; SMA200</span>
        <span className="px-2 py-0.5 rounded bg-slate-700/50">Avg Vol 20 &gt;= 500K</span>
        <span className="px-2 py-0.5 rounded bg-slate-700/50">0 &lt; PE &lt; 20</span>
        <span className="px-2 py-0.5 rounded bg-slate-700/50">0 &lt; PB &lt; 5</span>
      </div>

      {/* Table */}
      {data.length > 0 ? (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider w-12">#</th>
                  <ThSort col="Symbol" label="Symbol" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} />
                  <ThSort col="Close" label="Giá" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <ThSort col="SMA200" label="SMA200" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <ThSort col="Pct_Below_SMA200" label="% Dưới SMA" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <ThSort col="Avg_Vol_20" label="Vol TB 20" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <ThSort col="PE" label="PE" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <ThSort col="PB" label="PB" onSort={handleSort} sortKey={sortKey} sortAsc={sortAsc} align="right" />
                  <th className="px-4 py-3 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Ngày Quét</th>
                </tr>
              </thead>
              <tbody>
                {displayData.map((stock, index) => {
                  const pctBelow = Number(stock.Pct_Below_SMA200)
                  const pctColor = pctBelow <= -20 ? 'text-red-400' : pctBelow <= -10 ? 'text-orange-400' : 'text-amber-400'

                  return (
                    <tr key={stock.Symbol + index} className="border-b border-slate-800/50 hover:bg-slate-700/20 transition-colors">
                      <td className="px-4 py-2.5 text-xs text-slate-600">{index + 1}</td>
                      <td className="px-4 py-2.5">
                        <span className="text-sm font-bold text-blue-400">{stock.Symbol}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-300">
                        {Number(stock.Close).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-500">
                        {Number(stock.SMA200).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={`text-xs font-bold ${pctColor}`}>
                          {pctBelow.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-400">
                        {Number(stock.Avg_Vol_20).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={`text-xs font-semibold ${Number(stock.PE) < 10 ? 'text-emerald-400' : 'text-slate-300'}`}>
                          {Number(stock.PE).toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <span className={`text-xs font-semibold ${Number(stock.PB) < 1.5 ? 'text-emerald-400' : 'text-slate-300'}`}>
                          {Number(stock.PB).toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-600">
                        {stock.Scan_Date}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Load more */}
          {sortedData.length > showCount && (
            <div className="text-center py-3 border-t border-slate-700/50">
              <button
                onClick={() => setShowCount(prev => prev + 30)}
                className="text-xs text-blue-400 hover:text-blue-300 font-medium"
              >
                Xem thêm ({sortedData.length - showCount} còn lại)
              </button>
            </div>
          )}
        </>
      ) : (
        !isRunning && (
          <div className="px-6 py-12 text-center text-slate-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-sm">Chưa có kết quả. Nhấn <strong>&quot;Bắt Đầu Quét&quot;</strong> để quét toàn thị trường.</p>
            <p className="text-xs mt-1 text-slate-600">Quét ~1700 mã có thể mất vài giờ. Tiến trình được lưu tự động.</p>
          </div>
        )
      )}
    </div>
  )
}

function ThSort({ col, label, onSort, sortKey, sortAsc, align = 'left' }: {
  col: keyof PriceFilterResult
  label: string
  onSort: (key: keyof PriceFilterResult) => void
  sortKey: keyof PriceFilterResult
  sortAsc: boolean
  align?: 'left' | 'right'
}) {
  const isActive = sortKey === col
  return (
    <th
      onClick={() => onSort(col)}
      className={`px-4 py-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-slate-300 transition-colors select-none ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
    >
      {label}
      <span className={`ml-1 ${isActive ? 'text-blue-400' : 'text-slate-700'}`}>
        {isActive ? (sortAsc ? '\u25B2' : '\u25BC') : '\u2195'}
      </span>
    </th>
  )
}
