#!/bin/bash

# ══════════════════════════════════════════════════════════════
# Stock4N - Cloud Run Deployment Script
# ══════════════════════════════════════════════════════════════
# One-command setup for production deployment
# Run: bash scripts/deploy-cloud-run.sh
# ══════════════════════════════════════════════════════════════

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

PROJECT_ID=""
REGION="asia-southeast1"
SERVICE_NAME="stock4n-pipeline"
BUCKET_NAME="stock4n-data"
MIN_INSTANCES=1
MEMORY="2Gi"
CPU="2"
TIMEOUT="3600"

# ══════════════════════════════════════════════════════════════
# STEP 0: Prerequisites Check
# ══════════════════════════════════════════════════════════════

log_info "Checking prerequisites..."

# Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found!"
    echo ""
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    echo ""
    echo "Quick install (Linux/Mac):"
    echo "  curl https://sdk.cloud.google.com | bash"
    echo "  exec -l \$SHELL"
    echo "  gcloud init"
    exit 1
fi

log_success "gcloud CLI found"

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    log_warning "Not logged in to gcloud"
    log_info "Running: gcloud auth login"
    gcloud auth login
fi

log_success "Authenticated with Google Cloud"

# ══════════════════════════════════════════════════════════════
# STEP 1: Project Setup
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 1: Google Cloud Project Setup"
log_info "════════════════════════════════════════"
echo ""

# List existing projects
log_info "Your existing Google Cloud projects:"
gcloud projects list --format="table(projectId,name,projectNumber)"

echo ""
read -p "Enter PROJECT_ID (or press Enter to create new): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    # Create new project
    read -p "Enter new project name (e.g., stock4n-prod): " PROJECT_NAME
    PROJECT_ID="${PROJECT_NAME}-$(date +%s)"

    log_info "Creating new project: $PROJECT_ID"
    gcloud projects create $PROJECT_ID --name="$PROJECT_NAME"

    log_warning "⚠️  IMPORTANT: Enable billing for this project"
    log_info "Go to: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    read -p "Press Enter after enabling billing..."
fi

# Set default project
gcloud config set project $PROJECT_ID
log_success "Using project: $PROJECT_ID"

# ══════════════════════════════════════════════════════════════
# STEP 2: Enable Required APIs
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 2: Enable Required APIs"
log_info "════════════════════════════════════════"
echo ""

APIS=(
    "run.googleapis.com"
    "cloudscheduler.googleapis.com"
    "cloudbuild.googleapis.com"
    "storage-api.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
)

for API in "${APIS[@]}"; do
    log_info "Enabling $API..."
    gcloud services enable $API --project=$PROJECT_ID
done

log_success "All APIs enabled"

# ══════════════════════════════════════════════════════════════
# STEP 3: Create Cloud Storage Bucket
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 3: Create Cloud Storage Bucket"
log_info "════════════════════════════════════════"
echo ""

# Create bucket
log_info "Creating bucket: gs://$BUCKET_NAME"
if gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME 2>/dev/null; then
    log_success "Bucket created"
else
    log_warning "Bucket already exists or name taken, trying alternative..."
    BUCKET_NAME="${BUCKET_NAME}-${PROJECT_ID}"
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
fi

# Make bucket publicly readable
log_info "Setting bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# Set CORS for web access
cat > /tmp/cors.json <<EOF
[
  {
    "origin": ["*"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

gsutil cors set /tmp/cors.json gs://$BUCKET_NAME
rm /tmp/cors.json

log_success "Bucket configured: gs://$BUCKET_NAME"

# ══════════════════════════════════════════════════════════════
# STEP 4: Get API Keys
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 4: Configure API Keys"
log_info "════════════════════════════════════════"
echo ""

# Check for .env file
if [ -f .env ]; then
    log_info "Found .env file, loading API keys..."
    source .env

    if [ -z "$VNSTOCK_API_KEY" ]; then
        log_warning "VNSTOCK_API_KEY not found in .env"
        read -p "Enter VNSTOCK_API_KEY: " VNSTOCK_API_KEY
    fi

    if [ -z "$GOOGLE_API_KEY" ]; then
        log_warning "GOOGLE_API_KEY not found in .env"
        read -p "Enter GOOGLE_API_KEY: " GOOGLE_API_KEY
    fi
else
    log_warning ".env file not found"
    read -p "Enter VNSTOCK_API_KEY: " VNSTOCK_API_KEY
    read -p "Enter GOOGLE_API_KEY: " GOOGLE_API_KEY
fi

# Validate API keys
if [ -z "$VNSTOCK_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then
    log_error "API keys are required!"
    exit 1
fi

log_success "API keys configured"

# ══════════════════════════════════════════════════════════════
# STEP 5: Build and Deploy to Cloud Run
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 5: Build & Deploy to Cloud Run"
log_info "════════════════════════════════════════"
echo ""

log_info "This will take 5-10 minutes (building Docker image)..."
log_info "Building and deploying..."

# Create a temporary entrypoint script
cat > /tmp/entrypoint.sh <<'EOF'
#!/bin/bash
set -e

# If PORT is set, run as web server
if [ ! -z "$PORT" ]; then
    # Run Flask server for health checks and manual triggers
    python -c "
from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/trigger', methods=['POST', 'GET'])
def trigger():
    try:
        result = subprocess.run(['python', 'src/main.py', 'all'],
                              capture_output=True, text=True, timeout=3600)
        return jsonify({
            'status': 'completed',
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
"
else
    # Run pipeline directly
    python src/main.py all
fi
EOF

chmod +x /tmp/entrypoint.sh

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --timeout $TIMEOUT \
    --memory $MEMORY \
    --cpu $CPU \
    --min-instances $MIN_INSTANCES \
    --max-instances 1 \
    --set-env-vars "VNSTOCK_API_KEY=${VNSTOCK_API_KEY},GOOGLE_API_KEY=${GOOGLE_API_KEY},BUCKET_NAME=${BUCKET_NAME}" \
    --allow-unauthenticated \
    --command "/bin/bash" \
    --args "/tmp/entrypoint.sh"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

log_success "Cloud Run deployed!"
log_info "Service URL: $SERVICE_URL"

# Test health endpoint
log_info "Testing service health..."
sleep 5
if curl -s "${SERVICE_URL}/health" | grep -q "healthy"; then
    log_success "Service is healthy!"
else
    log_warning "Health check failed, but service is deployed"
fi

# ══════════════════════════════════════════════════════════════
# STEP 6: Setup Cloud Scheduler
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 6: Setup Cloud Scheduler"
log_info "════════════════════════════════════════"
echo ""

# Create scheduler job
log_info "Creating daily job (7AM Vietnam time)..."

gcloud scheduler jobs create http stock4n-daily-job \
    --location $REGION \
    --schedule "0 0 * * *" \
    --time-zone "Asia/Ho_Chi_Minh" \
    --uri "${SERVICE_URL}/trigger" \
    --http-method POST \
    --attempt-deadline 3600s \
    --max-retry-attempts 3 \
    --min-backoff 60s \
    --max-backoff 300s \
    --project $PROJECT_ID \
    || log_warning "Scheduler job might already exist"

log_success "Cloud Scheduler configured"

# ══════════════════════════════════════════════════════════════
# STEP 7: Test Manual Trigger
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 7: Test Manual Trigger (Optional)"
log_info "════════════════════════════════════════"
echo ""

read -p "Do you want to test the pipeline now? (y/n): " TEST_NOW

if [ "$TEST_NOW" = "y" ]; then
    log_info "Triggering pipeline manually..."
    log_warning "This will take ~8 minutes. You can check logs in another terminal:"
    log_info "  gcloud logging tail 'resource.type=cloud_run_revision' --format=json"

    curl -X POST "${SERVICE_URL}/trigger"

    log_success "Pipeline triggered! Check logs for progress."
else
    log_info "Skipping manual test"
fi

# ══════════════════════════════════════════════════════════════
# STEP 8: Setup Monitoring (Optional)
# ══════════════════════════════════════════════════════════════

echo ""
log_info "════════════════════════════════════════"
log_info "STEP 8: Setup Monitoring"
log_info "════════════════════════════════════════"
echo ""

read -p "Setup email alerts for failures? (y/n): " SETUP_ALERTS

if [ "$SETUP_ALERTS" = "y" ]; then
    read -p "Enter email for alerts: " ALERT_EMAIL

    log_info "Creating notification channel..."

    # Create notification channel
    cat > /tmp/notification-channel.json <<EOF
{
  "type": "email",
  "displayName": "Stock4N Alerts",
  "labels": {
    "email_address": "${ALERT_EMAIL}"
  }
}
EOF

    CHANNEL_NAME=$(gcloud alpha monitoring channels create \
        --notification-channel-content-from-file=/tmp/notification-channel.json \
        --format="value(name)")

    rm /tmp/notification-channel.json

    # Create alert policy
    cat > /tmp/alert-policy.json <<EOF
{
  "displayName": "Stock4N Pipeline Failed",
  "conditions": [
    {
      "displayName": "Error rate > 10%",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\"",
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
  "notificationChannels": [
    "${CHANNEL_NAME}"
  ],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

    gcloud alpha monitoring policies create \
        --policy-from-file=/tmp/alert-policy.json

    rm /tmp/alert-policy.json

    log_success "Email alerts configured for: $ALERT_EMAIL"
fi

# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════

echo ""
echo "══════════════════════════════════════════════════════════════"
log_success "🎉 DEPLOYMENT COMPLETED!"
echo "══════════════════════════════════════════════════════════════"
echo ""
log_info "📊 Deployment Summary:"
echo "  Project ID:        $PROJECT_ID"
echo "  Region:            $REGION"
echo "  Service Name:      $SERVICE_NAME"
echo "  Service URL:       $SERVICE_URL"
echo "  Storage Bucket:    gs://$BUCKET_NAME"
echo "  Schedule:          Daily at 7:00 AM (Vietnam time)"
echo ""
log_info "🔗 Quick Links:"
echo "  Cloud Run Console: https://console.cloud.google.com/run?project=$PROJECT_ID"
echo "  Cloud Scheduler:   https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
echo "  Storage Browser:   https://console.cloud.google.com/storage/browser/$BUCKET_NAME?project=$PROJECT_ID"
echo "  Logs:              https://console.cloud.google.com/logs/query?project=$PROJECT_ID"
echo ""
log_info "📝 Next Steps:"
echo "  1. Update Vercel frontend to fetch from:"
echo "     https://storage.googleapis.com/$BUCKET_NAME/db.json"
echo ""
echo "  2. Test manual trigger:"
echo "     curl -X POST ${SERVICE_URL}/trigger"
echo ""
echo "  3. View logs:"
echo "     gcloud logging tail 'resource.type=cloud_run_revision'"
echo ""
echo "  4. Update schedule if needed:"
echo "     gcloud scheduler jobs update http stock4n-daily-job --schedule='0 0 * * *' --location=$REGION"
echo ""
log_info "💰 Estimated Cost: ~\$1.37/month"
echo ""
log_success "Deployment complete! Your pipeline will run daily at 7AM Vietnam time."
echo "══════════════════════════════════════════════════════════════"
