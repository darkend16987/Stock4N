#!/bin/bash

# ══════════════════════════════════════════════════════════════
# Stock4N - Cloud Run Test Script
# ══════════════════════════════════════════════════════════════
# Run: bash scripts/test-cloud-run.sh
# ══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get service URL
PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"
SERVICE_NAME="stock4n-pipeline"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    log_error "Cloud Run service not found!"
    log_info "Run deployment first: bash scripts/deploy-cloud-run.sh"
    exit 1
fi

log_info "Testing Stock4N Cloud Run Deployment"
log_info "Service URL: $SERVICE_URL"
echo ""

# Test 1: Health Check
log_info "Test 1: Health Check"
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
if echo $HEALTH_RESPONSE | grep -q "healthy"; then
    log_success "✓ Health check passed"
else
    log_error "✗ Health check failed"
    echo "Response: $HEALTH_RESPONSE"
fi
echo ""

# Test 2: Manual Trigger
log_info "Test 2: Manual Pipeline Trigger"
log_info "This will take ~8 minutes..."
echo ""

read -p "Start pipeline now? (y/n): " START_PIPELINE

if [ "$START_PIPELINE" = "y" ]; then
    log_info "Triggering pipeline..."

    # Start pipeline in background
    TRIGGER_RESPONSE=$(curl -s -X POST "${SERVICE_URL}/trigger")

    log_info "Pipeline started!"
    log_info "Follow logs in real-time:"
    echo ""
    echo "  gcloud logging tail 'resource.type=cloud_run_revision' --format=json --project=$PROJECT_ID"
    echo ""

    # Wait for completion
    log_info "Checking pipeline progress (this takes ~8 minutes)..."

    START_TIME=$(date +%s)

    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))

        # Check logs for completion
        RECENT_LOGS=$(gcloud logging read "resource.type=cloud_run_revision AND timestamp>=\"$(date -u -d '-1 minute' +%Y-%m-%dT%H:%M:%SZ)\"" --limit 5 --format json 2>/dev/null)

        if echo "$RECENT_LOGS" | grep -q "Pipeline completed"; then
            log_success "✓ Pipeline completed!"
            break
        fi

        if [ $ELAPSED -gt 600 ]; then
            log_error "✗ Pipeline timeout (>10 minutes)"
            log_info "Check logs manually:"
            echo "  gcloud logging read 'resource.type=cloud_run_revision' --limit 50"
            break
        fi

        echo -ne "\r  Running... ${ELAPSED}s elapsed"
        sleep 10
    done

    echo ""
fi

# Test 3: Check Storage
echo ""
log_info "Test 3: Check Cloud Storage"

BUCKET_NAME=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(spec.template.spec.containers[0].env[?name=="BUCKET_NAME"].value)' 2>/dev/null)

if [ ! -z "$BUCKET_NAME" ]; then
    log_info "Checking bucket: gs://$BUCKET_NAME"

    if gsutil ls "gs://$BUCKET_NAME/db.json" &>/dev/null; then
        log_success "✓ db.json found in Cloud Storage"

        # Get file info
        FILE_SIZE=$(gsutil du -sh "gs://$BUCKET_NAME/db.json" | awk '{print $1}')
        FILE_TIME=$(gsutil ls -l "gs://$BUCKET_NAME/db.json" | grep db.json | awk '{print $2, $3}')

        log_info "  Size: $FILE_SIZE"
        log_info "  Last updated: $FILE_TIME"

        # Get public URL
        PUBLIC_URL="https://storage.googleapis.com/$BUCKET_NAME/db.json"
        log_info "  Public URL: $PUBLIC_URL"

        # Test public access
        if curl -s -I "$PUBLIC_URL" | grep -q "200 OK"; then
            log_success "✓ Public access working"
        else
            log_error "✗ Public access failed"
        fi
    else
        log_error "✗ db.json not found"
        log_info "Pipeline might not have completed yet"
    fi
else
    log_error "✗ Bucket name not configured"
fi

# Test 4: Check Scheduler
echo ""
log_info "Test 4: Check Cloud Scheduler"

SCHEDULER_STATUS=$(gcloud scheduler jobs describe stock4n-daily-job --location=$REGION --format='value(state)' 2>/dev/null)

if [ ! -z "$SCHEDULER_STATUS" ]; then
    if [ "$SCHEDULER_STATUS" = "ENABLED" ]; then
        log_success "✓ Scheduler is enabled"

        # Get next run time
        NEXT_RUN=$(gcloud scheduler jobs describe stock4n-daily-job --location=$REGION --format='value(schedule)')
        log_info "  Schedule: $NEXT_RUN (Vietnam time)"

        # Get last run
        LAST_RUN=$(gcloud scheduler jobs describe stock4n-daily-job --location=$REGION --format='value(status.lastAttemptTime)' 2>/dev/null)
        if [ ! -z "$LAST_RUN" ]; then
            log_info "  Last run: $LAST_RUN"
        fi
    else
        log_error "✗ Scheduler is disabled"
    fi
else
    log_error "✗ Scheduler not configured"
fi

# Test 5: Check Monitoring
echo ""
log_info "Test 5: Check Monitoring"

# Check if monitoring is enabled
if gcloud services list --enabled --filter="name:monitoring.googleapis.com" --format="value(name)" | grep -q "monitoring"; then
    log_success "✓ Cloud Monitoring enabled"

    # Check for alert policies
    ALERT_COUNT=$(gcloud alpha monitoring policies list --format="value(name)" | wc -l)
    log_info "  Alert policies: $ALERT_COUNT"
else
    log_error "✗ Cloud Monitoring not enabled"
fi

# Summary
echo ""
echo "══════════════════════════════════════════════════════════════"
log_info "📊 Test Summary"
echo "══════════════════════════════════════════════════════════════"
echo ""
log_info "Service Status:"
echo "  URL:           $SERVICE_URL"
echo "  Health:        $(curl -s ${SERVICE_URL}/health | grep -o 'healthy' || echo 'unknown')"
echo "  Storage:       gs://$BUCKET_NAME/db.json"
echo "  Public URL:    https://storage.googleapis.com/$BUCKET_NAME/db.json"
echo ""
log_info "Useful Commands:"
echo "  View logs:     gcloud logging tail 'resource.type=cloud_run_revision'"
echo "  Manual run:    curl -X POST ${SERVICE_URL}/trigger"
echo "  Check status:  gcloud run services describe $SERVICE_NAME --region $REGION"
echo "  Delete:        bash scripts/cleanup-cloud-run.sh"
echo ""
echo "══════════════════════════════════════════════════════════════"
