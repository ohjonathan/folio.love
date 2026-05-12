You are the codex external verifier for llm-dev strict-P3 Phase D.5, deliverable folio-correspondence-ingest-v1-3-0.

Do not run Ontos. Do not run a broad test suite. Verify D.3/D.4 against the implementation and focused tests. Slice summary: native correspondence ingest and Message-ID versioning.

Use these files:
- docs/validation/strict_p3_rerun_2026_05_12/folio-correspondence-ingest-v1-3-0_D.3_canonical_verdict.md
- docs/validation/strict_p3_rerun_2026_05_12/folio-correspondence-ingest-v1-3-0_d4_fix_summary.md
- frameworks/manifests/folio-correspondence-ingest-v1-3-0.yaml
- folio/cli.py
- folio/correspondence.py
- folio/ingest.py
- folio/tracking/registry.py
- tests/test_correspondence_ingest.py
- tests/test_cli_correspondence.py

Focused validation command reported by orchestrator:
- ./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q

Artifact target: docs/validation/strict_p3_rerun_2026_05_12/review-board/folio-correspondence-ingest-v1-3-0-D.5-codex-verifier.md

Artifact contract:
- Write the markdown artifact to the artifact target above.
- Do not edit any repository file except the artifact target.
- The artifact must be at least 700 characters.
- It must begin with this exact YAML frontmatter:
---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.5
role: verifier
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
- Include a top-level heading and a section named exactly "## Verdict" containing approve, request changes, reject, or concur.
- If verification finds a remaining release issue, use "request changes" and cite file paths. Otherwise use "approve".
