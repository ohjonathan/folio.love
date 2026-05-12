---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.5
role: verifier
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# D.5 Codex External Verification

## Verdict

approve

## Scope

Verified D.3 and D.4 for `folio-correspondence-ingest-v1-3-0` against the named implementation and focused tests only. I did not run Ontos and did not run a broad suite.

## Evidence

Direct focused validation command:

```bash
./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q
```

Result: exit code 0, `7 passed in 0.11s`.

Static inspection confirmed the D.3/D.4 claims are represented in implementation:

- `folio/correspondence.py` provides native `.eml` parsing through `parse_eml`, including RFC 5322 headers, message ID extraction from `Message-ID`, `In-Reply-To`, and `References`, body extraction from plain text or HTML, attachment filename/type/size/hash metadata, and correspondence markdown/frontmatter generation.
- `folio/correspondence.py` implements Message-ID overlap continuation in `ingest_email`, merges prior and new IDs, increments version history on matched correspondence entries, and honors `as_new_entry` by bypassing overlap matching.
- `folio/cli.py` exposes `ingest-email` and routes `folio ingest --type email_thread` or `.eml` sources into `ingest_email`, while preserving explicit CLI date and participant precedence for the email route.
- `folio/ingest.py` includes `.eml` in supported extension messaging but prevents transcript ingest from processing `.eml` directly, keeping the correspondence route authoritative.
- `folio/tracking/registry.py` carries `message_ids` through `RegistryEntry`, serialization, registry rebuild, and entry loading.

The focused tests cover header/body/attachment parsing, correspondence frontmatter and registry metadata, Message-ID continuation to version 2, `--as-new-entry`, the dedicated CLI command, generic ingest email routing, and CLI date/participants precedence. I found no remaining release issue in this slice.
