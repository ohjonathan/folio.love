---
id: playbook
version: 1.0.0
role: operator-guide
audience: [human-operator, orchestrator]
---

# Playbook — How to Run the Framework

This is the operator-facing guide. If you are the orchestrator LLM, you
primarily read `00-orchestrator-runbook.md`; this playbook is the human's
wiring map and the failure-mode catalog. Read it once end to end before
your first deliverable.

---

## 10-minute adoption

1. Copy `frameworks/llm-dev-v1/` into your repo (or git-submodule it).
2. Copy `tokens.md` to `tokens.local.md`. Fill in every "Example fill"
   column with your project's real values. Commit it.
3. Read `framework.md`. It's short. Principles P1–P12 are what your
   orchestrator and workers enforce.
4. Pick your starting point (next section).
5. Dispatch.

---

## Entry points — which template do I start from?

| Situation                                             | Start here                                  |
|------------------------------------------------------|---------------------------------------------|
| New direction / approach to validate before specifying | `16-proposal-review.md` (pre-A.proposal)    |
| Pile of findings / backlog to triage before specifying | `17-triage.md` (pre-A.triage)               |
| Deployed code to observe under a real-world run        | `18-validation-run.md` (pre-A.validation)   |
| New deliverable, nothing written yet                  | Draft a manifest (see `manifest/example-manifest.yaml`), then dispatch via `02-phase-dispatch-handoff.md` for phase A |
| Manifest already drafted, need to run a phase         | `02-phase-dispatch-handoff.md` — the orchestrator wraps it around the role template |
| A worker halted mid-phase                             | `11-continuation-prompt.md`                 |
| Need a review board on an artifact someone else wrote | `03`, `04`, `05` (+ `19` for user-facing) in parallel, then `06` to consolidate |
| Final sign-off before merge                           | `07-final-approval-gate.md`                 |
| Post-merge learnings                                  | `08-retrospective.md`                       |
| Incident in tooling / infra during a run              | `09-incident-postmortem.md`                 |
| Setting up the control-plane host                     | `10-infra-bootstrap.md`                     |

---

## Composition — how templates stack

Every worker dispatch is a single prompt composed of four layers:

```
┌─────────────────────────────────────────────────────────┐
│ Dispatch preamble (from 02)                              │
│   ┌─────────────────────────────────────────────────────┐│
│   │ Worker session contract (from 01, inlined verbatim) ││
│   │   ┌─────────────────────────────────────────────────┘│
│   │   │ Role-specific wrapping (03–11)                    │
│   │   │   - Role definition                               │
│   │   │   - Lens / stance                                 │
│   │   │   - Output schema                                 │
│   │   │   - Role halt conditions                          │
│   │   └───────────────────────────────────────────────────┘
│   └─────────────────────────────────────────────────────┘
│ Runtime facts (branch, worktree, CLI drift, preflight)   │
└─────────────────────────────────────────────────────────┘
```

The orchestrator (loaded with `00-orchestrator-runbook.md`) does this
composition per dispatch. In v1 by hand; in v2 the manifest generator
emits each composed prompt.

---

## Running a phase — orchestrator's fixed loop

1. Read the tracker row for the current phase.
2. Verify exit criteria for the **previous** phase are met.
3. Set up worktree + branch for the **current** phase.
4. Compose the dispatch (preamble + contract + wrapping).
5. Invoke the worker CLI. Wait for final report or halt report.
6. Run the phase's gate validation commands (`direct-run` evidence).
7. Write the tracker row for the phase outcome.
8. Advance, loop, or halt.

The orchestrator never authors the deliverable. If step 4 requires the
orchestrator to write the artifact's content, the deliverable has collapsed
into orchestration (P1 violation) — halt and escalate.

---

## Review board — strict three-lens composition

v1 requires **at least four model families configured**: one author family
plus three distinct non-author families for every review board. No
degraded modes — no "skip a lens", no "double-role same family", no
"single-family" fallback. If only three families are available, one of
them can be split into a second variant (e.g., `claude-opus` +
`claude-sonnet`) so long as the variants are independent CLI invocations.
If fewer than four distinct families/variants can be configured, v1 is
not the right tool for the project.

The `manifest/deliverable-manifest.schema.yaml` invariant rejects
`model_assignments` entries for phases `B` and `D.2` that do not satisfy
these constraints. The orchestrator confirms the constraint at dispatch
time and halts on failure.

**User-facing addendum (v1.1).** When the manifest declares
`user_facing: true`, Phase B.1 / B.2 / D.2 boards add a Product reviewer
(Template `19`). The Product family may overlap one of the three engineering
families, provided the Product review runs in a separate worker session
under P10. `verify-p3.sh` enforces both the 3-engineering-family floor AND
the Product-presence requirement on user-facing deliverables. See
`framework.md` § P3 for the full rule.

## When the Product lens applies

Trigger: the artifact touches a **user-facing surface**. Examples:

- UI copy, error messages, empty-state strings
- UX flows (step count, cognitive load, failure visibility)
- Public API signatures that external users compose against
- Pricing or billing surfaces (including free-tier bounds)
- Marketing claims, landing-page promises, onboarding copy
- Accessibility surfaces (contrast, keyboard nav, screen-reader hints,
  localization hooks)

Product review is **not** applicable for internal-only code (build scripts,
test harnesses, CI glue, infra) unless that code produces artifacts the
user will read. When unsure, mark `user_facing: true` — an unused Product
reviewer is cheap; a user-facing regression caught post-ship is not.

## Pre-A entry-point selection

Pick a pre-A variant instead of entering Phase 0 directly when:

- **Proposal Review (`-A.proposal`, Template `16`)** — you have an approach
  to validate, not a pile of findings. Multiple proposed directions; the
  team needs to converge before committing to a spec. Verdict set: Proceed
  to A / Revise / Split / Abandon. Per playbook §13, this uses a 2-reviewer
  board (Adversarial+Product, Alignment+Technical); strict P3 does not
  apply (see `framework.md` § P3 pre-A carve-out).

- **Triage (`-A.triage`, Template `17`)** — an audit, bug report, or
  discovery phase surfaced multiple findings that need categorization before
  a release. Each finding is classified In-Scope / Deferred / Rejected. The
  board is the standard 3-lens (Peer / Alignment / Adversarial); P3 holds.
  Fast-patch branch: a triage verdict with only trivial findings may jump
  straight to C-direct (fix + regression test, skipping A and B) —
  generator-spec invariant 17 enforces this.

- **Validation Run (`-A.validation`, Template `18`)** — there is deployed
  or runnable code and you need a structured observation report (field
  test, performance benchmark, corpus run, pre-release acceptance). Per
  playbook §15.3 Validation/Observation Runs, this is a gate protocol, not a review board; no P3
  floor. Verdict set: Run clean (proceed to A) / Run inconclusive (re-run) /
  Run exposed defect (escalate to hotfix or incident).

If none of the above applies, enter at Phase 0 as before.

## Halt circuit breaker

If a worker halts three times on the same
`(deliverable, phase, role, family)` tuple, the orchestrator must
escalate — do not dispatch a fourth time. Escalation paths:

- Scope-violation loops → return to phase 0 (re-scope the manifest).
- Capability-mismatch loops → reassign to a different family.
- Spec-defect loops → return to phase A with a spec-update worker.
- Framework-defect loops → record the defect against the bundle version
  and stop; do not patch templates from an in-flight deliverable.

This implements the source playbook's one-revision cap.

## Merge safety (P8 clarification)

For the final merge, use a **fresh non-local clone** (not a worktree).
Worktrees share the parent clone's `.git`; if the origin state is
poisoned or tampered with, a worktree inherits the poison. For routine
per-phase dispatch, a worktree remains acceptable. The final-merge step
alone requires the fresh clone.

---

## Failure-mode catalog (observed → framework remediation)

| Failure mode                                                   | What goes wrong                                     | Framework remediation                                                              |
|---------------------------------------------------------------|-----------------------------------------------------|------------------------------------------------------------------------------------|
| **Hardcoded smoke assertions drift**                          | Copied prompts carry stale cardinality (`len==16` when actual is 64) | P12 + manifest is source of truth; generator (v2) substitutes assertions from manifest |
| **Tool CLI drifts during a run**                              | Docs say `tool health`; CLI now exposes only `tool doctor`  | Dispatch preamble's "CLI drift notes" captures live divergence; orchestrator substitutes in `<DOC_INDEX_TOOL>` calls |
| **Workers cannot execute shell / git / tests**                | Worker claims a result it cannot verify              | P2 evidence labels (`direct-run` vs `static-inspection`); orchestrator runs gates and labels `orchestrator-preflight` |
| **Generated files conflict on merge**                         | Context maps, lockfiles, indexes regenerated per branch | P7: regenerate from target; halt only on non-generated conflict                    |
| **Tracker ownership violations**                              | Worker edits an orchestrator-only row                | P11 + tracker has explicit `owner` column; orchestrator reverts unauthorized writes |
| **Approvals without evidence**                                | "Looks good" with no file:line                        | P5 + meta-consolidator downgrades unsupported blockers to should-fix               |
| **Scope creep**                                               | Worker edits `migrations/` while doing `src/currency/` | P6 + dispatch preamble inlines no-touch paths; worker halts on no-touch violation  |
| **Stale identifiers in copied prompts**                       | Phase / deliverable names left over from a prior run  | P12 + v2 generator emits per-deliverable prompts from a single manifest            |
| **Final approval is a vibe**                                  | "Overall looks good" verdict without checklist        | P9 + `07-final-approval-gate.md` is a yes/no table; one `no` fails                 |
| **Role fatigue**                                              | One session carries Peer AND Adversarial and becomes neither | P10 one-role-per-session; contract identity block names the single role            |
| **Author family reviews its own artifact**                    | Model bias blind spot                                 | P3 + manifest generator rejects assignments where author family appears as reviewer in the same phase |
| **Worker halts because of missing tooling**                   | E.g., no `rg` on the worker host                      | Halt classification `capability-mismatch` → orchestrator reassigns or supplies preflight |

---

## Guardrails that consistently paid off

- **Evidence labels on every claim.** Cheap to require; makes
  consolidation mechanical.
- **Scope lock as runnable asserts.** `rg` patterns with expected exit
  codes beat prose policies.
- **Canonical artifact protection.** Only the meta-consolidator writes the
  unsuffixed verdict. No race, no overwrite, clean audit.
- **No-fast-forward merges.** Branch history preserves the full review
  trail, including downgraded blockers.
- **Structured final-approval gate.** A `no` on any row forces a specific
  remediation, not a general "do better."

---

## When to skip v2 and stay on v1

The manifest generator (v2) is worth building when you run the framework
on more than a handful of deliverables per quarter and the prompt-cloning
cost becomes real. For a single deliverable or a one-off experiment, hand-
composing prompts from the templates is fine. v1 is usable as-is; v2 is
an ergonomic upgrade, not a correctness upgrade.

---

## Known limits of v1.1

- Requires at least four model-family CLIs (one author + three non-author
  reviewers). Projects with fewer cannot use v1.x; there are no degraded
  modes. See README "Prerequisites" for the exact rule. User-facing
  deliverables may reuse one of those four families as the Product reviewer
  in a separate P10 session (no raised floor).
- Manifest generator is spec-only; hand-composition is the v1 workflow.
  Implementation ships in v2 (see `ROADMAP.md` and
  `manifest/generator-spec.md`).
- The `infra-bootstrap` template is opt-in and intentionally
  hardware-agnostic; project-specific infra details live in your local
  `tokens.local.md`, not the template body.
- Pre-A Validation Run (Template `18`) observes a run; it does not *drive*
  one. Workers that need to execute deployed code depend on the orchestrator
  (or host-project CI) to produce the run; the template consumes the run's
  output.

---

## Review board for the framework itself

Before declaring v1.0.0 stable, run the framework on itself:

1. Treat the bundle as a deliverable. Manifest it.
2. Dispatch a three-lens review board across the core artifacts
   (`framework.md`, every template, `generator-spec.md`).
3. Meta-consolidate. Fix blockers. Bump to v1.0.0.

This is the intended first use of the framework in the host project.
