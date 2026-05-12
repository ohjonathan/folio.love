---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# D.2 Codex Alignment Round 2 Review

## Verdict

approve

## Scope

I reviewed the round-2 blocker closure for `folio-config-defaults-v1-2-0` against the Phase A acceptance criteria and the strict-P3 manifest. The review focused on the requested files: `folio/defaults.py`, `folio/cli.py`, `folio/correspondence.py`, `folio/config.py`, `tests/test_config_defaults.py`, `tests/test_cli_correspondence.py`, the Phase A spec, and the manifest.

## Evidence

The client and engagement resolution path now has an explicit derivation step before defaults. In `resolve_ingest_metadata`, `client` and `engagement` are resolved as CLI value, `_derive_text_field(...)`, then `config.defaults.*`. In `resolve_convert_metadata`, the same ordering exists, with source-root inference also applied before config defaults. `_derive_text_field` handles `source_root.client`, `source_root.engagement`, markdown frontmatter, filename regex, and explicit derive defaults through `defaults.derive`.

The `.eml` route through `folio ingest` now preserves CLI precedence. The branch for `.eml` and `--type email_thread` forwards `client`, `engagement`, `event_date=event_date.date() if event_date else None`, `participants=participant_list`, `title`, `target`, `note`, and `as_new_entry` into `ingest_email`. `ingest_email` then replaces the parsed email date with the provided event date when present, keeps provided participants when present, and passes those effective values into `resolve_ingest_metadata`.

The focused tests cover both blocker fixes. `tests/test_config_defaults.py` includes `test_ingest_resolution_derives_client_and_engagement_from_source_root`, plus convert source-root/default precedence coverage. `tests/test_cli_correspondence.py` includes `test_ingest_eml_route_preserves_cli_date_and_participants_precedence`, which invokes `folio ingest` on an `.eml` file with explicit `--date` and `--participants` and verifies the resulting frontmatter uses those CLI values.

## Direct Run

Command:

```bash
./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py tests/test_cli_correspondence.py -q
```

Result:

```text
21 passed in 0.12s
```

## Round-1 Blocker Closure

The round-1 blockers requested for this review are fixed:

- client/engagement derivation now occurs before defaults.
- `.eml` ingest receives CLI date and participants before correspondence resolution.
- tests cover client/engagement derivation and `.eml` date/participants precedence.
- the focused validation command passes.

No remaining alignment blocker found in this round.
