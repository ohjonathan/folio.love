# Changelog

All notable changes to folio.love are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); folio is pre-1.0, so breaking
changes at minor versions are permitted but flagged explicitly.

## [v0.6.3] — 2026-04-15

### Changed
- **Emission-time rejection memory:** proposals matching a previously
  rejected `basis_fingerprint` are now marked `lifecycle_state: "suppressed"`
  at enrichment time instead of being silently dropped. Suppressed proposals
  are preserved in frontmatter for audit trail.
- **Queue-cap enforcement:** per §9.1, no producer may hold more than 20
  proposals in `lifecycle_state: "queued"` per library. Excess proposals
  are marked `"suppressed"`. Tie-breaking: high-confidence first, then
  emission order.

### Fixed
- **Rejected-proposal preservation:** operator rejections
  (`folio links reject`) now survive re-enrichment. Previously, rejected
  entries were lost when `_llm_metadata.enrich` was rebuilt on the next
  enrich run.

### Added
- `suppression_counts` field in `_llm_metadata.enrich.axes.relationships`
  reports per-cause suppression totals (keys: `rejection_memory`,
  `queue_cap`).

## [v0.6.2] — 2026-04-15

### Changed
- **Provenance proposal schema rename:** `ProvenanceProposal.status` →
  `lifecycle_state`, same mapping as v0.6.1 relationship proposals.
  `stale_pending` value preserved (provenance-specific).
  **No operator action required.** Spec:
  `docs/specs/v0.6.2_provenance_lifecycle_rename_spec.md`.

## [v0.6.1] — 2026-04-15

### Changed
- **Proposal schema rename:** relationship proposal `status` field renamed to
  `lifecycle_state`. Values: `pending_human_confirmation` → `queued`;
  `rejected` unchanged; new enum members `accepted`, `suppressed`, `stale`,
  `superseded` (reserved, no writers this release). `from_dict` reads legacy
  `status` transparently; `to_dict` emits only `lifecycle_state`. Raw-dict
  readers also handle both formats via fallback.
  **No operator action required** — backward-compatible reads handle old data
  automatically. Spec: `docs/specs/v0.6.1_proposal_lifecycle_rename_spec.md`.

## [v0.6.0] — 2026-04-15

### Added
- **Rejection memory for relationship proposals.** `folio links review` now filters out
  pending proposals whose `(source_id, target_id, relation, basis_fingerprint)` matches an
  existing `status: rejected` entry in the same document's frontmatter. A previously-rejected
  proposal with a *different* `basis_fingerprint` surfaces with a `(revived — basis changed)`
  annotation so operators can distinguish genuine new suggestions from resurfacing noise.
  The output always renders a suppression-count disclosure line ("N proposals suppressed by
  rejection memory.") so the feature's state is observable. Spec:
  `docs/specs/v0.6.0_proposal_review_hardening_spec.md`.
- **Producer acceptance-rate diagnostic on `folio graph doctor`.** A new `### Producer
  acceptance rates` section renders per-producer accepted/rejected counts, cumulative
  acceptance rate, and status (`ok`, `low-acceptance (< 50%)`, or `warmup (< 10 reviewed)`).
  Diagnostic-only in v0.6.0 — the status column does NOT throttle surfacing. Computed at
  query time from existing frontmatter (rejections in
  `_llm_metadata.<producer>.axes.relationships.proposals`; acceptances in
  `_llm_metadata.links.confirmed_relationships`); no new persistence or timestamps required.

### Changed (BREAKING)
- **`folio graph doctor --json` output shape.** Previously: top-level JSON array of
  finding objects. Now: top-level object with keys `findings` (unchanged list content),
  `producer_acceptance_rates` (new array), and `producer_acceptance_rates_data_integrity`
  (new object with `missing_producer_count`). Consumers that parsed the top-level array
  must be updated to extract `findings` from the new top-level object. Rationale: the
  additional diagnostic data needed a first-class location; adding keys to a list output
  would have required stashing them in a magic "meta" entry. See
  `docs/specs/v0.6.0_proposal_review_hardening_spec.md` §7.

### Notes
- `collect_pending_relationship_proposals` return type changed from
  `list[RelationshipProposalView]` to `tuple[list[RelationshipProposalView], dict[str, int]]`.
  All internal callers updated in the same commit (`folio/links.py`, `folio/graph.py`,
  `folio/cli.py`). No external API consumers identified.
