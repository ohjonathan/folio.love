# Tier 3 Closeout — Validation Prompt

## Task Specification

**Objective:** Execute the Tier 3 closeout validation run for folio.love,
validating that all Tier 3 exit criteria are met on a production library.

**Spec Version:** `folio_context_docs_tier3_closeout_spec.md` (rev 1)

---

## Scope

The closeout validation must verify:

1. **EC-1 (Ingest):** `folio ingest` converts a transcript to structured
   interaction note in <60 seconds.
2. **EC-2 (Entity Registry):** Entity registry tracks people, departments,
   systems via `folio entities`.
3. **EC-3 (Name Resolution):** Name resolution produces wikilinks for
   confirmed entities in enriched notes.
4. **EC-4 (Enrich):** `folio enrich` adds tags, relationship links, and
   entity resolution to existing assets.
5. **EC-5 (Provenance):** Retroactive provenance infrastructure works on
   confirmed `supersedes`-linked evidence pairs.
6. **EC-6 (Context Docs):** Context documents provide engagement scaffolding
   via `folio context init` and are registry-visible.
7. **EC-7 (Full Lifecycle):** Full engagement lifecycle tested end-to-end
   via `test_tier3_lifecycle.py`.

---

## Hard-Fail Conditions (Spec §9.6)

All three must be met for PASS:

- [ ] Tier 3 lifecycle integration test passes in CI
- [ ] `folio status --refresh`, `scan`, `refresh` complete without crash
      on mixed library with context row
- [ ] Production validation: real context doc created and registry-visible
      in `folio status`

---

## Environment Requirements

| Requirement | Value |
|-------------|-------|
| Primary env | Personal Folio dev laptop (editable install) |
| Production env | McKinsey laptop (production library) |
| Python | 3.14.x |
| Branch | `feature/pr-e-context-docs-tier3-closeout` |

---

## Validation Steps

### Phase 1: Automated (Dev Laptop)

```bash
# 1. Run the full Tier 3 test suite
python3 -m pytest tests/test_context.py tests/test_registry.py \
    tests/test_tier3_lifecycle.py -v

# 2. Run the frontmatter validator on existing library
python3 tests/validation/validate_frontmatter.py
```

### Phase 2: Production (McKinsey Laptop)

```bash
# 3. Create a real context document
folio context init --client "ClientName" --engagement "Engagement Name"

# 4. Verify registry visibility
folio status
folio status --refresh

# 5. Verify pipeline safety with context row present
folio scan
folio refresh --dry-run
```

### Phase 3: Evidence Collection

Fill in the closeout report with evidence from each step above. Each EC
PASS decision must include:

- Current corroborating evidence (not historical-only)
- Date of evidence
- Method of verification

---

## Deliverables

1. `tier3_closeout_report.md` — completed with evidence
2. `tier3_closeout_session_log.md` — chronological action log
3. `tier3_closeout_chat_log.md` — raw interaction transcript
4. This prompt file (already exists)

---

## Anti-Rubber-Stamp Rules (Spec §9.7)

- A PASS decision for any exit criterion MUST cite current evidence from
  this validation run, not a prior session.
- "It passed before" is not valid evidence. Re-run and cite the new result.
- If a prior run's evidence is cited, the report must explain why re-running
  was not feasible and what compensating check was performed.
- Each PASS must include the exact command output or screenshot that proves
  the criterion was met.
