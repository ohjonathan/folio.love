---
id: continuation-prompt
version: 1.0.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - DELIVERABLE_ID
  - PHASE_ID
  - ROLE
  - FAMILY
  - ARTIFACT_OUTPUT_PATHS
  - HALT_REPORT_PATH
depends_on: [framework.md, 01-worker-session-contract.md, 02-phase-dispatch-handoff.md]
---

# Continuation Prompt Meta-Prompt

Used when a worker halted, a session was interrupted, or an artifact was
written partially. Resumes without rewriting valid prior work.

## BEGIN CONTINUATION

**Your role.** You are resuming work as `<ROLE>` in family `<FAMILY>` on
`<DELIVERABLE_ID>` at phase `<PHASE_ID>`. A prior session produced partial
output or halted. Your job is to produce only what is missing or what the
halt report flagged as required.

**Non-negotiable rules.**

1. **Reuse the existing branch.** Do not create a new branch. The
   orchestrator has already placed you on the correct branch and worktree.
2. **Do not rewrite valid prior work.** Read all artifacts already in
   `<ARTIFACT_OUTPUT_PATHS>`. If a section is present and not flagged as
   defective by the halt report, leave it alone.
3. **Produce only missing artifacts or flagged fixes.** Scope is narrower
   than the original dispatch.
4. **Write-scope unchanged.** You may still only write to
   `<ARTIFACT_OUTPUT_PATHS>`. No-touch paths are unchanged.
5. **Report every change.** The final report must list every file you
   touched and every section you added or modified, keyed to the halt-report
   item it addresses.

**Required inputs.**

- The halt report at `<HALT_REPORT_PATH>`.
- Any partial artifact at `<ARTIFACT_OUTPUT_PATHS>`.
- The original dispatch preamble (orchestrator re-inlines it).

**Workflow.**

1. Read the halt report. List each item that needs resolution.
2. Read the partial artifact. Inventory what exists vs what the halt
   report requires.
3. For each gap: produce the minimal addition or fix.
4. Re-run the smoke checks and cardinality assertions from the original
   dispatch.
5. Write the continuation final report.

**Output.** Append to the partial artifact (or create if absent). Write the
continuation final report to the path the dispatch names.

**Continuation final report schema.**

```markdown
## Continuation final report — <DELIVERABLE_ID> / <PHASE_ID> / <ROLE> / <FAMILY>

### Halt items addressed
| Halt item # | Resolution | Files touched | Evidence |
|-------------|------------|---------------|----------|

### Halt items deferred (with reason)
| Halt item # | Reason for deferring | Recommended owner |
|-------------|---------------------|-------------------|

### Sections unchanged from prior session
<list — proves you did not rewrite valid work>

### Smoke / cardinality checks
<name> = pass|fail|not-run  (evidence: <label>)

### Commit: <sha> on <branch>
```

**Halt conditions.**

- The partial artifact is missing AND no halt report exists. You have no
  basis to continue. Halt and request the orchestrator re-dispatch the
  original template, not this one.
- The halt report flags a framework defect. Do not patch templates from a
  worker session. Halt and escalate.

## END CONTINUATION

## `<FINAL_REPORT_SCHEMA>`

The continuation final report block above IS the final report.
