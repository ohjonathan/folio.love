---
id: phase-dispatch-handoff
version: 1.0.0
role: meta-prompt
audience: orchestrator
required_tokens:
  - DELIVERABLE_ID
  - PHASE_ID
  - ROLE
  - FAMILY
  - WORKSPACE
  - DEFAULT_BRANCH
  - BRANCH_CONVENTION
  - WORKTREE_ROOT
  - ARTIFACT_OUTPUT_PATHS
  - SCOPE_LOCK_PATHS
  - NO_TOUCH_PATHS
  - SMOKE_CHECKS
optional_tokens:
  - DOC_INDEX_ARCHIVE
  - FORBIDDEN_SYMBOLS
  - CARDINALITY_ASSERTIONS
  - COMMIT_PREFIX
  - CLI_DRIFT_NOTES
  - PREFLIGHT_EVIDENCE
  - RUN_ORDER_NOTES
  - REFERENCE_DOCS
  - ARTIFACT_UNDER_REVIEW
  - HALT_CATALOG_BLOCK
depends_on: [00-orchestrator-runbook.md, 01-worker-session-contract.md]
---

# Phase Dispatch Handoff (Meta-Prompt)

The orchestrator emits one instance of this prompt per worker dispatch. It
composes with `01-worker-session-contract.md` (inlined) and the role-specific
reviewer/author template. Inject **runtime facts** (branch name, worktree
path, live CLI notes, corrected smoke checks, preflight evidence) so workers
do not rely on stale defaults.

## BEGIN DISPATCH PREAMBLE

**Deliverable:** `<DELIVERABLE_ID>`
**Phase:** `<PHASE_ID>`
**Role:** `<ROLE>`
**Family:** `<FAMILY>`

### Runtime facts (orchestrator-verified)

- Workspace: `<WORKSPACE>`
- Worktree: `<WORKTREE_ROOT>/<DELIVERABLE_ID>/<ROLE>-<FAMILY>`
- Branch: `<BRANCH_CONVENTION>` (off `<DEFAULT_BRANCH>`, clean working tree verified)
- Commit prefix: `<COMMIT_PREFIX>`
- CLI drift notes: `<CLI_DRIFT_NOTES?>`
- Preflight evidence already in the tracker: `<PREFLIGHT_EVIDENCE?>`
- Run-order notes for this dispatch: `<RUN_ORDER_NOTES?>`

### Read before acting (in order)

1. `framework.md` (doctrine; skim principles P1–P12)
2. `01-worker-session-contract.md` (inlined below)
3. The role-specific wrapping template, picked from `<ROLE>`:
   - `03` peer (B/D)  ·  `04` alignment (B/D)  ·  `05` adversarial (B/D)
   - `06` meta-consolidator (B.3, D.3)  ·  `07` final-approval gate (D.6)
   - `08` retrospective (E)  ·  `09` incident postmortem (ad hoc)
   - `11` continuation prompt (resume after halt)
   - `12` spec author (A)  ·  `13` implementation author (C)
   - `14` fix-summary author (D.4)  ·  `15` verifier (D.5)
   - **v1.1 additions:** `16` proposal reviewer (`-A.proposal`) ·
     `17` triage author (`-A.triage`) ·
     `18` validation-run author (`-A.validation`) ·
     `19` product reviewer (B.1 / B.2 / D.2 when `user_facing: true`)
4. Approved reference documents: `<REFERENCE_DOCS?>`
5. Artifact under review or spec under implementation: `<ARTIFACT_UNDER_REVIEW?>`

### Allowed writes (exclusive)

```
<ARTIFACT_OUTPUT_PATHS>
```

### No-touch paths

```
<NO_TOUCH_PATHS>
```

### Scope lock

```
Allowed paths:      <SCOPE_LOCK_PATHS>
Forbidden symbols:  <FORBIDDEN_SYMBOLS>
Cardinality checks: <CARDINALITY_ASSERTIONS>
```

### Smoke checks to run before completion

```
<SMOKE_CHECKS>
```

### Halt conditions for `<ROLE>`

`<HALT_CATALOG_BLOCK>`

(The orchestrator or generator substitutes this token with the exact
subsection text from `01-worker-session-contract.md`'s role-specific
halt-condition catalog, keyed by `<ROLE>`. If the role is not present in
the catalog, dispatch is invalid — the catalog must be updated in a
separate pass first; do not mutate templates at dispatch time.)

### Evidence-label guidance

- `direct-run` — you executed the check in this session.
- `orchestrator-preflight` — the orchestrator executed it (see runtime facts).
- `static-inspection` — you inferred from the artifact, did not run.
- `not-run` — the check was not performed.

Blocking findings (if your role produces findings) require `direct-run` or
`orchestrator-preflight` with file:line citation and reproduction.

### Session archive

At session end, run `<DOC_INDEX_ARCHIVE>` if defined, then emit the final
report per the wrapping template's `<FINAL_REPORT_SCHEMA>`.

---

## Inlined worker session contract

_(Verbatim paste of `01-worker-session-contract.md`'s BEGIN/END block with
tokens substituted.)_

---

## Wrapping template body

_(Paste the body of the role-specific template per the picker in
"Read before acting" §3 above. v1.0 reviewer/consolidator/gate
templates: `03`, `04`, `05`, `06`, `07`, `08`, `09`, `11`. v1.0
end-to-end author templates: `12`, `13`, `14`, `15`. v1.1 pre-A and
Product templates: `16`, `17`, `18`, `19`.)_

## END DISPATCH PREAMBLE

---

## Orchestrator checklist before sending

- [ ] All tokens substituted. No unresolved angle-bracket placeholders remaining except
      `<FINAL_REPORT_SCHEMA>` placeholders explicitly carried forward.
- [ ] Branch, worktree, and workspace state verified clean.
- [ ] Role-specific halt-condition entry inlined.
- [ ] Smoke checks reflect the **current** scope lock and cardinality, not
      defaults copied from a prior phase (prompts are software — P12).
- [ ] Approved reference documents exist at the cited paths.
- [ ] Tracker row for this dispatch exists with `orchestrator` owner and
      phase `<PHASE_ID>`.
