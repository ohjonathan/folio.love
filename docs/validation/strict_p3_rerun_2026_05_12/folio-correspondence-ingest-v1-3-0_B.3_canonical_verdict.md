---
id: folio-correspondence-ingest-v1-3-0-b3-canonical-verdict
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: B.3
role: meta-consolidator
family: codex
status: completed
---

# Phase B.3 Canonical Verdict: folio-correspondence-ingest-v1-3-0

## Verdict
approve

## Review Inputs
- Claude Sonnet peer round 1: approved.
- Codex alignment round 1: approved.
- Gemini adversarial round 1: approved.

## Canonical Decision
The correspondence-ingest slice may proceed to Phase C. Reviewers found the spec and manifest adequate for issues #61 and #64: add `folio ingest-email`, support `.eml` through `folio ingest --type email_thread`, emit correspondence metadata and `message_ids`, parse message headers/body/attachments, and dedupe/version by Message-ID overlap with `--as-new-entry` override.

## Phase C Scope
Implement native RFC 5322 ingestion, registry/frontmatter correspondence metadata, and deterministic continuation matching.
