---
id: walkthrough-currency-converter
version: 1.0.0
role: worked-example
---

# Walkthrough: The `currency-converter` Mini-Deliverable

An end-to-end mental walkthrough of the framework on a toy deliverable.
It uses the manifest at `manifest/example-manifest.yaml` and references
every template in the bundle. If a step cannot be completed with the
templates provided, the framework has a gap — the walkthrough is a
dogfood check.

**Scenario.** A project wants a pure-Python `currency-converter` module
with a 1-function public API (`convert`), a fixed 20-entry ISO-4217 table
(`CURRENCIES`), and no network I/O.

**Four model families are configured** (per manifest + strict P3):

| Family           | shell | git | tests | doc index | Role in this deliverable           |
|------------------|:-----:|:---:|:-----:|:---------:|------------------------------------|
| `claude-opus`    |  ✓    |  ✓  |  ✓    |    ✓     | Author (A, C, D.4)                  |
| `claude-sonnet`  |  ✓    |  ✓  |  ✓    |    ✓     | Reviewer and verifier (non-author)  |
| `codex`          |  ✓    |  ✓  |  ✓    |    ✓     | Reviewer, meta-consolidator, gate   |
| `gemini`         |  —    |  —  |  —    |    ✓     | Reviewer (doc-only, advisory verifier), retro |

With strict P3, every review board for B.1 and D.2 uses exactly the
three non-author families. The author family (`claude-opus`) never
reviews its own artifact.

---

## Phase 0 — Scoping and manifest authoring

A human operator (or a scoping LLM) drafts the manifest at
`manifest/example-manifest.yaml`. Key commitments:

- **Allowed paths:** `src/currency/`, `tests/test_currency.py`.
- **Forbidden symbols:** `requests.`, `httpx.`, `import asyncio` — the
  module must be synchronous and dependency-free.
- **Cardinality:** table has exactly 20 entries; public API exports
  `convert` and `CURRENCIES`.
- **Gate prerequisites:** 10 entries spanning the 6 mandatory categories
  (test, scope, cardinality, verdict-presence, blocker-closure, branch),
  all self-contained commands.

The operator validates the manifest:

```bash
bash scripts/verify-schema.sh    # manifest conforms to schema
bash scripts/verify-p3.sh        # review boards have ≥3 non-author families
bash scripts/verify-gate-categories.sh  # gate covers all 6 categories
```

---

## Phase A — Spec authoring (template 12)

The orchestrator (loaded with `00-orchestrator-runbook.md`) dispatches
`claude-opus` via `02-phase-dispatch-handoff.md` wrapped around
`12-spec-author.md`.

The worker produces `docs/specs/currency-converter-spec.md` with the ten
mandatory sections: Overview, Scope, Dependencies, Technical Design,
Open Questions, Test Strategy, Migration/Compatibility, Risk Assessment,
Exclusion List, Diagrams. Two text-based diagrams: architecture +
state machine (showing both happy path and error paths).

**Diagram-gate check (A.5).** Every component named in the diagram
appears in the prose, and vice versa. Error paths are in the state
machine, not just the happy path. External dependencies are visually
distinct (e.g., dashed borders) from internal components.

**Orchestrator exit gate (phase A).** Ten sections present; diagrams
and prose agree; open questions resolved or deferred with authority;
A.5 self-review summary block present in the spec's final report.

---

## Phase B.1 — Spec review (templates 03, 04, 05)

The orchestrator dispatches three workers in parallel. Per manifest
assignments:

| Family          | Role         | Template |
|-----------------|--------------|----------|
| `codex`         | Peer         | `03`     |
| `gemini`        | Alignment    | `04`     |
| `claude-sonnet` | Adversarial  | `05`     |

(`claude-opus` is excluded — it authored the spec.)

Each produces a family verdict. Per manifest `artifacts.family_verdict`,
the paths are:

- `docs/reviews/currency-converter-B.1-codex-peer.md`
- `docs/reviews/currency-converter-B.1-gemini-alignment.md`
- `docs/reviews/currency-converter-B.1-claude-sonnet-adversarial.md`

Say `claude-sonnet` (adversarial) raises a blocker with direct-run
evidence and reproduction: "`CURRENCIES` is a module-level list,
exposing it to mutation by callers; the spec claims immutability."
Claude (family, not author) knew where to look.

## Phase B.3 — Meta-consolidation (template 06)

`codex` runs `06-meta-consolidator.md`. Output:
`docs/reviews/currency-converter-B.3-verdict.md` (canonical path
without `<family>` / `<role>` placeholders, per schema invariant 10).

Preserved blocker (evidenced, single-family raised): the mutability
concern. Canonical verdict: **Needs Fixes**.

`claude-opus` (author) reads the canonical verdict, updates the spec:
`CURRENCIES` becomes a frozen tuple-of-tuples; type annotation updated;
Open Questions updated with authority citation (self-override is
recorded as a spec-update pass per `templates/14-fix-summary.md`
structure, even for pre-implementation changes).

Re-run B → Approve.

---

## Phase C — Implementation (template 13)

`claude-opus` implements via `13-implementation-author.md`. Output:
`src/currency/__init__.py` with `CURRENCIES: tuple[tuple[str, float], ...]`
and `def convert(amount: float, src: str, dst: str) -> float`. Tests in
`tests/test_currency.py`.

**Phase C smoke checks** (from manifest):

| Check | Command | Expect |
|-------|---------|--------|
| module imports | `python -c 'import src.currency'` | `exit-0` |
| full test suite | `pytest -xvs tests/test_currency.py` | `exit-0` |

Worker final report declares both pass with `direct-run` evidence,
lists files touched keyed by spec section, and declares zero spec
deviations.

---

## Phase D.2 — Code review (templates 03, 04, 05)

Same three-lens structure, different family mix (manifest rotates
roles so no family holds the same lens across B.1 and D.2 for the
same deliverable):

| Family          | Role         |
|-----------------|--------------|
| `gemini`        | Peer         |
| `claude-sonnet` | Alignment    |
| `codex`         | Adversarial  |

`codex` (adversarial) raises a finding: `convert` silently rounds
returned amounts to 2 decimal places, but the spec says no rounding.
`direct-run` reproduction attached. Blocker.

## Phase D.3 — Consolidation (template 06)

`codex` meta-consolidates. One preserved blocker. Canonical verdict:
**Needs Fixes**.

## Phase D.4 — Fix (template 14)

`claude-opus` runs `14-fix-summary.md`:

1. Writes a regression test asserting `convert(1.0, "USD", "USD") == 1.0`
   (not `0.99999…` or `1.00`).
2. Removes the rounding.
3. Confirms the regression test fails pre-fix and passes post-fix.
4. Runs all smoke + cardinality checks.
5. Declares zero spec deviations (rounding was never in the spec —
   removing it restores compliance).
6. Emits the fix summary at
   `docs/reviews/currency-converter-D.4-fix-summary.md`.

## Phase D.5 — Verification (template 15)

All three non-author families verify:

| Family          | Evidence mode        | Role in verification                                    |
|-----------------|----------------------|---------------------------------------------------------|
| `codex`         | `direct-run`         | Reproduces original failure; runs regression test.      |
| `claude-sonnet` | `direct-run`         | Independent reproduction; confirms fix addresses scope. |
| `gemini`        | `static-inspection`  | Reads diff + fix summary; advisory only (no shell).     |

Per template 15's evidence rule: with `codex` and `claude-sonnet`
contributing `direct-run` evidence, the D.5 phase has the ≥1
non-static-inspection verifier the final-approval gate requires
(template 07). `gemini`'s verdict is archived for transparency but
does not count toward the verdict-presence category.

Regression check (full smoke suite + cardinality assertions) passes
on the post-fix commit.

## Phase D.6 — Final-approval gate (template 07)

`codex` runs `07-final-approval-gate.md` against the 10 prerequisites,
grouped by category:

| # | Category          | Prereq                                                  | Result | Evidence |
|---|-------------------|---------------------------------------------------------|--------|----------|
| G-test-1 | test      | Full test suite passes                                  | yes    | direct-run |
| G-scope-1 | scope     | No forbidden symbols in allowed paths                   | yes    | direct-run |
| G-scope-2 | scope     | No changes outside allowed paths                        | yes    | direct-run |
| G-cardinality-1 | cardinality | Table has exactly 20 entries                      | yes    | direct-run |
| G-verdict-1 | verdict-presence | B.3 canonical verdict exists                   | yes    | direct-run |
| G-verdict-2 | verdict-presence | D.3 canonical verdict exists                   | yes    | direct-run |
| G-verdict-3 | verdict-presence | D.5 verifier artifacts from 3 families exist   | yes    | direct-run |
| G-blocker-1 | blocker-closure | No open blockers in any canonical verdict        | yes    | direct-run |
| G-branch-1 | branch    | Working tree clean                                      | yes    | direct-run |
| G-branch-2 | branch    | Branch behind `main` by 0                              | yes    | direct-run |

All six categories covered, all yes, all `direct-run`. Gate: **PASSED**.

Orchestrator merges per P8: **fresh non-local clone** (not a worktree),
`--no-ff`, push from the fresh clone.

## Phase E — Retrospective (template 08)

`gemini` runs `08-retrospective.md`. Typical learnings:

- Strict P3 prevented the "what lens do we drop?" debate entirely —
  the operator configured 4 families up front and no review board
  decision was needed mid-deliverable.
- `gemini`'s advisory verifier verdict caught a docstring mismatch
  that neither `direct-run` verifier flagged. Advisory verifiers are
  worth keeping in the pool even though they don't satisfy the
  gate on their own.
- The fix-summary template's explicit "no spec deviations declared"
  row forced `claude-opus` to prove compliance, not just claim it.

Retrospective feeds the next deliverable's manifest.

---

## What this walkthrough tests in the framework

| Concern                                                         | Checked by |
|-----------------------------------------------------------------|-----------|
| Every template is reachable from an orchestration path         | All 16 templates referenced above |
| Strict P3 is executable without mid-run doctrine debates       | 4-family manifest; verify-p3.sh |
| Scope lock enforcement end-to-end                              | Cardinality + forbidden symbols + allowed-path diff check |
| Evidence discipline across a no-shell family                   | `gemini` verifier labeled static-inspection; advisory-only per template 07 |
| Meta-consolidator preserves evidenced single-family blocker    | `claude-sonnet`'s mutability blocker in B.1 → B.3 canonical verdict |
| Final-approval gate is structured, not vibes                   | 10-row / 6-category yes/no table; all direct-run |
| Schema validates example manifest mechanically                 | `scripts/verify-schema.sh` |
| Templates survive round-trip substitution                      | `scripts/verify-tokens.sh` + `scripts/verify-frontmatter.sh` |

If a future walkthrough reveals a path that cannot be executed with
only the bundle's templates, that is a framework gap and bumps a patch
version.
