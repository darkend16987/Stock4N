export interface StockAnalysis {
  Symbol: string
  Total_Score: number
  Recommendation: string
  Fund_Score: number
  Tech_Score: number
  Fund_Reason: string
  Tech_Reason: string
  Price: number
}

export interface PortfolioPosition {
  Symbol: string
  Action: string
  Score: number
  Entry_Price: string
  'Weight_%': string
  Capital_VND: string
  Volume_Shares: number
  Stop_Loss: string
  Target: string
  'Risk/Reward': string
}

export interface StockData {
  last_updated: string
  analysis: StockAnalysis[]
  portfolio: PortfolioPosition[]
  charts: Record<string, any[]>
  metadata?: {
    total_symbols: number
    total_positions: number
    chart_days: number
    export_timestamp: string
  }
}

const emptyData: StockData = {
  last_updated: new Date().toISOString(),
  analysis: [],
  portfolio: [],
  charts: {},
  metadata: {
    total_symbols: 0,
    total_positions: 0,
    chart_days: 100,
    export_timestamp: new Date().toISOString()
  }
}

export async function getStockData(): Promise<StockData> {
  try {
    const baseUrl = typeof window === 'undefined'
      ? 'http://localhost:3000'
      : ''

    const dataUrl = process.env.NEXT_PUBLIC_DATA_URL || `${baseUrl}/data/db.json`

    const response = await fetch(dataUrl, {
      cache: 'no-store'
    })

    if (!response.ok) {
      console.warn('db.json not found, returning empty data')
      return emptyData
    }

    const data: StockData = await response.json()
    return data
  } catch (error) {
    console.error('Error loading stock data:', error)
    return emptyData
  }
}

export function getRecommendationColor(recommendation: string): string {
  if (recommendation.includes('MUA MẠNH')) return 'text-emerald-400 bg-emerald-500/15 border border-emerald-500/30'
  if (recommendation.includes('MUA THĂM DÒ')) return 'text-blue-400 bg-blue-500/15 border border-blue-500/30'
  if (recommendation.includes('THEO DÕI')) return 'text-amber-400 bg-amber-500/15 border border-amber-500/30'
  if (recommendation.includes('BÁN')) return 'text-red-400 bg-red-500/15 border border-red-500/30'
  return 'text-slate-400 bg-slate-500/15 border border-slate-500/30'
}

export function getScoreColor(score: number): string {
  if (score >= 7.5) return 'text-emerald-400'
  if (score >= 6.0) return 'text-blue-400'
  if (score >= 4.0) return 'text-amber-400'
  return 'text-red-400'
}

export function getScoreBg(score: number): string {
  if (score >= 7.5) return 'bg-emerald-500/20'
  if (score >= 6.0) return 'bg-blue-500/20'
  if (score >= 4.0) return 'bg-amber-500/20'
  return 'bg-red-500/20'
}
