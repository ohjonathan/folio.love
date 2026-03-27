---
id: tier2_platform_model_comparison_chat_log
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_platform_model_comparison
created: 2026-03-27
---

# Chat Log — Tier 2 Platform Model Comparison

## Platform

Cursor IDE (Agent mode). Raw transcript export was not supported by the
platform, so this file is the decision-and-rationale substitute allowed by the
validation prompt. The raw transcript remains in Cursor's workspace-local agent
transcript storage outside this repo.

## Session Summary

**Date:** 2026-03-22  
**Operator:** Jonathan Oh  
**Agent:** Ada (Cursor Agent, claude-4.6-opus-high-thinking)

### Key Decisions Made

1. **Workspace scope:** Execute in an isolated companion workspace using the
   installed `folio-love 0.2.0` package rather than the repo checkout itself.
2. **Candidate set:** Score 15 profiles across Anthropic, OpenAI, and Google.
   Candidate expansion reflected gateway availability rather than the original
   idealized shortlist.
3. **Google provider patch:** Patch the installed Google provider module to use
   the correct Vertex AI auth mode for the gateway-backed environment.
4. **Corpus:** Use a 40-slide, 16-source real corpus with anonymized `CORP_*`
   and `SRC_*` IDs in committed artifacts.
5. **Artifacts:** Stage raw outputs under a validation-output staging folder,
   then promote sanitized canonical artifacts into the repo.
6. **Execution strategy:** Run profiles sequentially with resume logic rather
   than parallelizing same-provider traffic across the corpus.

### Rationale For Key Choices

- **Large candidate set:** The operator requested broad provider coverage.
  Gateway constraints prevented the originally desired GPT-5.4 family and
  limited Anthropic availability, so the final scored set reflects what the
  environment could actually run.
- **Sequential execution:** Slower, but lower-risk for provider rate limits and
  PowerPoint-backed normalization behavior during a long real-corpus run.
- **Gold reference shortcut:** The run reused prior converted-output state in
  the companion workspace as the working reference instead of creating a fresh
  manual annotation workflow inside the execution environment.

### Outcome Captured For Repo Use

- Best Pass 1 recommendation: `openai_gpt53`
- Best diagram-stage recommendation: `anthropic_haiku45`
- Best interim Pass 2 recommendation: `anthropic_haiku45`
- Best current single-route `main` default: `anthropic_haiku45`
- Follow-on implication if stage routing is later implemented:
  - `routing.analysis.primary = openai_gpt53`
  - `routing.diagram.primary = anthropic_haiku45`
  - `routing.depth.primary = anthropic_haiku45`

### Limits Of This Substitute

- This is not a verbatim chat export.
- It preserves the major choices and rationale that explain the run outcome.
- The chronological command-level record lives in the session log.
