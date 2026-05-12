---
deliverable_id: folio-config-defaults-v1-2-0
phase: D.2
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Phase D.2 Peer Review: folio-config-defaults-v1-2-0

## Verdict

request changes

## Evidence

**Test run (direct-run):**

```
./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py -q
16 passed in 0.10s
```

All 16 tests in the focused slice pass.

**Cardinality gate (direct-run):**

All cardinality anchors verified present: `resolve_ingest_metadata`, `resolve_convert_metadata`, and field terms `client`, `engagement`, `target`, `type`, `date`, `participants` all appear in `tests/test_config_defaults.py`.

## Findings

### BLOCKER — Variable shadowing destroys `DefaultsConfig` when `providers:` is configured

**File:** `folio/config.py`, line 529

Inside `FolioConfig.load()`, the variable `defaults` is assigned the parsed `DefaultsConfig` at line 521:

```python
defaults = _parse_defaults(raw.get("defaults") or {})
```

Immediately below, inside the providers loop (lines 527–539), the same variable name is reused as a convenience reference to the provider's runtime settings:

```python
for pname, pdata in providers_raw.items():
    if isinstance(pdata, dict) and pname in _DEFAULT_PROVIDER_SETTINGS:
        defaults = _DEFAULT_PROVIDER_SETTINGS[pname]   # line 529 — clobbers DefaultsConfig
        providers[pname] = ProviderRuntimeSettings(
            rate_limit_rpm=pdata.get("rate_limit_rpm", defaults.rate_limit_rpm),
            ...
        )
```

At line 554, the clobbered variable is passed directly to `cls(...)`:

```python
return cls(
    ...
    defaults=defaults,   # line 554 — receives ProviderRuntimeSettings, not DefaultsConfig
    ...
)
```

If any provider is configured in `folio.yaml`, `defaults` is overwritten with the last `ProviderRuntimeSettings` object from the loop. The `FolioConfig` instance then holds a `ProviderRuntimeSettings` in its `defaults` attribute. Any subsequent call to `resolve_ingest_metadata` or `resolve_convert_metadata` will fail with `AttributeError` (e.g., `ProviderRuntimeSettings` has no attribute `client`) — directly breaking the slice's primary contract.

The fix is to rename the loop-local variable, for example:

```python
prov_defaults = _DEFAULT_PROVIDER_SETTINGS[pname]
providers[pname] = ProviderRuntimeSettings(
    rate_limit_rpm=pdata.get("rate_limit_rpm", prov_defaults.rate_limit_rpm),
    ...
)
```

**Why this is not caught by the current test suite:** `test_config_loads_defaults_block` (the only test that calls `FolioConfig.load()`) uses a config file that has only a `defaults:` block and no `providers:` block. The shadowing loop therefore never executes in any test, leaving the defect latent.

## Conformance Assessment

| Criterion | Status |
|---|---|
| `folio/defaults.py` exists with `resolve_ingest_metadata` and `resolve_convert_metadata` | Pass |
| Resolution order: CLI flag → derive → defaults → error | Pass |
| `--type` and `--date` optional at Click parsing level | Pass (`required=False` at `cli.py:463,466`) |
| Resolution error raised when type/date unresolvable | Pass (`DefaultResolutionError` in `defaults.py:91-94`) |
| `folio convert` resolves client/engagement/target via source-root then defaults | Pass |
| Field-specific test anchors for all six ingest fields | Pass |
| `config.py` correctly passes `DefaultsConfig` to `FolioConfig` when `providers:` also configured | **FAIL** — line 529 clobbers `defaults` |

## Required Changes

1. **`folio/config.py:529`** — rename the loop-local variable from `defaults` to `prov_defaults` (or equivalent) and update its three uses on lines 531–538 accordingly. This restores the `DefaultsConfig` object for the `return cls(..., defaults=defaults, ...)` call at line 554.
2. **`tests/test_config_defaults.py`** — add a test that loads a `folio.yaml` containing both a `defaults:` block and a `providers:` block, and asserts `config.defaults.client` is the expected string (not an `AttributeError`). This closes the coverage gap that allowed the bug to survive all current tests.
