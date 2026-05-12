---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Peer Review (Round 2): folio-config-defaults-v1-2-0

## Verdict

approve

## Round-1 Blocker Re-Assessment

The round-1 blocker was a variable-shadowing defect in `FolioConfig.load()` where the loop-local variable `defaults` inside the providers parsing block clobbered the `DefaultsConfig` object parsed earlier, causing any config that included a `providers:` section to pass a `ProviderRuntimeSettings` instance rather than a `DefaultsConfig` to the `FolioConfig` constructor.

### Fix Verification

**`folio/config.py` line 529 (direct-run):**

The offending assignment has been renamed from:
```python
defaults = _DEFAULT_PROVIDER_SETTINGS[pname]
```
to:
```python
provider_defaults = _DEFAULT_PROVIDER_SETTINGS[pname]
```

All three downstream uses of the loop-local variable on lines 531–538 have been updated to `provider_defaults.*` accordingly. The `defaults` name at line 554 (`return cls(..., defaults=defaults, ...)`) now correctly refers to the `DefaultsConfig` object assigned at line 521 and is never overwritten by the providers loop. The fix is minimal, precise, and does not alter any other load logic.

**New focused test (`tests/test_config_defaults.py`, line 52–70, direct-run):**

`test_config_loads_defaults_block_when_providers_are_configured` loads a `folio.yaml` that contains both a `defaults:` block (`client: Scotiabank`) and a `providers:` block (`anthropic.rate_limit_rpm: 12`), then asserts:
- `config.defaults.client == "Scotiabank"` — confirms `DefaultsConfig` survives the providers loop
- `config.providers["anthropic"].rate_limit_rpm == 12` — confirms the provider override is applied correctly

This test closes the exact coverage gap identified in round 1 (the prior `test_config_loads_defaults_block` used only a `defaults:` block with no `providers:` section, so the shadowing loop never executed in any test).

### Validation Command (direct-run)

```
./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py tests/test_cli_correspondence.py -q
21 passed in 0.12s
```

All 21 tests pass (up from 16 in round 1; 5 new tests were added, including the focused defaults+providers regression test).

## Conformance Assessment

| Criterion | Status |
|---|---|
| `folio/defaults.py` exists with `resolve_ingest_metadata` and `resolve_convert_metadata` | Pass |
| Resolution order: CLI flag → derive → defaults → error | Pass |
| `--type` and `--date` optional at Click parsing level | Pass |
| Resolution error raised when type/date unresolvable | Pass |
| `folio convert` resolves client/engagement/target via source-root then defaults | Pass |
| Field-specific test anchors for all six ingest fields | Pass |
| `FolioConfig.load()` no longer clobbers `DefaultsConfig` when `providers:` configured | **Pass** — `provider_defaults` variable renaming at line 529 |
| Focused test covers defaults + providers in a single `FolioConfig.load()` call | **Pass** — `test_config_loads_defaults_block_when_providers_are_configured` |
| Focused validation command passes | **Pass** — 21/21 |

## Summary

Both required changes from round 1 are implemented correctly. The variable-shadowing defect is eliminated, and the new test directly exercises the previously uncovered code path. No other conformance issues were identified. The slice is ready to proceed to D.3.
