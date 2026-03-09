#!/bin/bash
# Phase 4.2: Full 50-deck automated PPTX two-pass run
# Must be run from Terminal.app for PowerPoint automation permissions
set -euo pipefail

cd /Users/Jonathan_Oh/dev/folio.love
source .venv/bin/activate
[ -f tests/validation/.env ] && source tests/validation/.env

LOGDIR="tests/validation"
CORPUS="tests/validation/corpus"

DECK_COUNT=$(ls -1 "$CORPUS"/*.pptx 2>/dev/null | wc -l | tr -d ' ')

echo "============================================"
echo "Phase 4.2: Full Tier 1 Two-Pass Run"
echo "Started: $(date)"
echo "Corpus: $CORPUS"
echo "Decks: $DECK_COUNT"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+SET (${#ANTHROPIC_API_KEY} chars)}"
echo "Dedicated session: enabled (restart every 15)"
echo "Passes: 2"
echo "============================================"

START=$(date +%s)
folio -v batch "$CORPUS" \
    --pattern "*.pptx" \
    --passes 2 \
    --dedicated-session \
    2>&1 | tee "$LOGDIR/rerun_phase42_two_pass.log"
EXIT=$?
END=$(date +%s)
ELAPSED=$((END - START))

echo ""
echo "============================================"
echo "Phase 4.2 complete"
echo "Exit code: $EXIT"
echo "Duration: ${ELAPSED}s"
echo "Finished: $(date)"
echo "============================================"
echo "EXIT_CODE=$EXIT ELAPSED=${ELAPSED}s" >> "$LOGDIR/rerun_phase42_two_pass.log"
