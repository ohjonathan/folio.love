---
deliverable_id: folio-config-defaults-v1-2-0
phase: B.1
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# B.1 Codex Alignment Review Round 2

Loaded: `pre_a_triage`, `folio-config-defaults-v1-2-0_phase_a_spec`, `folio-config-defaults-v1-2-0.yaml`.

This review is limited to the Phase A spec, the strict-P3 pre-A triage source, and the slice manifest named in the prompt. I did not rely on prior failed closeout artifacts or implementation-history evidence.

## Verdict
request changes

## Scope Alignment

The first two round-1 blockers are fixed in the Phase A spec. The spec explicitly applies the metadata resolution order to `folio ingest` fields `client`, `engagement`, `target`, `type`, `date`, and `participants`, matching issue #63's full ingest surface in `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`. It also explicitly applies defaults and derivation to `folio convert` for `client`, `engagement`, and `target`, including source-root client/engagement derivation before config defaults.

The manifest also fixes the allowed-path blocker: `frameworks/manifests/folio-config-defaults-v1-2-0.yaml` includes `folio/converter.py` in `scope.allowed_paths`, includes `tests/test_config_defaults.py`, and includes the focused test gate for `tests/test_config_defaults.py tests/test_cli_ingest.py`.

## Remaining Blocker

The manifest still does not contain enough contract anchors to prevent a narrow date/type-only implementation. Both `scope.cardinality_assertions` and `gate_prerequisites` / `G-cardinality-1` use this broad command:

```bash
test -f folio/defaults.py && rg -n "defaults|derive|resolve_convert_metadata|resolve_ingest_metadata" folio/defaults.py folio/cli.py folio/converter.py tests/test_config_defaults.py
```

That anchor can pass if the implementation only adds generic defaults/derive plumbing or only handles `date` and `type`. It does not require the full ingest field list (`client`, `engagement`, `target`, `type`, `date`, `participants`) to appear in test contracts, and it does not require converter-specific assertions for `client`, `engagement`, and `target` derivation/default behavior. The presence of `tests/test_config_defaults.py` in allowed paths and smoke checks is useful, but the manifest does not currently prove that those tests cover the convert surface or the complete issue #63 metadata surface.

Concrete requested fix: strengthen `frameworks/manifests/folio-config-defaults-v1-2-0.yaml` so the cardinality assertion and `G-cardinality-1` anchor the complete ingest metadata fields and converter metadata fields in the tests, not only generic resolver names. A field-specific `rg` check against `tests/test_config_defaults.py` for `resolve_ingest_metadata`, `resolve_convert_metadata`, `client`, `engagement`, `target`, `type`, `date`, and `participants`, plus converter-oriented test names or assertions, would close this blocker.

## Stale Evidence

The stale-evidence blocker is otherwise addressed. The pre-A triage states prior `folio_*_v1_*` artifacts and the preserved dirty attempt are implementation history only, and the Phase A spec repeats that old artifacts from the prior failed closeout must not count as evidence. The manifest roots lifecycle artifacts under `docs/validation/strict_p3_rerun_2026_05_12/` and uses strict-P3 lifecycle receipt gates.
