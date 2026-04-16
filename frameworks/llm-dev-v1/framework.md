---
id: framework
version: 1.0.0
role: doctrine
audience: [orchestrator, worker, human-operator]
---

# LLM Development Framework — Doctrine

This document defines the invariant principles of the framework. Templates
reference the principles below by number (e.g., "P3 applies"). Keep principles
small, unambiguous, and testable.

The framework runs on two foundational ideas:

- **Model diversity catches what single-model review misses.** Different
  model families produce different risk thresholds, not just more prose.
  The framework requires ≥3 non-author families for every review board
  (P3).
- **Evidence is the currency of consensus.** A verdict without file:line
  citations and reproduction is a preference, not a finding.

---

## Roles

| Role                        | Phase  | Purpose                                                                |
|-----------------------------|--------|------------------------------------------------------------------------|
| **Orchestrator**            | all    | Owns phase state, branch hygiene, worker dispatch, gate validation, tracker. Never authors deliverable artifacts. |
| **Worker (Spec Author)**    | A      | Produces the spec. Template `12`.                                       |
| **Worker (Impl Author)**    | C      | Implements the spec. Template `13`.                                     |
| **Worker (Fix Author)**     | D.4    | Applies fixes from D.3 canonical verdict. Template `14`.                |
| **Worker (Peer)**           | B, D.2 | Reviews for quality: "Is this good?" Template `03`.                     |
| **Worker (Alignment)**      | B, D.2 | Reviews for compliance: "Does this match approved docs?" Template `04`. |
| **Worker (Adversarial)**    | B, D.2 | Reviews for failure: "How does this fail?" Template `05`.               |
| **Worker (Product)**        | B.1, B.2, D.2 (user-facing only) | Reviews for user impact: "Is this the right thing to build / ship?" Template `19`. |
| **Meta-Consolidator**       | B.3, D.3 | Adjudicates family verdicts into a canonical verdict. Template `06`. |
| **Worker (Proposal Reviewer)** | -A.proposal | Pre-A direction review; 2-lens (Adversarial+Product, Alignment+Technical) per playbook §13.4. Template `16`. |
| **Worker (Triage Author)**  | -A.triage | Pre-A backlog triage; 3-lens (Peer, Alignment, Adversarial) per playbook §12.4. Template `17`. |
| **Worker (Validation-Run Author)** | -A.validation | Pre-A observation protocol over deployed code per playbook §15.3 Validation/Observation Runs. Template `18`. |
| **Verifier**                | D.5    | Confirms each D.3 blocker is addressed and no regression. Template `15`. |
| **Final-Approval Gate**     | D.6    | Runs a structured yes/no prerequisite checklist before merge. Template `07`. |
| **Retrospective Author**    | E      | Post-merge orchestration report. Template `08`.                         |
| **Investigator**            | ad hoc | Incident postmortem. Template `09`.                                      |
| **Infra-Bootstrap Worker**  | ad hoc | Control-plane setup. Template `10`.                                      |

A single worker session holds exactly one role. Role fatigue and blind spots
emerge when one session carries more than one. See P10.

---

## Phase state machine

```
┌───────┐   ┌───────────┐   ┌───────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────┐
│ 0 Scope│──▶│ A Spec     │──▶│ B Spec Review │──▶│ C Implement │──▶│ D Code Rev. │──▶│ E Retro │
└───────┘   └───────────┘   └───────────────┘   └─────────────┘   └─────────────┘   └─────────┘
                │                    │                    │                │
                │                    ▼                    │                ▼
                │              Needs-fixes ─────┐         │         Needs-fixes ─────┐
                │                                ▼        │                          ▼
                └─────────── re-scope ◀── re-spec         └─────────── re-implement ◀┘
```

**Pre-A variants (optional).** v1.1 adds three optional entry points that
execute before Phase A when the work is not yet a known-scope deliverable:

```
  New direction to validate   ──▶ -A.proposal   ──▶ A (Proceed) | 0 (Revise) | 0 (Split) | ∅ (Abandon)
  Pile of findings to sort    ──▶ -A.triage     ──▶ A (In-scope work) | C direct (trivial fix) | ∅ (Deferred only)
  Deployed run to observe     ──▶ -A.validation ──▶ A (revised plan) | hotfix/incident | re-run
```

Pre-A variants are optional; a known-scope deliverable enters at Phase 0 as
before. Manifests that declare a `pre_a` block produce the pre-A artifact
before Phase A dispatches (generator-spec invariant 16).

**Entry / exit criteria (summary).** Full exit criteria live in each template.

| Phase           | Entry                                   | Exit                                                       |
|-----------------|-----------------------------------------|------------------------------------------------------------|
| -A.proposal     | New direction or approach to validate    | Proposal decision: Proceed to A / Revise / Split / Abandon |
| -A.triage       | Pile of findings to categorize           | Approved scope: In-Scope / Deferred / Rejected per finding |
| -A.validation   | Deployed code to observe                 | Observation report + run verdict (clean / inconclusive / defect) |
| 0               | New request or roadmap item             | Scope lock: paths, forbidden paths, cardinality, gates     |
| A               | Scope lock (or pre-A exit verdict)       | Spec v1.0 with all mandatory sections + diagrams           |
| B               | Spec v1.0                               | Canonical verdict == "Approve" or escalate to A            |
| C               | Spec vN (approved)                      | Pull request against target branch with worker session log |
| D               | Pull request                            | Canonical verdict + final-approval gate passes → merge     |
| E               | Merged deliverable                      | Retrospective report; learnings fed back to framework      |

Phases B and D both run the three-lens review board (P4). When
`user_facing: true` in the manifest, the Phase B.1 / B.2 / D.2 boards add a
Product reviewer (P3 extension; see P3 below).

---

## Principles

<!-- Each principle cites its source in a provenance comment. Reader-facing prose stays clean. -->

### P1 — Orchestrator / worker separation (anti-collapse)

The orchestrator is forbidden to author deliverable artifacts. Workers are
forbidden to take orchestrator-only actions (merge, tag, close). When a worker
cannot proceed without orchestrator action, it halts and reports.

<!-- Provenance: D2 report §3 anti-collapse stanza -->

### P2 — Evidence discipline

Every worker claim is labeled with one of four evidence classes:

- `direct-run` — the worker executed the check
- `orchestrator-preflight` — the orchestrator executed it and reported the result
- `static-inspection` — derived from reading the artifact, not running it
- `not-run` — the check was not performed

Blocking findings require `direct-run` or `orchestrator-preflight` evidence
with file:line citations and a reproduction. Unsupported claims are downgraded
at consolidation (P5).

<!-- Provenance: D2 report §3 evidence labels; playbook §9.3 role instructions -->

### P3 — Model diversity (strict)

Every review board uses **at least three non-author model families**. The
author family is excluded from reviewing its own artifact in the same phase.
The same family holds no more than one role per phase. Sessions are
single-role (P10). No degraded modes: there is no "skip a lens" or
"double-role" path in v1. If a project has fewer than four model-family
CLIs configured (three reviewers + one author), it cannot use v1.

A **round** is one pass of the full review board on a single artifact
version. A phase may contain multiple rounds. Each round produces exactly
three family verdicts (Peer, Alignment, Adversarial) from three distinct
non-author families, plus one canonical verdict from the meta-consolidator.

**Pre-A carve-out.** P3 applies to review boards on phase-advance artifacts
(Phases B and D). The pre-A variants are scoped differently and do not all
share the strict P3 floor:

- **Proposal Review** (Template `16`, phase `-A.proposal`) uses the 2-reviewer
  configuration from playbook §13.4 (Reviewer 1 = Adversarial + Product
  lens; Reviewer 2 = Alignment + Technical lens). It does not gate a phase
  advance and does not require ≥3 families.
- **Triage** (Template `17`, phase `-A.triage`) uses the standard 3-lens
  board (Peer, Alignment, Adversarial) per playbook §12.4 and satisfies P3
  automatically.
- **Validation Run** (Template `18`, phase `-A.validation`) is an observation
  protocol rather than a review board; it has no P3 floor.

**User-facing extension.** When a deliverable's manifest declares
`user_facing: true`, Phase B.1 / B.2 / D.2 review boards must additionally
include a Product reviewer (Template `19`). The Product family may be the
same as one of the three engineering families, provided the Product review
runs in a separate worker session under P10. This keeps the adoption floor
at four families while adding the user-impact voice for user-facing
deliverables. `verify-p3.sh` enforces the branched check. Adopters who prefer
a strictly-disjoint 5-family composition (1 author + 3 engineering + 1
Product, all distinct families) may configure their manifest that way; v1.1
does not mandate it.

<!-- Provenance: playbook §2 intentional model diversity; v1.0.0 review board verdict §7 B1; v1.1 extension scope per docs/v1.1-doctrine-decisions.md §3 -->

### P4 — Three-lens review

The review board is Peer (quality), Alignment (compliance with approved docs),
and Adversarial (how does this fail). Role instructions are not interchangeable.
Each lens carries a mandatory stance:

- Peer: "Your job is to find problems. If you find none, look harder."
- Alignment: "Deviations from approved documents are issues, not style choices."
- Adversarial: "Your default stance is skeptical. The author rated this
  [RISK LEVEL]. Prove them wrong."

<!-- Provenance: playbook §9.3 literal role instructions -->

### P5 — Evidence-weighted consensus

A blocker raised by a single reviewing family, carrying file:line evidence
and a reproduction, overrides two approvals from the other families.
Consolidation is not arithmetic voting. The meta-consolidator:

- preserves blockers that carry evidence (P2), regardless of family count
- downgrades blockers that do not carry evidence to should-fix
- separates contradictions (workers disagree on facts) from blockers
- separates should-fix findings from merge blockers

<!-- Provenance: D2 report §3 blocker preservation rule -->

### P6 — Scope lock as mechanical guard

Scope is expressed as explicit path allowlists, forbidden-path lists, and
cardinality assertions (e.g., "matrix is 16×4"; "module exports exactly 3
functions"). Scope is enforced by runnable checks (`rg` / grep patterns, count
assertions), not by prose. Scope violations are automatic blockers.

<!-- Provenance: D2 report §3 scope lock, playbook §7 scope section -->

### P7 — Generated-file conflict policy

If only auto-generated files (e.g., context maps, indexes, lockfiles with
deterministic regeneration) conflict during merge: regenerate from the target
branch state. If any non-generated file conflicts: halt and report.

<!-- Provenance: D2 report §3 generated-file conflict policy -->

### P8 — Fresh-clone merge safety

Never merge from a workspace that is not guaranteed clean. Create a fresh
clone or worktree, validate it, merge there, push from there. Use
`--no-ff` so branch history preserves the full review trail.

<!-- Provenance: D2 report §3 merge safety -->

### P9 — Structured final-approval gate

Final approval is a yes/no prerequisite table, not a prose verdict. The
template (`07-final-approval-gate.md`) mandates ≥10 concrete yes/no items
covering tests, scope, canonical artifacts, regression guards, and branch
hygiene. One `no` means the gate fails.

<!-- Provenance: D2 report §3 "final approval not a vibe" -->

### P10 — One role per session

A worker session is bound to exactly one role for exactly one phase. The
session contract (`01-worker-session-contract.md`) names the role in its
identity block. Switching roles mid-session voids the contract and invalidates
the output.

<!-- Provenance: playbook §9 role fatigue; D2 report §3 role ownership -->

### P11 — Tracker ownership

A single tracker (CSV, markdown table, or equivalent) is the source of truth
for phase state. Each row names its owner: orchestrator-only or worker-writable.
Writes outside ownership are reverted. Parallel phases use per-phase rows, not
shared state.

<!-- Provenance: D2 report §3 tracker ownership violations -->

### P12 — Prompts are software

Prompt suites are versioned, reviewed, and validated before dispatch. Copied
prompts inherit stale identifiers, stale smoke checks, and stale scope locks;
prompt-clone hygiene is a first-class requirement. The manifest-driven
generator (see `manifest/generator-spec.md`) exists to eliminate hand-cloning.

<!-- Provenance: D2 report §3 "prompt suites are software artifacts" -->

---

## Artifact contracts

| Artifact            | Produced in | Owner role           | Storage                               |
|---------------------|-------------|----------------------|---------------------------------------|
| Spec vN             | A           | Author               | `<SPEC_DIR>/<DELIVERABLE_ID>-spec.md` |
| Family verdict      | B, D        | Peer/Alignment/Adversarial per family | `<REVIEWS_DIR>/<DELIVERABLE_ID>-<phase>-<family>-<role>.md` |
| Product verdict     | B, D (user-facing only) | Product per family | `<REVIEWS_DIR>/<DELIVERABLE_ID>-<phase>-<family>-product.md` |
| Canonical verdict   | B, D        | Meta-Consolidator    | `<REVIEWS_DIR>/<DELIVERABLE_ID>-<phase>-verdict.md` |
| Fix summary         | B, D        | Author               | `<REVIEWS_DIR>/<DELIVERABLE_ID>-<phase>-fix-summary.md` |
| Final-approval gate | D (final)   | Final-Approval Gate  | `<REVIEWS_DIR>/<DELIVERABLE_ID>-final-approval.md` |
| Retrospective       | E           | Retrospective author | `<RETRO_DIR>/<DELIVERABLE_ID>-retro.md` |
| Incident postmortem | ad hoc      | Investigator         | `<INCIDENTS_DIR>/<DATE>-<slug>.md`    |
| Proposal review verdict | -A.proposal | Proposal Reviewer | `<REVIEWS_DIR>/<DELIVERABLE_ID>-proposal-verdict.md` |
| Triage report       | -A.triage   | Triage Author        | `<REVIEWS_DIR>/<DELIVERABLE_ID>-triage-report.md` |
| Validation run report | -A.validation | Validation-Run Author | `<REVIEWS_DIR>/<DELIVERABLE_ID>-validation-run.md` |

Every artifact carries frontmatter: `id`, `deliverable_id`, `phase`, `role`,
`family`, `evidence_labels_used`, `status`.

### Template frontmatter metadata keys (formal list)

Every template under `templates/` carries frontmatter with these keys:

| Key               | Required | Meaning                                                             |
|-------------------|----------|---------------------------------------------------------------------|
| `id`              | yes      | Template identifier, kebab-case.                                    |
| `version`         | yes      | Semver, tied to bundle version.                                     |
| `role`            | yes      | Always `meta-prompt` for templates in this bundle.                   |
| `audience`        | yes      | One of: `orchestrator`, `worker`, `[orchestrator, worker]`, `human-operator`. |
| `wraps`           | no       | When set, names the template this one composes with (typically `01-worker-session-contract.md`). Enforces composition order. |
| `lens`            | no       | For review-board templates: `peer`, `alignment`, `adversarial`, `product`, `verifier`, `author`. |
| `phase`           | no       | The phase id this template is dispatched in. Used by the generator to pick templates per manifest `model_assignments`. |
| `required_tokens` | yes      | List of `<TOKEN>` forms that must be substituted before dispatch.   |
| `optional_tokens` | no       | List of `<TOKEN?>` forms that may be substituted.                    |
| `depends_on`      | no       | Other bundle files this template expects to be present.             |

---

## Failure modes and framework remediations

| Failure mode (observed)                | Framework remediation                                     |
|----------------------------------------|-----------------------------------------------------------|
| Hardcoded smoke assertions drift       | Manifest-driven prompt suite (P12); cardinality asserted in manifest, never inlined |
| Tool CLI drifts mid-deliverable        | Template references `<DOC_INDEX_TOOL>` and per-phase dispatch preambles carry live CLI facts |
| Workers can't execute shell/git/tests  | `01-worker-session-contract.md` requires evidence-class labels (P2); orchestrator runs gates |
| Generated files conflict on merge      | P7 + merge-safety preflight in `00-orchestrator-runbook.md` |
| Tracker ownership violations           | P11 + explicit per-row ownership column                   |
| Approvals without evidence             | P5 blocker-preservation + meta-consolidator template enforces |
| Scope creep during implementation      | P6 scope lock with runnable `rg` / count guards           |
| Copied prompts carry stale identifiers | P12 + manifest generator spec                             |

---

## Compatibility with source playbook (v1 scope map)

This framework derives from a source LLM-development playbook. Not every
source construct lands in v1. The table below makes the gap explicit.

| Source playbook construct          | v1 status                                          |
|-----------------------------------|----------------------------------------------------|
| Four-phase lifecycle (A / B / C / D) | Shipped (framework.md § Phase state machine)    |
| Three-lens review board            | Shipped (templates `03` / `04` / `05`)             |
| Meta-consolidation to canonical verdict | Shipped (template `06`)                        |
| Fix / Verify loop                  | Shipped (templates `14` / `15`)                     |
| Final-approval gate                | Shipped (template `07`)                             |
| Retrospective                      | Shipped (template `08`)                             |
| Ten-section spec                   | Shipped (template `12`)                             |
| One-revision cap                   | Shipped as a halt circuit breaker (three halts on same deliverable/phase/role/family → escalate). See `playbook.md` § Halt circuit breaker. |
| Spec deviation protocol            | Shipped (template `14` requires deviation declaration with authority citation). |
| Proposal Review pre-phase          | Shipped in v1.1 (template `16`; playbook §13-aligned). |
| Product lens                       | Shipped in v1.1 as an optional Phase B / D reviewer on user-facing deliverables (template `19`; see extension note below). |
| Triage pre-phase variant           | Shipped in v1.1 (template `17`; playbook §12-aligned). |
| Validation / Observation Run       | Shipped in v1.1 (template `18`; playbook §15.3 Validation/Observation Runs aligned). |

**v1.1 extension note.** Source playbook §13.4 scopes the Product lens to
Proposal Review only. v1.1 extends Product as an optional fourth reviewer
on Phase B.1 / B.2 / D.2 when `user_facing: true` in the manifest. This is
a deliberate framework extension, not a port. Rationale: user-facing
regressions surface at code time, not proposal time, and the 3-lens board
does not have a designated user-impact voice. The doctrine decisions
behind this and other v1.1 additions are recorded in
`docs/v1.1-doctrine-decisions.md`.

## Out of scope for this framework

- Language/stack-specific test harnesses. The framework declares `<SMOKE_CHECKS>`
  as a token; the project fills it in.
- CI/CD pipeline integration. The framework assumes a human or orchestrator LLM
  drives dispatch; wiring into CI is project-specific.
- Tool-specific auto-activation hooks (e.g., agent configuration files). The
  framework is tool-agnostic; activation is a project concern.
- Generator implementation. `manifest/generator-spec.md` defines what a
  generator must emit; building it is a v2 task.
