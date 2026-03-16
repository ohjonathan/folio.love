#!/bin/bash
# Phase 3.1 Preflight: Targeted rerun of the 17 files that consistently failed with -9074 in March 2026
# Must be run from Terminal.app for PowerPoint automation permissions
set -euo pipefail

cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
source .venv/bin/activate
[ -f tests/validation/.env ] && source tests/validation/.env

LOGDIR="tests/validation"
COHORT_DIR="tests/validation/cohort_9074"

mkdir -p "$COHORT_DIR"

# Symlink the 17 previously-failing files into a dedicated cohort directory
FAILURES=(
    "Building Blocks.pptx"
    "Data_Layers_2-251023.pptx"
    "Demo_Workstream_Introduction_Sessions_v1.pptx"
    "Eclipse Architecture Review - Workplan.pptx"
    "EcliptOS_Workstream_PM_PO_Reponsibilities_v1.pptx"
    "IconGallery.pptx"
    "JO Pie Chart of Your Life Team Learning Exercise slide 1.pptx"
    "LM Modernization - workplan_v6.pptx"
    "Lines_Textblocks_Trackersymbols.pptx"
    "PO Entry path to production.pptx"
    "SOW PS.pptx"
    "Sanitized qualitative dashboard  -  Read-Only.pptx"
    "SlideLibrary.pptx"
    "Traj team.pptx"
    "Trajectory sketch for knowledge graph.pptx"
    "USS AI Program Meeting Cadences.pptx"
    "USS AI Workstreams - Value Execution Alignment v2.pptx"
)

# Clear and repopulate cohort directory
rm -f "$COHORT_DIR"/*.pptx 2>/dev/null || true
for f in "${FAILURES[@]}"; do
    SRC="tests/validation/corpus/$f"
    if [ -e "$SRC" ]; then
        ln -sf "$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")" "$COHORT_DIR/$f"
    else
        echo "WARNING: Missing file: $f"
    fi
done

DECK_COUNT=$(ls -1 "$COHORT_DIR"/*.pptx 2>/dev/null | wc -l | tr -d ' ')

echo "============================================"
echo "Phase 3.1 Preflight: -9074 Cohort Rerun"
echo "Started: $(date)"
echo "Cohort: $COHORT_DIR"
echo "Decks: $DECK_COUNT"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+SET (${#ANTHROPIC_API_KEY} chars)}"
echo "Code: open -a two-step + dedicated-session"
echo "============================================"

START=$(date +%s)
folio -v batch "$COHORT_DIR" \
    --pattern "*.pptx" \
    --passes 1 \
    --dedicated-session \
    2>&1 | tee "$LOGDIR/rerun_preflight_9074.log"
EXIT=$?
END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "============================================"
echo "Phase 3.1 Preflight complete"
echo "Exit code: $EXIT"
echo "Duration: ${ELAPSED}s"
echo "Finished: $(date)"
echo "============================================"
echo "EXIT_CODE=$EXIT ELAPSED=${ELAPSED}s" >> "$LOGDIR/rerun_preflight_9074.log"
