'use client'

import { useState, useCallback } from 'react'
import { runCommand, PIPELINE_COMMANDS, type CommandStatus } from '@/lib/api'

interface CommandCenterProps {
  onComplete: () => void
}

const CATEGORY_CONFIG = {
  data:     { label: 'Data Pipeline',  color: 'blue',   gradient: 'from-blue-600 to-blue-700' },
  analysis: { label: 'Analysis',       color: 'violet',  gradient: 'from-violet-600 to-violet-700' },
  trading:  { label: 'Trading',        color: 'emerald', gradient: 'from-emerald-600 to-emerald-700' },
  ai:       { label: 'AI / ML',        color: 'amber',   gradient: 'from-amber-600 to-amber-700' },
} as const

const ICONS: Record<string, string> = {
  download:  'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
  cpu:       'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z',
  upload:    'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12',
  chart:     'M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
  activity:  'M22 12h-4l-3 9L9 3l-3 9H2',
  sliders:   'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4',
  briefcase: 'M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  rewind:    'M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z',
  brain:     'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  zap:       'M13 10V3L4 14h7v7l9-11h-7z',
  target:    'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
  play:      'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
}

function CommandIcon({ name, className }: { name: string; className?: string }) {
  const path = ICONS[name] || ICONS.play
  return (
    <svg className={className || 'w-4 h-4'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={path} />
    </svg>
  )
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin-slow" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

export function CommandCenter({ onComplete }: CommandCenterProps) {
  const [expanded, setExpanded] = useState(false)
  const [statuses, setStatuses] = useState<Record<string, CommandStatus>>({})
  const [runAllActive, setRunAllActive] = useState(false)
  const [lastOutput, setLastOutput] = useState<string>('')

  const execute = useCallback(async (cmdId: string) => {
    setStatuses(prev => ({ ...prev, [cmdId]: 'running' }))
    try {
      const result = await runCommand(cmdId)
      setStatuses(prev => ({ ...prev, [cmdId]: result.success ? 'success' : 'error' }))
      if (result.stdout) setLastOutput(result.stdout.slice(-500))
      if (!result.success && result.stderr) setLastOutput(result.stderr.slice(-500))
      return result.success
    } catch (e) {
      setStatuses(prev => ({ ...prev, [cmdId]: 'error' }))
      setLastOutput(`Error: ${e}`)
      return false
    }
  }, [])

  const runAll = useCallback(async () => {
    setRunAllActive(true)
    setLastOutput('')
    const sequence = ['ingestion', 'processing', 'analysis', 'breadth', 'portfolio', 'export']
    for (const cmd of sequence) {
      const ok = await execute(cmd)
      if (!ok) break
    }
    setRunAllActive(false)
    onComplete()
  }, [execute, onComplete])

  const runSingle = useCallback(async (cmdId: string) => {
    await execute(cmdId)
    if (['export', 'portfolio', 'analysis'].includes(cmdId)) {
      onComplete()
    }
  }, [execute, onComplete])

  const categories = ['data', 'analysis', 'trading', 'ai'] as const
  const grouped = Object.fromEntries(
    categories.map(cat => [cat, PIPELINE_COMMANDS.filter(c => c.category === cat)])
  )

  const statusIcon = (status: CommandStatus) => {
    if (status === 'running') return <Spinner />
    if (status === 'success') return <span className="text-emerald-400 text-xs">&#10003;</span>
    if (status === 'error') return <span className="text-red-400 text-xs">&#10007;</span>
    return null
  }

  return (
    <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Header bar */}
      <div
        className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-slate-700/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center">
            <CommandIcon name="play" className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Command Center</h2>
            <p className="text-xs text-slate-400">Pipeline controls & automation</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Run All button */}
          <button
            onClick={(e) => { e.stopPropagation(); runAll(); }}
            disabled={runAllActive}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
              runAllActive
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:from-blue-400 hover:to-cyan-400 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40'
            }`}
          >
            {runAllActive ? <Spinner /> : <CommandIcon name="play" className="w-4 h-4" />}
            {runAllActive ? 'Running...' : 'Run All Pipeline'}
          </button>
          {/* Chevron */}
          <svg
            className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-6 pb-5 space-y-4 border-t border-slate-700/50">
          {/* Command grid by category */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
            {categories.map(cat => {
              const cfg = CATEGORY_CONFIG[cat]
              return (
                <div key={cat} className="space-y-2">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{cfg.label}</h3>
                  <div className="space-y-1.5">
                    {grouped[cat].map(cmd => {
                      const status = statuses[cmd.id] || 'idle'
                      const isRunning = status === 'running'
                      return (
                        <button
                          key={cmd.id}
                          onClick={() => runSingle(cmd.id)}
                          disabled={isRunning || runAllActive}
                          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all duration-150 group ${
                            isRunning
                              ? 'bg-slate-700/50 text-slate-300'
                              : status === 'success'
                                ? 'bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
                                : status === 'error'
                                  ? 'bg-red-500/10 text-red-300 hover:bg-red-500/20'
                                  : 'bg-slate-700/30 text-slate-300 hover:bg-slate-700/60 hover:text-white'
                          } ${(isRunning || runAllActive) ? 'cursor-not-allowed opacity-60' : ''}`}
                        >
                          <CommandIcon name={cmd.icon} className="w-4 h-4 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium truncate">{cmd.label}</div>
                            <div className="text-[10px] text-slate-500 truncate">{cmd.description}</div>
                          </div>
                          <div className="flex-shrink-0">
                            {statusIcon(status)}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Output log */}
          {lastOutput && (
            <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-700/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">Last output</span>
                <button
                  onClick={() => setLastOutput('')}
                  className="text-[10px] text-slate-500 hover:text-slate-300"
                >
                  Clear
                </button>
              </div>
              <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
                {lastOutput}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
