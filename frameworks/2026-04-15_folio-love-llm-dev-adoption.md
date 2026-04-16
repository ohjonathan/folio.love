---
id: folio-love-llm-dev-adoption
date: 2026-04-15
role: adoption-handoff
status: ready
---

# `folio.love` Adoption Handoff — LLM Development Framework v1.1

A standalone handoff prompt for the folio.love project's orchestrator
(human or LLM) to bootstrap onto the `llm-dev-v1` framework bundle at
version v1.1.0. This file lives outside the bundle; adoption guidance
is project-specific (johnny-os has folio.love as its first production
adopter) and not part of the normative framework.

## Goal

Stand up the `llm-dev-v1` bundle inside the folio.love repo so that the
first folio.love deliverable can be shipped using the framework. The
first production run is both the first real use of v1.1 and a feedback
source for v1.2.

## Step 1 — Pull the bundle

The bundle lives at `frameworks/llm-dev-v1/` inside the johnny-os
monorepo. Both `git subtree` and `git submodule` operate at the
**repo** level, not the **subdirectory** level — naively running
`git subtree add --prefix=ops/llm-dev-v1 <johnny-os-url> <branch>`
imports the **entire johnny-os repo** under `ops/llm-dev-v1/`, not
just the bundle subtree. Three honest options:

| Approach            | How                                                                                                                   | Updates                                                                                  | When to choose                                                                                       |
|---------------------|-----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| **verbatim copy** (recommended) | `cp -r path/to/johnny-os/frameworks/llm-dev-v1 path/to/folio.love/ops/llm-dev-v1`                       | manual re-copy per upgrade (bundle is ~20 files; cheap)                                  | First deliverable. Simplest mental model. No upstream-tracking machinery to maintain.                |
| **git subtree (split-then-pull)** | (1) In a johnny-os clone: `git subtree split --prefix=frameworks/llm-dev-v1 -b llm-dev-v1-export`. (2) Push that branch to a small mirror repo `johnny-os-llm-dev-v1`. (3) In folio.love: `git subtree add --prefix=ops/llm-dev-v1 <mirror-url> main --squash`. | (1) Re-run split + push when the upstream bundle changes; (2) `git subtree pull` from the mirror. | You want bundle history inside folio.love AND will run multiple deliverables AND can maintain a mirror repo. |
| **git submodule (sparse-checkout)** | `git submodule add --depth=1 <johnny-os-url> ops/_johnny-os-vendor` then in a sparse-checkout config restrict to `frameworks/llm-dev-v1/`. Symlink `ops/llm-dev-v1 → ops/_johnny-os-vendor/frameworks/llm-dev-v1`. | `git submodule update --remote` + sparse-checkout reapply.                               | You want strict commit pinning AND tolerate the vendor-clone overhead AND have a Git that supports sparse-checkout in submodules. |

**Recommended:** verbatim copy for the first folio.love deliverable.
The bundle is ~20 files; manual re-copy on v1.2 is low-friction and
avoids the split-mirror or sparse-checkout machinery while the bundle
matures. Switch to the split-then-pull subtree pattern once folio.love
runs two+ deliverables and the bundle stabilizes — the one-time mirror
setup amortizes by then.

**Pitfall to avoid:** do NOT run `git subtree add --prefix=ops/llm-dev-v1 <johnny-os-url> frameworks/llm-dev-v1.1 --squash`
(or the submodule equivalent) directly against johnny-os without a
split or sparse-checkout. That puts the whole monorepo under
`ops/llm-dev-v1/` — `agents/`, `docs/`, every other framework, etc. —
which is not the bundle adopters want.

**Location inside folio.love:** `ops/llm-dev-v1/` (or another path
the orchestrator picks; the bundle is self-contained, so any path
works).

## Step 2 — Fill `tokens.local.md`

The bundle ships `tokens.md` (the canonical glossary) with "Example
fill" values that are generic. Copy it to `tokens.local.md` and fill
in folio.love specifics:

```bash
cp ops/llm-dev-v1/tokens.md ops/llm-dev-v1/tokens.local.md
# (or `.local.yaml` — matching your preferred fill format)
```

Minimum fills to set before the first deliverable dispatch:

- `<WORKSPACE>` — absolute path to the folio.love repo on the
  orchestrator host.
- `<REPO_URL>` — folio.love's canonical git remote URL.
- `<DEFAULT_BRANCH>` — folio.love's merge-target branch (likely
  `main`).
- `<BRANCH_CONVENTION>` — folio.love's branch naming pattern
  (suggested: `feat/<DELIVERABLE_ID>-<PHASE_ID>-<ROLE>-<FAMILY>`).
- `<DOC_INDEX_TOOL>` / `<DOC_INDEX_ACTIVATION>` /
  `<DOC_INDEX_ARCHIVE>` — if folio.love uses an Ontos-like doc
  indexer; otherwise leave empty.
- `<CLI_CLAUDE>` / `<CLI_CODEX>` / `<CLI_GEMINI>` — the actual CLI
  invocations for each model family CLI installed on the
  orchestrator host.
- `<TEST_COMMAND>` — folio.love's test command. For a Next.js /
  TypeScript stack this is likely `npm test` or `pnpm test` or
  `vitest run`.
- `<PR_TOOL>` — `gh` unless the project uses a different PR tool.

The `verify-tokens.sh` script confirms the template-side tokens are
all defined; it does NOT validate that `tokens.local.md` has real
values rather than placeholders. Operators are responsible for the
local fill's correctness.

## Step 3 — Decide the first deliverable's entry point

folio.love is a user-facing product (the site is the product). Most
deliverables will set `user_facing: true` in their manifest, which
triggers the v1.1 Product-lens extension (see
`ops/llm-dev-v1/framework.md § P3 user-facing extension` after copy).

Choose a pre-A entry per the question below:

| Starting state                                                                | Pre-A entry                      | Template |
|-------------------------------------------------------------------------------|----------------------------------|----------|
| Direction is undecided; multiple candidate approaches on the table            | `-A.proposal`                    | `16-proposal-review.md` |
| Audit / backlog / bug list exists; need to sort scope for this release        | `-A.triage`                      | `17-triage.md` |
| Deployed site exists; want a structured observation before specifying         | `-A.validation`                  | `18-validation-run.md` |
| Scope is known; go directly to manifest                                       | (none — enter Phase 0 / A)       | `02-phase-dispatch-handoff.md` + `12-spec-author.md` |

For folio.love's first deliverable, the likely entry is either
Proposal Review (if the team is converging on a UX direction) or
Validation Run (if there is a hypothesis about current site behavior
worth measuring before changes).

## Step 4 — Draft the first manifest

Two worked examples ship in the bundle:

- `manifest/example-manifest.yaml` — v1.0.0 shape, non-user-facing
  (currency-converter toy). Useful as a minimum-viable manifest.
- `manifest/example-user-facing-manifest.yaml` — v1.1 shape,
  user_facing true, pre_a block populated. This is the closer
  template for a folio.love deliverable.

Draft folio.love's first manifest by copying the user-facing example
and substituting:

- `id:` / `slug:` → the folio.love deliverable id.
- `summary:` → one-sentence description.
- `scope.allowed_paths` / `forbidden_paths` → folio.love's code
  layout (if Next.js / TS: likely `src/app/...` / `src/components/...`
  for the deliverable; `node_modules/`, `.next/`, etc. forbidden).
- `scope.cardinality_assertions` → folio.love-specific invariants
  (e.g., "settings page exports exactly X components", or a
  reasonable cardinality for the deliverable's scope).
- `model_assignments` → folio.love's configured model families.
- `artifacts.*` → folio.love's docs-review paths.
- `gate_prerequisites` → folio.love's test / scope / cardinality /
  verdict-presence / blocker-closure / branch commands.

Validate with:

```bash
cd ops/llm-dev-v1
bash scripts/verify-all.sh
```

All checks should return OK.

## Step 5 — Dispatch the first worker

Once the manifest validates and tokens.local.md is populated, the
orchestrator dispatches the first worker per the bundle's
`00-orchestrator-runbook.md` (v1 is hand-composition — the generator
is v2).

The 10-minute adoption path in `ops/llm-dev-v1/README.md` is the
primary reference; this handoff doc supplements it with folio.love
specifics.

## Step 6 — Feedback loop

folio.love is the first production run of v1.1. Feedback returns to
johnny-os (the framework maintainer's repo) as one of:

- **GitHub issue** on johnny-os tagged `framework:llm-dev-v1.1`.
  Preferred for bug reports, missing halt-catalog entries, or
  template ambiguities.
- **Retrospective doc** at `folio.love/docs/retros/<deliverable>-retro.md`
  (generated by `08-retrospective.md` at Phase E). The maintainer
  reads these during roadmap updates; recommendations graded per the
  ROADMAP "Decision log" section.

Do not patch the bundle inside folio.love without upstreaming the fix
to johnny-os first. A locally-patched bundle diverges from the
canonical version and loses the backward-compat guarantee the
framework ships.

## Known unknowns for v1.2 (feedback targets)

These are candidate improvement areas that the v1.1 review board flagged
or that this handoff anticipates folio.love will hit. If folio.love
confirms any of them as a real friction point, they become v1.2
candidates:

- **Per-language scope-lock appendix for TS/React.** The v1.0.0
  currency-converter example is Python; a TS/React appendix would
  make folio.love's scope setup more straightforward.
- **Pattern library for UI deliverables.** Common shapes (settings
  page, modal flow, CTA flow) as reusable scope-lock + gate-prereq
  starting points.
- **Tracker schema reference.** v1 leaves the tracker column set to
  the operator; a reference layout for UI deliverables would reduce
  first-run friction.

These are NOT in v1.1 scope. They land in v1.2 only if folio.love
feedback confirms the pain.

## Pointer

For everything else, read `ops/llm-dev-v1/README.md` (after copy).
It has the 10-minute adoption path and the verify-suite rationale.
The framework is self-contained; this handoff only provides
folio.love-specific guidance beyond the README.
