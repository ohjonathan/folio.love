# Roadmap

This is a proposed trajectory, not a committed schedule. Every version after
v1.0.0 depends on what the LLM review board and real deliverables teach us.
Retrospectives (template `08-retrospective.md`) feed this file; update here
rather than in a separate tracker.

Versioning is bundle-scoped: `llm-dev-vMAJOR.MINOR.PATCH`. Breaking changes
to any template contract or the manifest schema bump the major and move the
bundle to `frameworks/llm-dev-vN+1/`.

---

## v1.0.0 — Released 2026-04-15

**Status.** Released. Merged via PR #3 at commit `1a1d9e5` on 2026-04-15.
No git tag (tags reserved for a future extracted project).

**Scope as shipped.** The bundle as it existed at v1.0.0 merge: doctrine
(P1-P12), 16 meta-prompt templates, manifest schema + example +
generator-spec, playbook, tokens glossary (9 categories), worked
walkthrough, mechanical conformance suite (7 verify scripts), build-plan
archive, and canonical review-board verdict + response doc + focused
re-review round.

**Exit criteria met.** 3-family review board (Claude + Codex + Gemini)
produced canonical verdict; 7 preserved blockers + 11 should-fixes
closed in D.4; focused re-review surfaced two RR-CODEX blockers (both
closed); subtraction-operator pseudo-token gap patched; final-approval
gate (10 rows / 6 categories) passed.

---

## v1.1.0 — Released 2026-04-15

**Status.** Released via PR #4. Canonical 3-family review-board
verdict: **Approve** (commit `6bde749`, `review-board/v1.1.0-spec-verdict.md`).
No git tag (tags reserved for a future extracted project).

**Scope shipped.**

- **Proposal Review pre-phase** — `templates/16-proposal-review.md`
  implements playbook §13 (2-lens, Product + Technical) with pre-A
  carve-out from strict P3.
- **Triage pre-phase variant** — `templates/17-triage.md` implements
  playbook §12 (3-lens categorization) including the fast-patch route
  via `Proceed to Phase C-direct`.
- **Validation Run pre-phase variant** —
  `templates/18-validation-run.md` implements playbook §15.3 Validation/Observation Runs
  observation protocol over deployed code.
- **Product lens** — `templates/19-review-board-product.md` is a 4th
  reviewer on Phase B.1 / B.2 / D.2 when `user_facing: true`.
- **Apache 2.0 licensing** — `LICENSE` at bundle root.
- **Schema + conformance** — `manifest_version` widens to 1.1.0;
  backward-compatible additions for `user_facing`, `pre_a`,
  `product_verdict`. `verify-p3.sh` extended; `verify-pre-a.sh` added.
- **User-facing example + walkthrough** —
  `examples/walkthrough-user-facing.md` and
  `manifest/example-user-facing-manifest.yaml`.

**Non-goals held.** No manifest-generator implementation (still v2). No
breaking schema changes — v1.0.0 manifests validate under v1.1
unchanged (mechanically verified by `scripts/verify-schema.sh`).

**Exit criteria met.** 3-family review board produced canonical verdict
at `review-board/v1.1.0-spec-verdict.md` (**Approve**, commit
`6bde749`); all preserved blockers closed across Batches A-F with
commit references; CHANGELOG stamped; session archived via
`ontos log -e "v1-1-0-release"`. Three rounds of Codex re-review closed
the last mechanics gap (Codex-7). Same playbook as v1.0.0.

> **Note.** End-to-end template coverage (Phase A author, implementation
> author, fix summary, verifier) and the strict ≥3-family P3 policy
> originally planned for v1.1 shipped in v1.0.0 instead, following the
> LLM review board's verdict on the v1.0.0 draft. v1.1 delivers the
> scope items that were deferred *from* v1.0.0 (Proposal Review,
> Product lens, Triage, Validation Run) plus licensing.

---

## v1.1.1 — Candidate (2026-04-16)

**Status.** Under review as PR #7 (merge SHA `TBD` until the
cross-family canonical verdict reaches Approve). Cherry-picked from
folio.love PR #51 (merge `ab4bc2735660`) — the first production
adopter of v1.1.0 surfaced five backward-compat-safe bug fixes; the
framework maintainer pulled them into the canonical bundle so the two
copies stay byte-equivalent.

**Scope shipped.** Five fixes; patch-level normative clarifications only:

- **C-1** (F-011): `id` regex accepts dot separators for semver
  fragments (`manifest/deliverable-manifest.schema.yaml`). `slug`
  stays dot-free.
- **C-2** (F-009): `verify-tokens.sh` suppresses defined-but-not-used
  warnings for orchestrator-only tokens; `tokens.md` gains a named
  section listing the six affected tokens.
- **C-4** (F-004): Archive ordering — `<DOC_INDEX_ARCHIVE?>` runs after
  the Phase E retrospective is committed. Template 08 adds a normative
  paragraph; `tokens.md` row updated.
- **C-5** (F-005): `verify-schema.sh` hard-fails (exit 1) when
  `check-jsonschema` is absent. Silent-skip looked identical to a
  passing check. README marks the dependency as required.
- **B-5** (F-026, F-027): Cardinality re-baseline at B.3 Approve is
  normative. Template 06 adds a 3-step procedure; `playbook.md`
  cross-references it in the review-board section.

**Non-goals held.** No breaking schema changes, no schema renames, no
new templates, no token removals. Existing templates and scripts
receive patch-level normative clarifications only (Template 06 B.3
cardinality re-baseline; Template 08 archive ordering; verify-schema
exit-semantics; verify-tokens orchestrator-only suppression; `id`
regex widening). v1.0.0 and v1.1.0 example manifests validate under
v1.1.1 unchanged (mechanically confirmed by `scripts/verify-schema.sh`).
`verify-all.sh` remains 8-script / 8 green.

**Exit criteria (pending merge).** 2-family review board (Claude +
Codex) per patch-release policy; Gemini reviewer-of-reviewer audits
the cross-family meta-consolidator. Canonical verdict at
`frameworks/llm-dev-v1/review-board/v1.1.1-spec-verdict.md` upon
Approve. Post-merge stamp replaces TBD PR# and merge SHA; session
archived via `ontos log -e "v1-1-1-release"`.

---

## v1.x — Continuous improvements

**Trigger.** Per-deliverable retrospectives.

**Shape.** Each real deliverable produces a retrospective that may
recommend framework updates. Patch-size changes (typo fixes, clarifications,
new halt-catalog entries) ship as `v1.0.1`, `v1.0.2`, … Feature-size changes
that don't break contracts ship as `v1.2.0`, `v1.3.0`, …

**Likely candidates discovered during v1 authoring but deferred:**

- A token-fill validator script (independent of the full generator).
- A lightweight tracker schema example (currently column-named only).
- Per-language scope-lock patterns (Python / TS / Go) as appendices to
  `framework.md`, not as templates.
- Pattern library for common deliverable shapes: new module, schema
  migration, API endpoint, library-wide refactor.

**Caps.** Stop at `v1.9.x`. If we approach `v1.10`, something is wrong —
either a breaking change is overdue (→ v2) or we're over-elaborating v1.

---

## v2.0.0 — Manifest generator

**Trigger.** Hand-composing prompts for a third deliverable is painful
enough to justify a tool.

**Scope.** Implement `manifest/generator-spec.md` as a real tool. Probable
shape: Python + Jinja2, strict templating, unit-tested against
`manifest/example-manifest.yaml`.

**Deliverables.**

- `tools/manifest-generator/` (or separate repo) with CLI entry point.
- Resolves a manifest + token fill into a full prompt suite, tracker rows,
  branch map, and `validation-plan.sh`.
- Enforces the 9 invariants listed in `generator-spec.md` (model-diversity
  rule P3, author-excluded-from-own-review, orphan-token detection, etc.).
- `--dry-run` mode for substitution preview.

**Why this is a major.** The generator changes how workers are dispatched.
Any project currently hand-composing prompts must migrate its workflow (not
its manifest — the manifest schema is preserved). Templates themselves may
also pick up generator-specific frontmatter fields that older orchestrators
won't parse.

**Non-scope for v2.**

- Running LLM dispatches for you (it emits prompts; orchestrator dispatches).
- CI integration.
- Manifest schema changes.

---

## v3.0.0 — Speculative

**Trigger.** We run the framework across **two or more repos** and
friction from per-repo duplication becomes real. Until then, v3 is a
placeholder and should not be planned for.

**Candidate scope (if the trigger fires).**

- **Cross-repo regression-guard library.** Shared test manifest that any
  project using the framework can inherit from (e.g., "no network calls
  in pure modules," "no secrets in committed files").
- **Standardized tracker tool.** Today the tracker is a markdown table;
  at v3 it might be a sqlite file, a CSV, or an API, with a thin CLI to
  read/write phase rows.
- **Multi-project registry.** A single inventory of manifests across
  repos, used by a dashboard or a scheduling agent.
- **First-class prompt-cache coordination.** If LLM infrastructure exposes
  stable cache keys per template, the generator can warm caches ahead of
  dispatch.

**Default stance:** do not build v3. Solve the concrete friction from two
repos before generalizing.

---

## What is explicitly NOT on the roadmap

- **CLAUDE.md / AGENTS.md auto-activation hooks.** The framework is
  tool-agnostic by design (`framework.md` § "Out of scope"). Projects wire
  activation themselves.
- **Model-specific prompt tuning.** Templates are written to be family-
  portable. If a family needs a tweak, that's a project-local overlay, not
  a framework version.
- **CI/CD pipeline integration.** Orchestrator-driven dispatch assumes a
  human or long-lived agent is present. Pipelines can use the bundle but
  integration wiring is project-local.
- **A GUI.** The framework is a text artifact; any GUI belongs to a
  separate product, not this bundle.

---

## Decision log

How decisions land on this roadmap:

1. Review board or retrospective flags a recommendation.
2. The framework maintainer grades it: `patch`, `minor`, `major`,
   `out-of-scope`.
3. `patch` / `minor` items land in v1.x directly; `major` items queue for
   v2 or v3; `out-of-scope` items are documented above under "What is
   explicitly NOT."
4. Changelog entries cite the retrospective or review that drove the
   change.

This file is updated whenever a version is cut, not continuously.
