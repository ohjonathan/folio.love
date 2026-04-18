---
id: log_20260417_v1-0-0-spec-canonical-verdict
type: log
status: active
event_type: decision
source: codex
branch: feat/folio-enrich-diagnose-v1-0-0-C-author-claude
created: 2026-04-17
---

# v1.0.0 spec canonical verdict

## Context

Goal: produce the B.3 canonical spec verdict for
`folio-enrich-diagnose-v1-0-0`, consolidating the four B.1 R1 lens verdicts
against the v1.1 spec and manifest closures.

Inputs reviewed:
- `frameworks/llm-dev-v1/framework.md` P1-P12
- `frameworks/llm-dev-v1/templates/01-worker-session-contract.md`
- `frameworks/llm-dev-v1/templates/06-meta-consolidator.md`
- B.1 verdicts from codex adversarial, gemini alignment, claude-sub peer,
  and claude-sub product
- `docs/specs/v1.0.0_folio_enrich_diagnose_spec.md`
- `frameworks/manifests/folio-enrich-diagnose-v1-0-0.yaml`
- parent enrich spec §7.7
- implementation anchors in `folio/enrich.py` and `folio/cli.py`

## Decision

Key Decisions:
- Wrote `docs/validation/v1.0.0_spec_canonical_verdict.md`.
- Canonical verdict is `REQUEST-FURTHER-FIXES`; Phase C remains locked.
- Preserved the cross-provider Click blocker as gating because
  ADV-B1-002 and PEER-B1-001 converge across codex and claude-sub.
- Marked CB-4 as needing rework because v1.1's diagnose help docstring
  includes literal `--include-flagged` inside the marker-bounded CLI block
  while manifest G-scope-6/G-scope-7 require that literal to be absent.
- Marked CSF-1 as needing rework because §7.2 and the manifest summary retain
  stale two-key sort wording after the primary spec changed to the three-level
  sort.

## Rationale

Alternatives Considered:
- Approve with minor cleanups deferred: rejected because CB-2 is a
  cross-provider blocker and still reproduces for option-before-scope legacy
  invocations.
- Treat the include-flagged help text as a product-only should-fix: rejected
  because it directly conflicts with the manifest firewall gates and would
  fail if implemented from the spec.
- Ignore stale gate/test inventory as non-gating: rejected for the canonical
  verdict because the B.3 instructions required disposition for all findings
  and explicit verification that manifest gates encode v1.1 promises.

Direct checks performed:
- `ontos map` exited 0 and regenerated the context map.
- A minimal Click reproduction using existing `ScopeOrCommandGroup` plus the
  v1.1 hidden `--scope` option showed `["--dry-run", "ClientA"]`,
  `["--llm-profile", "X", "ClientA"]`, and `["--force", "ClientA"]` all
  exit 2 with `No such command 'ClientA'`.
- Framework verification scripts passed: `verify-schema.sh`, `verify-p3.sh`,
  `verify-frontmatter.sh`, and `verify-gate-categories.sh`.

## Consequences

Impacts:
- B.2/R2 or equivalent author fix pass is required before Phase C dispatch.
- Required fixes are listed in the canonical verdict: preserve option-before-
  scope forms, reconcile include-flagged help text with firewall gates, finish
  sort-wording cleanup, and repair stale gate/test metadata.
- Ontos context map changed because activation regenerated it. No manual edit
  was made to `Ontos_Context_Map.md`.
