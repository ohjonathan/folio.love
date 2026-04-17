# Changelog

All notable changes to folio.love are documented here. The format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); folio is pre-1.0, so breaking
changes at minor versions are permitted but flagged explicitly.

## [v0.8.0] — 2026-04-17

### Added

- **`folio synthesize [SCOPE]`** — new top-level command. Structural
  synthesis report of §5 proposal-linked cross-references in a scope.
  `SCOPE` resolves to a registered document ID, an engagement subtree
  (matching `markdown_path` or `deck_dir`), or library-wide when `-`,
  empty string, or omitted. Invalid scope exits with code 1 and a
  stderr error message.
  Read-only: no LLM calls, no registry mutations, no new doc artifacts.
  This is the second sub-slice of Shipping Plan §15.6 (shared-consumer
  expansion); sub-slice 1 (`folio graph` generalized proposals, v0.7.1)
  shipped at PR #60. Narrative synthesis (LLM-backed) is planned for a
  future version; v0.8.0 surfaces the shared proposal contract
  structurally so operators can audit proposal flow across a scope.
- **`folio synthesize --json`** — shared payload-level envelope with
  `schema_version: "1.0"`, `command: "synthesize"`, `scope` (null for
  library-wide), `trust_override_active`, `excluded_flagged_count`,
  `findings`. Each finding carries all 11 parent §5 shared-contract
  keys matching graph v0.7.1, plus `proposal_id` and `relation`.
- **`folio synthesize --include-flagged`** — parent §11 trust-override
  for flagged source/target inputs. Envelope `trust_override_active`
  mirrors the flag; stdout shows "Trust override active" annotation.
- **`folio synthesize --limit N`** — caps findings list (default
  unbounded; must be ≥ 0 per `click.IntRange`). `excluded_flagged_count`
  reflects full upstream exclusion, not the post-limit slice. When
  `--limit` truncates, stdout prints a `(limited to N of M total)`
  footer; the envelope's `findings_truncated` flag is deferred to
  v0.8.1 with a `schema_version` bump.
- Zero-findings + zero-exclusions case prints a `Next: check that the
  scope resolves, or run \`folio ingest\` / \`folio enrich\`…`
  diagnostic breadcrumb so operators can distinguish empty-scope from
  producers-haven't-run (parent §11 rule 5 purposive honoring).
- Each finding in the `--json` envelope carries `flagged_inputs`
  (a list of `"source"` / `"target"`) so auditors running with
  `--include-flagged` can tell which document triggered the flag.
  Stdout renders this as `[flagged: source]`, `[flagged: target]`,
  or `[flagged: source+target]`.
- Shared trust-posture helper `folio.tracking.trust.derive_trust_status`
  (promoted from `folio.graph._derive_trust_status` in Phase 0 commit
  `831a741`). Both `folio graph doctor` and `folio synthesize` call
  the same function object, proving shared-consumer uniformity per
  parent §12.

### Breaking

- None. The shared envelope is NEW with synthesize — no existing
  consumers to migrate.

### Known gaps / planned follow-ups

- **Graph envelope migration** — `folio graph doctor --json` still
  emits the v0.7.1 shape without the `schema_version`/`command`
  envelope wrap. Follow-up slice will migrate graph to the shared
  envelope. Until then, graph is the divergent surface.
- **LLM-backed narrative synthesis** — deferred to v0.8.1.
- **`schema_gate_result` on synthesize findings** — v0.8.0 emits
  literal `null` on every finding; synthesize is surface-time only
  and does NOT compute gate rules (graph does, at its renderer).
  Follow-up may lift gate computation into the shared collector.
- **`input_fingerprint`** continues as legacy `basis_fingerprint`
  alias pending a parallel parent-§7 revision workstream.
- **`findings_truncated: bool`** envelope key (when `--limit` caps)
  is reserved for v0.8.1 with a `schema_version` bump to `"1.1"`.

## [v0.7.1] — 2026-04-16

### Breaking

- **`folio graph doctor --json`**: `pending_relationship_proposal` findings now
  carry `subject_id: null` per parent §5 semantics. The proposal identifier
  previously stored under `subject_id` is now exposed under a new top-level
  `proposal_id` key. Consumers that read `subject_id` for the proposal ID MUST
  switch to `proposal_id`. The default CLI stdout rendering is preserved
  (proposal ID still visible to operators running `folio graph doctor`).

### Added

- `folio graph doctor` findings for `pending_relationship_proposal` now carry
  the §5 shared-proposal-contract fields: `proposal_type`, `source_id`,
  `target_id`, `evidence_bundle`, `reason_summary`, `trust_status`,
  `schema_gate_result`, `producer`, `input_fingerprint`, `lifecycle_state`,
  plus the new `proposal_id` key (see "Breaking" above). Non-proposal findings
  are unchanged.
- `folio graph doctor` now emits a minimal `schema_gate_result` for
  relationship proposals (today-computable rules: `target_registered`,
  `supported_relation`). Default stdout annotates failures as
  `[schema-gate: <rule>]`.
- `folio graph doctor` default stdout annotates `[flagged]` for proposals
  whose source or target document has `review_status: flagged`.
- `folio graph doctor --include-flagged` — parity with `folio links`; surface
  proposals whose source or target document is flagged.
- `recommended_action` on pending-proposal findings now varies by
  `trust_status` and `schema_gate_result` (four variants: baseline, flagged,
  target-missing, unsupported-relation) instead of a single static message.

### Known gaps

- `input_fingerprint` is surfaced as a legacy `basis_fingerprint` alias
  pending a future parent-spec §7 revision; the full §7 contract (normalized
  claim identity + relation kind + producer identity) is not yet satisfied.
- Full `evidence_bundle` rendering in default stdout (1–3 locator lines per
  finding) is deferred to sub-slice 2+ of the Shipping Plan §15.6 expansion
  (`folio synthesize` v0.8.0).
- Payload-level `schema_version` field on `folio graph doctor --json` is
  deferred to sub-slice 2+ (`--json` envelope redesign scope).
- Schema-gate `target_registered` rule checks registry deck-ID membership
  only; archived / deprecated / non-deck target validity is deferred to
  validation-track follow-up slices per parent §13.
- Schema-gate `supported_relation` rule is **forward-compat today**: the
  current producer path filters unsupported relations at
  `folio/links.py:191` before `graph_doctor` sees them, so operators
  won't encounter a `[schema-gate: supported_relation]` annotation in
  v0.7.1. The rule is in place for future `proposal_type` producers that
  emit via a different path (e.g., diagram-archetype proposals in
  validation-track follow-ups).

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
