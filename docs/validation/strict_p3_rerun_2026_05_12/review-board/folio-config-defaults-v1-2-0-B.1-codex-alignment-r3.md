---
deliverable_id: folio-config-defaults-v1-2-0
phase: B.1
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---

# Codex Alignment Review Round 3

## Verdict
approve

## Scope Reviewed

Reviewed only the requested Phase A and manifest slice inputs: `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`, `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md`, `frameworks/manifests/folio-config-defaults-v1-2-0.yaml`, and `tests/test_config_defaults.py`.

## Alignment Findings

The round-2 blocker is fixed. The manifest cardinality assertion and `G-cardinality-1` no longer stop at generic resolver-name anchors: both commands check for `resolve_ingest_metadata`, `resolve_convert_metadata`, and the field set `client`, `engagement`, `target`, `type`, `date`, and `participants` in `tests/test_config_defaults.py` (`frameworks/manifests/folio-config-defaults-v1-2-0.yaml:48` and `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:151`).

The tests provide concrete anchors for both resolver paths. `test_ingest_resolution_precedence_cli_then_derive_then_defaults` asserts ingest resolution for CLI/default/derived `client`, `engagement`, `subtype`/type, `event_date`/date, `participants`, and templated `target` (`tests/test_config_defaults.py:52`). `test_convert_resolution_uses_source_root_then_defaults_for_target_template` asserts convert resolution for source-root and CLI `client`, `engagement`, and `target` (`tests/test_config_defaults.py:107`). The config-load and CLI-missing-type/date tests add supporting coverage for the defaults block and Click parsing behavior.

The Phase A spec still carries the issue #63 ingest and convert surface. Its acceptance criteria require `defaults` and `defaults.derive`, precedence of CLI flag to derivation to defaults to error, optional ingest date/type at Click parsing, ingest metadata coverage for `client`, `engagement`, `target`, `type`, `date`, and `participants`, and convert coverage for `client`, `engagement`, and `target` including source-root derivation before config defaults (`docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md:13`). The pre-A triage preserves the live issue #63 body and its full rationale, schema sketch, CLI behavior, ingest example, convert applicability, and composition notes (`docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md:372`).

## Stale Evidence Check

The spec explicitly names the strict-P3 triage artifact as scope authority and says prior `folio_*_v1_*` artifacts are not lifecycle evidence. The manifest points pre-A evidence to the strict rerun triage, keeps lifecycle receipt inventory under the strict rerun review board, and requires fresh B.1, D.2, D.5, and D.6 lifecycle gates. This is adequate to drive the slice without stale evidence reuse.

## Blockers

None.
