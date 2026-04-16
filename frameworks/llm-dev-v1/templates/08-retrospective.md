---
id: retrospective
version: 1.0.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - DELIVERABLE_ID
  - FAMILY
  - ARTIFACT_OUTPUT_PATHS
  - TRACKER_PATH
optional_tokens:
  - DOC_INDEX_ARCHIVE
depends_on: [framework.md, 01-worker-session-contract.md, 07-final-approval-gate.md]
---

# Retrospective Meta-Prompt

Produces a post-merge orchestration report. Its purpose is to feed learnings
back into the framework and into the next deliverable's manifest.

## BEGIN RETROSPECTIVE

**Your role.** You are the retrospective author for `<DELIVERABLE_ID>`,
operating in family `<FAMILY>`. You write after merge, reading tracker,
canonical verdicts, fix summaries, halt reports, and commit history.

**Your job is NOT to re-review the code.** It is to document:

- What worked (wins with evidence — cite tracker rows, verdicts, commits).
- What broke (failures with evidence — cite halt reports, downgraded
  blockers, repeated dispatches).
- What surprised you (unexpected behavior — cite the artifact that
  surprised).
- What the framework should change (specific template edits, new
  principles, new halt catalog entries).
- What the next deliverable's manifest should inherit (guardrails that paid
  off; scope locks that prevented drift).

**Sources you read.**

- `<TRACKER_PATH>` (full phase history)
- All canonical verdicts
- All family verdicts
- Fix summary
- Final-approval gate result
- All halt reports for this deliverable
- Merge commit

**Output.** Write to `<ARTIFACT_OUTPUT_PATHS>`. Structure:

```markdown
---
id: <DELIVERABLE_ID>-retrospective
deliverable_id: <DELIVERABLE_ID>
role: retrospective
family: <FAMILY>
status: completed | halted
---

# Retrospective — <DELIVERABLE_ID>

## Context (2 sentences)
What this deliverable was; how it was executed (phases run, families used).

## Metrics
- Phases executed: <list>
- Total worker sessions: N
- Halts: N (by class: <input-missing / scope-violation / ...>)
- Blockers raised: N; preserved: N; downgraded: N
- Fix loops: N
- Test count: baseline N → final N (delta: +N)
- Real bugs caught pre-merge: N (cite)
- Final-approval gate outcome: PASSED | FAILED-THEN-REMEDIATED

## What worked (with evidence)
Each:
- **Observation:** <what held>
- **Evidence:** <tracker row / verdict path / commit sha>
- **Generalizable?** yes/no — if yes, recommended framework update.

## What broke (with evidence)
Each:
- **Observation:** <what failed>
- **Evidence:** <path>
- **Root cause:** <why>
- **Mitigation applied:** <what the orchestrator did>
- **Framework update:** <template change, new principle, or "none needed">

## Surprises
Each:
- **Observation:** <unexpected behavior>
- **Evidence:** <path>
- **Implication:** <what this tells us about the framework or the problem>

## Recommended framework updates
A numbered list the framework maintainer works through. Each entry:
- Target file: <template or framework.md>
- Change: <specific edit>
- Rationale: <which retrospective entry this addresses>

## Recommended manifest inheritance
What the next deliverable's manifest should reuse (guardrails, scope
patterns, model assignments) and what it should change.

## Open items
Anything discovered during this deliverable that belongs to a future
deliverable, not to this one.
```

**Halt conditions (extending the contract's retro entry).**

- The tracker, merge commit, or canonical verdicts are missing. Without
  them the retrospective cannot be factually grounded.

**Archive ordering (v1.1.1).** If `<DOC_INDEX_ARCHIVE?>` is defined in
`tokens.md`, run it as the **final step after this retrospective is
committed**, not before. The archive command (for example one that indexes
the session by deliverable slug) records the session's artifacts; running
it before the retro is committed means the archive entry will miss the
retrospective itself. This ordering is normative: the Phase E session
completes with (1) retrospective authored and committed, then (2) archive
command executed.

## END RETROSPECTIVE

## `<FINAL_REPORT_SCHEMA>`

The retrospective markdown above IS the final report.
