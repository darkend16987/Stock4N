# 🚀 Cloud Run Deployment - Complete Guide

## Overview

Deploy Stock4N to Google Cloud Run for **production-grade reliability** with:
- ✅ **60-minute timeout** (no risk of interruption)
- ✅ **Zero code changes** (uses existing Dockerfile)
- ✅ **No cold starts** (min_instances=1)
- ✅ **Professional monitoring** (Cloud Logging + Alerts)
- ✅ **$1.37/month** (affordable for small scale)

---

## 📋 Prerequisites

### 1. Google Cloud Account
- Create account: https://cloud.google.com
- **Free $300 credit** for new users (3 months)
- Credit card required (but won't charge unless you upgrade)

### 2. gcloud CLI
Install from: https://cloud.google.com/sdk/docs/install

**Quick install:**
```bash
# Linux/Mac
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Windows
# Download: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
```

### 3. API Keys
- **Vnstock API Key**: Register at https://vnstocks.com/login
- **Google Gemini API Key**: Get from https://aistudio.google.com/apikey

---

## 🎯 ONE-COMMAND DEPLOYMENT

### **Step 1: Clone & Setup** (1 minute)

```bash
# Clone repository
git clone https://github.com/your-username/Stock4N.git
cd Stock4N

# Create .env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
# or use your preferred editor
```

Your `.env` should have:
```bash
VNSTOCK_API_KEY=vnstock_YOUR_KEY_HERE
GOOGLE_API_KEY=AIzaSy_YOUR_KEY_HERE
AI_MODEL=gemini-2.0-flash
```

### **Step 2: Deploy to Cloud Run** (10 minutes)

```bash
# Run deployment script
bash scripts/deploy-cloud-run.sh
```

**The script will:**
1. ✅ Check prerequisites (gcloud CLI)
2. ✅ Login to Google Cloud
3. ✅ Create/select project
4. ✅ Enable required APIs (Cloud Run, Storage, Scheduler)
5. ✅ Create Cloud Storage bucket
6. ✅ Deploy Docker container to Cloud Run
7. ✅ Setup Cloud Scheduler (daily 7AM)
8. ✅ Configure monitoring & alerts (optional)

**That's it!** ☕ Grab coffee while it deploys.

### **Step 3: Test Deployment** (2 minutes)

```bash
# Run test script
bash scripts/test-cloud-run.sh
```

This will:
- ✅ Test health endpoint
- ✅ Trigger pipeline manually (optional)
- ✅ Check Cloud Storage
- ✅ Verify scheduler configuration
- ✅ Check monitoring status

---

## 📊 What Gets Deployed

### **Architecture**

```
┌─────────────────────────────────────┐
│ Cloud Scheduler (7AM daily)         │
│ • Trigger: HTTP POST                │
│ • Retry: 3 attempts                 │
│ • Timeout: 60 minutes               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Cloud Run (Docker Container)        │
│ • Image: Your Dockerfile            │
│ • Memory: 2 GiB                     │
│ • CPU: 2 vCPU                       │
│ • Min instances: 1 (no cold start)  │
│ • Timeout: 3600s (60 min)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Cloud Storage (Public)              │
│ • Bucket: stock4n-data              │
│ • File: db.json                     │
│ • Access: Public read               │
│ • Cache: 1 hour                     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Vercel Frontend                     │
│ • Reads: Cloud Storage URL          │
│ • Revalidate: Hourly                │
└─────────────────────────────────────┘
```

---

## 🔧 Configuration Details

### **Cloud Run Service**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Memory | 2 GiB | For TA-Lib & 100 stocks |
| CPU | 2 vCPU | Parallel processing |
| Timeout | 3600s (60 min) | Safe buffer (pipeline: 8 min) |
| Min Instances | 1 | No cold start |
| Max Instances | 1 | Cost control |
| Concurrency | 1 | Sequential execution |

### **Cloud Scheduler**

| Parameter | Value |
|-----------|-------|
| Schedule | `0 0 * * *` (daily) |
| Timezone | Asia/Ho_Chi_Minh |
| Method | HTTP POST |
| Retry | 3 attempts |
| Backoff | Exponential (60s, 120s, 240s) |

### **Cloud Storage**

| Parameter | Value |
|-----------|-------|
| Location | asia-southeast1 |
| Storage Class | Standard |
| Public Access | Enabled (read-only) |
| CORS | Enabled (GET from *) |
| Cache-Control | 1 hour |

---

## 💰 Cost Breakdown

### **Monthly Costs (asia-southeast1)**

| Service | Usage | Cost/Month |
|---------|-------|------------|
| **Cloud Run** | 2 vCPU × 24h × 30 days | ~$1.24 |
| **Cloud Run Memory** | 2 GiB × 720 hours | ~$0.13 |
| **Cloud Scheduler** | 3 jobs | Free (3 free) |
| **Cloud Storage** | 1 MB | Free (5GB free) |
| **Cloud Storage Operations** | ~30 writes/month | Free |
| **Egress (bandwidth)** | ~30 MB/month | Free (1GB free) |
| **TOTAL** | | **~$1.37/month** |

**Cost Optimization:**
- Set `MIN_INSTANCES=0` → **~$0.10/month** (but 10s cold start)
- Use Cloud Functions → **$0-2/month** (but 9 min timeout risk!)

---

## 🎯 Usage

### **Manual Trigger**

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe stock4n-pipeline \
  --region asia-southeast1 \
  --format='value(status.url)')

# Trigger pipeline
curl -X POST $SERVICE_URL/trigger

# Check health
curl $SERVICE_URL/health
```

### **View Logs**

```bash
# Real-time logs
gcloud logging tail 'resource.type=cloud_run_revision' --format=json

# Recent errors
gcloud logging read 'resource.type=cloud_run_revision AND severity>=ERROR' \
  --limit 20 --format=json

# Specific time range
gcloud logging read 'resource.type=cloud_run_revision AND timestamp>="2026-02-25T00:00:00Z"' \
  --limit 50
```

### **Check Status**

```bash
# Service details
gcloud run services describe stock4n-pipeline --region asia-southeast1

# Recent revisions
gcloud run revisions list --service stock4n-pipeline --region asia-southeast1

# Scheduler status
gcloud scheduler jobs describe stock4n-daily-job --location asia-southeast1
```

### **Update Environment Variables**

```bash
# Update API keys
gcloud run services update stock4n-pipeline \
  --region asia-southeast1 \
  --update-env-vars "VNSTOCK_API_KEY=new_key,GOOGLE_API_KEY=new_key"
```

### **Update Schedule**

```bash
# Change to 8AM Vietnam time
gcloud scheduler jobs update http stock4n-daily-job \
  --location asia-southeast1 \
  --schedule "0 1 * * *"
```

---

## 🔍 Monitoring & Alerts

### **Setup Email Alerts**

Done automatically by `deploy-cloud-run.sh` if you choose "y" for alerts.

**Manual setup:**

1. **Create Notification Channel**
```bash
cat > notification-channel.json <<EOF
{
  "type": "email",
  "displayName": "Stock4N Alerts",
  "labels": {
    "email_address": "your-email@example.com"
  }
}
EOF

CHANNEL_NAME=$(gcloud alpha monitoring channels create \
  --notification-channel-content-from-file=notification-channel.json \
  --format="value(name)")
```

2. **Create Alert Policy**
```bash
cat > alert-policy.json <<EOF
{
  "displayName": "Stock4N Pipeline Failed",
  "conditions": [
    {
      "displayName": "Error rate > 10%",
      "conditionThreshold": {
        "filter": "resource.type=\\"cloud_run_revision\\" AND metric.type=\\"run.googleapis.com/request_count\\" AND metric.labels.response_code_class=\\"5xx\\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0.1,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE"
          }
        ]
      }
    }
  ],
  "notificationChannels": ["${CHANNEL_NAME}"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

### **View Metrics**

```bash
# Request count
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --format=json

# Latency
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --format=json
```

---

## 🛠️ Troubleshooting

### **Issue 1: Deployment Failed**

**Symptoms:**
```
ERROR: (gcloud.run.deploy) Cloud Run error: Container failed to start
```

**Solutions:**

1. **Check logs:**
```bash
gcloud logging read 'resource.type=cloud_run_revision' --limit 50
```

2. **Test Docker locally:**
```bash
docker build -t stock4n-test .
docker run -e VNSTOCK_API_KEY=xxx -e GOOGLE_API_KEY=yyy stock4n-test python src/main.py all
```

3. **Check Dockerfile path:**
- Ensure Dockerfile is in project root
- Verify all dependencies in requirements.txt

### **Issue 2: Timeout Errors**

**Symptoms:**
```
ERROR: Request timed out after 3600s
```

**Solutions:**

1. **Check pipeline time:**
```bash
# Should be < 10 minutes
time python src/main.py all
```

2. **Increase timeout (if needed):**
```bash
gcloud run services update stock4n-pipeline \
  --region asia-southeast1 \
  --timeout 3600
```

3. **Optimize pipeline:**
- Check API rate limits
- Reduce max_workers if needed
- Check network connectivity

### **Issue 3: Cloud Storage Upload Failed**

**Symptoms:**
```
ERROR: Failed to upload to Cloud Storage: 403 Forbidden
```

**Solutions:**

1. **Check bucket permissions:**
```bash
gsutil iam get gs://stock4n-data
```

2. **Verify bucket exists:**
```bash
gsutil ls -b gs://stock4n-data
```

3. **Re-create bucket:**
```bash
gsutil mb -p your-project-id -l asia-southeast1 gs://stock4n-data-new
gsutil iam ch allUsers:objectViewer gs://stock4n-data-new
```

### **Issue 4: Scheduler Not Running**

**Symptoms:**
- Pipeline not running at 7AM
- No recent logs

**Solutions:**

1. **Check scheduler status:**
```bash
gcloud scheduler jobs describe stock4n-daily-job --location asia-southeast1
```

2. **Manual trigger to test:**
```bash
gcloud scheduler jobs run stock4n-daily-job --location asia-southeast1
```

3. **Check scheduler logs:**
```bash
gcloud logging read 'resource.type=cloud_scheduler_job' --limit 20
```

### **Issue 5: High Costs**

**Symptoms:**
- Monthly bill > $5

**Solutions:**

1. **Check actual usage:**
```bash
# Go to: https://console.cloud.google.com/billing
```

2. **Optimize min_instances:**
```bash
# Change to 0 (accept 10s cold start)
gcloud run services update stock4n-pipeline \
  --region asia-southeast1 \
  --min-instances 0
```

3. **Review logs for errors:**
- Errors cause retries → more costs
- Fix pipeline errors first

---

## 🔄 Updates & Rollbacks

### **Update Code**

```bash
# 1. Update local code
git pull origin main

# 2. Re-deploy
gcloud run deploy stock4n-pipeline \
  --source . \
  --region asia-southeast1

# Auto-increments revision
```

### **Rollback to Previous Version**

```bash
# List revisions
gcloud run revisions list --service stock4n-pipeline --region asia-southeast1

# Get previous revision name
PREVIOUS_REVISION=stock4n-pipeline-00002-abc

# Rollback
gcloud run services update-traffic stock4n-pipeline \
  --region asia-southeast1 \
  --to-revisions $PREVIOUS_REVISION=100
```

### **Delete Deployment**

```bash
# Use cleanup script
bash scripts/cleanup-cloud-run.sh

# Or manual cleanup
gcloud run services delete stock4n-pipeline --region asia-southeast1
gcloud scheduler jobs delete stock4n-daily-job --location asia-southeast1
gsutil -m rm -r gs://stock4n-data
```

---

## 📚 Next Steps

### **After Deployment**

1. **Update Vercel Frontend**
   - Change data source to Cloud Storage URL
   - Update `frontend/lib/data.ts`:
   ```typescript
   const PUBLIC_URL = 'https://storage.googleapis.com/stock4n-data/db.json'
   ```

2. **Monitor First Run**
   - Check logs during first scheduled run
   - Verify db.json uploaded to Cloud Storage
   - Test frontend access

3. **Setup Backup** (Optional)
   - Export db.json to GitHub daily
   - Keep local CSV backups
   - Setup Cloud Storage versioning

4. **Optimize Costs** (Optional)
   - Review usage after 1 week
   - Adjust min_instances if needed
   - Consider cheaper regions

---

## 🎯 Summary

**What You Get:**
- ✅ **99.95% uptime** (Google Cloud SLA)
- ✅ **No timeout risks** (60 min buffer)
- ✅ **No cold starts** (instant execution)
- ✅ **Professional monitoring** (logs + alerts)
- ✅ **Automatic retries** (3 attempts)
- ✅ **Easy debugging** (Cloud Logging)
- ✅ **Affordable** ($1.37/month)

**Total Setup Time:** ~15 minutes

**Maintenance:** None (fully automated)

**Recommended For:**
- ✅ Production deployments
- ✅ Teams/clients
- ✅ Need reliability
- ✅ Want peace of mind

---

## 🆘 Support

**Need Help?**
- 📧 GitHub Issues: [Stock4N/issues](https://github.com/your-username/Stock4N/issues)
- 💬 Discussions: [Stock4N/discussions](https://github.com/your-username/Stock4N/discussions)
- 📚 Docs: [docs/](../docs/)

**Google Cloud Support:**
- Community: https://stackoverflow.com/questions/tagged/google-cloud-run
- Official: https://cloud.google.com/run/docs

---

**Ready to deploy?** Run:
```bash
bash scripts/deploy-cloud-run.sh
```

🚀 **Good luck!**
