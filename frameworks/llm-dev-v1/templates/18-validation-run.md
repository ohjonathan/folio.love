---
id: validation-run
version: 1.1.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - DELIVERABLE_ID
  - PHASE_ID
  - FAMILY
  - VALIDATION_RUN_INPUT_PATH
  - ARTIFACT_OUTPUT_PATHS
optional_tokens:
  - DATE
  - VALIDATION_RUN_BUDGET
  - REVIEWS_DIR
depends_on: [framework.md, 01-worker-session-contract.md, 02-phase-dispatch-handoff.md]
---

# Validation Run Meta-Prompt (Pre-A.validation)

For observing a **deployed or runnable** code path under real or
representative input and emitting a structured report. This is a gate
protocol, not a review board: you observe a run, you do not drive one.

Per playbook §15.3 "Validation / Observation Runs" (an H4 sub-section
under the Hotfix Phase §15.3), a Validation Run is not a development
phase — it is a protocol for tasks that run deployed code and report
results without changing it. Examples: field testing, performance
benchmarking, corpus processing, pre-release acceptance testing.

P3 does not apply (not a review board; see `framework.md` § P3 pre-A
carve-out).

Provenance: playbook §15.3 → "Validation / Observation Runs" (H4
sub-section, not §15.3.1 — the playbook does not number at the H4
level); §15.2 "Patch/Polish Phase" (the Evidence-Based Patch pattern
referenced as a common exit path is described within §15.3's
Validation Runs block).

## BEGIN VALIDATION RUN

**Your role.** You are the Validation-Run Author for `<DELIVERABLE_ID>`
at phase `<PHASE_ID>`, family `<FAMILY>`. You read the run input at
`<VALIDATION_RUN_INPUT_PATH>` — which specifies what to observe, not
what to change — and emit a structured report the orchestrator uses to
decide next steps.

**Scope constraint.** You do not modify deployed code. You do not
propose fixes (the report may surface defect candidates; fix decisions
are the orchestrator's, feeding into Phase A, Evidence-Based Patch, or
an incident). If the run cannot be performed without code changes,
halt.

**Mandatory evidence.** A validation run without `direct-run` or
`orchestrator-preflight` evidence is not a validation run; it is static
inspection mislabeled. At minimum, the report must include:

| Evidence class (at least one required)       | What it looks like |
|-----------------------------------------------|--------------------|
| `direct-run` output from the deployed system  | Captured command + stdout/stderr + exit code + timestamp |
| `orchestrator-preflight` telemetry            | Metric name + timestamp + value + dashboard link |
| Observation of a live system (read-only)      | Query + timestamp + result + source-of-truth link |

If none of these can be produced, the run is **inconclusive** — mark
the document accordingly and record the narrowing path as far as it
goes. Do not claim a run verdict without live evidence.

**Verdict set (playbook §15.3 Validation/Observation Runs aligned).** Exactly one of:

- **Run clean — proceed to A** — observations match expectations; no
  defects; feed forward to Phase A (spec) with the validated approach.
- **Run inconclusive — re-run with revised plan** — the run did not
  produce decisive signal (input gap, timing wrong, environment drift,
  sample size too small). Record what would need to change and
  re-dispatch at Pre-A.validation.
- **Run exposed defect — escalate to hotfix or incident** — the run
  revealed a concrete failure. Route to either:
  - `09-incident-postmortem.md` (severity critical/high; systemic
    failure mode)
  - Evidence-Based Patch via Phase A (severity medium/low; defect
    candidate with clear fix direction)

**Output.** Write to the path in `<ARTIFACT_OUTPUT_PATHS>` (typically
`<REVIEWS_DIR>/<DELIVERABLE_ID>-validation-run.md`). The scaffolding
below is mandatory.

```markdown
---
id: <DELIVERABLE_ID>-validation-run
deliverable_id: <DELIVERABLE_ID>
phase: <PHASE_ID>
role: validation-run-author
family: <FAMILY>
run_input: <VALIDATION_RUN_INPUT_PATH>
evidence_labels_used: [direct-run, orchestrator-preflight, static-inspection, not-run]
status: completed | halted
---

# Validation Run Report — <DELIVERABLE_ID>

## 1. Context header
- **Run input spec:** <VALIDATION_RUN_INPUT_PATH>
- **Date:** <DATE>
- **Run author family:** <FAMILY>
- **Run budget:** <VALIDATION_RUN_BUDGET>  (may be empty; e.g., "60m wall-clock, $5 API spend, 1000 requests")
- **Verdict:** Run clean — proceed to A | Run inconclusive — re-run with revised plan | Run exposed defect — escalate to hotfix or incident

## 2. Run setup
- **Target system:** what was observed (URL, service, module, environment).
- **Version / deployment identity:** commit SHA, release tag, container
  image digest — whatever pins the observed system to a reproducible
  state.
- **Environment:** OS, runtime versions, relevant configuration. Without
  this, re-run reproducibility is impossible.
- **Read-only guarantee:** declare that nothing you ran modified the
  target system. If the run required write access (e.g., creating a
  test account), record what you wrote and where it lives.

## 3. Observations
Each observation: what you measured, how, and the raw result.

| ID | Observation | Measurement method | Raw result | Evidence | Timestamp |
|----|-------------|--------------------|------------|----------|-----------|
| VR-<n> | … | `curl` / metric query / log grep / ... | stdout / value / log line | direct-run | 2026-04-XX hh:mm UTC |

Include the exact commands / queries in a fenced block for
reproducibility. Raw output is preferred over summarized output; if
summarizing is necessary due to volume, note the summarization rule
(e.g., "count of 4xx responses aggregated per 1-minute bucket").

## 4. Measurements
Quantitative results against the run input's expected values (if any).

| Metric | Expected | Observed | Delta | Pass / fail / unknown |
|--------|----------|----------|-------|-----------------------|

If the run input did not specify expected values, document what you
observed against prior baseline (if known) and flag "no baseline" for
any metric without one.

## 5. Findings
Categorize each finding; do not conflate types.

### 5.1 Defect candidates (observed failures)
| ID | Description | Reproduction | Severity (critical/high/medium/low) | Suggested next step |
|----|-------------|--------------|--------------------------------------|---------------------|

Suggested next step is one of: incident postmortem (critical/high) |
Evidence-Based Patch via Phase A (medium/low) | re-run with revised
plan (cannot determine).

### 5.2 Out-of-bounds observations (unexpected but not failures)
Things the run surfaced that are not defects but deserve follow-up
(performance cliff at an unexpected load, behavior under an unusual
input class, etc.).

### 5.3 Positive observations
What the run validated. Required — absence reads as unearned severity.

## 6. Decision
One of: Run clean — proceed to A | Run inconclusive — re-run with revised plan | Run exposed defect — escalate to hotfix or incident

Justification: one paragraph citing the §3 observations, §4
measurements, and §5 findings that drove the verdict.

## 7. Exit path
If Run clean: specify what the Phase A spec should cover (scope candidates).
If Re-run: specify what the revised run plan should change (inputs,
sample size, duration, environment, instrumentation).
If Defect: specify the route (incident | Evidence-Based Patch) and
which §5.1 finding drives the route.

## 8. Notes
Anything that doesn't fit above (e.g., instrumentation gaps that made
the run harder, recommended observability improvements that are not
defects).
```

**Halt conditions (extending the contract's validation-run-author entry).**

- Run input at `<VALIDATION_RUN_INPUT_PATH>` is missing or unreadable.
- The target system is not reachable from your execution environment.
  Record what you tried (network, auth, DNS) and halt; do not
  substitute static inspection for direct observation.
- The run would require writing to the target system beyond what the
  run input declared. Halt; do not silently escalate write scope.
- A critical-severity defect is observed. Emit the report with verdict
  "Run exposed defect — escalate to hotfix or incident" and halt
  (do not proceed to any speculative fix).
- `<VALIDATION_RUN_BUDGET>` is exhausted without a conclusive
  observation. Record what you have, mark Run inconclusive, halt.

## END VALIDATION RUN

## `<FINAL_REPORT_SCHEMA>`

The structured output block above IS the final report. Emit it verbatim
at session end and commit it at the single path in
`<ARTIFACT_OUTPUT_PATHS>`.
