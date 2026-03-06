/**
 * API client for Stock4N backend REST API (port 8502)
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8502'

export type CommandStatus = 'idle' | 'running' | 'success' | 'error'

export interface CommandResult {
  command: string
  success: boolean
  stdout: string
  stderr: string
}

export interface CommandState {
  status: CommandStatus
  result?: CommandResult
  error?: string
}

export async function runCommand(command: string): Promise<CommandResult> {
  const response = await fetch(`${API_BASE}/run/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(3000),
    })
    const data = await response.json()
    return data.status === 'ok'
  } catch {
    return false
  }
}

export async function getAvailableCommands(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE}/commands`)
    const data = await response.json()
    return data.commands || []
  } catch {
    return []
  }
}

// ── Scan API (background price filter) ─────────────────

export interface ScanStatus {
  status: 'idle' | 'running' | 'completed' | 'error'
  started_at: string
  error: string
  processed?: number
  batch?: string
  matches?: number
  errors?: number
  last_update?: string
}

export async function startScan(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/scan/start`, { method: 'POST' })
    const data = await res.json()
    return data.success === true
  } catch {
    return false
  }
}

export async function getScanStatus(): Promise<ScanStatus> {
  try {
    const res = await fetch(`${API_BASE}/scan/status`)
    return await res.json()
  } catch {
    return { status: 'idle', started_at: '', error: '' }
  }
}

export async function getScanResults(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/scan/results`)
    const data = await res.json()
    return data.results || []
  } catch {
    return []
  }
}

export async function stopScan(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/scan/stop`, { method: 'POST' })
    const data = await res.json()
    return data.success === true
  } catch {
    return false
  }
}

// ── Pipeline Commands ──────────────────────────────────

export interface PipelineCommand {
  id: string
  label: string
  description: string
  category: 'data' | 'analysis' | 'trading' | 'ai'
  icon: string
}

export const PIPELINE_COMMANDS: PipelineCommand[] = [
  // Data Pipeline
  { id: 'ingestion', label: 'Thu thap du lieu', description: 'Tai du lieu gia & tai chinh tu TCBS/VCI', category: 'data', icon: 'download' },
  { id: 'processing', label: 'Xu ly du lieu', description: 'Tinh toan chi so ky thuat & co ban', category: 'data', icon: 'cpu' },
  { id: 'export', label: 'Xuat du lieu', description: 'Export db.json cho frontend', category: 'data', icon: 'upload' },

  // Analysis
  { id: 'analysis', label: 'Phan tich & Cham diem', description: 'Scoring co phieu (Fund 65% + Tech 35%)', category: 'analysis', icon: 'chart' },
  { id: 'breadth', label: 'Market Breadth', description: 'Phan tich sentiment thi truong', category: 'analysis', icon: 'activity' },
  { id: 'adaptive', label: 'Adaptive Params', description: 'Toi uu RSI/MA cho tung ma', category: 'analysis', icon: 'sliders' },

  // Trading
  { id: 'portfolio', label: 'Danh muc dau tu', description: 'Phan bo von & de xuat vi the', category: 'trading', icon: 'briefcase' },
  { id: 'backtest', label: 'Backtest', description: 'Kiem thu chien luoc tren du lieu qua khu', category: 'trading', icon: 'rewind' },

  // AI/ML
  { id: 'learn', label: 'Pattern Learning', description: 'Hoc mau seasonality, momentum, S/R', category: 'ai', icon: 'brain' },
  { id: 'ml_train', label: 'ML Training', description: 'Huan luyen model RandomForest/GBM', category: 'ai', icon: 'zap' },
  { id: 'ml_predict', label: 'ML Du doan', description: 'Du doan xu huong bang ML model', category: 'ai', icon: 'target' },
]
