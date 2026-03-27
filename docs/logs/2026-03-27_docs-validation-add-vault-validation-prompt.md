---
id: log_20260327_docs-validation-add-vault-validation-prompt
type: log
status: active
event_type: tier2-model-comparison-finalization-and-tier3-validation-sequencing
source: cli
branch: main
created: 2026-03-27
---

# docs(validation): add vault validation prompt

## Summary

Finalized the Tier 2 platform model-comparison package as the decision record
for current routing, recorded the resulting Tier 3 sequencing update in the
Tier 3 tracker, added a dedicated real-library rerun prompt and then a real
vault-validation prompt, and pushed the safe documentation updates to `main`.

The key outcome of this session was a change in operational baseline:

- the model-comparison package recorded `anthropic_haiku45` as the best
  interim single-route default for current `main`
- the subsequent full-corpus real-library rerun on the managed validation laptop showed
  that the production `anthropic_sonnet4` library still outperformed the
  `haiku45` scratch rerun at full-corpus scale
- therefore the production `sonnet4` library remains the baseline for real
  vault validation and for PR C (`folio enrich`)

## Changes Made

- Promoted the Tier 2 platform model-comparison artifacts into canonical
  `docs/validation/` filenames and removed the duplicate staging folder.
- Added and pushed `docs/reference/folio-model-evaluation-methodology.md` to
  capture the stable recurring methodology behind future model-comparison runs.
- Added and pushed
  `docs/validation/tier2_real_library_rerun_prompt.md` to drive the managed-
  laptop full-corpus rerun.
- Updated
  `docs/validation/tier3_kickoff_checklist.md` to record:
  - the finalized model-comparison decision
  - completion of the real-library rerun
  - retention of the production `sonnet4` library as the Tier 3 baseline
  - vault validation as the next immediate step before PR C
- Added and pushed
  `docs/validation/tier2_real_vault_validation_prompt.md` to drive the next
  laptop validation run.
- Regenerated `Ontos_Context_Map.md` so the graph reflects the newly-added
  docs.
- Deliberately did **not** push the new `tier2_real_library_rerun_*`
  artifacts because they still contain real machine paths and engagement
  directory names that should be sanitized before committing.

## Goal

Create a decision-ready bridge from Tier 2 validation into the next Tier 3
step by:

- finalizing the model-comparison package
- determining the correct real-library baseline
- updating the Tier 3 tracker accordingly
- preparing the next operational validation prompt for the managed validation laptop

## Key Decisions

- Treat the Tier 2 model-comparison package as complete enough to record a
  routing recommendation, while clearly caveating that Pass 2 lacked separate
  instrumented rows.
- Accept the real-library rerun as the stronger production-baseline signal
  than the smaller model-comparison subset.
- Keep the production `sonnet4` library as the baseline for vault validation
  and PR C.
- Push only the safe docs changes to GitHub and hold back the rerun artifacts
  until they are sanitized.
- Make vault validation, not another rerun or per-stage routing work, the next
  immediate step.

## Alternatives Considered

- Switching the production baseline to the `haiku45` rerun library based on the
  smaller model-comparison package alone.
  Rejected because the full-corpus rerun showed lower overall quality versus
  the production `sonnet4` library.
- Pushing the rerun artifacts immediately.
  Rejected because the report, manifest, session log, and comparison JSON still
  expose real machine paths and engagement directory names.
- Starting PR C immediately after the rerun.
  Rejected because the tracker and rerun report both still require real vault
  validation first.

## Impacts

- The current Tier 3 working sequence is now:
  1. real vault validation on the managed validation laptop
  2. PR C (`folio enrich`) against the production `sonnet4` library
  3. PR D and PR E afterward
- The repo now has reusable prompts for both the real-library rerun and the
  real-vault validation stages.
- The Tier 3 tracker more accurately reflects actual production readiness and
  the correct library baseline.
- A follow-on sanitation pass is still needed before the real-library rerun
  artifacts can be safely committed.

## Testing

- `ontos map` succeeded after the new docs were added.
- No application tests were run because this session only changed validation
  docs, tracker state, and Ontos metadata.
