#!/bin/bash

# ══════════════════════════════════════════════════════════════
# Stock4N - Cloud Run Cleanup Script
# ══════════════════════════════════════════════════════════════
# Run: bash scripts/cleanup-cloud-run.sh
# ══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"
SERVICE_NAME="stock4n-pipeline"
BUCKET_NAME="stock4n-data"

echo "══════════════════════════════════════════════════════════════"
log_warning "⚠️  Cloud Run Cleanup Script"
echo "══════════════════════════════════════════════════════════════"
echo ""
log_warning "This will DELETE:"
echo "  • Cloud Run service: $SERVICE_NAME"
echo "  • Cloud Scheduler job: stock4n-daily-job"
echo "  • Cloud Storage bucket: gs://$BUCKET_NAME"
echo "  • All data in the bucket"
echo ""
log_error "THIS CANNOT BE UNDONE!"
echo ""

read -p "Are you sure? Type 'DELETE' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
log_warning "Starting cleanup..."

# Delete Cloud Run service
echo ""
echo "Deleting Cloud Run service..."
gcloud run services delete $SERVICE_NAME --region $REGION --quiet || true

# Delete Cloud Scheduler job
echo ""
echo "Deleting Cloud Scheduler job..."
gcloud scheduler jobs delete stock4n-daily-job --location $REGION --quiet || true

# Delete Cloud Storage bucket
echo ""
echo "Deleting Cloud Storage bucket..."
gsutil -m rm -r gs://$BUCKET_NAME || true

# Delete alert policies
echo ""
echo "Deleting monitoring policies..."
for POLICY in $(gcloud alpha monitoring policies list --filter="displayName:Stock4N" --format="value(name)"); do
    gcloud alpha monitoring policies delete $POLICY --quiet || true
done

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✓ Cleanup completed"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "Note: The Google Cloud project '$PROJECT_ID' still exists."
echo "To delete the project completely:"
echo "  gcloud projects delete $PROJECT_ID"
echo ""
