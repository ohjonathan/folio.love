---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.2
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# D.2 Codex Alignment Review

## Verdict
request changes

## Evidence

Reviewed Phase C against the Phase A spec and B.3 canonical verdict for the `folio.yaml` defaults and derivation slice. I also direct-ran the focused validation command:

`./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py -q`

Result: `16 passed in 0.10s`.

## Blockers

1. `client` and `engagement` do not follow the required CLI flag, derivation, defaults, then error order across the declared metadata surface. Phase A says the order applies to ingest fields `client`, `engagement`, `target`, `type`, `date`, and `participants`; B.3 repeats that the broader ingest/convert surface is in scope. In `folio/defaults.py:57` and `folio/defaults.py:58`, ingest resolves `client` and `engagement` directly from CLI-or-defaults, with no derivation step. In `folio/defaults.py:116` through `folio/defaults.py:118`, convert supports source-root inference before defaults, but does not apply any `defaults.derive` surface for `client` or `engagement`. If client/engagement derivation was intentionally excluded, the Phase A/B.3 contract needs to say that; as written, the implementation under-covers named fields.

2. The `.eml` path under `folio ingest` bypasses CLI precedence for `date` and `participants`. `folio/cli.py:466` and `folio/cli.py:469` parse those CLI options, and `folio/cli.py:504` normalizes participants, but `folio/cli.py:507` through `folio/cli.py:519` routes `.eml` sources to `ingest_email()` without passing either value. That means email header derivation wins over explicit CLI metadata for `.eml` ingest, violating the required precedence for `date` and `participants` on the `folio ingest` surface.

## Test Coverage Gaps

The focused tests pass, but they do not catch the blockers above. `tests/test_config_defaults.py:52` covers CLI/default client and engagement plus derive for type/date, but not derive for client or engagement. `tests/test_cli_ingest.py` verifies transcript option forwarding, but not the `.eml` route that is advertised in ingest help and handled by the same command. The manifest cardinality assertion only searches for field names in `tests/test_config_defaults.py`; it does not prove field-specific precedence behavior for each resolver.

## Required Changes

Implement or explicitly de-scope derivation for `client` and `engagement` in the defaults resolver contract, then add focused tests proving the intended precedence. Also preserve CLI `--date` and `--participants` precedence for `.eml` ingest or split that command behavior out of the Phase A/B.3 contract. Re-run the focused pytest command after the changes.
