---
id: claude_code_prompt_diagram_pr2_cache_hit_provenance_fix
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-15
---

# Implementation Prompt: Diagram Extraction PR 2 - Cache-Hit Mixed-Provider Provenance Fix

**For:** Developer Agent Team (CA lead + spawned developers)  
**Parent prompt:** `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr2_provider_dpi_tiles.md`  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Branch:** `codex/diagram-pr2-provider-dpi-tiles` from `main`  
**Test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `fix(diagrams): description`  
**Scope:** narrow follow-up to close the final known PR 2 merge blocker

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end and keeps the work tightly scoped.
2. One developer patches the pass-1/pass-2 cache-hit bookkeeping.
3. One developer adds regression coverage for cache-hit provenance and frontmatter reporting.
4. The CA lead verifies targeted tests first, then runs the full suite before recommending merge.

Do not reopen the broader PR 2 design. This is a surgical follow-up.

---

## Task Context

### What To Fix

Fix the remaining mixed-provider provenance gap in PR 2.

The latest branch added `StageLLMMetadata.per_slide_providers` and updated
`folio/converter.py` to derive run-level `_llm_metadata` from that map. That
closed the miss-path provenance issue, but cache-hit paths still do not
populate the new field.

As a result, warm-cache reruns can still under-report provider usage and claim
`mixed_providers: false` even when cached slide analyses were produced by a
fallback provider.

### Reproduced Failure

This failure has already been reproduced locally:

1. Save a pass-1 cache entry under the primary route cache file with:
   - `_provider = "openai"`
   - `_model = "gpt-4o"`
2. Run `analyze_slides(...)` with:
   - `provider_name="anthropic"`
   - matching cache key and `_text_hash`
3. Observe:
   - `stats.hits == 1`
   - `stage_meta.per_slide_providers == {}`
   - `stage_meta.fallback_activated is False`

That means the follow-up fix is incomplete.

### Why This Matters

`folio/converter.py` now relies on `per_slide_providers` to emit:

- `mixed_providers`
- `pass1.providers_used`
- `pass2.providers_used`

If cache hits are omitted from that map, frontmatter still misreports the
actual provenance of the analyses being reused.

---

## Scope Boundaries

Keep this follow-up narrow.

- Fix cache-hit provenance bookkeeping in pass 1 and pass 2.
- Keep `_llm_metadata` reporting internally consistent on warm-cache reruns.
- Add regression tests that fail on the current branch and pass after the fix.

Do not:

- change prompts
- change extraction logic
- redesign `_llm_metadata`
- change provider runtime behavior
- change cache invalidation rules
- add new frontmatter fields beyond what already exists
- widen PR 2 scope

---

## Read Before Writing

Read these in order before editing code:

1. `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr2_provider_dpi_tiles.md`
2. `folio/pipeline/analysis.py`
3. `folio/converter.py`
4. `folio/llm/types.py`
5. `tests/test_analysis_cache.py`
6. `tests/test_converter_integration.py`
7. `tests/test_llm_providers.py`

---

## Current Codebase Reality

### Pass 1 Cache-Hit Path

In `folio/pipeline/analysis.py`, pass-1 cache hits currently do:

- load `cached_entry`
- validate `_text_hash`
- `SlideAnalysis.from_dict(cached_entry)`
- increment hit count
- `continue`

They do **not** copy cached `_provider` / `_model` into
`stage_meta.per_slide_providers`.

### Pass 2 Deep Cache-Hit Path

In `folio/pipeline/analysis.py`, pass-2 deep cache hits currently do:

- load `cached`
- validate `_text_hash` and `_pass1_hash`
- merge cached evidence / reassessments
- increment hit count
- `continue`

They also do **not** copy cached `_provider` / `_model` into
`stage_meta.per_slide_providers`.

### Existing Data Already Available

The cache entries already persist provenance:

- pass 1 cache stores `_provider` and `_model`
- pass 2 deep cache stores `_provider` and `_model`

This is not a schema-design problem. It is a bookkeeping omission on read.

---

## Required Behavior

### 1. Pass 1 Cache Hits Must Populate `per_slide_providers`

When pass 1 uses a cached analysis entry:

- populate `stage_meta.per_slide_providers[slide_num]`
- prefer cached `_provider` / `_model`
- if either field is missing, fall back to the active route primary:
  - provider = `provider_name`
  - model = `model`

### 2. Pass 2 Deep Cache Hits Must Populate `per_slide_providers`

When pass 2 uses a cached deep entry:

- populate `stage_meta.per_slide_providers[slide_num]`
- prefer cached `_provider` / `_model`
- if either field is missing, fall back to the active route primary:
  - provider = `provider_name`
  - model = `model`

### 3. Fallback Summary Flags Must Stay Honest

If a cache-hit provider differs from the active route primary, the stage-level
summary metadata must remain internally consistent.

Minimum requirement:

- the stage metadata must not claim a pure-primary run when cached entries show
  fallback-provider provenance

You may satisfy this either by:

1. updating `fallback_activated` / `fallback_provider` / `fallback_model` on
   cache-hit reads, or
2. making converter-level reporting derive fallback usage from
   `per_slide_providers` instead of only the summary booleans

Choose the smaller, clearer fix. Do not implement both unless necessary.

### 4. Backward Compatibility

Old cache entries may lack `_provider` / `_model`.

Required behavior:

- no crash
- no invalidation just because those fields are missing
- fallback to primary provider/model for reporting only

### 5. No Behavior Changes Outside Provenance

This fix must not alter:

- blank gating
- retry/fallback execution behavior
- cache keys
- cache version markers
- image rendering
- provider request formatting

---

## Required Code Changes

### `folio/pipeline/analysis.py`

Patch both cache-hit branches:

- pass 1 cached-hit branch
- pass 2 deep-cache-hit branch

Add small local helpers if they reduce duplication, for example:

```python
def _cached_provider_model(
    cached: dict,
    primary_provider: str,
    primary_model: str,
) -> tuple[str, str]: ...
```

If you add a helper:

- keep it private to `analysis.py`
- keep it trivial and well-named
- do not over-abstract

### `folio/converter.py`

Only edit if needed to keep `_llm_metadata` consistent after the cache-hit fix.

If the cleanest solution is to derive `fallback_used` from
`per_slide_providers`, that is acceptable. If not needed, leave converter
alone.

### `folio/llm/types.py`

Only edit if absolutely necessary. The new `per_slide_providers` field is
already present and should likely remain the only added field.

---

## Test Requirements

Add focused regression coverage for the exact bug.

### 1. Pass 1 Cache-Hit Provenance Test

Add a test that:

- writes a pass-1 cache entry with cached `_provider="openai"` and
  `_model="gpt-4o"`
- runs `analyze_slides(...)` with `provider_name="anthropic"`
- gets a cache hit
- asserts `stage_meta.per_slide_providers[1] == ("openai", "gpt-4o")`

Also assert the chosen fallback-summary behavior if your implementation updates
that metadata.

### 2. Pass 2 Deep Cache-Hit Provenance Test

Add a test that:

- writes a compatible deep-cache entry with `_provider` / `_model`
- triggers a deep cache hit
- asserts `stage_meta.per_slide_providers[slide_num]` is populated correctly

### 3. Backward-Compatibility Test

Add a test for cache entries missing `_provider` / `_model`:

- cache hit still succeeds
- provider/model fall back to primary route values
- no exception is raised

### 4. Converter / Frontmatter Reporting Test

Add an integration-style test proving the actual user-visible bug is fixed.

Minimum expectation:

- warm-cache conversion no longer reports a pure-primary run when cached slide
  provenance shows more than one provider

A good shape is:

- one slide with cached primary provenance
- one slide with cached fallback provenance
- verify `_llm_metadata.convert.mixed_providers is True`
- verify `pass1.providers_used` contains both providers

If your implementation derives `fallback_used` from cached provenance, assert
that too.

---

## Verification Commands

Run these before concluding:

```bash
.venv/bin/python -m pytest tests/test_analysis_cache.py tests/test_converter_integration.py tests/test_llm_providers.py -v
.venv/bin/python -m pytest tests/ -q
```

If any test is skipped because an optional SDK is unavailable, say so explicitly
in the closeout.

---

## Acceptance Criteria

The fix is complete only if all of the following are true:

1. Pass-1 cache hits populate `per_slide_providers`.
2. Pass-2 deep cache hits populate `per_slide_providers`.
3. Warm-cache provenance no longer under-reports mixed-provider runs.
4. Missing cached `_provider` / `_model` does not crash or invalidate cache.
5. Full test suite passes.

If you find yourself editing unrelated PR 2 behavior, stop and shrink the
change.
