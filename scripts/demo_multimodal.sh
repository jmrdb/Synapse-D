#!/bin/bash
# =============================================================
# Synapse-D Multi-Modal Demo Script
# =============================================================
#
# Demonstrates the full Brain Digital Twin analysis:
#   T1w  → Brain Age, Morphometry, AD Risk
#   FLAIR → WMH Segmentation, Fazekas Grading
#   SWI  → Cerebral Microbleed Detection, MARS Classification
#
# Prerequisites:
#   - Docker containers running (cd docker && docker compose up -d)
#   - Sample data in data/sample/sub-01/anat/
#
# Usage:
#   ./scripts/demo_multimodal.sh
#
# =============================================================

set -e
cd "$(dirname "$0")/.."

API="http://localhost:8000/api/v1"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[Synapse-D]${NC} $1"; }
info() { echo -e "${BLUE}  →${NC} $1"; }

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ${NC}Synapse-D Brain Digital Twin — Multi-Modal Demo${BLUE}       ║${NC}"
echo -e "${BLUE}║  ${NC}T1w + FLAIR + SWI 통합 뇌 분석 시연${BLUE}                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check API
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}Error: API server not running. Start with:${NC}"
    echo "  cd docker && docker compose up -d"
    exit 1
fi

# ============= Step 1: Upload All Modalities =============
log "Step 1: 다중 모달리티 업로드"

# T1w
SID=$(curl -s -X POST "${API}/upload?modality=T1w" \
    -F "file=@data/sample/sub-01/anat/sub-01_T1w_real.nii.gz" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['subject_id'])")
info "T1w 업로드 → Subject: ${BLUE}${SID}${NC}"

# FLAIR
curl -s -X POST "${API}/upload?modality=FLAIR&subject_id=${SID}" \
    -F "file=@data/sample/sub-01/anat/sub-01_FLAIR.nii.gz" > /dev/null
info "FLAIR 업로드 → ${SID}"

# SWI (sub-02 data — different person, for CMB demo)
SID_SWI=$(curl -s -X POST "${API}/upload?modality=SWI" \
    -F "file=@data/sample/sub-02/anat/sub-02_SWI.nii.gz" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['subject_id'])")
info "SWI 업로드 → Subject: ${BLUE}${SID_SWI}${NC} (별도 피험자)"

# ============= Step 2: Analyze T1+FLAIR =============
echo ""
log "Step 2: T1w + FLAIR 통합 분석 (HD-BET + Brain Age + WMH)"
info "비동기 제출 중..."

JOB=$(curl -s -X POST "${API}/analyze/${SID}?chronological_age=60&sex=M" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
info "Job: ${JOB}"

# Poll
info "HD-BET 처리 중 (CPU ~8분 소요)..."
for i in $(seq 1 40); do
    sleep 30
    STATUS=$(curl -s "${API}/results/${JOB}" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        break
    fi
    printf "."
done
echo ""

# Results
if [ "$STATUS" = "completed" ]; then
    curl -s "${API}/results/${JOB}" | python3 -c "
import sys, json
r = json.load(sys.stdin)['result']
p = r.get('preprocessing',{})
m = p.get('morphometrics',{})
ba = r.get('brain_age',{})
wmh = r.get('wmh',{})
ad = r.get('ad_risk',{})
norm = r.get('normative',{})

print()
print('  ┌──────────────────────────────────────┐')
print('  │  T1w + FLAIR 분석 결과               │')
print('  ├──────────────────────────────────────┤')
vol = m.get('total_brain_volume_cm3','?')
print(f'  │  뇌 부피:      {vol} cm³')
print(f'  │  부피 신뢰:     {m.get(\"volume_plausible\",\"?\")}')
if 'predicted_age' in ba:
    print(f'  │  Brain Age:    {ba[\"predicted_age\"]}세 (Gap: {ba.get(\"brain_age_gap\")})')
if wmh.get('success'):
    print(f'  │  WMH:          {wmh[\"wmh_volume_ml\"]}mL, Fazekas {wmh[\"fazekas_grade\"]}')
    print(f'  │  WMH 병변:     {wmh[\"wmh_count\"]}개')
for s in norm.get('scores',[]):
    print(f'  │  z({s[\"metric\"]}): {s[\"z_score\"]} ({s[\"interpretation\"]})')
if 'risk_score' in ad and ad.get('risk_level') != 'insufficient_data':
    print(f'  │  AD Risk:      {ad[\"risk_score\"]} ({ad[\"risk_level\"]})')
print('  └──────────────────────────────────────┘')
"
else
    echo -e "${RED}  분석 실패: ${STATUS}${NC}"
fi

# ============= Step 3: Analyze SWI =============
echo ""
log "Step 3: SWI 미세출혈(CMB) 분석"
info "비동기 제출 중..."

JOB_SWI=$(curl -s -X POST "${API}/analyze/${SID_SWI}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

info "HD-BET + CMB 처리 중..."
for i in $(seq 1 40); do
    sleep 30
    STATUS=$(curl -s "${API}/results/${JOB_SWI}" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        break
    fi
    printf "."
done
echo ""

if [ "$STATUS" = "completed" ]; then
    curl -s "${API}/results/${JOB_SWI}" | python3 -c "
import sys, json
r = json.load(sys.stdin)['result']
mb = r.get('microbleeds',{})

print()
print('  ┌──────────────────────────────────────┐')
print('  │  SWI 미세출혈 분석 결과              │')
print('  ├──────────────────────────────────────┤')
if mb.get('success'):
    print(f'  │  CMB 수:       {mb[\"cmb_count\"]}개')
    print(f'  │  MARS 분류:    {mb[\"mars_category\"]}')
    rc = mb.get('regional_counts',{})
    print(f'  │  분포:         L:{rc.get(\"lobar\",0)} D:{rc.get(\"deep\",0)} I:{rc.get(\"infratentorial\",0)}')
    print(f'  │  해석:         {mb[\"clinical_significance\"][:50]}...')
else:
    print(f'  │  CMB 분석 실패: {mb.get(\"errors\",[])}')
print('  └──────────────────────────────────────┘')
"
fi

# ============= Step 4: Longitudinal =============
echo ""
log "Step 4: 종단적 추적 데이터"
curl -s "${API}/longitudinal/${SID}" | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f'  Timepoints: {r[\"timepoint_count\"]}')
if r.get('summary',{}).get('message'):
    print(f'  {r[\"summary\"][\"message\"]}')
"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Demo 완료!                                           ║${NC}"
echo -e "${GREEN}║  대시보드: http://localhost:3000                       ║${NC}"
echo -e "${GREEN}║  API 문서: http://localhost:8000/docs                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
