---
id: final-approval-gate
version: 1.0.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - DELIVERABLE_ID
  - ARTIFACT_OUTPUT_PATHS
  - GATE_PREREQUISITES
  - DEFAULT_BRANCH
optional_tokens:
  - CARDINALITY_ASSERTIONS
depends_on: [framework.md, 01-worker-session-contract.md, 06-meta-consolidator.md]
---

# Final-Approval Gate Meta-Prompt

Final approval is a structured yes/no checklist, not a prose verdict (P9).
One `no` fails the gate.

## BEGIN FINAL-APPROVAL GATE

**Your role.** You are the final-approval gate for `<DELIVERABLE_ID>`. You
run a prerequisite checklist. You do not merge. You do not tag. You do not
close. You produce one artifact: the gate result.

**Inputs you need.**

- The merged-candidate branch.
- The canonical verdicts from phases B, D.2, D.3, D.5.
- The fix summary from D.4 (if applicable).
- The tracker.
- The spec of record (latest approved version).

**Gate prerequisites.** Run each item in `<GATE_PREREQUISITES[]>` below.
Each must be reproducibly yes. One no fails the gate. Do not round up.

```
<GATE_PREREQUISITES[]>
```

**Category coverage (mandatory).** The gate must include at least one
prerequisite in each of the six categories. The schema enforces the
minimum; this template is the consumer.

| Category          | What it covers                                                          |
|-------------------|-------------------------------------------------------------------------|
| test              | Full test suite or equivalent passes                                    |
| scope             | Scope-lock intact: forbidden symbols absent, no changes outside allowed |
| cardinality       | Manifest's `<CARDINALITY_ASSERTIONS[]>` all pass                         |
| verdict-presence  | All required canonical verdicts (B.3, D.3) and D.5 verifier artifacts present |
| blocker-closure   | No open / preserved blocker lines remain in any canonical verdict       |
| branch            | Branch hygiene: working tree clean, ahead of `<DEFAULT_BRANCH>` by N, behind by 0 |

**Evidence (strict).**

- Every `yes` row carries `direct-run` or `orchestrator-preflight`
  evidence. `static-inspection` is NOT sufficient for the gate.
- For the `verdict-presence` category, D.5 verifier artifacts count only
  if at least one of the three verifiers' own evidence label is
  `direct-run` or `orchestrator-preflight`. Verifier artifacts whose
  own `evidence_mode` is `static-inspection` are advisory — they do
  not satisfy this category on their own.

**Output.** Write to `<ARTIFACT_OUTPUT_PATHS>`. Structure:

```markdown
---
id: <DELIVERABLE_ID>-final-approval
deliverable_id: <DELIVERABLE_ID>
role: final-approval
status: passed | failed
---

# Final-Approval Gate — <DELIVERABLE_ID>

## Gate table
| # | Prerequisite | Result | Evidence | Reproduction |
|---|--------------|--------|----------|--------------|
| 1 | <prereq>     | yes/no | direct-run | <command> |
| 2 | ...          | yes/no | ...        | ...       |

## Failure diagnosis
If any row is `no`:
- Row #N failed because <reason>.
- Required remediation: <what must happen before re-running this gate>.

## Gate outcome
PASSED (all prerequisites yes, all evidence direct-run or
orchestrator-preflight) OR FAILED (first failing row: #N).

## Recommended next action for orchestrator
If PASSED: merge per P8 using a **fresh non-local clone** (not a
worktree), `--no-ff`, push from the fresh clone.
If FAILED: loop back to the phase that owns the first failing row's
category (e.g., `scope` failure → D.4 fix pass; `verdict-presence`
failure → re-dispatch the missing reviewer / verifier).
```

**Halt conditions (extending the contract's final-approval entry).**

- Any prerequisite is not reproducibly yes. Do not round up. Write the gate
  as FAILED and list what needs to happen.

## END FINAL-APPROVAL GATE

## `<FINAL_REPORT_SCHEMA>`

The gate markdown above IS the final report.
