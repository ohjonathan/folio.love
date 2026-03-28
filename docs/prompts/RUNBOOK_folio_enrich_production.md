# `folio enrich` Production Library Test Runbook

## Purpose

Run `folio enrich` on the real production library on the McKinsey machine.
This validates PR C at production scale and produces the relationship output
that PR D (retroactive provenance) needs as its candidate filter.

## What `folio enrich` does and does not do

Before running, understand the shipped scope:

**Does:**
- Adds new tags to evidence and interaction notes (additive only, never removes)
- Backfills entity wikilinks into machine-owned sections (`### Analysis` prose
  for evidence, `## Entities Mentioned` for interaction)
- Proposes `supersedes` relationships for evidence notes, `impacts` for
  interaction notes — stored in `_llm_metadata.enrich` metadata only
- Generates `## Related` section from human-confirmed canonical relationship
  fields (not from proposals)
- Skips unchanged notes via fingerprint-based idempotency
- Continues on per-file failures

**Does not:**
- Touch diagram notes (excluded at registry eligibility)
- Write proposals into canonical relationship fields (human-owned)
- Emit `depends_on`, `draws_from`, `relates_to`, or `instantiates` proposals
- Mutate `## Summary`, `## Key Findings`, `### Text (Verbatim)`, raw
  transcripts, or quoted evidence
- Modify `registry.json` with enrich-specific fields
- Modify notes at `curation_level` L1+ or `review_status: reviewed/overridden`
  (metadata-only updates for those)

## Prerequisites

```bash
# 1. Pull latest main (must include PR #37: folio enrich core)
cd /path/to/folio
git pull origin main

# 2. Verify PR #37 is present
git log --oneline | head -5
# Should see the folio enrich squash merge

# 3. Reinstall
pip install -e .

# 4. Verify the command exists
folio enrich --help
# Should show: scope, --dry-run, --llm-profile, --force

# 5. Confirm API key (enrich uses routing.enrich or routing.default)
echo $ANTHROPIC_API_KEY | head -c 10

# 6. Confirm folio.yaml has a valid routing config
cat folio.yaml | grep -A 3 routing
# If routing.enrich is not defined, routing.default is used
```

## Phase 1: Dry Run

Dry run makes **zero LLM calls** and writes **nothing**. It shows what enrich
would do.

```bash
cd /path/to/folio-library

# Full library dry run
folio enrich --dry-run
```

### Expected output format

```text
Scope: N eligible document(s)
Estimated calls: primary=N relationship<=N
Dry run: N would_analyze, N would_skip, N would_protect, N would_conflict
```

### What to look for

| Check | Expected | Red flag |
|-------|----------|----------|
| Eligible documents | ~160 evidence + interaction notes | 0 eligible, or 1,500+ (means diagram notes leaking in) |
| `would_analyze` | Most L0 notes on first run | 0 (nothing to do — wrong library?) |
| `would_skip` | 0 on first run (nothing enriched yet) | Large number on first run |
| `would_protect` | Notes at L1+, reviewed, overridden | 0 if all notes are L0/clean |
| `would_conflict` | 0 on first run | Any (means managed body was edited since last enrich — investigate) |
| Diagram notes | Should NOT appear in output | Any diagram note IDs visible |

### Decision gate

If eligible count is reasonable and no diagram notes appear, proceed. If
output looks wrong, stop and investigate.

## Phase 2: Scoped Test Run

Run on one client/engagement to validate output quality before full library.

```bash
# Pick a scope with 5-15 files
folio enrich ClientA/DD_Q1_2026
```

### Expected output format

```text
Scope: N eligible document(s)
Estimated calls: primary=N relationship<=N
Enriching N document(s)...
✓ note_id  tags:+2 entities:+1 proposals:1
✓ note_id  tags:+1 entities:+0 proposals:0
↷ note_id  unchanged
! note_id  protected; metadata only
✗ note_id  <error message>

Enrich complete: N updated, N unchanged, N protected, N conflicted, N failed
```

### Post-run checks

**1. Open enriched files and verify:**

- **Frontmatter `tags`**: New tags present? Reasonable consulting vocabulary?
  No garbage? No removed tags?
- **Frontmatter `_llm_metadata.enrich`**: Block present with `status: executed`,
  fingerprints, and per-axis results?
- **Body `### Analysis` sections** (evidence): Entity wikilinks like `[[Name]]`
  inserted in `**Visual Description:**`, `**Key Data:**`, `**Main Insight:**`
  fields? NOT in `### Text (Verbatim)` or `**Evidence:**` blocks?
- **Body `## Entities Mentioned`** (interaction): Entity lists updated with
  `[[wikilinks]]`?
- **Body `## Summary` and `## Key Findings`** (interaction): UNCHANGED?
- **Body `## Related`**: Only present if canonical relationship fields exist
  in frontmatter. Links rendered as `[[path/to/note|Title]]`.
- **Relationship proposals** in `_llm_metadata.enrich.axes.relationships.proposals`:
  Each has `relation` (`supersedes` or `impacts`), `target_id`, `confidence`
  (`high`/`medium`), `signals`, `basis_fingerprint`, `status:
  pending_human_confirmation`.

**2. Idempotency check:**

```bash
# Run again on same scope — should skip everything
folio enrich ClientA/DD_Q1_2026
```

Expected: all notes show `↷ unchanged`. Zero LLM calls. If notes re-analyze,
the fingerprint logic has a bug.

**3. Human-edit safety check:**

```bash
# Edit an enriched evidence note — change something in ### Analysis
# Save the file
# Run enrich again
folio enrich ClientA/DD_Q1_2026
```

- If you edited a **managed section** (`### Analysis`), enrich should detect
  a `managed_body_fingerprint` mismatch and report `! conflict; metadata only`
  — it updates metadata but does not overwrite your edit.
- If you edited a **protected section** (`### Text (Verbatim)`, `## Summary`),
  enrich should process normally — protected sections are outside the managed
  surface.

**4. Entity registry check:**

```bash
folio entities
folio entities --unconfirmed
```

- New unconfirmed entities may appear (auto-created during resolution)
- Use `folio entities confirm <name>` to confirm real entities
- After confirming, re-run enrich — it should detect the confirmation and
  re-enrich affected notes to upgrade `[[unresolved]]` → `[[Canonical Name]]`

**5. Obsidian check (if available):**

- Open library as vault
- Navigate to an enriched note — wikilinks should be clickable
- Entity links resolve to entity mentions (not stub pages — entity markdown
  stubs are deferred)
- `## Related` links resolve to real notes via registry paths
- No YAML parse errors in frontmatter

### Decision gate

If scoped run quality is good, proceed to Phase 3. If tags are garbage,
entities are wrong, or protected content was mutated, stop and report.

## Phase 3: Full Library Run

```bash
cd /path/to/folio-library

# Full library enrichment
folio enrich

# Or with explicit profile override:
folio enrich --llm-profile anthropic_sonnet
```

### What to expect

- **Eligible notes**: ~160 evidence + interaction (diagram notes excluded)
- **LLM calls per note**: 1 primary analysis + 0-1 relationship evaluation
- **Runtime**: Depends on rate limits. At 50 RPM, ~160 notes takes ~5-10 min
  for primary analysis plus relationship passes. Budget 15-30 min.
- **Progress**: Per-file output with ✓/↷/!/✗ symbols
- **Exit code**: 0 if all succeed or skip; non-zero if any per-file failures

### If interrupted

Re-run the same command. Already-enriched notes will be skipped via
fingerprint match. Enrich is safe to restart.

### Force re-analysis

If you need to re-enrich notes that were already processed (e.g., after
fixing a prompt or confirming entities):

```bash
# Re-analyze everything, bypassing fingerprint skip
folio enrich --force

# Still respects body protection (L1+, reviewed, overridden)
# Still respects rejected proposal suppression when basis is unchanged
```

## Phase 4: Post-Run Validation

### Numbers to record

| Metric | Value |
|--------|-------|
| Total eligible notes | |
| Updated | |
| Unchanged (skipped) | |
| Protected (metadata only) | |
| Conflicted (metadata only) | |
| Failed | |
| Runtime | |
| New unconfirmed entities (`folio entities --unconfirmed \| wc -l`) | |
| Notes with relationship proposals | |

### Spot-check (5-10 files)

Pick a mix across clients/engagements:
- 3-4 evidence notes → verify tags, entity wikilinks in `### Analysis`,
  `### Text (Verbatim)` untouched
- 2-3 interaction notes → verify tags, `## Entities Mentioned` updated,
  `## Summary` and `## Key Findings` untouched, raw transcript untouched
- 1-2 protected notes (if any L1+) → verify body unchanged, metadata updated

### Idempotency at scale

```bash
# Re-run — should report all unchanged
folio enrich --dry-run
```

Expected: `would_analyze: 0`, `would_skip: N` (all previously enriched).

### Obsidian validation (if available)

```dataview
TABLE tags, _llm_metadata.enrich.status AS enrich_status
WHERE _llm_metadata.enrich != null
SORT file.name ASC
```

```dataview
TABLE supersedes, impacts
WHERE supersedes != null OR impacts != null
```

### Refresh compatibility

If you need to refresh any enriched notes later:

```bash
folio refresh --scope ClientA/DD_Q1_2026
```

- Canonical relationship fields (`supersedes`, `impacts`) survive refresh
- `_llm_metadata.enrich` survives refresh
- If source changed: enrich status becomes `stale`, fingerprints cleared
- `## Related` body section is lost on refresh (re-run `folio enrich` to
  restore it from preserved canonical fields)

## What to Bring Back

1. **The numbers table** from Phase 4
2. **Quality assessment**: Are tags reasonable? Are entity mentions correct?
   Are relationship proposals plausible?
3. **Any errors or warnings** from the run output
4. **Spot-check notes**: 2-3 before/after comparisons showing what enrich added
5. **Entity discovery**: How many new entities found? Any obvious
   false positives?
6. **Relationship proposals**: Sample of `supersedes` and `impacts` proposals —
   do they make sense? Would a human confirm them?
7. **Obsidian screenshots** if graph view shows new structure

This data becomes the enrichment baseline for the PR D spec and the eventual
Tier 3 closeout validation.
