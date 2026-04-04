---
id: log_20260404_production-ingest-validation-closes-tier-3-ec-1-fo
type: log
status: active
event_type: decision
source: cli
branch: main
created: 2026-04-04
---

# Production ingest validation closes Tier 3 EC-1 follow-up

## Summary

Recorded a successful real production `folio ingest` run on the McKinsey
library and used it to close the carried-forward EC-1 field-validation gap
from the Tier 3 closeout package.

## Goal

Capture the first production-library interaction ingest as explicit evidence so
the roadmap and closeout docs no longer describe EC-1 as awaiting real-world
validation.

## Key Decisions

1. Treat the operator-reported production ingest run as sufficient evidence to
   close the EC-1 follow-up because it includes runtime, output location, and
   quality metadata from the real production library.
2. Update the Tier 3 closeout report as a post-closeout addendum rather than
   rewriting the original 2026-03-31 run context.
3. Remove EC-1 from the active Tier 4 next-actions list while leaving the
   production `entities.json` bootstrap as the remaining operational
   prerequisite.
4. Preserve the exact note identity in the record:
   `us_bank_technologyresilience2026_interview_20260324_20260324_interview_mark_piersak_for_kubernetes`
   (`20260324 Interview Mark Piersak For Kubernetes`).

## Alternatives Considered

- Leave the production ingest result in chat only. Rejected because the active
  roadmap and closeout docs would remain stale.
- Rewrite the closeout report as if the March 31 run had included this ingest.
  Rejected because that would blur the distinction between the original
  closeout evidence and the later follow-up run.
- Keep EC-1 listed as a Tier 4 prerequisite even after the production run.
  Rejected because the reported ~25-second ingest closes the specific <60s
  field-validation gap.

## Impacts

- EC-1 now has both automated closeout evidence and real production evidence.
- The remaining immediate Tier 4 operational prerequisite is production
  `entities.json` import/bootstrap.
- The real production ingest produced an interaction note under
  `ada-folio/library/us_bank/technologyresilience2026/interactions/` with note
  id
  `us_bank_technologyresilience2026_interview_20260324_20260324_interview_mark_piersak_for_kubernetes`
  and title `20260324 Interview Mark Piersak For Kubernetes`.
- The note recorded participants `Mark Piersak`, `Andrew Lee`, and
  `Bradley Pearce`, review status `clean`, extraction confidence `0.96`, 10/10
  validated claims, 7 generated tags, and the expected L0 interaction sections
  including a preserved Raw Transcript callout.
