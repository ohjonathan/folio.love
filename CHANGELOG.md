# Changelog

All notable changes to folio.love are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); folio is pre-1.0, so breaking
changes at minor versions are permitted but flagged explicitly.

## [v0.7.0] — 2026-04-16

### Added
- **`folio digest` command** — first implementation of the Tier 4 digest cluster
  (`docs/specs/tier4_digest_design_spec.md` rev 4 + `docs/specs/v0.7.0_folio_digest_spec.md`
  v1.2). Generates daily and weekly synthesis digests for one engagement scope.
- `folio digest <scope>` — daily digest from the day's eligible evidence and
  interaction notes. `--date YYYY-MM-DD` for non-current days; `--include-flagged`
  to widen the predicate to source-backed inputs whose `review_status` is `flagged`
  (daily mode only; no-op in `--week`).
- `folio digest <scope> --week` — weekly digest assembled from existing daily
  digests in the requested ISO week.
- `--llm-profile` override for routing.digest.
- Output path: `<engagement-root>/analysis/digests/<digest-id>/<digest-id>.md`,
  ID `{client}_{engagement-short}_analysis_{period-compact}_{label}`.
- Source-less `analysis` registry entries (omits `source`, `source_hash`, etc.;
  carries `subtype: digest`, `digest_period`, `digest_type`, `draws_from`,
  `review_status: flagged`, `review_flags: [synthesis_requires_review]`).
- Programmatic `## Trust Notes` and `## Documents Drawn From` / `## Daily Digests
  Drawn From` rendering — never trusted to the LLM, deterministic audit trail.
- `folio.digest.generate_daily_digest` and `folio.digest.generate_weekly_digest`
  public API; `DigestResult`, `DigestFlaggedCounts`, `DailyInputSelection` dataclasses.
- 50+ tests (`tests/test_digest.py` + `tests/test_cli_digest.py`) covering the
  predicate, identity, atomicity, registry contract, retry policy, fence-aware
  heading detection, AST-based forbidden-symbol scan, and the registry-compatibility
  canaries (status, scan, refresh, enrich, rebuild_registry).

### Changed
- `cli.refresh` skipped-analysis message is now subtype-aware: digest rows
  receive `↷ <id>: skipping digest (source-less); rerun \`folio digest\` instead`,
  preserving the prior generic message for non-digest analysis subtypes.

### Notes
- Digest mutations are serialized via the existing `library_lock(library_root,
  "digest")` to prevent concurrent rerun races.
- Validation retry: missing/duplicate LLM-owned section triggers one corrective
  re-prompt before failing per spec §11. Transient-error retry (timeout, rate-limit)
  is deferred to a follow-up slice.
- Deferred from this slice: `--steerco`, watcher/automatic trigger, cross-engagement
  scope, digest-generated relationship suggestions, manual-edit preservation across
  rerun (see §14 carry-forwards).
## [v0.6.5] — 2026-04-16

### Added
- **Entity-merge rejection memory.** `folio entities suggest-merges` now
  filters rejected merge candidates via a per-pair `basis_fingerprint`
  stored in `entities.json`'s new `rejected_merges` key. `folio graph doctor`
  and `folio graph status` both honor the same filter. Suggestions revive
  when entity aliases change enough to shift the fingerprint (e.g., new
  alias adds a new heuristic signal). Output always discloses suppression
  count and a total-rejections-recorded line.
- **New `folio entities reject-merge <left> <right>` command.** Persists a
  rejection record keyed on the sorted pair + current basis_fingerprint.
  Locked via `library_lock` against concurrent registry mutations.

### Changed
- **`folio graph status` label change.** `Duplicate person candidates:`
  renamed to `Reviewable duplicate person candidates:` to disclose that
  the count now reflects only candidates not yet dismissed by rejection
  memory. Scripts scraping the prior label need to update.
- `entities.json` schema gains top-level `rejected_merges: []` key.
  Backward-compatible in both directions: pre-v0.6.5 readers preserve the
  key via `save()` write-through; pre-v0.6.5 writers emit files that
  v0.6.5 readers load cleanly (key defaulted to `[]`). `_schema_version`
  is NOT bumped (stays at `1`).
  Spec: `docs/specs/v0.6.5_entity_merge_rejection_memory_spec.md`.
## [v0.6.4] — 2026-04-15

### Added
- **Trust-gated surfacing** for the `folio links` command family (§11 of the
  Tier 4 proposal). Proposals whose source or target document has
  `review_status: flagged` are excluded from `folio links review`,
  `folio links status`, and bulk mutations by default.
- `--include-flagged` flag on `folio links review`, `status`, `confirm`,
  `reject`, `confirm-doc`, and `reject-doc` — operator opt-in to see or act
  on flagged-input proposals. Flagged proposals surfaced under the flag carry
  a `(flagged: source|target|source, target)` trust-posture tag.
- `folio links status` output gains a `Flagged Excluded` column and footer
  total. Rows are emitted for sources that have only flagged-excluded
  proposals (no silent omission).
- Silent-empty disclosure on `folio links review` when the queue is empty
  only because flagged inputs were filtered.
- `folio links confirm-doc` / `reject-doc` print a diagnostic when 0
  proposals were acted on but flagged exclusions exist.

### Changed
- **Return-type migration:** `collect_pending_relationship_proposals` now
  returns `tuple[list[RelationshipProposalView], SuppressionCounts]` (was
  `dict[str, int]`). `SuppressionCounts` has `.rejection_memory: dict[str, int]`
  and `.flagged_input: int`. Prevents producer-name collision with a sentinel
  dict key.
- `relationship_status_summary` returns
  `tuple[list[RelationshipStatusRow], int]` where the `int` is the total
  flagged-excluded count across the scope.
- `RelationshipStatusRow` gains `flagged_excluded: int = 0`.
- `RelationshipProposalView` gains `flagged_inputs: list[str]` (empty when
  neither source nor target is flagged).
- `confirm_doc` / `reject_doc` return `tuple[int, int]` (`acted`,
  `flagged_excluded`).
- `_find_pending_view`, `confirm_proposal`, `reject_proposal` gain
  `include_flagged: bool` keyword-only parameter for consent propagation.

### Fixed
- **Target trust-state staleness (CB-1):** target `review_status` is now
  read from the target document's frontmatter, not the registry snapshot.
  Registry state can lag behind frontmatter edits; reading frontmatter
  directly closes the bypass path where a flagged target was still
  surfaced as default-reviewable between syncs.

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

## [v0.5.2] — 2026-03-28

### Added
- `folio enrich` — post-hoc enrichment for tags, entity backfill, and
  LLM-proposed relationships (`supersedes`, `impacts`) surfaced under
  `_llm_metadata.enrich`.
- `## Related` section generation from canonical relationship frontmatter.
- `folio enrich diagnose` — read-only pre-run mutation-safety surface.
- `--dry-run` preview mode, idempotency markers, per-file skip behavior
  so reruns are safe.

## [v0.5.1] — 2026-03-23

### Added
- Entity registry (`entities.json`): canonical name store with type
  namespacing (person, department, system, process), aliases, and
  confirmation workflow.
- `folio entities` CLI: `list`, `show`, `import` (CSV), `confirm`, `reject`.
- CSV import for bulk org-chart loading — names, titles, departments,
  reporting relationships, client tags.
- Ingest-time entity resolution: exact-match and alias-match against
  confirmed entities during `folio ingest`.
- LLM soft-match proposals for unconfirmed entity candidates, flagged
  `needs_confirmation` for human review.

## [v0.5.0] — 2026-03-22

### Added
- `folio ingest` — interaction ingestion pipeline for `.txt` and `.md`
  transcripts.
- Interaction document type (`type: interaction`; subtypes:
  `client_meeting`, `expert_interview`, `internal_sync`,
  `partner_check_in`, `workshop`).
- Reviewability fields on interaction notes: `review_status`,
  `review_flags`, `extraction_confidence`, `grounding_summary`.
- Ingest-time entity extraction (people, departments, systems, processes)
  rendered as unresolved Obsidian wikilinks for later confirmation.
- Interaction registry integration: interaction entries tracked in
  `registry.json` alongside evidence documents.
- Re-ingest identity via `source_hash` to prevent duplicate notes on
  re-processing.
- Optional flags: `--client`, `--engagement`, `--participants`,
  `--duration-minutes`, `--source-recording`, `--title`, `--target`,
  `--llm-profile`.
