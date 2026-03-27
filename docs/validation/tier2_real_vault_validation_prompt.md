---
id: tier2_real_vault_validation_prompt
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-27
---

# Task: Tier 2 Real Vault Validation Before PR C

## What You're Doing

This is a **real Obsidian vault validation run** on the **McKinsey laptop**
using the **production Folio library** after the real-library rerun decision.

This is **not** an implementation task.

This run exists to answer one operational question:

> Is the current production Folio library usable enough, in the real vault, to
> justify starting PR C (`folio enrich`) on top of it?

The production baseline for this run is locked by
`tier2_real_library_rerun_report.md`:

- use the production `sonnet4` library
- do **not** switch to the `haiku45` scratch rerun library

## Required Outputs

Produce the standard validation artifacts in `docs/validation/` using the label
`tier2_real_vault_validation`:

1. `tier2_real_vault_validation_prompt.md`
2. `tier2_real_vault_validation_report.md`
3. `tier2_real_vault_validation_session_log.md`
4. `tier2_real_vault_validation_chat_log.md`

Optional only if useful:

5. `tier2_real_vault_validation_checklist.md`

Use the optional checklist only if it materially helps track a large set of
manual review checks. Do not create extra artifacts casually.

## Read Before Doing Anything

Read these first:

1. [AGENTS.md](/Users/jonathanoh/Dev/folio.love/AGENTS.md)
2. [tier2_real_library_rerun_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_library_rerun_report.md)
3. [tier2_platform_model_comparison_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_platform_model_comparison_report.md)
4. [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md)
5. [tier2_accelerated_precloseout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_report.md)
6. [obsidian_transclusion_test_result.md](/Users/jonathanoh/Dev/folio.love/docs/validation/obsidian_transclusion_test_result.md)

## Environment Rules

Use the machine that has:

- the real production Obsidian vault
- the real production Folio library
- the exact plugins/workflow you actually use for day-to-day review

This run is about **real usability**, not synthetic render testing.

If possible:

- use Obsidian itself for the actual vault checks
- use Cursor only to coordinate, take notes, and write the validation artifacts

## Scope

This run should validate the **current production library in the real vault**
before PR C.

In scope:

- opening the production vault cleanly
- navigating the production Folio library in Obsidian
- checking representative evidence notes and interaction notes
- checking representative diagram-heavy notes
- checking that metadata, tags, and review-state surface are usable enough for
  real work
- checking that mixed-library behavior is coherent enough to enrich later

Out of scope:

- switching the library baseline
- implementing fixes
- starting `folio enrich`
- synthetic-only renderer testing as a substitute for actual vault review

## Baseline You Must Respect

Use:

- the **production `sonnet4` library**

Do **not** validate against:

- the `haiku45` scratch rerun library as the primary baseline

You may reference the scratch rerun library only if it helps explain a specific
comparison or suspected issue, but the gate decision must be about the
production library.

## Goal And Gate

The final report must end with one of these decisions:

- `PASS TO PR C`
- `PARTIAL / FIX KNOWN ISSUES FIRST`
- `BLOCKED`

Your decision must explicitly answer:

1. Is the production library usable enough in Obsidian for real engagement work
   right now?
2. Is it usable enough to serve as the input baseline for PR C (`folio enrich`)?

## What To Check

You do not need to manually open all 115 decks. Use a representative but
deliberate sample.

Minimum sample requirements:

1. At least **12 evidence notes** spanning:
   - simple narrative/text-heavy decks
   - dense multi-page documents
   - diagram-heavy decks
   - one or more known trouble areas from the rerun comparison where `haiku45`
     and `sonnet4` differed materially

2. At least **3 interaction notes** if any are present in the production vault,
   to confirm mixed-library usability

3. At least **2 entity-heavy notes** where registry-backed entity links or
   references are visible

4. At least **2 diagram notes / diagram transclusion cases** if present, to
   confirm the current production vault still renders the expected output

5. At least **3 Dataview or metadata-based workflows** you actually care about,
   for example:
   - list flagged notes
   - filter by client / engagement
   - inspect notes by subtype or authority

If the production vault lacks one of those categories, record that fact rather
than faking the sample.

## Recommended Check Areas

### A. Vault Open / Navigation

Check:

- vault opens without parse/render errors
- Folio folders are navigable
- OneDrive sync state does not obviously corrupt notes or images

### B. Note Rendering Quality

For sampled notes, check:

- frontmatter parses cleanly
- headings and sections are readable
- embedded images render where expected
- Mermaid and transcluded sections render where expected
- long notes remain usable and not obviously broken

### C. Reviewability

Check whether a human can actually use the notes to review or reason:

- `review_status` and `review_flags` are visible and understandable
- confidence and grounding summaries are interpretable
- the note body is structured enough to support real review

### D. Mixed-Library Usability

Check whether evidence and interaction notes can coexist in the same vault
without confusion:

- note types are distinguishable
- interaction notes do not break queries/navigation
- links and entity mentions remain understandable

### E. Query / Retrieval Practicality

Check whether the current library can support real discovery work:

- Dataview queries or equivalent metadata browsing work on sampled cases
- client / engagement / subtype filtering behaves as expected
- flagged-note discovery is usable

### F. Known Tier 2 Risks

Specifically assess whether any of these are still meaningfully blocking:

- broken inline images
- confusing review-state surface
- diagram rendering regressions
- mixed-library confusion after `folio ingest`
- entity-link noise or ambiguity

## Session Log Requirements

The session log must be chronological and must include:

- exact notes / folders opened when feasible
- exact Dataview queries or navigation methods used
- what rendered correctly
- what rendered poorly
- any Obsidian warnings or glitches seen
- whether an issue is isolated or systemic

If sensitive titles or paths appear in raw local notes, sanitize them in the
tracked artifact. Preserve the fact pattern even when the exact source title is
omitted.

## Report Requirements

The final report must contain:

- run date
- operator
- machine / Obsidian context
- production library baseline used
- sample composition
- what worked
- what was awkward
- what would block real daily use
- gate decision
- clear next step

The report must explicitly answer:

1. Is the production `sonnet4` library good enough for real vault use?
2. Is it good enough to start PR C?
3. If not, what is the minimum blocking fix set?

## Sensitive Data Rules

Do not commit:

- screenshots containing client-sensitive content
- raw client slide text copied into the report
- secrets or tokens

You may commit:

- sanitized descriptions of issues
- counts
- categories of notes reviewed
- anonymized or generalized examples

If screenshots are useful during the run, keep them local/untracked unless they
are clearly sanitized and safe to commit.

## Deliverable Back To The User

When you finish, report:

- the gate decision
- whether the production library passed real vault validation
- the main blocking or awkward issues, if any
- whether PR C should start now
