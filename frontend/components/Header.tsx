export function Header({ lastUpdated }: { lastUpdated: string }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-slate-800 dark:text-white mb-2">
            Stock4N
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            VN Stock Intelligent Advisor - AI-powered Portfolio Recommendations
          </p>
        </div>
        <div className="text-right">
          <div className="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <svg className="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm">
              <div className="text-slate-600 dark:text-slate-400">Last Updated</div>
              <div className="font-semibold text-slate-800 dark:text-white">
                {new Date(lastUpdated).toLocaleString('vi-VN')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
