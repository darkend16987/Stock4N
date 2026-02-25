import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Stock4N - VN Stock Intelligent Advisor',
  description: 'AI-powered Vietnamese stock market analysis and portfolio recommendations',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <div className="min-h-screen bg-[#0a0f1c]">
          {children}
        </div>
      </body>
    </html>
  )
}
