---
deliverable_id: folio-config-defaults-v1-2-0
phase: B.1
role: alignment
family: codex
status: completed
evidence_labels_used:
  - direct-run
---
# B.1 Alignment Review: folio-config-defaults-v1-2-0

## Verdict
request changes

## Review Scope
Reviewed only the Phase A spec, strict-P3 pre-A triage entry, and lifecycle manifest named in the prompt:
`docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`,
`docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md`, and
`frameworks/manifests/folio-config-defaults-v1-2-0.yaml`.

## Blockers
- `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md:13` reduces the acceptance contract to generic `defaults` / `defaults.derive` support and explicitly calls out only ingest `date/type` optionality at `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md:16`. The live issue scope in `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md:388` names both `folio ingest` and `folio convert`, and the repeated metadata table at `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md:407` through `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md:414` names `client`, `engagement`, `target`, `type`, `date`, and `participants`. The Phase A contract should either require resolution coverage for those fields or explicitly defer specific fields as non-goals. As written, a Phase C implementation could satisfy the spec while leaving most of issue #63 unresolved.
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:4` frames the slice as ingest metadata only, and the validation surface at `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:127` through `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:129` runs only `tests/test_config_defaults.py` and `tests/test_cli_ingest.py`. There is no manifest-level guard that `folio convert` participates in defaults resolution, despite the triage source saying `folio ingest` and `folio convert` should stop requiring repeated metadata. If convert is intentionally out of this slice, the manifest and spec need an explicit non-goal or sibling-slice reference.

## Stale Evidence Assessment
The stale-evidence boundary is mostly aligned. The Phase A spec states that prior `folio_*_v1_*` artifacts are not lifecycle evidence at `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md:12` and repeats that as a non-goal at `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md:30`. The manifest also roots pre-A to the regenerated triage artifact at `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:5` through `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:7`, keeps review artifacts under the strict-P3 rerun review board at `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:32` through `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:36`, and defines a fresh lifecycle receipt inventory at `frameworks/manifests/folio-config-defaults-v1-2-0.yaml:136`.

## Required Changes
Revise the Phase A spec and manifest so the deliverable cannot pass with only partial ingest `date/type` behavior. At minimum, enumerate the metadata fields in scope, state whether `folio convert` is in scope or explicitly deferred, and add validation expectations that prove the intended coverage from fresh strict-P3 artifacts rather than relying on prior closeout history.
