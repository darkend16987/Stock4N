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

export interface PipelineCommand {
  id: string
  label: string
  description: string
  category: 'data' | 'analysis' | 'trading' | 'ai'
  icon: string
}

export const PIPELINE_COMMANDS: PipelineCommand[] = [
  // Data Pipeline
  { id: 'ingestion', label: 'Thu thập dữ liệu', description: 'Tải dữ liệu giá & tài chính từ TCBS/VCI', category: 'data', icon: 'download' },
  { id: 'processing', label: 'Xử lý dữ liệu', description: 'Tính toán chỉ số kỹ thuật & cơ bản', category: 'data', icon: 'cpu' },
  { id: 'export', label: 'Xuất dữ liệu', description: 'Export db.json cho frontend', category: 'data', icon: 'upload' },

  // Analysis
  { id: 'analysis', label: 'Phân tích & Chấm điểm', description: 'Scoring cổ phiếu (Fund 65% + Tech 35%)', category: 'analysis', icon: 'chart' },
  { id: 'breadth', label: 'Market Breadth', description: 'Phân tích sentiment thị trường', category: 'analysis', icon: 'activity' },
  { id: 'adaptive', label: 'Adaptive Params', description: 'Tối ưu RSI/MA cho từng mã', category: 'analysis', icon: 'sliders' },

  // Trading
  { id: 'portfolio', label: 'Danh mục đầu tư', description: 'Phân bổ vốn & đề xuất vị thế', category: 'trading', icon: 'briefcase' },
  { id: 'backtest', label: 'Backtest', description: 'Kiểm thử chiến lược trên dữ liệu quá khứ', category: 'trading', icon: 'rewind' },

  // AI/ML
  { id: 'learn', label: 'Pattern Learning', description: 'Học mẫu seasonality, momentum, S/R', category: 'ai', icon: 'brain' },
  { id: 'ml_train', label: 'ML Training', description: 'Huấn luyện model RandomForest/GBM', category: 'ai', icon: 'zap' },
  { id: 'ml_predict', label: 'ML Dự đoán', description: 'Dự đoán xu hướng bằng ML model', category: 'ai', icon: 'target' },
]
