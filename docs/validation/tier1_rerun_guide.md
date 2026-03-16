# Tier 1 Validation Rerun Guide

Post-merge validation rerun to prove the `open -a` fix resolves the 17-file -9074 failure cohort.

## Prerequisites

- Managed Mac with TCC automation permission for Terminal.app → PowerPoint
- folio installed in `.venv` with latest `codex/pptx-renderer-reliability-fix` merged
- The original 50-deck corpus from `tier1_validation_report.md`

## Targeted Rerun: 17-File Failure Cohort

Run from **Terminal.app** (not Cursor):

```bash
cd /path/to/folio.love
source .venv/bin/activate

# Run only the 17 files that consistently failed with -9074
folio batch ./decks \
  --pattern "*.pptx" \
  --client test --engagement tier1-rerun \
  --dedicated-session \
  --passes 1
```

### Success Criteria
- **FM1 (file-specific -9074):** ≥15 of the 17 previously-failing files now succeed
- **FM4 (sandbox dialog):** Zero "Grant File Access" dialogs appear (pptx_output_dir fix)
- **Instrumentation:** Batch summary shows `renderer=powerpoint` (not `auto`) for all PPTX outcomes

## Fatigue Rerun: 30+ Deck Batch

```bash
folio batch ./decks \
  --pattern "*.pptx" \
  --client test --engagement fatigue-rerun \
  --dedicated-session \
  --passes 1
```

### Success Criteria
- **FM2 (fatigue):** Preemptive restart fires at conversion 15 with log message
- **No dead-on-arrival phase:** All post-restart conversions succeed
- **No manual intervention:** Entire batch completes without user input

## Cache Validation (PDF-First Only)

```bash
# First run
folio batch ./pdf-exports --pattern "*.pdf" \
  --client test --engagement cache-test --passes 1

# Second run (same files)
folio batch ./pdf-exports --pattern "*.pdf" \
  --client test --engagement cache-test --passes 1
```

### Success Criteria
- Second run: 100% cache hit (0 API calls)
- Automated PPTX cache persistence deferred to Approach J (v0.5.1)

## Full 50-Deck Rerun (if targeted passes)

Only after the targeted and fatigue reruns show material improvement:

```bash
folio batch ./decks \
  --client test --engagement full-rerun \
  --dedicated-session \
  --passes 1
```

### Gate Decision
- **≥45/50 succeed** → Tier 1 substantially closed
- **35-44 succeed** → Remaining failures need root-cause analysis
- **<35 succeed** → `open -a` fix insufficient, further investigation needed
