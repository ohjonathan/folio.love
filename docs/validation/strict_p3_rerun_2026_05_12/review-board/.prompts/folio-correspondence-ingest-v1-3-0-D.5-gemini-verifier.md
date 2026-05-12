You are Gemini in a strict-P3 D.5 verifier dispatch. The wrapper can only accept your STDOUT as the artifact. Do not write files. Do not say you saved a file. Your first three characters in stdout must be exactly `---`.

Verify deliverable folio-correspondence-ingest-v1-3-0. Slice summary: native correspondence ingest and Message-ID versioning.

Read these files:
- docs/validation/strict_p3_rerun_2026_05_12/folio-correspondence-ingest-v1-3-0_D.3_canonical_verdict.md
- docs/validation/strict_p3_rerun_2026_05_12/folio-correspondence-ingest-v1-3-0_d4_fix_summary.md
- frameworks/manifests/folio-correspondence-ingest-v1-3-0.yaml
- folio/cli.py
- folio/correspondence.py
- folio/ingest.py
- folio/tracking/registry.py
- tests/test_correspondence_ingest.py
- tests/test_cli_correspondence.py

Focused validation command already run by the orchestrator:
- ./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q

Output exactly this artifact structure. It must be at least 900 characters total:
---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.5
role: verifier
family: gemini
status: completed
evidence_labels_used:
  - static-inspection
---
# Phase D.5 Verification - folio-correspondence-ingest-v1-3-0 - gemini

## Verdict
approve — if the D.3/D.4 record and implementation are ready for D.6; otherwise request changes.

## Verification
State whether D.3/D.4 closed the D.2 review findings and whether the focused tests are adequate based on static reading. Do not claim command execution. Avoid naming stronger evidence labels in the body.
