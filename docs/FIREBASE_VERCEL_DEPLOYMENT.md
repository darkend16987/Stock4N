# 🚀 Firebase + Vercel Deployment Guide

## Recommended: GitHub Actions + Vercel

### **Architecture**

```
GitHub Actions (7AM daily)
    ↓
Run Python pipeline in GitHub runner
    ↓
Generate db.json
    ↓
Commit to repo (frontend/public/data/db.json)
    ↓
Vercel auto-deploy (git push hook)
    ↓
Users access updated dashboard
```

---

## 📋 **Migration Checklist**

### **Step 1: Setup GitHub Actions** (5 minutes)

Create `.github/workflows/daily-pipeline.yml`:

```yaml
name: Daily Stock Analysis Pipeline

on:
  schedule:
    # Run at 7:00 AM Vietnam time (UTC+7 = 00:00 UTC)
    - cron: '0 0 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # 30 min max (pipeline takes ~8 min)

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install TA-Lib dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y wget build-essential
          wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
          tar -xzf ta-lib-0.4.0-src.tar.gz
          cd ta-lib/
          ./configure --prefix=/usr
          make
          sudo make install
          cd ..

      - name: Install Python dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run data pipeline
        env:
          VNSTOCK_API_KEY: ${{ secrets.VNSTOCK_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          TZ: Asia/Ho_Chi_Minh
        run: |
          cd src
          python main.py all

      - name: Copy db.json to frontend
        run: |
          mkdir -p frontend/public/data
          cp data/export/db.json frontend/public/data/db.json

      - name: Commit and push if changed
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add frontend/public/data/db.json
          git diff --staged --quiet || git commit -m "chore: Update stock data $(date +'%Y-%m-%d %H:%M')"
          git push
```

### **Step 2: Add GitHub Secrets** (2 minutes)

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add secrets:
   - `VNSTOCK_API_KEY`: Your vnstock API key
   - `GOOGLE_API_KEY`: Your Google Gemini API key

### **Step 3: Deploy Frontend to Vercel** (3 minutes)

**Option A: Vercel CLI**
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from frontend folder
cd frontend
vercel

# Follow prompts, link to GitHub repo
```

**Option B: Vercel Dashboard** (Easier)
1. Go to https://vercel.com
2. Import GitHub repository
3. Framework: Next.js
4. Root Directory: `frontend`
5. Deploy!

### **Step 4: Configure Vercel** (1 minute)

In Vercel dashboard:
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`
- **Root Directory**: `frontend`

**Environment Variables** (if needed):
- None required (reads from static db.json)

### **Step 5: Test** (5 minutes)

```bash
# Trigger GitHub Actions manually
# Go to: Actions → Daily Stock Analysis Pipeline → Run workflow

# Wait ~8 minutes

# Check Vercel deployment
# Vercel will auto-deploy when GitHub Actions pushes db.json
```

---

## 🎯 **Alternative: Firebase Functions** (Advanced)

If you want **real-time data** instead of daily updates:

### **Architecture**

```
Cloud Scheduler → Firebase Functions → Firestore → Vercel
```

### **Step 1: Setup Firebase**

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Init project
firebase init functions
# Select: Python, Firestore

# Init Firestore
firebase init firestore
```

### **Step 2: Create Cloud Function**

Create `functions/main.py`:

```python
from firebase_functions import scheduler_fn, https_fn
from firebase_admin import initialize_app, firestore
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

initialize_app()

@scheduler_fn.on_schedule(schedule="0 0 * * *", timezone="Asia/Ho_Chi_Minh")
def scheduled_pipeline(event: scheduler_fn.ScheduledEvent) -> None:
    """Run daily at 7AM Vietnam time"""

    # Import your modules
    from modules.ingestion.loader import VNStockLoader
    from modules.processing.calculator import FinancialCalculator
    from modules.analysis.scorer import StockScorer
    from modules.portfolio.manager import PortfolioManager
    import config

    # 1. Ingestion
    loader = VNStockLoader()
    loader.run_ingestion(config.VN100_SYMBOLS)

    # 2. Processing
    calculator = FinancialCalculator()
    calculator.run_processing(config.VN100_SYMBOLS)

    # 3. Analysis
    scorer = StockScorer()
    analysis_df = scorer.run_analysis()

    # 4. Portfolio
    manager = PortfolioManager()
    portfolio_df = manager.generate_recommendation(100_000_000)

    # 5. Save to Firestore
    db = firestore.client()

    # Save analysis
    for _, row in analysis_df.iterrows():
        db.collection('stocks').document(row['Symbol']).set({
            'symbol': row['Symbol'],
            'score': float(row['Total_Score']),
            'recommendation': row['Recommendation'],
            'fund_score': float(row['Fund_Score']),
            'tech_score': float(row['Tech_Score']),
            'price': float(row['Price']),
            'updated_at': firestore.SERVER_TIMESTAMP
        })

    # Save portfolio
    for _, row in portfolio_df.iterrows():
        db.collection('portfolio').document(row['Symbol']).set(row.to_dict())

    # Save metadata
    db.collection('metadata').document('last_run').set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'total_stocks': len(config.VN100_SYMBOLS),
        'status': 'success'
    })

    print("✅ Pipeline completed successfully")

@https_fn.on_request()
def manual_trigger(req: https_fn.Request) -> https_fn.Response:
    """Manual trigger via HTTPS"""
    scheduled_pipeline(None)
    return https_fn.Response("Pipeline triggered!")
```

### **Step 3: Update requirements.txt**

`functions/requirements.txt`:
```txt
firebase-admin>=6.0.0
firebase-functions>=0.4.0
pandas>=2.0.0
numpy
git+https://github.com/thinh-vu/vnstock@main
ta-lib
scipy
scikit-learn>=1.3.0
```

### **Step 4: Deploy**

```bash
# Deploy functions
firebase deploy --only functions

# Deploy Firestore rules
firebase deploy --only firestore:rules

# Deploy Firestore indexes
firebase deploy --only firestore:indexes
```

### **Step 5: Update Frontend**

`frontend/lib/data.ts`:
```typescript
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  // ... other config
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export async function getStockData() {
  const stocksSnapshot = await getDocs(collection(db, 'stocks'));
  const portfolioSnapshot = await getDocs(collection(db, 'portfolio'));

  return {
    analysis: stocksSnapshot.docs.map(doc => doc.data()),
    portfolio: portfolioSnapshot.docs.map(doc => doc.data()),
    last_updated: new Date().toISOString()
  };
}
```

**Vercel Environment Variables**:
- `NEXT_PUBLIC_FIREBASE_API_KEY`
- `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
- etc.

---

## 📊 **Comparison**

| Feature | GitHub Actions + Vercel | Firebase Functions + Vercel |
|---------|------------------------|----------------------------|
| **Setup Complexity** | ⭐⭐ Easy | ⭐⭐⭐⭐ Complex |
| **Code Changes** | ✅ Minimal | ⚠️ Significant (Firestore SDK) |
| **Data Freshness** | Daily (scheduled) | Real-time (Firestore) |
| **Cost** | **$0** (free tier) | **$0-5/month** (depends on traffic) |
| **Timeout** | 6 hours ✅ | 9 minutes ⚠️ (but enough) |
| **Scalability** | Good | Excellent |
| **Maintenance** | Low | Medium |

---

## 🎯 **FINAL RECOMMENDATION**

### **For Most Users: GitHub Actions + Vercel**

**Why?**
- ✅ FREE forever
- ✅ Minimal code change
- ✅ No timeout worries
- ✅ Already have run_all.sh workflow
- ✅ Simple to maintain

**Use Case**: Daily stock analysis, personal use, small teams

### **For Production/Scale: Firebase Functions + Vercel**

**Why?**
- ✅ Real-time data
- ✅ Auto-scaling
- ✅ Better for high traffic
- ✅ Professional infrastructure

**Use Case**: Public service, many users, need real-time updates

---

## ✅ **Next Steps**

Choose your path:

**Path A: Quick & Free (GitHub Actions)**
```bash
1. Create .github/workflows/daily-pipeline.yml
2. Add GitHub secrets (API keys)
3. Deploy frontend to Vercel
4. Done! ✅
```

**Path B: Production-Ready (Firebase)**
```bash
1. Setup Firebase project
2. Create Cloud Function
3. Update frontend to use Firestore
4. Deploy to Vercel
5. Done! 🚀
```

---

**Need help with implementation?** Let me know which path you choose! 💪
