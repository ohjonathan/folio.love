---
deliverable_id: folio-config-defaults-v1-2-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Peer Review — folio-config-defaults-v1-2-0 Phase B.1 Round 2

Reviewer: claude-sonnet  
Date: 2026-05-12  
Round: 2 (re-review after codex-alignment blockers from round 1)  
Source artifacts read:
- `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md`
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml`
- `docs/validation/strict_p3_rerun_2026_05_12/review-board/folio-config-defaults-v1-2-0-B.1-codex-alignment.md` (round-1 blocker source)

## Verdict

approve

## Round-1 Blocker Resolution

The codex-alignment round-1 review (`folio-config-defaults-v1-2-0-B.1-codex-alignment.md`) raised two blockers. Each is assessed below against the current spec and manifest.

### Blocker 1: Metadata fields not enumerated; partial implementation could satisfy the spec

**Raised at**: `folio-config-defaults-v1-2-0_phase_a_spec.md:13` — the original AC bullet named only "defaults/defaults.derive support" and "date/type optionality," without listing all six fields from issue #63's metadata table.

**Current spec at line 17**: "Apply the resolution order to `folio ingest` metadata fields `client`, `engagement`, `target`, `type`, `date`, and `participants`."

**Resolution**: Fixed. All six fields from the issue #63 metadata table (`pre_a_triage.md:407–414`) are now explicitly enumerated in the acceptance criteria. A Phase C implementation can no longer satisfy the spec by handling only `date` and `type` while leaving `client`, `engagement`, `target`, and `participants` unresolved.

### Blocker 2: `folio convert` participation unclear; no manifest guard for converter defaults coverage

**Raised at**: `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:4` — the original manifest summary described "ingest metadata" only; `scope.allowed_paths` did not include `folio/converter.py`; smoke checks ran only ingest tests.

**Current spec at line 18–19**: "Apply the same defaults/derivation surface to `folio convert` for `client`, `engagement`, and `target`, including source-root client/engagement derivation before config defaults."

**Current manifest evidence**:
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:28`: `folio/converter.py` is in `scope.allowed_paths`.
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:50`: cardinality assertion now reads `rg -n "defaults|derive|resolve_convert_metadata|resolve_ingest_metadata" folio/defaults.py folio/cli.py folio/converter.py tests/test_config_defaults.py`, requiring `resolve_convert_metadata` to be present in `folio/converter.py`.
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:155` (G-cardinality-1): the gate prerequisite runs the same assertion as an exit-0 check before D.6 can close.

**Resolution**: Fixed. `folio/converter.py` is in scope, `resolve_convert_metadata` is an explicit cardinality anchor, and the manifest gate blocks D.6 if that symbol is absent.

## Remaining Checklist

### Issue #63 metadata surface for `folio ingest`
Spec line 17 names `client`, `engagement`, `target`, `type`, `date`, and `participants` as the full ingest resolution surface. Matches the issue's metadata table verbatim. Confirmed covered.

### `folio convert` coverage — `client`, `engagement`, `target`
Spec line 18 names these three fields for convert. The issue's scope (`pre_a_triage.md:42`: "defaults/derive in folio.yaml; metadata resolution order CLI flag -> derivation -> defaults -> error") applies to both commands. Source-root derivation is called out as a convert-specific prior step before config defaults, which correctly reflects issue #63's intent that target should be derivable from client/engagement slugs. Confirmed covered.

### Converter participation in scope and tests
`folio/converter.py` is in `scope.allowed_paths`. The cardinality assertion (`G-cardinality-1`) enforces `resolve_convert_metadata` exists at that path. The test surface (`tests/test_config_defaults.py`) is designed to cover the shared resolution module rather than a per-command test; the cardinality gate provides the executable hook that would catch a convert implementation gap. This is the same verification approach as the ingest side. Confirmed adequate.

### Resolution order: CLI flag → derivation → defaults → error
Spec line 15: "Resolve metadata in order: CLI flag, derivation, defaults, then error." This matches the issue's four-level hierarchy from `pre_a_triage.md:479–484` exactly. The "error" step is scoped correctly — it fires when a field is required and unresolvable, which is the behavior the issue requires. Confirmed covered.

## Stale Evidence

No change from round 1. The spec explicitly excludes prior `folio_*_v1_*` artifacts as non-goals. The manifest's `pre_a.artifact_path` roots to the regenerated triage document and the lifecycle receipt inventory is fresh. No stale evidence reuse detected.

## Summary

All four round-1 blocker items are resolved by concrete, verifiable changes to the spec acceptance criteria and manifest scope/cardinality guards. The spec and manifest are adequate to drive Phase C implementation without ambiguity about which fields are in scope, whether `folio convert` participates, and what the resolution order must be.
