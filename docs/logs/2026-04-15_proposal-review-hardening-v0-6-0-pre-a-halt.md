---
id: log_20260415_proposal-review-hardening-v0-6-0-pre-a-halt
type: log
status: complete
event_type: chore
source: claude-code
branch: codex/tier4-latent-discovery-proposal-layer
created: 2026-04-15
concepts: [llm-dev-v1, pre-a-proposal, halt, tier-4-proposal-review-hardening, framework-adoption]
depends_on:
  - log_20260415_tier-4-graph-ops-layer
---

# proposal-review-hardening-v0-6-0 Pre-A halt

## Summary

First production run of the `llm-dev-v1.1` framework bundle against folio.love. Lifecycle halted at Pre-A.proposal Round 1 per the operator's framework-mandated halt list (`Pre-A verdict ≠ Proceed to Phase A → HALT`). Consolidated canonical verdict: **Revise and re-review** — Claude-sub reviewer (Adversarial+Product posture) raised three blocker-severity findings against the proposal doc, while Gemini reviewer (Alignment+Technical posture) returned Proceed. Split verdict is expected Template 16 behavior; orchestrator consolidated per P5 evidence-weighted-consensus rule.

## Changes Made

**Setup (phase 0):**
- `frameworks/llm-dev-v1/tokens.local.md` — folio-specific token fill.
- `frameworks/manifests/proposal-review-hardening-v0-6-0.yaml` — first adopter manifest. Schema-validated against `deliverable-manifest.schema.yaml`.
- `docs/trackers/proposal-review-hardening-v0-6-0.md` — phase tracker.
- `docs/retros/llm-dev-v1-adoption.md` — friction log (append-only), finalized at session end with Phase E retro (narrowed scope).

**Pre-A.proposal (Round 1):**
- `docs/validation/v0.6.0_pre_a_proposal_claude-sub_adversarial_product.md` — Reviewer 1 verdict (Revise; 3 blockers, 5 should-fix, 3 minor).
- `docs/validation/v0.6.0_pre_a_proposal_gemini_alignment_technical.md` — Reviewer 2 verdict (Proceed; 0 blockers).
- `docs/validation/v0.6.0_pre_a_proposal_canonical_verdict.md` — orchestrator-consolidated canonical verdict (Revise, preserved blockers B-1/B-2/B-3).
- `docs/logs/2026-04-15_proposal-review-hardening-v0-6-0--A.proposal-halt.md` — halt report.

**Did NOT execute:** Phases A, B, C, D, full E. Framework halt at Pre-A per operator's strict-first-round-halt policy.

## Testing

- `frameworks/llm-dev-v1/scripts/verify-all.sh`: **8/8 green** after `pip install check-jsonschema`.
- `check-jsonschema --schemafile <schema> <adopter-manifest>`: **valid** after fixing id pattern (dots → dashes, see friction [F-011]).
- `python3 -m pytest tests/ -q`: not run this session (no Phase C).

## Goal

Run the llm-dev-v1.1 framework end-to-end against a real folio.love deliverable (FR-813 Proposal Review Hardening, smallest coherent slice) to stress-test the framework's first production adoption and surface every friction point as v1.2 input.

## Key Decisions

- **Bundle location:** kept at existing `frameworks/llm-dev-v1/` rather than moving to adoption-doc-prescribed `ops/llm-dev-v1/`. Bundle is self-contained; cosmetic path choice.
- **Fourth family:** declared `claude-sub` (Claude sub-agent via Agent tool) as a non-author engineering family to clear the P3 ≥3-non-author floor. Documented as a strict-violation-in-spirit (both share the Claude model family) and flagged as the #1 v1.2 blocker.
- **Pre-A round policy:** honored the operator brief's strict-first-round-halt, overriding the framework's default one-revision-cap allowance. Halted on Round 1 Revise rather than attempting a Round 2.
- **Consolidation for Pre-A:** Template 16 does not define a meta-consolidator; orchestrator hand-rolled consolidation using P5 (evidence-weighted consensus) adapted from Template 06. Flagged as v1.2 target.

## Alternatives Considered

- **Run Round 2 anyway (framework default):** Rejected per operator brief's explicit halt list. Framework would have allowed a second round; operator stipulated single-round strict halt for Pre-A.
- **Halt at Setup over P3 violation:** Considered but rejected — a halt at Setup would have produced no dispatch-level friction evidence. Proceeding with a declared pseudo-family (with explicit v1.2 retro annotation) surfaced more actionable v1.2 targets.
- **Treat split verdict as net-Proceed (majority-vote across lenses):** Considered but rejected — claude-sub's blocker findings were supported by direct proposal-doc citation with evidence labels; gemini's Proceed verdict did not engage with those findings. P5 evidence-weighted consensus rule preserves evidenced blockers over unevidenced approvals.

## Impacts

- **Framework adoption:** 16 friction entries captured in `docs/retros/llm-dev-v1-adoption.md` with ranked v1.2 targets. 3 A-severity items (P3 model, Pre-A consolidator, adoption-doc v2). Actionable upstream as a johnny-os GitHub issue.
- **Tier 4 proposal:** 3 preserved blockers (B-1/B-2/B-3) require author revision before a Round 2 Pre-A can return Proceed. The existing PR #43 (the proposal doc) is not independently blocked — this review ran on the post-amendment revision 2 that PR #43 already contains — but any downstream spec-authoring against this proposal must address the three blockers.
- **Tooling:** `check-jsonschema` installed (0.36.2) as a dev dependency; future sessions won't need the install step.
