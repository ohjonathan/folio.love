# Changelog

All notable changes to the `llm-dev-v1` framework bundle are documented here.
Versioning is bundle-scoped (`llm-dev-vMAJOR.MINOR.PATCH`).

## v1.2.0 — Candidate 2026-04-16 (PR #TBD, merge `TBD`)

Minor release; first v1.x release to merge cross-run findings from two
independent adopter retros: the framework maintainer's D3 Manifest Spec
retro and folio.love's v1.1.0 adoption retro (5 slices). Full 3-family
review board (Claude + Codex + Gemini) per minor-release policy —
distinct from v1.1.1's 2-family focused review. Canonical verdict path:
`review-board/v1.2.0-spec-verdict.md` (pending Gemini reviewer-of-
reviewer audit on top of the consolidated family verdicts).

**Non-goals held.** No breaking schema changes, no schema renames, no
token removals. New schema fields (`review_rounds[]`,
`cli_capability_matrix[].evidence_cap`,
`cross_provider_adversarial_passes[]`) are additive and optional —
v1.0.0 / v1.1.0 / v1.1.1 manifest CONTRACTS are preserved (a manifest
drafted under any earlier version still validates under the v1.2.0
schema). The bundled `manifest/example-manifest.yaml` file stays at
`manifest_version: "1.0.0"` but gained v1.2 demonstration entries
(`evidence_cap` on gemini in `cli_capability_matrix`; one-entry
`review_rounds[]`; one-entry `cross_provider_adversarial_passes[]`
+ matching verdict-presence gate) — these are grandfathered for
pre-v1.2 manifests by `verify-p3.sh` and are there only to show the
shape v1.2 adopters use. The v1.0.0 walkthrough
(`examples/walkthrough-mini-deliverable.md`) is byte-unchanged.

Source evidence: merged via evidence-weight priority from
`docs/v1.2-build-plan.md`. Cross-run findings (both retros concur) get
must-ship; single-retro findings get should-ship unless
coherence-critical.

**Must-ship shipped (cross-run consensus).**

| Item | Summary | Files |
|------|---------|-------|
| 1.1 | Adversarial-family MUST-differ-provider invariant. Provider = first hyphen-delimited segment of family name (`claude-opus` + `claude-sonnet` share `claude`). Same-provider adversarial is advisory-only; escape hatch via `gate_prerequisites` id prefix `G-xprov-adv-<phase>`. v1.2+ manifests only; v1.0/1.1/1.1.1 grandfathered. | `framework.md` § P3, `templates/05-review-board-adversarial.md`, `scripts/verify-p3.sh` |
| 1.2 | `scripts/verify-d6-gate.sh` (new) — machine-readable D.6 gate-table parser. Template 07 output schema updated with `Evidence class` column + allowed tag set (test-pass, file-exists, grep-empty, grep-match, count-eq, count-gte, command-exit-0, command-exit-nonzero, orchestrator-preflight). `verify-all.sh` runs the script against `examples/d6-gate-fixture.md` as a regression. | `templates/07-final-approval-gate.md`, `scripts/verify-d6-gate.sh`, `playbook.md` § D.6 |
| 1.3 | Circuit-breaker preserved-blocker-ID carry-forward. Schema adds optional `review_rounds[]`; Template 06 emits `preserved_blocker_ids` in frontmatter; `scripts/verify-circuit-breaker.sh` (new) reports per-phase CB fire (ID overlap) vs quiescent (new IDs). | `manifest/deliverable-manifest.schema.yaml`, `templates/06-meta-consolidator.md`, `scripts/verify-circuit-breaker.sh`, `examples/cb-fixture-*.yaml` |
| 1.4 | Template 06 CB escalation-record + new-vs-recurring judgment prose (orchestrator-authored override for false CB fires). | `templates/06-meta-consolidator.md` |
| 2.1 | `scripts/verify-adopter.sh` (new) — unified adopter-CI entrypoint; `--manifest <path>` flag propagated to `verify-schema.sh`, `verify-p3.sh`, `verify-gate-categories.sh`, `verify-artifact-paths.sh`. | `scripts/verify-adopter.sh`, 4 verify-\*.sh scripts, `README.md` |
| 2.2 | Template 16 P5-style divergent-reviewer consolidation (blocker deltas → BUG/STRUCTURAL/COSMETIC priority → consolidated verdict matrix). Single-variant only; cross-variant deferred to v1.3. | `templates/16-proposal-review.md` |

**Should-ship shipped.**

| Item | Summary |
|------|---------|
| 3.1 | `<CLI_CODEX_MODEL?>` token + `verify-tokens.sh --probe-codex-model` preflight. |
| 3.2 | `cli_capability_matrix[].evidence_cap` — declarative per-family evidence ceiling; Template 06 auto-downgrades over-cap claims. |
| 3.3 | Canonical loader-swap verification pattern in Template 15 (`git show <pre>:<path>` → pytest swap). |
| 3.4 | Template 06 preserve/downgrade metrics block (per-family counts, evidence cap column). |
| 3.5 | Adoption doc v2: README § Adopter onboarding rewritten; `examples/day-one.sh` (new) bootstrap script; `<MANIFEST_DIR>` token; per-language scope-lock starting points (Python / TS / Go). |
| 3.6 | Orchestrator consolidation fast-path on unanimous non-conflicting rounds (playbook § Review board + Template 06). |
| 3.7 | Codex adversarial targeted-prompt pattern (Template 05): sparingly-read file list + pre-declared failure categories + classified output. |
| 3.8 | Contract enumeration checklist (Template 12 § 11) + B.1/D.2 `yq` preflight (Template 02). |
| 3.9 | Role-boundary tightening on Templates 03 / 04 / 19 (enumeration audit → Alignment; scope compliance → mechanical gate; Product stays on UX). |

**Nice-to-have shipped.**

| Item | Summary |
|------|---------|
| 4.1 | `<MERGE_WORKSPACE?>` token + workspace / worktree / merge-workspace clarifier (tokens.md). |
| 4.2 | `examples/walkthrough-triage.md` + `examples/walkthrough-validation-run.md` micro-walkthroughs (closes v1.1.0 PEER-SF2 deferral). |

**Deferred to v1.3 or later.**

- Phase 4.3 ADV-SF5 — `<USER_FACING>` / `<PRODUCT_VERDICT_PATH>`
  token↔manifest mechanical linkage re-deferred to the v2 generator
  (substitution-layer work; adopter friction did not surface in
  folio.love v1.1 slices).
- Cross-variant Pre-A proposal consolidation (Template 16b) — user
  decision 2026-04-16.
- Folio.love-parked items: B-1 (scope-audit pre-phase), B-4
  (stdout-worker adapter), B-6 (`<SCOPE_BASE_COMMIT>`), B-7
  (regression_guards inherits-from), C-3 (rate-limit observability),
  C-6 (Pre-A posture suffix), C-7 (severity-aware CB — superseded by
  1.3 mechanical CB), C-8 (partial-closure state), C-10 (Template 12
  planner's findings), C-11 (forbidden-path glob negation), C-14
  (D.4 fix-summary line-citation regen), ADV-SF-003 (mechanical B.3
  cardinality re-baseline beyond B-5 prose norm).

Friction surfaced during v1.2 build (details in
`docs/retros/v1.2-build-retro.md`) promoted to v1.3 should-fix:
- #11 pseudo-token scanner false positives (3rd recurrence).
- #13 shellcheck not in conformance suite.
- #14 `yq` dependency introduced implicitly by 3.8 preflight.

Conformance suite: 10/10 green throughout the build (8 from v1.0/1.1
+ `verify-d6-gate.sh` fixture regression + `verify-circuit-breaker.sh`
on both example manifests).

## v1.1.1 — Released 2026-04-16 (PR #7, merge `4dfa01f`)

Five bug fixes cherry-picked from folio.love's first production adoption
of v1.1.0. Canonical 2-family review-board verdict: **Approve** at
`review-board/v1.1.1-spec-verdict.md`; Gemini reviewer-of-reviewer
**Concur** at `review-board/v1.1.1-gemini-audit.md`. Patch-release
policy (light-touch 2-family board); full 3-family board reserved for
v1.2.

**Non-goals held.** No breaking schema changes, no schema renames, no new
templates, no token removals. Existing templates and scripts receive
patch-level normative clarifications only. v1.0.0 and v1.1.0 manifests
remain valid under v1.1.1.

Source: cherry-picked from `folio.love#51` merge `ab4bc2735660`. Five
fixes originated in folio.love's first production adoption (5 slices,
findings F-001..F-046).

Shipped:

| # | Fix | File(s) | Friction |
|---|-----|---------|----------|
| C-1 | `id` regex accepts dots as component separators (`^[a-z][a-z0-9]*([.-][a-z0-9]+)*$`) so adopters may embed semver fragments (e.g., `my-thing-v0.6.4`). Rejects pathological forms (`x..y`, `x.`, `x.-y`). `slug` stays dot-free. | `manifest/deliverable-manifest.schema.yaml` | F-011 |
| C-2 | `verify-tokens.sh` suppresses the "defined but not referenced" warning for tokens tagged orchestrator-only. `tokens.md` gains a dedicated "Orchestrator-only tokens" section listing `<DELIVERABLE_SLUG>`, `<META_CONSOLIDATOR_FAMILY>`, `<MODEL_ASSIGNMENTS>`, `<PR_TITLE_PATTERN>`, `<REPO_URL>`, `<STATIC_CHECKS>`. | `scripts/verify-tokens.sh`, `tokens.md` | F-009 |
| C-4 | Archive ordering documented: `<DOC_INDEX_ARCHIVE?>` runs as the final step **after** the Phase E retrospective is committed, not before. Prevents the archive entry from missing the retrospective itself. | `templates/08-retrospective.md`, `tokens.md` | F-004 |
| C-5 | `verify-schema.sh` fails hard (exit 1) when `check-jsonschema` is absent — silent-skip (exit 2) was masking real schema failures because "validator missing" looked identical to "validation passed". `README.md` updated to mark the dependency as required. | `scripts/verify-schema.sh`, `scripts/verify-all.sh`, `README.md` | F-005 |
| B-5 | Cardinality re-baseline at B.3 is now a normative meta-consolidator step. Manifest `cardinality_assertions` are drafted before Phase A; Phase A often narrows scope, leaving stale assertions that surface as false D.6 failures. `templates/06-meta-consolidator.md` prescribes the re-baseline; `playbook.md` cross-references it in the review-board section. | `templates/06-meta-consolidator.md`, `playbook.md` | F-026, F-027 |

Conformance suite: 8/8 green (`scripts/verify-all.sh`).

## v1.1.0 — Released 2026-04-15 (PR #4, merge `2ec49e7`)

Canonical 3-family review-board verdict: **Approve** (commit `6bde749`,
`review-board/v1.1.0-spec-verdict.md`). All preserved blockers across
Claude + Codex + Gemini closed prior to meta-consolidation; conformance
suite 8/8 green; backward-compat regression guards intact.

Four additive scope items per `ROADMAP.md` plus Apache 2.0 licensing.
All additions are opt-in; v1.0.0 manifests, templates, and workflows
function unchanged. `scripts/verify-schema.sh` mechanically confirms
backward compat by validating both the v1.0.0 example and the v1.1
user-facing example against the v1.1 schema.

Shipped:

- **Proposal Review pre-phase** (`templates/16-proposal-review.md`).
  Playbook §13-aligned 2-lens analysis (Product + Technical) in a
  single consolidated session. Verdict set: `Proceed to Phase A |
  Revise and re-review | Split into multiple proposals | Abandon
  direction`. Pre-A carve-out from P3 added to `framework.md`.
- **Triage pre-phase variant** (`templates/17-triage.md`). Playbook
  §12-aligned 3-lens classification; per-finding dispositions
  `In-Scope | In-Scope + fast-patch | Deferred | Rejected`. Overall
  exit includes `Proceed to Phase C-direct` fast-patch route
  (generator-spec invariant 17).
- **Validation Run pre-phase variant**
  (`templates/18-validation-run.md`). Playbook §15.3 (Validation/Observation Runs) aligned
  observation protocol over deployed code; mandatory `direct-run`
  or `orchestrator-preflight` evidence. Verdicts:
  `Run clean — proceed to A | Run inconclusive — re-run with revised
  plan | Run exposed defect — escalate to hotfix or incident`.
- **Product lens** (`templates/19-review-board-product.md`). Optional
  fourth reviewer on Phases B.1 / B.2 / D.2 when `user_facing: true`.
  Structural twin of `03-review-board-peer.md`; mandatory stance
  ports playbook §13.4 preamble verbatim. v1.1 extension documented
  in `framework.md § Compatibility`: playbook scopes Product to
  Proposal Review; this extension widens Product to Phase B / D for
  user-facing deliverables. Rationale: user-facing regressions
  surface at code time, and the 3-lens board does not have a
  designated user-impact voice.
- **Meta-consolidator** (`templates/06-meta-consolidator.md`) gains
  conditional 4-verdict intake: three rows when `user_facing: false`
  (v1.0.0 behavior unchanged); four rows when `user_facing: true`,
  with the Product verdict as the fourth. Additive patch — default
  path is prose-unchanged. Missing Product verdict on user-facing
  phases is a halt.
- **Schema** (`manifest/deliverable-manifest.schema.yaml`): backward-
  compatible additions. `manifest_version` enum widens to include
  `1.1.0`. `phase_id` enum gains `-A.proposal`, `-A.triage`,
  `-A.validation`. `role_label` enum gains `product`,
  `proposal-reviewer`, `triage-author`, `validation-run-author`.
  Top-level `user_facing: bool` (default `false`) and optional
  `pre_a` block. New optional `artifacts.product_verdict`,
  `proposal_verdict`, `triage_report`, `validation_run_report`.
- **Generator-spec** (`manifest/generator-spec.md`): invariants
  15-17 added (Product presence on user-facing phases; pre-A exit
  declaration; pre-A-variant coherence including fast-patch
  routing). Versioning coupling accepts both `1.0.0` and `1.1.0`.
- **Conformance suite** (`scripts/`). `verify-p3.sh` extended with
  a user-facing branch: asserts `product` role presence on
  B.1 / B.2 / D.2 when `user_facing: true`; aggregates across
  multiple model-assignment entries per phase (supports same-family-
  separate-session per P10). New `verify-pre-a.sh` validates
  `pre_a` block coherence statically. `verify-all.sh` picks up the
  new script. `verify-schema.sh` now validates both example
  manifests.
- **Examples** (`examples/walkthrough-user-facing.md`): supplements
  the currency-converter walkthrough with a user-facing scenario
  (notification-preferences settings UI) demonstrating
  pre-A.proposal Round 2 convergence, 4-lens review boards, 4-row
  meta-consolidation, and same-family-separate-session dispatch.
- **Example manifest** (`manifest/example-user-facing-manifest.yaml`):
  v1.1-shape manifest for the notification-preferences walkthrough;
  validates against the schema. Demonstrates `user_facing: true`,
  `pre_a` block, separate Product sessions.
- **License** (`LICENSE`): Apache 2.0 at bundle root. README §
  License provides downstream-adoption pointer.
- **Doctrine annex** (`docs/v1.1-doctrine-decisions.md`): records
  the four doctrine decisions that shaped v1.1 execution (Template
  18 = Validation Run per playbook §15.3; Template 16 verdict
  labels per playbook §13.5; P3 user-facing extension with
  same-family-separate-session; walkthrough supplement). Non-
  normative.

Doctrine & playbook updates that support the above:

- `framework.md § Roles` gains Worker (Product) plus three pre-A
  worker roles (Proposal Reviewer, Triage Author, Validation-Run
  Author).
- `framework.md § Phase state machine` documents pre-A variants
  and their exit paths.
- `framework.md § P3` gains explicit pre-A carve-out and
  user-facing extension paragraphs.
- `framework.md § Artifact contracts` adds Product verdict, proposal
  review verdict, triage report, and validation run report rows.
- `framework.md § Compatibility` flips Proposal Review, Product lens,
  Triage, and Validation Run from "Deferred to v1.1" to "Shipped in
  v1.1" and adds the v1.1 extension note for the Product lens scope.
- `framework.md § Template frontmatter metadata keys` extends the
  `lens` enum to include `product`.
- `playbook.md` Entry-points table gains three pre-A rows.
  `playbook.md` Review board section gains a user-facing addendum.
  New subsections "When the Product lens applies" and "Pre-A
  entry-point selection" land. Known-limits section updated to v1.1.
- `tokens.md` Category 6 (Review board) gains `<USER_FACING?>` and
  `<PRODUCT_VERDICT_PATH?>`. New Category 13 (Pre-A variants) lists
  `<PROPOSAL_DOC_PATH>`, `<TRIAGE_INPUT_PATH>`,
  `<VALIDATION_RUN_INPUT_PATH>`, `<VALIDATION_RUN_BUDGET?>`.
- `templates/01-worker-session-contract.md` halt-catalog gains
  entries for proposal-reviewer, triage-author, validation-run-
  author, and product reviewer.

No git tag is created in this repo (tags reserved for a future
extracted project per `ROADMAP.md`).

## v1.0.0 — Released 2026-04-15 (PR #3, merge `1a1d9e5`)

Initial extraction, revised against the LLM review board's v1.0.0
verdict (7 blockers + 11 should-fix). Derived from an internal
four-phase playbook and a multi-model orchestration report. Contains:

- `framework.md` with 12 numbered doctrine principles (P3 strict ≥3
  non-author families; no degraded modes).
- 16 meta-prompt templates covering orchestrator, worker contract,
  phase dispatch, three-lens review board (§9.3-shaped scaffolding),
  meta-consolidation, final-approval gate, retrospective, incident
  postmortem, infra bootstrap, continuation, spec author,
  implementation author, fix-summary author, and verifier.
- `tokens.md` with a normative Grammar section (no pseudo-computed
  tokens, frontmatter-coverage invariant, optional/list rendering
  rules).
- `manifest/deliverable-manifest.schema.yaml` with phase_id and
  role_label enums, expectation grammar, canonical/family verdict path
  split, category-based gate minimums.
- `manifest/example-manifest.yaml` validates against the schema;
  4-family configuration satisfies strict P3.
- `manifest/generator-spec.md` with 14 invariants, each mapped to a
  `scripts/verify-*.sh` script.
- `scripts/verify-all.sh` conformance suite: schema, tokens,
  frontmatter, P3, gate-categories, portability.
- `examples/walkthrough-mini-deliverable.md` dogfoods the bundle
  end-to-end with 4 families and strict P3.
- `PROVENANCE.md` distinguishes normative from non-normative files;
  `review-board/` and `docs/v1-build-plan.md` are provenance only.

Breaking changes to any template contract or to the manifest schema
will bump the major version and move the bundle to `llm-dev-v2/`.
