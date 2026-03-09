#!/bin/bash
# Phase 3.2 Preflight: Fatigue test — 30+ deck batch with dedicated-session restart automation
# Must be run from Terminal.app for PowerPoint automation permissions
set -euo pipefail

cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
source .venv/bin/activate
[ -f tests/validation/.env ] && source tests/validation/.env

LOGDIR="tests/validation"
CORPUS="tests/validation/corpus"

DECK_COUNT=$(ls -1 "$CORPUS"/*.pptx 2>/dev/null | wc -l | tr -d ' ')

echo "============================================"
echo "Phase 3.2 Preflight: Fatigue Test (30+ decks)"
echo "Started: $(date)"
echo "Corpus: $CORPUS"
echo "Decks: $DECK_COUNT (full 50-deck corpus)"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+SET (${#ANTHROPIC_API_KEY} chars)}"
echo "Dedicated session: enabled (restart every 15)"
echo "============================================"

START=$(date +%s)
folio -v batch "$CORPUS" \
    --pattern "*.pptx" \
    --passes 1 \
    --dedicated-session \
    2>&1 | tee "$LOGDIR/rerun_fatigue_30.log"
EXIT=$?
END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "============================================"
echo "Phase 3.2 Fatigue test complete"
echo "Exit code: $EXIT"
echo "Duration: ${ELAPSED}s"
echo "Finished: $(date)"
echo "============================================"
echo "EXIT_CODE=$EXIT ELAPSED=${ELAPSED}s" >> "$LOGDIR/rerun_fatigue_30.log"
