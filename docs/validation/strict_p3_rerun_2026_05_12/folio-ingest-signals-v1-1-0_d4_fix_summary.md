---
id: folio-ingest-signals-v1-1-0-d4-fix-summary
deliverable_id: folio-ingest-signals-v1-1-0
phase: D.4
role: fix-author
family: claude-opus
status: completed
---

# Phase D.4 Fix Summary: folio-ingest-signals-v1-1-0

Implemented the B.1/D.2 scope refinements: action items are included in validation summaries; speaker analytics now merge confirmed person aliases from the entity registry; and transcript-like inputs receive `speaker_analytics_unavailable` when analytics are expected but unavailable. The ingest path deliberately does not mark ordinary clean/free-form notes as flagged solely because they lack speaker timing. Added focused tests for alias merging and no-speaker degradation, plus full-suite compatibility checks.
