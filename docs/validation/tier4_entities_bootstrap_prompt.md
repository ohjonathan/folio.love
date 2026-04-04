---
id: tier4_entities_bootstrap_prompt
type: validation
status: complete
created: 2026-04-04
---

# Tier 4 Production Entities Bootstrap — Validation Prompt

## Task Specification

**Objective:** Bootstrap the production `entities.json` for the retained
production Folio library using the supported CLI import workflow, verify it on
the real library, document the run, and update the live docs so the remaining
Tier 4 operational prerequisite is closed.

**Target environment:** McKinsey laptop, running against the real production
`ada-folio` library with the correct `folio.yaml` context.

---

## Governing Documents

- `docs/validation/tier3_closeout_report.md`
- `docs/product/04_Implementation_Roadmap.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/product/02_Product_Requirements_Document.md`

---

## Supported Entity Workflow

Use the supported CLI path only:

```bash
folio entities import <csv>
folio entities generate-stubs --force
folio entities
folio entities --unconfirmed
folio entities show "<name>"
```

### Critical Constraints

- Run from the directory where the production `folio.yaml` context is correct.
- Prefer the supported CSV import path. Look for a real org-chart CSV first.
- A valid candidate CSV must have `name`, and should have either:
  - `reports_to`, or
  - both `department` and `level` / `org_level`
- Do not invent a stub-to-JSON migrator in this pass.
- Do not hand-author `entities.json` unless the supported import path is
  proven impossible and the run stops with a blocker.
- Do not mass-confirm unresolved entities just to make the output look clean.
- If `entities.json` already exists, merge into it via the supported CLI path.

---

## Execution Plan

### 1. Preflight

- Confirm repo root, active branch, and production `folio.yaml` location.
- Confirm the production library root.
- Run `folio status`.
- Check whether `entities.json` already exists.
- Count existing `_entities` stubs by type if present.
- Locate candidate CSV files under the engagement workspace and inspect
  headers.
- Choose the best current org-chart CSV for US Bank / Technology Resilience
  2026.

### 2. Safety Backup

- If `entities.json` exists, create a timestamped backup before mutation.
- Do not modify or delete existing markdown stubs manually.

### 3. Import

- Run `folio entities import <chosen_csv>`.
- Capture the exact import summary:
  - people imported
  - people updated
  - people skipped
  - departments created
  - warnings
- If import fails, stop and document the blocker with the exact error.

### 4. Stub Refresh

- Run `folio entities generate-stubs --force`.
- Confirm manual stubs were preserved if any exist.
- Summarize generated vs skipped stubs.

### 5. Verification

Run:

```bash
folio status
folio entities
folio entities --unconfirmed
folio entities show "<sample imported person>"
```

Additional rules:

- If one of `Mark Piersak`, `Andrew Lee`, or `Bradley Pearce` is present in
  the imported org chart, verify one of them explicitly with
  `folio entities show`.
- If those recent interaction participants are not in the CSV, state that
  clearly and do not force-create or confirm them manually.
- Verify `entities.json` is readable and non-empty.
- Summarize entity totals by type and remaining unconfirmed totals by type.

### 6. Documentation Updates

Update:

- `docs/validation/tier3_closeout_report.md`
- `docs/product/04_Implementation_Roadmap.md`
- `docs/validation/tier3_kickoff_checklist.md`

Create the four validation artifacts in `docs/validation/`:

1. `tier4_entities_bootstrap_prompt.md`
2. `tier4_entities_bootstrap_report.md`
3. `tier4_entities_bootstrap_session_log.md`
4. `tier4_entities_bootstrap_chat_log.md`

Archive the decision with:

```bash
ontos log --auto --event-type decision --source cli --title "Production entities bootstrap completed"
```

### 7. Final Sync And Verification

Run:

```bash
ontos map --sync-agents
git diff --check
git status --short --branch
```

Report any generated-file inconsistencies in `AGENTS.md` vs
`Ontos_Context_Map.md`, but do not hand-edit generated files.

---

## Acceptance Criteria

- Production `entities.json` exists and is readable.
- Import used the supported CLI path from a real org-chart CSV.
- `folio status` reflects entity presence.
- `folio entities` works on the production library.
- Remaining unconfirmed entities are summarized, not blindly confirmed.
- The four validation artifacts exist.
- The closeout report, roadmap, and kickoff checklist all reflect that the
  bootstrap follow-up is complete.
- Ontos log created and `ontos map --sync-agents` run.
- No custom bootstrap script or hand-built registry was introduced unless the
  run stopped with a documented blocker.
