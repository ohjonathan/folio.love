---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.5
role: verifier
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.5 Verification — folio-config-defaults-v1-2-0

## Verdict

approve

## Focused Test Run

Command executed:

```
./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py tests/test_cli_correspondence.py -q
```

Result: **21 passed in 0.11s** — exit 0. All gate-prerequisite G-test-1 criteria satisfied.

## D.3 Finding Closure

The D.3 canonical verdict (approved) identified three D.2 defects as resolved. This verification confirms each closure against the implementation:

### 1. Provider/defaults shadowing (`folio/config.py`)

`FolioConfig.load()` parses `defaults` at line 521 (`defaults = _parse_defaults(raw.get("defaults") or {})`), before the `providers` block is processed (lines 525–545). Both are passed independently to `cls()` at line 549. The `DefaultsConfig` object is never overwritten by provider parsing.

Test anchor: `test_config_loads_defaults_block_when_providers_are_configured` in `tests/test_config_defaults.py` asserts `config.defaults.client == "Scotiabank"` and `config.providers["anthropic"].rate_limit_rpm == 12` coexist correctly.

### 2. Client/engagement derivation in `resolve_ingest_metadata` and `resolve_convert_metadata` (`folio/defaults.py`)

Both functions call `_infer_convert_source_root()` first to extract `(inferred_client, inferred_engagement)` from the configured source root path structure, then fall through via `_derive_text_field()` → `config.defaults.client` / `config.defaults.engagement`. The resolution chain is: CLI → derive rules → source root inference → static default.

Test anchors:
- `test_ingest_resolution_derives_client_and_engagement_from_source_root`: source at `source_root/ClientA/ProjectX/...` yields `resolved.client == "ClientA"` and `resolved.engagement == "ProjectX"`.
- `test_convert_resolution_uses_source_root_then_defaults_for_target_template`: source at `source_root/Scotiabank/AI Platform/brief.docx` yields `resolved.client == "Scotiabank"` and `resolved.engagement == "AI Platform"`.

### 3. `.eml` route CLI precedence (`folio/cli.py`)

The `ingest` command at lines 507–528 detects `.eml` suffix and calls `ingest_email()` with `event_date=event_date.date() if event_date else None` and `participants=participant_list` (derived from `_split_csv_values(participants)`). CLI-supplied values are forwarded directly; `ingest_email()` in `folio/correspondence.py` then applies them with `replace(thread, event_date=event_date or thread.event_date)` and `effective_participants = participants if participants is not None else thread.participants`, so CLI values take precedence over email headers.

Test anchor: `test_ingest_eml_route_preserves_cli_date_and_participants_precedence` in `tests/test_cli_correspondence.py` (line 66) verifies the written frontmatter has `date == "2026-04-18"` and `participants == ["Explicit One", "Explicit Two"]` despite the `.eml` headers carrying a different date and participants. This test name also satisfies the G-cardinality-1 contract anchor from the manifest.

## Cardinality Assertions

All manifest cardinality assertions verified:
- `folio/defaults.py` exists.
- `resolve_ingest_metadata` present in `tests/test_config_defaults.py`.
- `resolve_convert_metadata` present in `tests/test_config_defaults.py`.
- `ingest_eml_route_preserves_cli_date_and_participants_precedence` present in `tests/test_cli_correspondence.py`.
- Terms `client`, `engagement`, `target`, `type`, `date`, `participants` all present in `tests/test_config_defaults.py`.

## Summary

D.3/D.4 record accurately describes the fixes. Implementation matches. Focused test suite is adequate in scope and all 21 tests pass. No remaining release issues identified.
