#!/bin/bash
# =============================================================
# Synapse-D Brain Digital Twin — Local Demo Script
# =============================================================
#
# Prerequisites:
#   - Docker Desktop running
#   - Node.js 18+
#   - Python 3.10+ with synapse-d installed (pip install -e .)
#
# Usage:
#   ./scripts/demo.sh           # Full demo (Docker backend + frontend)
#   ./scripts/demo.sh --local   # Local backend (no Docker)
#   ./scripts/demo.sh --stop    # Stop all services
#
# =============================================================

set -e
cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[Synapse-D]${NC} $1"; }
warn() { echo -e "${YELLOW}[Synapse-D]${NC} $1"; }
err() { echo -e "${RED}[Synapse-D]${NC} $1"; }

# =============================================================
# Stop mode
# =============================================================
if [ "$1" = "--stop" ]; then
    log "Stopping all services..."
    cd docker && docker compose down 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "uvicorn synapse_d" 2>/dev/null || true
    log "All services stopped."
    exit 0
fi

# =============================================================
# Banner
# =============================================================
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ${NC}Synapse-D Brain Digital Twin Platform${BLUE}       ║${NC}"
echo -e "${BLUE}║       ${NC}Local Demo — Structural MRI Analysis${BLUE}        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================
# 1. Start Backend
# =============================================================
if [ "$1" = "--local" ]; then
    log "Starting backend (local mode)..."
    uvicorn synapse_d.api.main:app --host 127.0.0.1 --port 8000 &
    BACKEND_PID=$!
    sleep 2
else
    log "Starting backend (Docker Compose)..."
    cd docker
    docker compose up -d redis api worker 2>&1 | grep -v "^$"
    cd "$PROJECT_DIR"
    sleep 3
fi

# Check backend health
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log "Backend: ${GREEN}OK${NC} (http://localhost:8000)"
else
    err "Backend failed to start!"
    exit 1
fi

# =============================================================
# 2. Start Frontend
# =============================================================
log "Starting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install --silent 2>&1 | tail -1
fi
npx next dev -p 3000 > /dev/null 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_DIR"
sleep 4

if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    log "Frontend: ${GREEN}OK${NC} (http://localhost:3000)"
else
    warn "Frontend may still be starting..."
fi

# =============================================================
# 3. API Demo
# =============================================================
echo ""
log "=== API Demo ==="
echo ""

# Check sample data
T1_SAMPLE="data/sample/sub-01/anat/sub-01_T1w.nii.gz"
FLAIR_SAMPLE="data/sample/sub-01/anat/sub-01_FLAIR.nii.gz"

if [ ! -f "$T1_SAMPLE" ]; then
    err "Sample T1 not found: $T1_SAMPLE"
    exit 1
fi

# Step 1: Upload T1
log "Step 1: Uploading T1w MRI..."
UPLOAD=$(curl -s -X POST http://localhost:8000/api/v1/upload \
    -F "file=@${T1_SAMPLE}" \
    -F "modality=T1w")
SUBJECT_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['subject_id'])")
SIZE=$(echo "$UPLOAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['size_mb'])")
log "  Subject: ${BLUE}${SUBJECT_ID}${NC} (${SIZE} MB)"

# Step 2: Upload FLAIR (if available)
if [ -f "$FLAIR_SAMPLE" ]; then
    log "Step 2: Uploading FLAIR MRI..."
    curl -s -X POST http://localhost:8000/api/v1/upload \
        -F "file=@${FLAIR_SAMPLE}" \
        -F "modality=FLAIR" \
        -F "subject_id=${SUBJECT_ID}" > /dev/null
    log "  FLAIR uploaded to ${BLUE}${SUBJECT_ID}${NC}"
else
    warn "Step 2: No FLAIR sample — WMH analysis will be skipped"
fi

# Step 3: Run Analysis
log "Step 3: Running analysis (sync mode)..."
RESULT=$(curl -s -X POST \
    "http://localhost:8000/api/v1/analyze/${SUBJECT_ID}?chronological_age=65&sex=M&sync=true")

# Parse results
SUCCESS=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('result',{}).get('preprocessing',{}).get('success','?'))")
TIER=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('result',{}).get('preprocessing',{}).get('resolution',{}).get('tier','?'))")
BRAIN_AGE=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); ba=r.get('result',{}).get('brain_age',{}); print(ba.get('predicted_age','N/A'))" 2>/dev/null)
BRAIN_VOL=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); m=r.get('result',{}).get('preprocessing',{}).get('morphometrics',{}); print(m.get('total_brain_volume_cm3','N/A'))")
AD_RISK=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); ad=r.get('result',{}).get('ad_risk',{}); print(f\"{ad.get('risk_score','N/A')} ({ad.get('risk_level','N/A')})\")" 2>/dev/null)

echo ""
log "=== Results ==="
echo -e "  Pipeline:     ${GREEN}${SUCCESS}${NC}"
echo -e "  Tier:         ${BLUE}${TIER}${NC}"
echo -e "  Brain Age:    ${BLUE}${BRAIN_AGE} years${NC}"
echo -e "  Brain Volume: ${BLUE}${BRAIN_VOL} cm³${NC}"
echo -e "  AD Risk:      ${BLUE}${AD_RISK}${NC}"

# Check WMH
WMH=$(echo "$RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); w=r.get('result',{}).get('wmh',{}); print(f\"{w.get('wmh_volume_ml','N/A')} mL, Fazekas {w.get('fazekas_grade','N/A')}\")" 2>/dev/null)
if [ "$WMH" != "N/A mL, Fazekas N/A" ]; then
    echo -e "  WMH:          ${BLUE}${WMH}${NC}"
fi

# Step 4: Longitudinal
log "Step 4: Longitudinal data..."
LONG=$(curl -s "http://localhost:8000/api/v1/longitudinal/${SUBJECT_ID}")
TP_COUNT=$(echo "$LONG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('timepoint_count',0))")
echo -e "  Timepoints:   ${BLUE}${TP_COUNT}${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Demo complete! Open http://localhost:3000       ║${NC}"
echo -e "${GREEN}║  Stop: ./scripts/demo.sh --stop                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
