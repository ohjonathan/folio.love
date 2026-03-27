---
id: tier2_platform_model_comparison_report
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_platform_model_comparison
created: 2026-03-27
---

# Tier 2 Platform LLM Model Comparison — Final Report

## Executive Summary

This package finalizes the McKinsey-laptop model-comparison run against the
current shipped `folio convert --passes 2` runtime on `main`.

- Corpus: 40 anonymized slides from 16 real source files
- Candidates: 15 profiles across Anthropic, OpenAI, and Google
- Interim current-`main` default: `anthropic_haiku45`
- Stage winners differ: yes
- Important caveat: the committed JSONL contains `pass1` and `diagram` rows,
  but no separately instrumented `pass2` rows

The run is still decision-useful. It supports a concrete operational routing
recommendation for current Folio, and it records the exact follow-on routing
implication if stage-specific routing is implemented later.

## Run Constraints And Evidence Quality

- The scored corpus and metrics remain repo-safe through anonymized `CORP_*`
  and `SRC_*` IDs only.
- The committed metrics file directly supports Pass 1 and diagram-stage ranking.
- Conclusion 3 below is an interim best-defensible Pass 2 recommendation drawn
  from the full `--passes 2` run package and aggregate recommendation, not from
  a separately instrumented Pass 2 rubric table in the JSONL.
- No application code changes are recommended from this package alone. The only
  code-facing output here is the routing decision record.

## Conclusion 1: Best Pass 1 Profile/Model

**Winner:** `openai_gpt53` (`OpenAI / gpt-5.3-chat-latest`)

Top Pass 1 ranking from the committed run package:

| Rank | Profile | Provider | Model | Score |
|---|---|---|---|---:|
| 1 | `openai_gpt53` | OpenAI | `gpt-5.3-chat-latest` | 60.0 |
| 2 | `openai_gpt41` | OpenAI | `gpt-4.1` | 58.7 |
| 3 | `anthropic_haiku45` | Anthropic | `claude-haiku-4-5-20251001` | 58.5 |
| 4 | `openai_gpt4o` | OpenAI | `gpt-4o` | 58.0 |
| 5 | `openai_gpt41mini` | OpenAI | `gpt-4.1-mini` | 55.0 |

Decision: if Folio ever routes Pass 1 independently, use `openai_gpt53`.

## Conclusion 2: Best Diagram-Stage Profile/Model

**Winner:** `anthropic_haiku45` (`Anthropic / claude-haiku-4-5-20251001`)

Top diagram-stage ranking from the committed run package:

| Rank | Profile | Provider | Model | Score |
|---|---|---|---|---:|
| 1 | `anthropic_haiku45` | Anthropic | `claude-haiku-4-5-20251001` | 75.4 |
| 2 | `openai_gpt41mini` | OpenAI | `gpt-4.1-mini` | 74.7 |
| 3 | `openai_gpt41` | OpenAI | `gpt-4.1` | 73.2 |
| 4 | `anthropic_opus4` | Anthropic | `claude-opus-4-20250514` | 69.8 |
| 5 | `anthropic_sonnet4` | Anthropic | `claude-sonnet-4-20250514` | 60.0 |

Decision: if Folio ever routes diagram extraction independently, use
`anthropic_haiku45`.

## Conclusion 3: Best Pass 2 Profile/Model

**Interim winner:** `anthropic_haiku45` (`Anthropic / claude-haiku-4-5-20251001`)

This conclusion is intentionally concrete, because the prompt requires a named
Pass 2 recommendation. It is also intentionally caveated:

- the committed JSONL does **not** contain separate `pass2` rows
- the committed package therefore does **not** directly prove a Pass 2 winner
  through a standalone incremental-evidence rubric
- the best defensible recommendation from the full `folio convert --passes 2`
  run package is still `anthropic_haiku45`

Why this is the right interim recommendation:

- it is the strongest diagram-stage winner by a clear margin
- it is also the run package's top aggregate current-`main` recommendation
- keeping Pass 2 aligned with the aggregate winner avoids documenting an
  unsupported split between depth and the interim shipped default
- no repo-safe staged evidence in this package supports a stronger alternative
  for depth specifically

Decision: until a rerun records explicit `pass2` metrics, treat
`anthropic_haiku45` as the interim best Pass 2 model for decision-recording
purposes.

## Conclusion 4: Best Interim Single Current-`main` `convert` Default

**Winner:** `anthropic_haiku45`

Current `main` still resolves one profile for all convert-time LLM stages via
`routing.convert.primary`, so the package must also name one practical default.

Top aggregate ranking from the staged run package:

| Rank | Profile | Provider | Model | Aggregate Score |
|---|---|---|---|---:|
| 1 | `anthropic_haiku45` | Anthropic | `claude-haiku-4-5-20251001` | 51.9 |
| 2 | `openai_gpt41` | OpenAI | `gpt-4.1` | 51.3 |
| 3 | `openai_gpt41mini` | OpenAI | `gpt-4.1-mini` | 49.9 |
| 4 | `anthropic_opus4` | Anthropic | `claude-opus-4-20250514` | 48.3 |
| 5 | `openai_gpt4o` | OpenAI | `gpt-4o` | 45.8 |

Operational decision for current Folio: keep
`routing.convert.primary = anthropic_haiku45`.

## Conclusion 5: Exact Code/Config Implications If Stage Winners Differ

**Do the stage winners differ?** Yes.

- Pass 1 winner: `openai_gpt53`
- Diagram winner: `anthropic_haiku45`
- Interim Pass 2 winner: `anthropic_haiku45`
- Interim single current-`main` default: `anthropic_haiku45`

Current limitation:

- shipped `folio convert` resolves one route for the whole convert pipeline via
  `routing.convert.primary`
- there is no stage-specific route surface today for analysis, diagram, or
  depth

Documented implication for today:

- keep `routing.convert.primary = anthropic_haiku45`

Documented implication if per-stage routing is implemented later:

- add config support for:
  - `routing.analysis.primary = openai_gpt53`
  - `routing.diagram.primary = anthropic_haiku45`
  - `routing.depth.primary = anthropic_haiku45`
- update `folio/config.py` and `folio/converter.py` so each stage resolves its
  own profile rather than sharing the single convert-level route
- do **not** interpret this package as approval to implement that routing split
  yet; it is a recorded future implication only

## Practical Decision Record

| Decision Surface | Recommendation |
|---|---|
| Best Pass 1 profile/model | `openai_gpt53` |
| Best diagram-stage profile/model | `anthropic_haiku45` |
| Best interim Pass 2 profile/model | `anthropic_haiku45` |
| Best interim single current-`main` default | `anthropic_haiku45` |
| Stage winners differ | Yes |
| Current operational setting | `routing.convert.primary = anthropic_haiku45` |

## Execution Summary

- Total conversion attempts recorded in the staged package: 1280
- Successes: 897
- Timeouts: 51
- Errors: 332
- Cached skips: 312
- Total wall time recorded in the session log: 90115s (25.0h)

## Recommended Next Steps

1. Run the real engagement/library rerun on the McKinsey laptop using the
   current single-route default `anthropic_haiku45`.
2. Validate the real Obsidian vault on the McKinsey laptop.
3. Only then begin PR C: `folio enrich`.
