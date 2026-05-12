---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Peer Review: folio-correspondence-ingest-v1-3-0

## Verdict

approve

## Summary

The Phase C implementation satisfies all acceptance criteria from Phase A and the scope confirmed in the B.3 canonical verdict. All 6 focused tests pass under direct run.

**Test run evidence:**
```
./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q
......
6 passed in 0.11s
```

## Criterion-by-Criterion Assessment

### AC-1: `folio ingest-email <path.eml>` and `folio ingest <path.eml> --type email_thread`

Both surfaces are implemented.

- `folio/cli.py:561` — dedicated `ingest-email` command with `--client`, `--engagement`, `--title`, `--target`, `--note`, and `--as-new-entry` flags.
- `folio/cli.py:507` — `ingest` command routes `.eml` source or `--type email_thread` to `ingest_email()` from `folio/correspondence.py`.
- `folio/ingest.py:113-114` — `ingest_source()` raises `IngestError` with a clear message when a `.eml` is passed directly, enforcing the separation.
- CLI tests `tests/test_cli_correspondence.py:23` and `:40` cover both surfaces and assert `exit_code == 0`.

### AC-2: Headers, messages, participants, attachments, correspondence metadata, and `message_ids`

The `parse_eml()` function in `folio/correspondence.py:216` extracts:
- Subject, sender, recipients (To/CC), event date from RFC 5322 headers.
- Body text with multipart handling, HTML-to-text fallback, and whitespace cleanup.
- `message_ids` from `Message-ID`, `In-Reply-To`, and `References` headers (`folio/correspondence.py:303-308`), deduplicated and order-preserved.
- Attachments with filename, content-type, size, and SHA-256 (`folio/correspondence.py:311-326`).

Frontmatter generation (`folio/correspondence.py:459-514`) emits: `type`, `subtype`, `source_type`, `sender`, `recipients_to`, `recipients_cc`, `participants`, `external_thread`, `message_ids`, `attachment_count`, `attachments`, `thread_message_count`, `date`, `version`, `source`, `source_hash`, `client`, `engagement`, `authority`, `curation_level`, `review_status`.

Test `test_ingest_email_writes_correspondence_note_and_registry` at `tests/test_correspondence_ingest.py:61` validates all key frontmatter fields and registry entry presence including `message_ids`.

### AC-3: Message-ID overlap for continuation/versioning with `--as-new-entry` override

- `folio/correspondence.py:363-373` — `_find_message_id_overlap()` scans `registry.json` for correspondence entries and returns a match when the incoming message IDs intersect any existing entry's `message_ids`.
- On a match without `--as-new-entry`, `ingest_email` versions the existing entry (`folio/correspondence.py:117`, `folio/correspondence.py:152-155`), merging message ID sets.
- On identical source hash + match (exact re-ingest), it skips and returns `skipped=True` (`folio/correspondence.py:118-126`).
- With `as_new_entry=True`, the match is bypassed and a new correspondence ID is generated.

Tests:
- `test_message_id_overlap_versions_existing_thread` (`:90`) asserts same `correspondence_id`, `version == 2`, and merged `message_ids` list.
- `test_as_new_entry_ignores_message_id_overlap` (`:113`) asserts different `correspondence_id` and `version == 1`.

### Registry integration

`folio/tracking/registry.py:63` — `RegistryEntry` carries an optional `message_ids: Optional[list[str]]` field, serialized correctly in `to_dict()` (`:82-83`). The `entry_from_dict` path at lines `:181` and `:228` round-trips `message_ids` from JSON. The correspondence ingest path calls `registry.upsert_entry()` with a fully populated `RegistryEntry` including `type="correspondence"`, `subtype="email_thread"`, and `message_ids`.

### Cardinality assertion

Manifest gate `G-cardinality-1` passes:
```
test -f folio/correspondence.py && rg -n "ingest-email|message_ids|email_thread|as-new-entry" folio tests
```
Returns 40+ hits across `folio/correspondence.py`, `folio/cli.py`, `folio/ingest.py`, `folio/tracking/registry.py`, and both test files.

## No Blockers Found

The implementation is complete, coherent, and test-covered. No gaps between Phase A acceptance criteria, B.3 canonical verdict, and Phase C deliverables were identified.
