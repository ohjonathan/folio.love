---
deliverable_id: folio-correspondence-ingest-v1-3-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# Codex Alignment Review Round 2

## Verdict
approve

## Scope Reviewed

Reviewed the Phase C implementation only against the supplied Phase A spec, B.3 canonical verdict, manifest, implementation files, and focused test files for `folio-correspondence-ingest-v1-3-0`. I did not run Ontos or any broad test suite.

## Alignment Findings

The CLI surface aligns with Phase A: `folio ingest-email <path.eml>` is implemented at `folio/cli.py:561`, and `folio ingest <path.eml> --type email_thread` routes `.eml` inputs into the correspondence ingest path at `folio/cli.py:457` and `folio/cli.py:507`. The generic ingest command also exposes `--as-new-entry` for the email-thread path at `folio/cli.py:481`.

The correspondence parser and note generation cover the required metadata surface. `parse_eml` extracts subject, sender, recipients, date, body text, Message-ID chain, and attachments in `folio/correspondence.py:216`; message IDs are collected from `Message-ID`, `In-Reply-To`, and `References` at `folio/correspondence.py:303`, while attachment filename/content type/size/hash metadata is extracted at `folio/correspondence.py:311`. Generated frontmatter includes `type: correspondence`, `subtype: email_thread`, source fields, sender/recipients/participants, attachment metadata, `external_thread`, and `message_ids` at `folio/correspondence.py:459`.

Continuation/versioning is aligned with B.3. `ingest_email` loads registry state, uses Message-ID overlap unless `as_new_entry` is set, and merges prior and new message IDs into the new correspondence version at `folio/correspondence.py:114`. The overlap resolver scans existing correspondence registry rows at `folio/correspondence.py:363`. Registry schema support for `message_ids` is present in `folio/tracking/registry.py:32`, and the upsert path writes correspondence rows with `source_type: email`, `type: correspondence`, `subtype: email_thread`, and `message_ids` at `folio/correspondence.py:180`.

Focused tests exercise header/body/attachment parsing, frontmatter and registry output, Message-ID overlap versioning, `--as-new-entry`, and both CLI entry points in `tests/test_correspondence_ingest.py:47`, `tests/test_correspondence_ingest.py:61`, `tests/test_correspondence_ingest.py:90`, `tests/test_correspondence_ingest.py:113`, `tests/test_cli_correspondence.py:23`, and `tests/test_cli_correspondence.py:40`.

## Direct-Run Evidence

Command run:

```text
./.venv/bin/python -m pytest tests/test_correspondence_ingest.py tests/test_cli_correspondence.py -q
```

Result: exit code 0, `6 passed in 0.11s`.

## Blockers

No implementation blockers identified for the Phase A/B.3 contract. Residual coverage is intentionally narrow per redispatch instructions; I did not assess unrelated ingest, refresh, lifecycle, or broad registry behavior.
