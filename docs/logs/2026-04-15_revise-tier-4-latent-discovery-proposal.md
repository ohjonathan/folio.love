---
id: log_20260415_revise-tier-4-latent-discovery-proposal
type: log
status: active
event_type: amend-pr-43-product-centered-tier-4-proposal-rewrite
source: codex
branch: codex/tier4-latent-discovery-proposal-layer
created: 2026-04-15
---

# Amend PR #43: product-centered Tier 4 proposal rewrite

## Summary

Amended PR #43 in place after external review. Reframed the Tier 4 proposal
around the operator problem of repeated machine-suggestion noise and hidden
trust filtering, narrowed the committed scope from a standalone latent-
discovery requirement to proposal review hardening, and fixed the objective
corpus gaps called out in review.

## Changes Made

- Rewrote the Tier 4 PRD framing around one concrete engagement moment:
  SteerCo-prep review of machine-suggested relationships.
- Removed standalone FR-813 latent-discovery commitment and renumbered the
  surviving proposal-governance requirement to FR-813 proposal review
  hardening.
- Re-sequenced the roadmap and prioritization matrix so user-visible digest,
  graph quality, related links, and synthesize work land before proposal
  hardening and deferred discovery experiments.
- Added explicit trust-gate override and excluded-count disclosure language,
  including `folio digest --include-flagged`.
- Brought `relates_to` into v1 relation governance while keeping
  `instantiates` deferred.
- Rewrote `docs/specs/tier4_discovery_proposal_layer_spec.md` into a proposal
  review hardening spec with stable fingerprint semantics, compact review
  rendering, queue bounds, rejection memory, and merge dampening.
- Updated `docs/specs/tier4_digest_design_spec.md` to include the trust
  override, empty-result disclosure, and clearer revision metadata.
- Updated `docs/specs/v0.5.1_tier3_entity_system_spec.md` to stop treating
  `folio entities merge` as a future unresolved gap.
- Added a concrete `folio enrich diagnose` contract to
  `docs/specs/folio_enrich_spec.md`.
- Renamed the misleading earlier log file so its filename now matches its
  content.

## Testing

- `git diff --check`
- terminology and numbering grep passes for removed `F-414` / `FR-814`
- Ontos sync and doctor run after doc edits

## Goal

Amend PR #43 without rolling it back, so the proposal becomes product-centered,
falsifiable, and explicit about trust filtering and review burden while still
keeping shared proposal governance.

## Key Decisions

- Accept the objective corpus gaps and strongest product critiques in
  substance.
- Keep proposal governance as the load-bearing Tier 4 change.
- Demote latent discovery from a standalone committed requirement to
  architecture framing and validation backlog.
- Keep canonical graph truth as frontmatter plus registries only.

## Alternatives Considered

- Withdraw the proposal entirely and revert to producer-specific metadata.
  Rejected because it would drop the shared review contract that Tier 4
  producers need.
- Keep the broader latent-discovery requirement as committed product scope.
  Rejected because it widened infrastructure before user-visible value.
- Treat flagged-input exclusion as strict with no override. Rejected because it
  hides useful context during operator review and makes empty results
  misleading.

## Impacts

- PR #43 now reads as a user-problem-driven proposal rather than an
  architecture-first expansion.
- Tier 4 reviewability has explicit numeric gates and queue bounds.
- Supporting specs no longer contradict shipped `folio entities merge` behavior
  or omit `folio enrich diagnose`.
