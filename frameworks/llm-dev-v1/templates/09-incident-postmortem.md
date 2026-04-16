---
id: incident-postmortem
version: 1.0.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - ARTIFACT_OUTPUT_PATHS
  - FAMILY
optional_tokens:
  - INCIDENT_DATE
  - INCIDENT_SLUG
  - INCIDENTS_DIR
depends_on: [framework.md, 01-worker-session-contract.md]
---

# Incident Postmortem Meta-Prompt

For debugging a defect in tooling, infrastructure, or a prior deliverable
that surfaces during (or after) an orchestration run. Not a deliverable
artifact itself.

## BEGIN INCIDENT POSTMORTEM

**Your role.** You are the investigator for an incident. You write a
root-cause document with enough evidence that another engineer can
reproduce, fix, and write a regression guard without re-doing your work.

**Mandatory evidence.** Root cause requires a concrete locator. The
locator class depends on the incident type:

| Incident type                   | Required locator                                      |
|---------------------------------|-------------------------------------------------------|
| Code defect                     | `file:line` in source (or test)                        |
| Configuration defect            | `config-hash` (commit sha or config snapshot hash) + key path |
| External provider failure       | Provider status page URL + incident id / timestamp     |
| Process failure                 | Runbook step number + which step deviated              |
| Environment / infrastructure    | Telemetry query (metric + timestamp) or log grep with timestamp |

If none of the above can be produced, the investigation is incomplete —
mark the document `status: open` and record the narrowing path as far as
it goes. Do not claim root cause without a concrete locator.

**Sections required.**

1. **Summary** — one paragraph: what broke, how severe, what changed.
2. **Environment** — OS, language/runtime versions, tool versions, relevant
   configuration. Reproduction is impossible without this.
3. **Symptom** — exact error text or observed wrong behavior.
4. **Minimal reproduction** — the smallest input that triggers the symptom.
   Commands to run. Expected vs actual output.
5. **Narrowing** — the steps you took to localize the fault. Bisection
   history, logs consulted, hypotheses tried and rejected.
6. **Root cause** — one of the locator classes above (typically
   `file:line` for code defects). One paragraph explaining why this
   locator, in this context, produces the symptom.
7. **Proposed fixes** — at least two options with trade-offs. Include:
   - Minimal patch (fewest lines, highest risk of regression).
   - Structural fix (more invasive, lower long-term risk).
   Declare which you recommend and why.
8. **Regression guard** — an automated test (or runnable assertion) that
   fails against the bug and passes after the fix. Inline the test.
9. **Secondary findings** — anything you noticed while narrowing that is
   not the cause of this incident but worth recording.
10. **Impact and workarounds** — who is affected, any temporary mitigation.
11. **Acceptance criteria** — how the fix is verified (tests to run,
    behaviors to observe).
12. **Prior-art note** — related issues, prior postmortems, commits that
    touched this area.

**Output.** Write to `<ARTIFACT_OUTPUT_PATHS>` (typically
`<INCIDENTS_DIR>/<INCIDENT_DATE>-<INCIDENT_SLUG>.md`). Structure:

```markdown
---
id: <INCIDENT_DATE>-<INCIDENT_SLUG>
date: <INCIDENT_DATE>
role: investigator
family: <FAMILY>
severity: critical | high | medium | low
status: open | fix-proposed | fix-applied | closed
---

# Incident Postmortem — <INCIDENT_SLUG>

## 1. Summary
## 2. Environment
## 3. Symptom
## 4. Minimal reproduction
## 5. Narrowing
## 6. Root cause
<file:line>

## 7. Proposed fixes
### Option A — Minimal patch
### Option B — Structural fix
### Recommendation

## 8. Regression guard
```language
<test code>
```

## 9. Secondary findings
## 10. Impact and workarounds
## 11. Acceptance criteria
## 12. Prior-art note
```

**Halt conditions (extending the contract's investigator entry).**

- You cannot reach the failing system from the current environment. Record
  the environment and halt; do not guess.
- You cannot produce any of the allowed root-cause locator classes
  (file:line, config-hash + key, provider status + id, runbook step,
  telemetry query). Label the document `status: open` and list the
  narrowing path as far as it goes; do not claim root cause.

## END INCIDENT POSTMORTEM

## `<FINAL_REPORT_SCHEMA>`

The postmortem markdown above IS the final report.
