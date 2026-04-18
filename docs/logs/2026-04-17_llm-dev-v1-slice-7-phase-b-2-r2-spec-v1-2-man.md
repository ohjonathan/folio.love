---
id: log_20260417_llm-dev-v1-slice-7-phase-b-2-r2-spec-v1-2-man
type: log
status: active
event_type: v1-0-0-spec-canonical-verdict-r2
source: cli
branch: feat/folio-enrich-diagnose-v1-0-0-C-author-claude
created: 2026-04-17
---

# v1.0.0 Spec Canonical Verdict R2

## Goal

Re-issue the B.3 canonical verdict for `folio-enrich-diagnose-v1-0-0` after the v1.2 author closure pass, verifying the four B.3 R1 required-fix items and overwriting the stable canonical verdict path.

## Key Decisions

- Returned `REQUEST-FURTHER-FIXES` instead of approving Phase C.
- Closed CB-4, CSF-1, and the stale metadata sweep based on direct text assertions and spec/manifest citations.
- Kept CB-2 open because the proposed v1.2 `ScopeOrCommandGroup.parse_args` passes the three option-before-scope enrich forms but fails `folio enrich diagnose ClientA` by rewriting the subcommand positional scope into group-level `--scope`.
- Preserved the canonical artifact path by overwriting `docs/validation/v1.0.0_spec_canonical_verdict.md`.

## Alternatives Considered

- Approval with a note was rejected because ED-CLI-23d is explicit in v1.2 and the minimal Click reproduction fails with exit 2.
- Treating the subcommand failure as a Phase C implementation detail was rejected because the dispatch requested verification of the v1.2-described parser shape before Phase C.

## Impacts

- Phase C remains locked until the parser stops rewriting arguments after a registered subcommand.
- The remaining fix is narrow: preserve `folio enrich --dry-run ClientA`, `folio enrich --llm-profile X ClientA`, and `folio enrich --force ClientA`, while ensuring `folio enrich diagnose ClientA` routes to the diagnose subcommand with `scope='ClientA'`.

## Changes Made

- Updated `docs/validation/v1.0.0_spec_canonical_verdict.md` to the B.3 R2 verdict.
- Ran `ontos log -e "v1-0-0-spec-canonical-verdict-r2"` and filled this session log.

## Testing

- `ontos map` exited 0 and regenerated `Ontos_Context_Map.md` with existing metadata warnings.
- Minimal Click harness copied from the v1.2 parser: option-before-scope forms passed; `folio enrich diagnose ClientA` failed with `Error: No such option: --scope`.
- Text assertions passed for CB-4 docstring posture, CSF-1 sort wording, and the four stale metadata sweep items.
- `frameworks/llm-dev-v1/scripts/verify-schema.sh --manifest frameworks/manifests/folio-enrich-diagnose-v1-0-0.yaml` exited 0.
- `frameworks/llm-dev-v1/scripts/verify-p3.sh --manifest frameworks/manifests/folio-enrich-diagnose-v1-0-0.yaml` exited 0.
- `frameworks/llm-dev-v1/scripts/verify-frontmatter.sh` exited 0.
- `frameworks/llm-dev-v1/scripts/verify-gate-categories.sh --manifest frameworks/manifests/folio-enrich-diagnose-v1-0-0.yaml` exited 0.
