---
id: tier4_entities_bootstrap_session_log
type: validation
status: complete
created: 2026-04-04
---

# Tier 4 Production Entities Bootstrap — Session Log

Chronological action log for the production `entities.json` bootstrap run.

## Reconstruction Note

This log was reconstructed from:

- the preserved execution prompt
- the operator-reported McKinsey-laptop run summary
- the reported changed-file set and commit id `8e8c78b`

The raw terminal history was not exported into this repo. Exact shell output
is preserved here only where it was reported explicitly. When a command or
exit code is reconstructed from the accepted task flow rather than copied from
the original terminal history, that is noted below.

---

## Session: 2026-04-04

| Time | Action | Result |
|------|--------|--------|
| Start | Confirmed production `folio.yaml` context and real library root | Success (reported) |
| +0:02 | `folio status` | Production library reachable before bootstrap (reported) |
| +0:04 | Inspected org-chart candidates under engagement workspace | Selected `ada-output/export-data/org_chart.csv` (1,531 rows) |
| +0:06 | Prepared `org_chart_folio_import.csv` via column-rename script | Success (reported) |
| +0:08 | Checked whether `entities.json` already existed | Bootstrap path proceeded against production registry state (reported) |
| +0:10 | `folio entities import org_chart_folio_import.csv` | Exit 0 (reported success); 1,492 people imported, 9 departments created |
| +0:11 | Import warnings captured | 55 alias-collision warnings reported |
| +0:12 | Import skips captured | 39 slug-collision skips reported |
| +0:14 | `folio entities generate-stubs --force` | Exit 0 (reported success); stubs regenerated to 2,635 total |
| +0:16 | `folio entities` | Exit 0 (reported success); totals reflected 1,492 people + 9 departments |
| +0:17 | `folio entities --unconfirmed` | Exit 0 (reported success); 0 unconfirmed entities |
| +0:18 | `folio entities show "<sample imported person>"` | Exit 0 reported, but the sampled entity name was not preserved in the exported summary |
| +0:20 | Checked recent interaction participants against imported org chart | `Mark Piersak`, `Andrew Lee`, and `Bradley Pearce` were not present in the CSV |
| +0:22 | Verified `entities.json` readability and size | Readable, non-empty, ~733 KB |
| +0:24 | Updated Tier 3 / Tier 4 docs and validation artifacts on the McKinsey laptop | Reported complete |
| +0:26 | Committed local changes | Reported commit `8e8c78b` |

---

## Observations

1. The bootstrap used the supported Folio CLI import path rather than a
   custom JSON writer.
2. The import auto-confirmed org-chart entities; no unresolved tail remained
   after the bootstrap.
3. The source CSV improved person / department coverage materially, but it did
   not cover every real interaction participant already present in the
   production note set.
4. The source CSV did not contain useful title data, so title-level entity
   enrichment remains limited.
