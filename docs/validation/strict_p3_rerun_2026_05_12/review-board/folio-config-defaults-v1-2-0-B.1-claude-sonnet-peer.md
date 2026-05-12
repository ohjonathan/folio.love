---
deliverable_id: folio-config-defaults-v1-2-0
phase: B.1
role: peer
family: claude-sonnet
status: completed
evidence_labels_used:
  - direct-run
---

# Peer Review — folio-config-defaults-v1-2-0 Phase B.1

Reviewer: claude-sonnet  
Date: 2026-05-12  
Source artifacts read:
- `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`
- `docs/validation/strict_p3_rerun_2026_05_12/folio-config-defaults-v1-2-0_phase_a_spec.md`
- `frameworks/manifests/folio-config-defaults-v1-2-0.yaml`

## Verdict

approve

## Scope Alignment

The spec correctly derives its scope authority from `pre_a_triage.md` (issue #63: "defaults/derive in folio.yaml; metadata resolution order CLI flag → derivation → defaults → error") and makes no reference to prior folio_*_v1_* artifacts as evidence. The stale-evidence exclusion rule from triage is explicitly echoed in the non-goals section: "Do not count any old artifacts from the prior failed closeout as evidence." No stale evidence reuse detected.

## Acceptance Criteria Adequacy

The three AC bullets map cleanly onto the issue's core requirements:

1. **`defaults` and `defaults.derive` blocks in config** — directly implements the `folio.yaml` schema additions from #63.
2. **Metadata resolution order: CLI flag → derivation → defaults → error** — matches the issue's four-level hierarchy (the issue's fifth level, interactive prompt under `--strict`, is conditional and its absence is not explicitly called out as a non-goal; this is a minor gap but not a blocker since the issue's primary use case is the four-level silent resolution).
3. **Make date/type optional at Click level while preserving required resolved metadata before ingest commits** — correctly identifies the architectural seam: optional at parse time, required at dispatch time.

## Implementation Surface

The spec lists `folio/config.py`, `folio/defaults.py`, `folio/cli.py`, `tests/test_config_defaults.py`, and `tests/test_cli_ingest.py`. All five appear in the manifest's `scope.allowed_paths`. The `folio/defaults.py` file is new (untracked on the branch per git status), which is appropriate for the new resolution module implied by the spec. `folio/ingest.py` is modified on the branch but is intentionally excluded from this slice's allowed_paths; the spec's resolution-at-CLI-layer design makes this acceptable.

## Manifest Quality

- `manifest_version: 1.6.0` — correct per triage requirements.
- `lifecycle_receipt_inventory_path` is present (`docs/validation/strict_p3_rerun_2026_05_12/review-board/folio-config-defaults-v1-2-0-lifecycle-receipts.yaml`), satisfying the strict-P3 structural requirement.
- `pre_a.entry: triage` and `artifact_path` correctly anchor to the triage document.
- `model_assignments` match triage: claude-opus for A, claude-sonnet/codex/gemini for B.1/D.2/D.5, codex for B.3/D.3, claude-opus for C/D.4/D.6/E.
- `cardinality_assertions` command (`test -f folio/defaults.py && rg -n "defaults|derive|resolve" folio/defaults.py folio/cli.py tests/test_config_defaults.py`) provides a concrete, executable anchor that will fail visibly if the implementation surface is absent.
- `gate_prerequisites` are complete: G-test-1 (tests), G-scope-1 (dir), G-cardinality-1 (symbol anchors), G-verdict-1 (D.5 verifier count = 3), G-blocker-1 (D.3 no unresolved markers), G-branch-1 (branch name).
- `forbidden_paths` and `forbidden_symbols` cover credential-leak scenarios appropriately.
- The `smoke_checks.phase: C` command matches the spec's required validation command verbatim.
- `scope.allowed_path_patterns` correctly covers the review-board artifact pattern used by this file.

## Minor Observations (non-blocking)

- The spec does not call out `--strict` interactive-prompt behavior as an explicit non-goal. Issue #63 describes this as conditional on `--strict` flag, so it is a distinct optional extension, not core. The omission is acceptable for a minimal viable slice.
- The B.3 canonical verdict path and D.3 canonical verdict path are listed in `scope.allowed_paths` even though they don't exist yet. This is standard manifest forward-declaration and is not a concern.

No blockers identified. The spec and manifest are adequate to drive phase C implementation without stale evidence reuse.
