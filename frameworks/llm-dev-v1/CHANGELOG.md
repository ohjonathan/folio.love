# Changelog

All notable changes to the `llm-dev-v1` framework bundle are documented here.
Versioning is bundle-scoped (`llm-dev-vMAJOR.MINOR.PATCH`).

## v1.1.1 — Released 2026-04-16 (PR #TBD, merge `TBD`)

Five bug fixes against v1.1.0's shipped surface — no schema breaking
changes, no new templates, no manifest contract changes. v1.0.0 and v1.1.0
manifests remain valid under v1.1.1. Ships ahead of the host project's
next deliverable so adopters don't re-eat the same friction. Light-touch
2-family review (claude + codex) per patch-release policy; full 3-family
board reserved for v1.2.

Source: `folio.love` first production adoption (5 slices, F-001..F-046).

Shipped:

| # | Fix | File(s) | Friction |
|---|-----|---------|----------|
| C-1 | `id` regex accepts dots as component separators (`^[a-z][a-z0-9]*([.-][a-z0-9]+)*$`) so adopters may embed semver fragments (e.g., `my-thing-v0.6.4`). Rejects pathological forms (`x..y`, `x.`, `x.-y`). `slug` stays dot-free. | `manifest/deliverable-manifest.schema.yaml` | F-011 |
| C-2 | `verify-tokens.sh` suppresses the "defined but not referenced" warning for tokens tagged orchestrator-only. `tokens.md` gains a dedicated "Orchestrator-only tokens" section listing `<DELIVERABLE_SLUG>`, `<META_CONSOLIDATOR_FAMILY>`, `<MODEL_ASSIGNMENTS>`, `<PR_TITLE_PATTERN>`, `<REPO_URL>`, `<STATIC_CHECKS>`. | `scripts/verify-tokens.sh`, `tokens.md` | F-009 |
| C-4 | Archive ordering documented: `<DOC_INDEX_ARCHIVE?>` runs as the final step **after** the Phase E retrospective is committed, not before. Prevents the archive entry from missing the retrospective itself. | `templates/08-retrospective.md`, `tokens.md` | F-004 |
| C-5 | `verify-schema.sh` fails hard (exit 1) when `check-jsonschema` is absent — silent-skip (exit 2) was masking real schema failures because "validator missing" looked identical to "validation passed". `README.md` updated to mark the dependency as required. | `scripts/verify-schema.sh`, `README.md` | F-005 |
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
