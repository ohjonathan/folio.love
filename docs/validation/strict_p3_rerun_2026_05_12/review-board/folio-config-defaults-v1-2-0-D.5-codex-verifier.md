---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.5
role: verifier
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# D.5 Codex Verifier: folio-config-defaults-v1-2-0

## Verdict

approve

## Scope

Verified the D.3 canonical approval and D.4 fix summary for the strict-P3 Phase D.5 slice covering defaults and `defaults.derive` metadata resolution for ingest, convert, and the `.eml` route. I did not run Ontos and did not run a broad test suite.

## Direct-Run Evidence

Command:

```bash
./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py tests/test_cli_correspondence.py -q
```

Result: exit 0, `21 passed in 0.12s`.

## Static Verification Notes

The provider/defaults shadowing fix is present in `folio/config.py`: `FolioConfig.load()` parses `defaults = _parse_defaults(...)` before provider runtime settings, merges provider settings separately, and returns `defaults=defaults` alongside `providers=providers`. The focused test `test_config_loads_defaults_block_when_providers_are_configured` covers that regression.

Metadata resolution is centralized in `folio/defaults.py`. `resolve_ingest_metadata()` resolves client and engagement from CLI input, configured derive rules, then defaults; it also resolves subtype, date, participants, and target before reporting missing required ingest metadata. `resolve_convert_metadata()` resolves client and engagement from CLI input, derive/source-root values, then defaults, and applies those values to target template resolution.

The `.eml` route is covered end to end. `folio/cli.py` forwards `--date` and `--participants` from `folio ingest` into `ingest_email()`. `folio/correspondence.py` applies an explicit event date before resolver invocation and uses explicit participants before falling back to parsed email headers. `tests/test_cli_correspondence.py` asserts the resulting markdown frontmatter preserves the CLI date and participants.

`folio/converter.py` calls `resolve_convert_metadata()` before document/deck routing, so convert receives the same defaults/derive behavior as the resolver tests exercise.

## Release Risk

No remaining release-blocking issue was found for this slice. The implementation matches the D.3/D.4 claims and the focused validation command passes.
