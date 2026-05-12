---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.5
role: verifier
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.5 Verification — folio-correspondence-ingest-v1-3-0

## Verdict

approve

## Verification Summary

The D.3 canonical verdict (phase D.3, codex meta-consolidator) recorded an `approve` with no unresolved blockers, citing native `.eml` parsing, correspondence frontmatter/registry metadata, attachment metadata, and Message-ID continuation behavior as implemented and tested. The D.4 fix summary (claude-opus fix-author) confirms all five feature areas were implemented, with a subsequent config-defaults fixup preserving CLI `--date` and `--participants` precedence in the `.eml` route. No open blocker markers remain in the D.3 verdict document.

## Implementation Verification

**`folio/correspondence.py`** — present and complete. `parse_eml()` extracts RFC 5322 headers (From, To, Cc, Date, Subject), body text (plain/HTML with fallback), `message_ids` (Message-ID + In-Reply-To + References headers), and attachment metadata (filename, content_type, size_bytes, sha256). `ingest_email()` calls `resolve_ingest_metadata()` for CLI-precedence resolution, performs Message-ID overlap detection via `_find_message_id_overlap()`, merges existing and new message IDs on continuation, and writes frontmatter + markdown atomically before calling `registry.upsert_entry()`. The `as_new_entry` flag correctly bypasses overlap matching.

**`folio/cli.py`** — `ingest-email` command (line 563) and the `--type email_thread` branch inside `ingest` (line 507) both route to `ingest_email()`. The `--as-new-entry` flag is wired on both paths (lines 481, 570). Output prints `Review: clean` on success, consistent with test assertions.

**`folio/ingest.py`** — `.eml` sources are explicitly redirected to `ingest_email()` at the ingest entry point (line 114), preventing accidental double-processing.

**`folio/tracking/registry.py`** — `RegistryEntry` carries an optional `message_ids` field (line 63) that serialises into the registry JSON and is read back during overlap detection. `entry_from_dict()` (line 181) and `upsert_entry()` both handle `message_ids` correctly.

## Test Coverage Assessment

The focused command `./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q` was executed directly and returned **7 passed in 0.11s** with zero failures or warnings.

Test coverage spans all contract-critical paths:

- `test_parse_eml_extracts_headers_message_ids_body_and_attachments` — round-trip parsing of subject, sender, recipients, message IDs, attachments, and body text.
- `test_ingest_email_writes_correspondence_note_and_registry` — full ingest producing frontmatter fields (`type`, `subtype`, `source_type`, `sender`, `message_ids`, `attachment_count`, `external_thread`), markdown structure (`## Messages`), and registry entry (`type`, `message_ids`).
- `test_message_id_overlap_versions_existing_thread` — second ingest sharing an In-Reply-To ID increments to version 2 and merges both message IDs in frontmatter.
- `test_as_new_entry_ignores_message_id_overlap` — `as_new_entry=True` produces a distinct `correspondence_id` at version 1 despite overlapping references.
- `test_ingest_email_command` — CLI `ingest-email` exits 0 and prints `Review: clean`.
- `test_ingest_routes_eml_to_correspondence` — CLI `ingest --type email_thread` exits 0 and prints `Review: clean`.
- `test_ingest_eml_route_preserves_cli_date_and_participants_precedence` — CLI-supplied `--date` and `--participants` override parsed email headers in written frontmatter.

## Gate Prerequisites Cross-Check

- **G-test-1**: focused tests pass — confirmed by direct run.
- **G-cardinality-1**: `folio/correspondence.py` exists; `ingest-email`, `message_ids`, `email_thread`, `as-new-entry` all present in code and tests.
- **G-blocker-1**: D.3 verdict contains `approve` with no `UNRESOLVED`, `BLOCKER`, or `REQUEST CHANGES` markers.
- **G-scope-1/G-branch-1**: out of verifier scope but evidenced by working directory state.

No remaining release issues found. Implementation is consistent with the spec, D.3/D.4 record, and all focused tests pass.
