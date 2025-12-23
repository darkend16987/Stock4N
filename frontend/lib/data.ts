import { readFile } from 'fs/promises'
import { join } from 'path'

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

export async function getStockData(): Promise<StockData> {
  try {
    // Try to read from backend data export
    const filePath = join(process.cwd(), '..', 'data', 'export', 'db.json')
    const fileContent = await readFile(filePath, 'utf-8')
    const data: StockData = JSON.parse(fileContent)
    return data
  } catch (error) {
    console.error('Error loading stock data:', error)
    // Return mock data if file not found
    return {
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
  }
}

export function getRecommendationColor(recommendation: string): string {
  if (recommendation.includes('MUA MẠNH')) return 'text-green-600 bg-green-50 dark:bg-green-900/20'
  if (recommendation.includes('MUA THĂM DÒ')) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
  if (recommendation.includes('THEO DÕI')) return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
  if (recommendation.includes('BÁN')) return 'text-red-600 bg-red-50 dark:bg-red-900/20'
  return 'text-slate-600 bg-slate-50 dark:bg-slate-900/20'
}

export function getScoreColor(score: number): string {
  if (score >= 7.5) return 'text-green-600 font-bold'
  if (score >= 6.0) return 'text-blue-600 font-semibold'
  if (score >= 4.0) return 'text-yellow-600'
  return 'text-red-600'
}
