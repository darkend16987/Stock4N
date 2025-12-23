# Stock4N - AI-Powered Vietnamese Stock Market Advisor

An intelligent stock analysis system for the Vietnamese stock market (VN100) using a defensive swing trading strategy with 60% fundamental and 40% technical analysis.

## Features

- **Automated Stock Analysis**: Analyzes top 30 VN100 stocks automatically
- **Multi-Source Data**: Fallback mechanism across VCI, TCBS, and MSN sources
- **Dual Analysis Approach**:
  - Fundamental: ROE, profit growth, asset growth, equity ratio
  - Technical: RSI, SMA, price trends, volume analysis
- **Portfolio Management**: Score-weighted position sizing with risk management
- **Modern Dashboard**: Next.js frontend with real-time insights
- **Production-Ready**: Comprehensive logging, validation, and error handling

## Trading Strategy

**Defensive Swing Trading (1-3 months holding period)**
- Risk/Reward: 1:2 ratio (-7% stop loss, +15% target)
- Position Sizing: Maximum 40% per stock, 20% cash reserve
- Entry Signal: Score ≥ 7.0 with positive technical indicators
- Score Weighting: 60% fundamentals + 40% technical

## Architecture

```
VN100 Top 30 Stocks
    ↓
[Ingestion] → Multi-source data fetching with retry logic
    ↓
[Processing] → Financial metrics calculation (ROE, growth rates)
    ↓
[Analysis] → Fundamental + Technical scoring
    ↓
[Portfolio] → Position sizing & risk management
    ↓
[Export] → JSON output (db.json)
    ↓
[Frontend] → Next.js dashboard
```

## Tech Stack

**Backend:**
- Python 3.10
- pandas, numpy, TA-Lib
- vnstock API (v3.x OOP mode)
- Docker containerization

**Frontend:**
- Next.js 14.1 (App Router)
- TypeScript
- Tailwind CSS
- Recharts for visualizations

## Installation

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Git

### Backend Setup (Docker)

1. Clone the repository:
```bash
git clone https://github.com/darkend16987/Stock4N.git
cd Stock4N
```

2. Build and run with Docker:
```bash
docker-compose up --build
```

The system will:
- Fetch data for 30 VN100 stocks
- Analyze fundamentals and technicals
- Generate portfolio recommendations
- Export results to `/data/export/db.json`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

4. Open http://localhost:3000 in your browser

## Usage

### Running Analysis

**Full analysis (all 30 stocks):**
```bash
docker-compose run stock4n python src/main.py all
```

**Single stock analysis:**
```bash
docker-compose run stock4n python src/main.py single VNM
```

**Custom stock list:**
```bash
docker-compose run stock4n python src/main.py custom VNM,FPT,VHM
```

### Output Files

- `/data/export/db.json` - Complete analysis results
- `/data/export/portfolio_recommendations.json` - Top recommendations
- `/data/logs/` - Daily rotating logs

## Configuration

Edit `/src/config.py` to customize:

**Scoring Thresholds:**
```python
FUNDAMENTAL_THRESHOLDS = {
    'roe': {'excellent': 20, 'good': 15, 'fair': 10},
    'profit_growth': {'strong': 20, 'good': 10, 'weak': -20}
}
```

**Portfolio Settings:**
```python
PORTFOLIO_CONFIG = {
    'max_position_pct': 0.40,  # Max 40% per position
    'cash_reserve_pct': 0.20   # Keep 20% cash
}
```

**Risk Management:**
```python
RISK_MANAGEMENT = {
    'stop_loss_pct': 0.07,      # -7% stop loss
    'target_profit_pct': 0.15   # +15% target
}
```

## Deployment

### Deploy Frontend to Vercel

1. **Connect GitHub Repository:**
   - Go to [vercel.com](https://vercel.com)
   - Click "Import Project"
   - Select your Stock4N repository
   - Set root directory to `frontend`

2. **Configure Build Settings:**
   ```
   Framework Preset: Next.js
   Build Command: npm run build
   Output Directory: .next
   Install Command: npm install
   ```

3. **Environment Variables:**
   No environment variables needed for basic setup.

4. **Deploy:**
   - Click "Deploy"
   - Vercel will build and deploy automatically
   - Get your production URL (e.g., `https://stock4n.vercel.app`)

5. **Data Sync Strategy:**

   **Option A: Manual Upload (Simple)**
   - Run backend analysis locally/Docker
   - Copy `/data/export/db.json` to `/frontend/public/data/export/`
   - Commit and push to trigger Vercel rebuild

   **Option B: API Integration (Advanced)**
   - Host backend on a server (AWS, DigitalOcean)
   - Create API endpoint to serve `db.json`
   - Update `frontend/lib/data.ts` to fetch from API
   - Set up cron job to run analysis daily

   **Option C: GitHub Actions (Recommended)**
   ```yaml
   # .github/workflows/analyze.yml
   name: Daily Stock Analysis
   on:
     schedule:
       - cron: '0 17 * * 1-5'  # Run at 5 PM weekdays
   jobs:
     analyze:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Run Analysis
           run: docker-compose up
         - name: Copy Results
           run: cp data/export/db.json frontend/public/data/export/
         - name: Commit Results
           run: |
             git config user.name "GitHub Actions"
             git add frontend/public/data/export/db.json
             git commit -m "Update analysis results"
             git push
   ```

### Deploy Backend to Cloud

**Option 1: AWS ECS (Recommended for production)**
```bash
# Build and push Docker image
docker build -t stock4n-backend .
docker tag stock4n-backend:latest <AWS_ACCOUNT>.dkr.ecr.ap-southeast-1.amazonaws.com/stock4n
docker push <AWS_ACCOUNT>.dkr.ecr.ap-southeast-1.amazonaws.com/stock4n

# Deploy to ECS with scheduled task (daily at 5 PM)
```

**Option 2: DigitalOcean App Platform**
- Connect GitHub repository
- Select Dockerfile deployment
- Set up cron job for daily analysis

## Project Structure

```
Stock4N/
├── src/
│   ├── modules/
│   │   ├── ingestion/
│   │   │   └── loader.py          # Multi-source data fetching
│   │   ├── processing/
│   │   │   └── calculator.py      # Financial metrics calculation
│   │   ├── analysis/
│   │   │   └── scorer.py          # Scoring engine
│   │   ├── portfolio/
│   │   │   └── manager.py         # Position sizing & risk
│   │   └── utils/
│   │       ├── logger.py          # Logging system
│   │       ├── validator.py       # Data validation
│   │       ├── exporter.py        # JSON export
│   │       └── exceptions.py      # Custom exceptions
│   ├── config.py                  # Centralized configuration
│   └── main.py                    # Entry point
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # Root layout
│   │   ├── page.tsx               # Main dashboard
│   │   └── globals.css            # Tailwind styles
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── StatsCards.tsx
│   │   ├── PortfolioTable.tsx
│   │   └── AnalysisTable.tsx
│   ├── lib/
│   │   └── data.ts                # Data fetching logic
│   └── public/
│       └── data/export/           # Analysis results
├── data/
│   ├── raw/                       # Raw API data cache
│   ├── processed/                 # Processed data
│   ├── export/                    # JSON outputs
│   └── logs/                      # Application logs
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## Key Improvements (Production-Ready)

### Priority 1 (Critical) - ✅ COMPLETED
- ✅ Created `utils/__init__.py` for proper package structure
- ✅ Comprehensive logging system (daily rotation, auto-cleanup)
- ✅ Custom exception hierarchy for better error handling
- ✅ Data validation at every pipeline stage
- ✅ Parametrized all hard-coded values in config

### Priority 2 (High) - ✅ COMPLETED
- ✅ Retry logic with exponential backoff for API calls
- ✅ Fixed YoY growth calculation (proper quarter matching)
- ✅ Fixed price unit auto-detection (handles both VND formats)
- ✅ Removed unsupported DNSE source
- ✅ Added logging throughout all modules

### Priority 3 (Medium) - PENDING
- ⏳ Unit tests for all modules
- ⏳ Parallel data fetching with ThreadPoolExecutor
- ⏳ Database migration (SQLite/PostgreSQL)
- ⏳ Backtest module for strategy validation

### Priority 4 (Low) - PENDING
- ⏳ Real-time monitoring dashboard
- ⏳ Sentiment analysis integration
- ⏳ Performance optimization
- ⏳ API documentation

## Testing

```bash
# Run unit tests (coming soon)
python -m pytest tests/

# Test single stock
docker-compose run stock4n python src/main.py single VNM

# Test with verbose logging
docker-compose run stock4n python src/main.py all --verbose
```

## Monitoring & Logs

**Log Files:**
- `/data/logs/stock4n_YYYY-MM-DD.log` - Daily logs
- `/data/logs/stock4n_error_YYYY-MM-DD.log` - Error logs
- Auto-cleanup after 7 days

**Log Levels:**
```python
# In config.py
LOG_CONFIG = {
    'level': logging.INFO,  # Change to DEBUG for verbose output
    'retention_days': 7
}
```

## Troubleshooting

**Issue: API rate limit errors**
```
Solution: System automatically retries with exponential backoff.
Check RATE_LIMIT config in config.py for cooldown settings.
```

**Issue: No data for certain stocks**
```
Solution: System tries VCI → TCBS → MSN sources automatically.
Check logs to see which source succeeded.
```

**Issue: Floating point display issues**
```
Solution: Already fixed with .1f format specifiers in manager.py
```

**Issue: DNSE source warnings**
```
Solution: DNSE removed from config (vnstock v3.x doesn't support it)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Disclaimer

**Important:** This system is for educational and research purposes only. It does not constitute financial advice. Always do your own research and consult with a licensed financial advisor before making investment decisions. Past performance does not guarantee future results.

## Support

For issues and questions:
- GitHub Issues: [https://github.com/darkend16987/Stock4N/issues](https://github.com/darkend16987/Stock4N/issues)
- Email: support@stock4n.com

## Acknowledgments

- [vnstock](https://github.com/thinh-vu/vnstock) - Vietnamese stock data API
- [TA-Lib](https://mrjbq7.github.io/ta-lib/) - Technical analysis library
- [Next.js](https://nextjs.org/) - React framework
- Vietnamese Stock Market Community

---

**Last Updated:** December 2025
**Version:** 1.0.0
**Status:** Production Ready 🚀
