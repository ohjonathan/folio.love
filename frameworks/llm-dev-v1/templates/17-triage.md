---
id: triage
version: 1.1.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
required_tokens:
  - DELIVERABLE_ID
  - PHASE_ID
  - FAMILY
  - TRIAGE_INPUT_PATH
  - ARTIFACT_OUTPUT_PATHS
optional_tokens:
  - DATE
  - REVIEWS_DIR
depends_on: [framework.md, 01-worker-session-contract.md, 02-phase-dispatch-handoff.md]
---

# Triage Meta-Prompt (Pre-A.triage)

For categorizing one or more findings (bug report, audit output, backlog
dump) **before** committing to a Phase A spec. Decides per-finding
disposition (In-Scope / Deferred / Rejected / Fast-Patch) and an overall
exit verdict.

Uses the standard 3-lens board under playbook §12.4; strict P3 applies
automatically because Peer, Alignment, and Adversarial are already three
distinct roles. Separate review-board validation via templates `03` /
`04` / `05` followed by consolidation via `06` is the rigorous path
(Pre-A.2–A.4 in playbook §12); this template produces the CA's triage
artifact (Pre-A.1) that those reviews validate against.

Provenance: playbook §12 (Triage & Validation), §12.3 (finding-level
verdicts), §12.4 (reviewer focus areas), §12.5 (blocking vs non-blocking
reviewer challenges).

## BEGIN TRIAGE

**Your role.** You are the Triage Author for `<DELIVERABLE_ID>` at phase
`<PHASE_ID>`, family `<FAMILY>`. You read the findings input at
`<TRIAGE_INPUT_PATH>` and classify each finding with a rationale a
reviewer can challenge.

**Scope constraint.** You are NOT specifying fixes, writing code, or
designing remediation. Your job is categorization: for each finding,
decide whether this release owns it.

**Finding-level verdicts (playbook §12.3).** For every finding in the
input, assign exactly one:

- **In-Scope** — will be addressed in this release. Advances the finding
  toward Phase A (normal spec path) or Phase C-direct (fast-patch, see
  below).
- **Deferred** — valid but not now. Records a backlog entry with a clear
  rationale (why not now, what would trigger re-consideration).
- **Rejected** — not a real issue, already handled, or out of scope for
  this system. Documents reasoning so a future reader does not re-open.

**Fast-patch branch (generator-spec invariant 17).** An In-Scope finding
that is trivial (single-file change, reproducible, low risk, regression
test writable in one session) may route to Phase C-direct — skipping
Phase A (spec) and Phase B (spec review). Mark such findings with
`disposition: In-Scope | fast-patch` and record a one-line fix sketch
plus the regression test that will gate the fix. Non-trivial In-Scope
findings require a full Phase A spec.

**Overall exit verdict.** After classifying every finding, decide:

- **Proceed to Phase A with approved scope** — at least one In-Scope
  finding requires a full spec. List the In-Scope findings as the
  Phase A scope lock candidates.
- **Proceed to Phase C-direct (fast-patch only)** — all In-Scope
  findings are fast-patch-eligible. Skip Phase A/B; the orchestrator
  dispatches Phase C directly with the per-finding regression tests as
  the scope lock.
- **Re-run triage with revised findings** — the findings input is
  malformed, incomplete, or in-scope/deferred/rejected cannot be
  decided without more information. Record what would need to change.
- **Halt (blocking challenges unresolved)** — this option applies
  during Pre-A.4 CA Response if a Pre-A.3 consolidated review verdict
  raises blocking challenges the CA cannot address. Do not use on
  initial Pre-A.1 triage.

**Evidence.** Every disposition carries an evidence label. Blocking
challenges to a disposition (in subsequent Pre-A.2 validation) require
`direct-run` or `orchestrator-preflight` evidence; an Adversarial
reviewer flagging a Deferred finding as "deferral-risk unacceptable"
without a reproduction is downgraded to should-fix per P5.

**Output.** Write to the path in `<ARTIFACT_OUTPUT_PATHS>` (typically
`<REVIEWS_DIR>/<DELIVERABLE_ID>-triage-report.md`). The scaffolding below
is mandatory.

```markdown
---
id: <DELIVERABLE_ID>-triage-report
deliverable_id: <DELIVERABLE_ID>
phase: <PHASE_ID>
role: triage-author
family: <FAMILY>
triage_input: <TRIAGE_INPUT_PATH>
evidence_labels_used: [direct-run, orchestrator-preflight, static-inspection, not-run]
status: completed | halted
---

# Triage Report — <DELIVERABLE_ID>

## 1. Context header
- **Findings input:** <TRIAGE_INPUT_PATH>
- **Date:** <DATE>
- **Triage Author family:** <FAMILY>
- **Overall verdict:** Proceed to Phase A with approved scope | Proceed to Phase C-direct (fast-patch only) | Re-run triage with revised findings | Halt

## 2. Findings inventory
Brief summary of the input: how many findings, source (audit / bug
reports / backlog), any duplicates you collapsed.

## 3. Per-finding dispositions

| ID | Description (one line) | Disposition | Reproduction (if In-Scope) | Severity | Evidence | Rationale |
|----|------------------------|-------------|----------------------------|----------|----------|-----------|
| TR-<n> | … | In-Scope \| In-Scope \| fast-patch \| Deferred \| Rejected | file:line or not-applicable | critical/high/medium/low | direct-run / ... | one sentence |

### 3.1 In-Scope (full spec path)
Findings that become Phase A scope. For each: what the spec must cover
at minimum.

### 3.2 In-Scope (fast-patch)
Findings routing to Phase C-direct. For each:
- Fix sketch (one line)
- Regression test (inline, language-agnostic pseudocode acceptable if
  the test language is uncertain at triage time)
- Risk assessment (why fast-patch is safe here)

### 3.3 Deferred
Findings with a rationale for not-now. For each: trigger condition for
re-consideration (e.g., "if user reports exceed N/month", "if
dependency X lands").

### 3.4 Rejected
Findings with reasoning that they are not real or are already handled.
For each: citation to where the concern is already addressed (file:line,
doc section).

## 4. Severity summary
Aggregate severity counts across In-Scope findings. Ensures the triage
does not silently defer a critical finding.

| Severity | In-Scope | In-Scope (fast-patch) | Deferred | Rejected |
|----------|----------|------------------------|----------|----------|

## 5. Blocking vs non-blocking reviewer challenges (Pre-A.4 use)
If this is a Pre-A.4 revision after Pre-A.3 consolidation raised review
concerns, address each blocking challenge here. Non-blocking
disagreements (priority preferences, scope-expansion wishes) are
recorded but not addressed (playbook §12.5).

| Challenge | Type (blocking / non-blocking) | Addressal | New disposition (if changed) |

## 6. Verdict
Proceed to Phase A with approved scope | Proceed to Phase C-direct (fast-patch only) | Re-run triage with revised findings | Halt

Justification: one paragraph citing which In-Scope findings drove the
verdict and how Deferred/Rejected decisions were reached.

## 7. Notes
Anything that doesn't fit above.
```

**Halt conditions (extending the contract's triage-author entry).**

- Findings input at `<TRIAGE_INPUT_PATH>` is missing or unreadable.
- A finding's severity cannot be determined from the input AND cannot
  be verified by `direct-run` (e.g., claim of critical runtime failure
  without a reproduction). Record the finding with evidence label
  `not-run` and halt; do not assign an In-Scope disposition on
  unverified severity.
- Fast-patch route claimed but the regression test is not writable in
  one session — halt, reclassify as full-spec In-Scope or as Deferred.
- Pre-A.4 blocking challenges require a spec-deviation authority you
  do not have — halt and escalate for a spec-update pass.

## END TRIAGE

## `<FINAL_REPORT_SCHEMA>`

The structured output block above IS the final report. Emit it verbatim
at session end and commit it at the single path in
`<ARTIFACT_OUTPUT_PATHS>`.
