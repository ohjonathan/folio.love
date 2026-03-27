---
id: tier2_real_library_rerun_prompt
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-27
---

# Task: Tier 2 Real Library Rerun After Model-Comparison Decision

## What You're Doing

This is a **real engagement rerun** on the **McKinsey laptop** after the Tier 2
platform model-comparison decision was finalized.

This is **not** an implementation task.

This run exists to answer one operational question:

> Does the current shipped Folio runtime produce a strong enough real-library
> baseline, using the chosen single-route model, to justify starting PR C
> (`folio enrich`)?

The rerun must use the current recorded operating decision from
`tier2_platform_model_comparison_report.md`:

- `routing.convert.primary = anthropic_haiku45`

Do **not** implement per-stage routing here. That remains a future implication
only.

## Required Outputs

Produce the standard validation artifacts in `docs/validation/` using the label
`tier2_real_library_rerun`:

1. `tier2_real_library_rerun_prompt.md`
2. `tier2_real_library_rerun_report.md`
3. `tier2_real_library_rerun_session_log.md`
4. `tier2_real_library_rerun_chat_log.md`

If needed, you may also create:

5. `tier2_real_library_rerun_manifest.md`

Use the optional manifest only if it materially helps track multiple source
directories or rerun batches.

## Read Before Doing Anything

Read these first:

1. [AGENTS.md](/Users/jonathanoh/Dev/folio.love/AGENTS.md)
2. [tier2_platform_model_comparison_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_platform_model_comparison_report.md)
3. [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md)
4. [tier2_accelerated_precloseout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_report.md)
5. [tier1_rerun_guide.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_guide.md)
6. Current runtime/code surface:
   - [folio/cli.py](/Users/jonathanoh/Dev/folio.love/folio/cli.py)
   - [folio/config.py](/Users/jonathanoh/Dev/folio.love/folio/config.py)
   - [folio/converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [folio/tracking/registry.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/registry.py)

## Environment Rules

Use the machine that has:

- the real engagement corpus
- working provider credentials
- the intended real library / vault target
- PowerPoint automation access, if PPTX files are in scope

For API keys:

- use `tests/validation/.env` if needed
- do not commit it
- delete it immediately after the run

For PowerPoint/TCC-sensitive reruns:

- use **Terminal.app** for the actual `folio batch` commands if the managed-mac
  PPTX automation path depends on Terminal automation permissions
- Cursor can still be used to coordinate, inspect outputs, and write the
  validation artifacts

## Scope

This rerun should validate the **current real library baseline** before PR C.

In scope:

- rerunning real engagement source directories with the current chosen model
- refreshing the real library baseline with `--no-cache`
- checking for runtime failures, stale behavior, and operational friction
- capturing whether the resulting library is good enough to proceed to real
  vault validation

Out of scope:

- implementing per-stage routing
- changing Folio code
- starting `folio enrich`
- retroactive provenance work
- synthetic-only substitutes for the real corpus

## Operational Decision You Must Respect

Use the current single-route default:

- `--llm-profile anthropic_haiku45`

Run with:

- `--passes 2`
- `--no-cache`

Why:

- `anthropic_haiku45` is the recorded best interim current-`main` default
- `--passes 2` exercises the shipped convert-time LLM surface that matters for
  future enrichment readiness
- `--no-cache` is mandatory because this is a rerun validation, not a cache-hit
  check

## Important Runtime Truths

1. `folio batch` is **not recursive**. Run it once per source directory that
   directly contains files you want to process.
2. PPTX and PDF directories may need separate invocations because pattern
   matching is explicit.
3. This is a real-library rerun, so you must be clear whether you are writing
   into:
   - the production library root, or
   - a scratch validation library root
4. If the current `folio.yaml` points at the real production vault and that is
   not intended, stop and record the blocker before running.
5. `folio refresh` skips interaction entries; that is expected and not a rerun
   failure.

## Stage 1: Preflight

Before running anything heavy:

1. Confirm the active branch / install / runtime you are using.
2. Confirm the effective library root.
3. Confirm the real source directories that will be rerun.
4. Confirm the chosen LLM profile is available:
   - `anthropic_haiku45`
5. Decide whether this run targets:
   - the production library, or
   - a scratch validation library

Record all of that in the session log.

If any of those are unclear, stop and record a blocker instead of guessing.

## Stage 2: Execute The Rerun

For each source directory, run the correct command shape.

### PPTX directories

```bash
folio batch "/ABS/PATH/TO/SOURCE_DIR" \
  --pattern "*.pptx" \
  --client "<Client>" \
  --engagement "<Engagement>" \
  --passes 2 \
  --no-cache \
  --llm-profile anthropic_haiku45 \
  --dedicated-session \
  --note "tier2-real-library-rerun-2026-03-27"
```

### PDF directories

```bash
folio batch "/ABS/PATH/TO/SOURCE_DIR" \
  --pattern "*.pdf" \
  --client "<Client>" \
  --engagement "<Engagement>" \
  --passes 2 \
  --no-cache \
  --llm-profile anthropic_haiku45 \
  --note "tier2-real-library-rerun-2026-03-27"
```

After the batch set finishes:

```bash
folio status --refresh
folio scan
```

Record each command, exit code, elapsed time, and any failure text in the
session log.

## Stage 3: Evaluate The Rerun

Your report must answer:

1. Did the rerun complete across the intended real source directories?
2. What failed, and were the failures systemic or isolated?
3. Did the chosen model/profile appear operationally acceptable on the real
   corpus?
4. Is the resulting library baseline good enough to proceed to real vault
   validation?
5. Based on this rerun alone, should PR C remain blocked or can it proceed to
   the next validation step?

## Report Requirements

The final report must contain:

- run date
- operator
- machine context
- branch / install context
- effective model decision used
- source directory inventory
- whether production or scratch library was targeted
- command inventory
- success/failure totals
- notable runtime failures
- whether `status --refresh` and `scan` behaved as expected
- gate decision:
  - `PASS TO VAULT VALIDATION`
  - `PARTIAL / FIX KNOWN ISSUES FIRST`
  - `BLOCKED`

The report should end with a short next-step section. If the rerun is good
enough, the next step is:

1. real vault validation on the McKinsey laptop
2. then PR C

## Sensitive Data Rules

Do not commit raw client slide text, screenshots, or secrets.

You may describe:

- source directories at a high level
- corpus scale
- failure classes
- durations
- counts

If a raw session transcript contains client-sensitive paths or filenames, keep
the raw data out of tracked artifacts and write a sanitized tracked summary
instead. State that choice explicitly in the chat log or session log.

## Deliverable Back To The User

When you finish, report:

- what commands were run
- whether the rerun passed, partially passed, or blocked
- the main failure classes, if any
- whether the resulting library is ready for real vault validation
- what should happen next
