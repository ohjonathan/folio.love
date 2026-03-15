---
id: claude_code_prompt_diagram_pr2_provider_dpi_tiles
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-14
---

# Implementation Prompt: Diagram Extraction PR 2 - Provider Abstraction, Per-Page DPI, Tiles, and Rate Limiting

**For:** Developer Agent Team (CA lead + spawned developers)  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Roadmap:** `docs/product/04_Implementation_Roadmap.md`  
**PR 1 prompt:** `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr1_page_inspection.md`  
**Validation gate:** `docs/validation/som_validation_20260314.json`  
**Branch:** `codex/diagram-pr2-provider-dpi-tiles` from `main`  
**Test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `feat(diagrams): description`  
**PR title:** `feat: add provider runtime and tile image infrastructure for diagrams`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, decomposes the work, and owns final verification.
2. Developers implement in the order defined below. Do not parallelize dependent refactors blindly; PR 2 crosses config, provider adapters, retry policy, rendering, converter orchestration, and tests.
3. The CA lead verifies each slice with the targeted tests, then runs the full suite before opening the PR.

---

## Task Context

### What to Build

Build the PR 2 infrastructure layer for diagram extraction. This PR adds:

- a multi-image `ProviderInput` contract
- provider adapters that can format multiple images per request
- a reusable rate-limit and retry runtime
- per-page DPI rendering driven by PR 1 `PageProfile.render_dpi`
- the tiles image strategy (`global + quadrant crops`)
- a visual highlight generator for later Pass C verification work
- token usage tracking that PR 4 can feed into `_extraction_metadata`

This PR does **not** add diagram extraction prompts, `DiagramAnalysis`, Mermaid generation, or output assembly.

### Why This PR Matters

PR 4 depends on this plumbing. Without PR 2:

- the provider layer still only accepts a single image
- rendering still happens at one global DPI for the entire PDF
- there is no reusable tile-preparation layer
- there is no reusable highlight overlay generator
- retry behavior is inline and primitive
- there is no provider-aware rate limiting or token tracking

### Settled Decisions from PR 1

Do not reopen these.

1. **Set-of-Mark is not viable.**  
   The real-corpus PR 1 run in `docs/validation/som_validation_20260314.json` produced:
   - `diagram_like_som_rate = 0.76`
   - `medium_dense_som_rate = 0.722`
   - a clear dense-document failure cluster in `dense_06_target_state_arch.pdf`

   PR 2 therefore implements **tiles only**. Do not add Set-of-Mark annotation code, fallback branches, or speculative SoM feature flags.

2. **PR 1 shipped with runtime drift from the original proposal.**  
   Use the merged code, not the earlier brief:
   - `PageProfile.vector_count`, not `vector_line_count`
   - classification values now include `image_blank` and `text_light`
   - `som_viable` is lexical-only, not spatially validated
   - `inspect_pages()` degrades per page rather than failing the entire document
   - `pdfium -> pdfplumber` fallback exists for soft text-extraction failures

3. **Hybrid blank gating is already live.**  
   `folio/converter.py` currently treats:
   - `classification == "blank"` as structurally blank
   - `classification == "image_blank"` as blank **only if** the rendered histogram also says blank

   PR 2 must preserve that behavior exactly.

### Scope Boundaries

Keep PR 2 narrow.

- Build reusable image and provider infrastructure.
- Retrofit the existing consulting-slide analysis runtime to the new provider contract using a single `global` image part.
- Make per-page DPI rendering real in runtime.
- Add tile preparation and highlight utilities for later PRs.
- Add provider-aware rate limiting, retry, and token accounting.

### What Not to Build

- No Set-of-Mark implementation.
- No diagram prompts.
- No `DiagramAnalysis`.
- No prompt rewrites for Pass 1 or Pass 2.
- No Mermaid rendering.
- No `_extraction_metadata` frontmatter changes yet.
- No output note changes.
- No diagram-routing decisions in the current slide-analysis path beyond exercising the new one-image provider contract.

### Rollout Constraint

PR 2 is an infrastructure PR, not an extraction PR.

- The existing consulting-slide runtime in `folio/pipeline/analysis.py` remains the proving ground for the new provider contract.
- That runtime should send one `global` `ImagePart` only.
- Tiles and highlights are built now but not wired into the existing prompts yet.

---

## Read Before Writing

Read these in order before editing code:

1. `docs/proposals/diagram-extraction-proposal.md`
   - Focus on Design Decisions 2, 8, 14, 16 and the Stage 2 architecture section.
2. `docs/validation/som_validation_20260314.json`
   - This is the closed gate for tiles.
3. `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr1_page_inspection.md`
4. `folio/pipeline/inspect.py`
5. `folio/converter.py`
6. `folio/pipeline/images.py`
7. `folio/pipeline/analysis.py`
8. `folio/llm/types.py`
9. `folio/llm/providers.py`
10. `folio/config.py`
11. `tests/test_llm_providers.py`
12. `tests/test_images.py`
13. `tests/test_converter_integration.py`
14. `tests/test_config.py`
15. `pyproject.toml`

Do not start implementation from the original PR 2 wish list. Start from the merged repo state.

---

## Current Codebase Reality

### Current Runtime Flow

`FolioConverter.convert()` currently does:

1. `normalize.to_pdf(...)`
2. `inspect.inspect_pages(pdf_path)`
3. `images.extract_with_metadata(pdf_path, deck_dir, dpi=self.config.conversion.image_dpi)`
4. blank gating via `PageProfile.classification` plus histogram confirmation for `image_blank`
5. `text.extract_structured(...)`
6. `analysis.analyze_slides(...)`
7. blank override to `SlideAnalysis.pending()` for confirmed blank slides
8. optional `analysis.analyze_slides_deep(...)`
9. `analysis.assess_review_state(... known_blank_slides=blank_slides ...)`

PR 2 changes step 3 from one global DPI to per-page DPI, but must not disturb the blank gate in steps 4, 7, 8, or 9.

### Current Provider Layer

The repo already has multi-provider support, but it is still single-image:

- `ProviderInput` is `image_path + prompt + max_tokens`
- adapters read image bytes themselves
- `analysis.py` constructs one provider call per slide using that shape
- retry/backoff is embedded inline in `analysis.py`
- there is no shared limiter, no token accounting, and no multi-image formatting

### Current Inspection Layer

PR 1 already provides:

- `PageProfile.render_dpi`
- `PageProfile.escalation_level`
- live classifications:
  - `blank`
  - `image_blank`
  - `text`
  - `text_light`
  - `diagram`
  - `mixed`
  - `unsupported_diagram`

Do not hardcode the pre-PR1 enum list from the proposal.

### Current Image Extraction Layer

`folio/pipeline/images.py` still:

- renders all pages in one `convert_from_path(...)` call
- uses a single `dpi` argument for the entire document
- returns `ImageResult(path, slide_num, is_blank, is_tiny, width, height)`
- uses histogram blankness as diagnostic metadata

PR 2 must preserve the atomic swap semantics and current `slide-001.png` naming.

---

## Target Architecture and Required Interfaces

### New Provider Input Contract

Replace the current single-image `ProviderInput` contract with this shape in `folio/llm/types.py`:

```python
@dataclass(frozen=True)
class ImagePart:
    image_data: bytes
    role: str
    media_type: str
    detail: str | None = None


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ProviderInput:
    prompt: str
    images: list[ImagePart]
    system_prompt: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.0
```

Keep current `ProviderOutput.raw_text`, `provider_name`, and `model_name`, but add:

```python
usage: TokenUsage = TokenUsage()
```

Also replace the enum-only `ErrorDisposition` with:

```python
@dataclass(frozen=True)
class ErrorDisposition:
    kind: Literal["transient", "permanent"]
    retry_after_seconds: float | None = None
```

Optional convenience constructors are fine, but this must be the normalized data shape.

### Additional Typed Runtime Config

Add one additional frozen type in `folio/llm/types.py` and use it instead of loose tuples:

```python
@dataclass(frozen=True)
class ProviderRuntimeSettings:
    rate_limit_rpm: int
    rate_limit_tpm: int | None = None
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    allowed_endpoints: list[str] = field(default_factory=list)
    excluded_endpoints: list[str] = field(default_factory=list)
    require_store_false: bool = False


@dataclass(frozen=True)
class ExecutionProfile:
    provider: str
    model: str
    api_key_env: str
    settings: ProviderRuntimeSettings
```

Do **not** extend the existing `fallback_profiles` tuple-of-strings pattern. Replace it.

### Stage Metadata

Extend `StageLLMMetadata` without breaking current frontmatter callers. It must continue to expose:

- `provider`
- `model`
- `slide_count`
- `cache_hits`
- `cache_misses`
- `fallback_activated`
- `fallback_provider`
- `fallback_model`

Add:

- `usage_total: TokenUsage`
- `per_slide_usage: dict[int, TokenUsage]`

These are for future `_extraction_metadata`; do not surface them in frontmatter yet.

### Provider Endpoint Names

Each adapter must expose a constant endpoint name used by config validation and runtime policy checks:

- Anthropic: `messages`
- OpenAI: `chat_completions`
- Google: `generate_content`

Requests to disallowed endpoints must fail **before** network I/O with a clear permanent configuration error.

---

## Implementation Order

Implement in this order:

1. `folio/llm/types.py` and `folio/config.py`
2. `folio/llm/runtime.py`
3. `folio/llm/providers.py` and `folio/llm/__init__.py`
4. `folio/pipeline/images.py` and new `folio/pipeline/image_strategy.py`
5. `folio/converter.py`
6. `folio/pipeline/analysis.py`
7. tests

Do not start with `analysis.py`. The new contract, settings, and runtime must exist first.

---

## File-by-File Implementation Instructions

### 1. `folio/llm/types.py`

Make this the canonical place for:

- `ImagePart`
- `TokenUsage`
- `ProviderInput`
- `ProviderOutput`
- `ErrorDisposition`
- `ProviderRuntimeSettings`
- `ExecutionProfile`
- existing protocol and route/profile metadata types

Update `AnalysisProvider` so adapters accept the new input shape and expose:

- `provider_name`
- `endpoint_name`
- `create_client(api_key_env: str = "")`
- `analyze(client, model, inp: ProviderInput) -> ProviderOutput`
- `classify_error(exc: Exception) -> ErrorDisposition`

Do not remove `ResolvedLLMProfile` or `ResolvedLLMRoute`.

### 2. `folio/config.py`

Add a new top-level `providers:` block. Keep the existing `llm:` profile/routing schema unchanged.

Required defaults:

```yaml
providers:
  anthropic:
    rate_limit_rpm: 50
    rate_limit_tpm: 80000
    max_attempts: 3
    base_delay_seconds: 1.0
    max_delay_seconds: 60.0
    allowed_endpoints: [messages]
    excluded_endpoints: []
    require_store_false: false
  openai:
    rate_limit_rpm: 60
    rate_limit_tpm: null
    max_attempts: 3
    base_delay_seconds: 1.0
    max_delay_seconds: 60.0
    allowed_endpoints: [chat_completions]
    excluded_endpoints: []
    require_store_false: false
  google:
    rate_limit_rpm: 60
    rate_limit_tpm: null
    max_attempts: 3
    base_delay_seconds: 1.0
    max_delay_seconds: 60.0
    allowed_endpoints: [generate_content]
    excluded_endpoints: []
    require_store_false: false
```

Implementation requirements:

- `FolioConfig` gets a new `providers: dict[str, ProviderRuntimeSettings]` field.
- Missing `providers:` config must backfill the defaults above.
- Partial provider entries must merge onto defaults; users should only need to override the fields they care about.
- Validate:
  - supported provider keys only: `anthropic`, `openai`, `google`
  - `rate_limit_rpm > 0`
  - `rate_limit_tpm` is `None` or `> 0`
  - `max_attempts >= 1`
  - `base_delay_seconds > 0`
  - `max_delay_seconds >= base_delay_seconds`
  - endpoint allow/exclude values are known strings for that provider
  - the same endpoint is not present in both `allowed_endpoints` and `excluded_endpoints`

Do not move `openai` or `google` from the optional `llm` dependency extra in `pyproject.toml`; PR 2 does not change dependency packaging.

### 3. `folio/llm/runtime.py`

Create this new module. It is the shared retry and throttle layer for both Pass 1 and Pass 2.

Required responsibilities:

- rolling-window RPM limiter
- rolling-window best-effort TPM limiter based on **actual** `TokenUsage.total_tokens` recorded after each call
- exponential backoff with jitter for transient failures
- exact `Retry-After` override when the provider error exposes it
- max-attempt handling per request

Do not put prompt construction, JSON parsing, or fallback policy in this module.

Implement:

- a small limiter class that tracks request timestamps and token-usage timestamps over a 60-second window
- a runtime wrapper function that:
  1. validates endpoint permissions from `ProviderRuntimeSettings`
  2. waits for RPM capacity before issuing the request
  3. waits for TPM capacity **only when the rolling usage window is already at or above the cap**
  4. performs the call
  5. records actual token usage after success
  6. retries transient failures up to `max_attempts`
  7. applies `Retry-After` when present, otherwise exponential backoff with jitter

Best-effort TPM policy is deliberate:

- do **not** reserve estimated tokens before the call
- do **not** invent token counts when the provider omits usage
- if no usage is returned, record zero and continue

Because the current runtime is sequential, this limiter can be in-process and stage-scoped. Do not overbuild a cross-process coordinator.

### 4. `folio/llm/providers.py`

Refactor all adapters to accept the new `ProviderInput.images` list and return normalized `TokenUsage`.

General rules:

- adapters format requests only; they do not decide which images to send
- adapters do not resize or mutate incoming bytes
- adapters do not implement retry loops
- adapters should continue to disable SDK-level automatic retries where supported

#### Anthropic

Use one `messages.create(...)` request with:

- one user message
- one text block for the prompt
- one image block per `ImagePart`
- `source.type = "base64"`
- the incoming `media_type`

Ignore `ImagePart.detail`. Anthropic detail tuning is not part of this PR.

Normalize:

- `usage.input_tokens`
- `usage.output_tokens`
- `total_tokens = input + output`
- truncation when `stop_reason == "max_tokens"`

If the SDK exception exposes headers, parse `Retry-After` into `ErrorDisposition.retry_after_seconds`.

#### OpenAI

Use the current Chat Completions vision path, not Responses API.

Build one user message with:

- one text content part
- one `image_url` part per `ImagePart`

Each image part must be:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "data:<media_type>;base64,...",
    "detail": "<auto|high>"
  }
}
```

Rules:

- if `ImagePart.detail` is missing, send `"auto"`
- if `require_store_false` is true in settings, pass `store=False`
- normalize usage from `response.usage.prompt_tokens`, `completion_tokens`, `total_tokens`
- truncation is `finish_reason == "length"`

If the SDK exception exposes a response object with headers, parse `Retry-After`.

#### Google

Stay on the stable current SDK surface. Do **not** switch to `v1alpha` just to chase per-image media-resolution fields.

Use:

- one text part
- one inline image part per `ImagePart`

For detail handling:

- Google does not provide a stable per-image detail equivalent on the current path
- when **any** incoming image part has `detail == "high"`, set request-level high media resolution on `GenerateContentConfig`
- otherwise leave media resolution unset
- do not drop or rewrite the `ImagePart.detail` field itself; just map it conservatively at request time

Normalize usage from:

- `usage_metadata.prompt_token_count`
- `usage_metadata.candidates_token_count`
- `usage_metadata.total_token_count`

Truncation is `finish_reason == "MAX_TOKENS"` (string-normalized to uppercase).

Retry-After on Google is often not explicit. If absent, return a transient `ErrorDisposition` without `retry_after_seconds`.

### 5. `folio/llm/__init__.py`

Re-export the new public types so the rest of the repo imports from `folio.llm` remain clean.

### 6. `folio/pipeline/images.py`

Refactor runtime rendering to support per-page DPI while preserving the current public behavior for legacy callers.

Required approach:

- keep `extract(pdf_path, output_dir, dpi=150, fmt="png")` as the existing single-DPI helper
- extend `extract_with_metadata(...)` to accept:

```python
page_profiles: dict[int, PageProfile] | None = None
```

- if `page_profiles` is `None`, keep the current code path
- if `page_profiles` is present, render each page individually using:

```python
convert_from_path(pdf_path, first_page=n, last_page=n, dpi=page_dpi, fmt=fmt)
```

Implementation rules:

- `page_dpi = page_profiles.get(n).render_dpi` when present and truthy, else `dpi`
- per-page rendering still writes to `.slides_tmp`
- keep `slide-001.<fmt>` naming
- only swap `.slides_tmp -> slides` once all pages succeed
- preserve current interrupted-run recovery with `.slides_old`
- validate that each per-page render returns exactly one image

Extend `ImageResult` with:

```python
render_dpi: int = 0
```

Populate it in both code paths.

Do not change `is_blank`, `is_tiny`, width, height, or filename semantics.

### 7. `folio/pipeline/image_strategy.py`

Create this new module.

It must export:

```python
def prepare_images(page_image: Image.Image, page_profile: PageProfile) -> list[ImagePart]: ...
def crop_region(page_image: Image.Image, bbox: tuple[float, float, float, float], padding: float = 0.1) -> Image.Image: ...
def highlight_regions(page_image: Image.Image, regions: list[tuple[float, float, float, float]], colors: list[str] | None = None) -> Image.Image: ...
```

#### `prepare_images()`

Behavior:

- tile-producing classes:
  - `diagram`
  - `mixed`
  - `unsupported_diagram`
- global-only classes:
  - `text`
  - `text_light`
  - `blank`
  - `image_blank`

Global image rules:

- keep aspect ratio
- if the long edge is greater than `1568`, resize down so the long edge becomes `1568`
- if the long edge is already `<= 1568`, keep original size
- serialize to PNG bytes
- role is `global`

Quadrant rules:

- crops come from the full rendered page image, not from the resized global image
- use exact half-width and half-height splits
- non-overlapping layout:
  - `tile_q1`: top-left
  - `tile_q2`: top-right
  - `tile_q3`: bottom-left
  - `tile_q4`: bottom-right
- preserve PNG serialization

Detail rules:

- default `detail="auto"`
- if `page_profile.classification` is tile-producing **and**
  `page_profile.escalation_level in {"medium", "dense"}`, set `detail="high"` on all returned image parts

Return values:

- tile-producing pages: exactly 5 `ImagePart`s
- global-only pages: exactly 1 `ImagePart`

#### `crop_region()`

Behavior:

- normalize bbox ordering first
- treat `padding` as a percentage of bbox width and height
- clamp to image bounds
- return a new cropped image

#### `highlight_regions()`

Behavior:

- do not mutate the input image
- draw on a copy
- use thick semi-transparent rectangles
- preserve original dimensions
- cycle through a fixed palette when `colors` is omitted
- this is a global-image overlay, not a crop helper

### 8. `folio/converter.py`

Modify only the rendering integration point.

Required changes:

- pass `page_profiles=page_profiles` into `images.extract_with_metadata(...)`
- keep the current blank gate exactly as-is:
  - structural blanks from `classification == "blank"`
  - `image_blank` requires histogram confirmation
- keep `blank_slides` feeding:
  - post-pass-1 pending override
  - Pass 2 `skip_slides`
  - `assess_review_state(... known_blank_slides=blank_slides)`

Do not route tiles or highlights into the existing prompts here.

### 9. `folio/pipeline/analysis.py`

Refactor this module to use the new provider runtime and typed image parts without changing the current prompt text or JSON normalization behavior.

Required changes:

- replace the current one-image `ProviderInput(image_path=...)` usage with:

```python
ProviderInput(
    prompt=full_prompt,
    images=[ImagePart(image_data=..., role="global", media_type=..., detail="auto")],
    max_tokens=...,
    temperature=0.0,
)
```

- derive `media_type` from file suffix:
  - `.png -> image/png`
  - `.jpg` / `.jpeg -> image/jpeg`
  - fallback to `image/png`

- do **not** call `prepare_images()` here
- do **not** send tiles here
- do **not** change `ANALYSIS_PROMPT`, `DEPTH_PROMPT`, `_normalize_pass1_json()`, `_normalize_pass2_json()`, or current consulting-slide semantics

Runtime refactor requirements:

- route all provider calls through `folio.llm.runtime`
- use `ExecutionProfile` for the primary path and fallbacks
- keep the current transient-only fallback behavior:
  - retry the current provider up to `max_attempts`
  - fallback only after transient exhaustion
  - no fallback on permanent failure
  - no fallback on truncation or malformed JSON

Cache requirements:

- continue using `.analysis_cache.json` and `.analysis_cache_deep.json`
- after each miss is resolved, update the in-memory cache entry and flush it to disk immediately using the existing atomic save helpers
- do the same for deep-cache entries
- do not wait until the end of the pass to write the first successful page
- increment `_ANALYSIS_CACHE_VERSION` only if the on-disk cache structure changes

Metadata requirements:

- update `stage_meta.usage_total` and `stage_meta.per_slide_usage[slide_num]` on each successful provider call
- continue returning provider/model/fallback metadata so existing `_llm_metadata` frontmatter behavior remains intact

Degraded-page handling:

- PR 1 may produce a degraded `PageProfile` with empty `bounded_texts`
- do not assume pypdfium2 geometry or bounded text is present anywhere in PR 2 runtime code

---

## Testing Requirements

### `tests/test_llm_providers.py`

Extend this file to cover:

- Anthropic request formatting with 1 image and 5 images
- OpenAI request formatting with 1 image and 5 images
- Google request formatting with 1 image and 5 images
- per-image `detail` handling for OpenAI
- Google high-resolution mapping when any image detail is `high`
- normalized `TokenUsage` extraction for all three adapters
- `Retry-After` parsing where supported
- no regression in truncation detection

Update `tests/llm_mocks.py` if needed, but keep the mock factories small and provider-native.

### `tests/test_llm_runtime.py`

Add this new file with focused unit tests for:

- RPM throttling
- TPM throttling from actual usage
- jittered exponential backoff
- max-delay cap
- exact `Retry-After` override
- one-page failure not blocking later pages
- endpoint allow/exclude rejection before network call

Patch `time.sleep` and random jitter so tests stay deterministic.

### `tests/test_images.py`

Expand to cover:

- `extract_with_metadata(... page_profiles=...)` rendering each page at its own DPI
- mixed decks containing both `150` and `300` DPI pages
- `ImageResult.render_dpi`
- `prepare_images()` returning 1 image for non-diagram classes
- `prepare_images()` returning 5 images for diagram-like classes
- global resize to `1568` long edge when needed
- quadrant coverage and non-overlap
- `crop_region()` padding and clamp behavior
- `highlight_regions()` non-mutation and visible overlays
- degraded profile fallback (`render_dpi` missing or falsey -> `150`)

Use generated images or generated PDFs; do not add binary fixtures to git.

### `tests/test_config.py`

Expand to cover:

- loading default provider settings
- partial provider override merging
- invalid numeric settings
- invalid endpoint names
- conflicting allow/exclude endpoint configuration
- `require_store_false` parsing for OpenAI

### `tests/test_converter_integration.py`

Add one focused integration test proving:

- `converter.py` passes `page_profiles` into `images.extract_with_metadata(...)`
- `image_blank` still requires histogram confirmation after the rendering refactor

Do not rewrite the full converter integration suite around PR 2. Keep the added test narrow.

### Regression Requirement

Run the full existing suite and keep it green. Do not quote a stale test count in code comments, docs, or the PR description.

---

## Smoke Commands

Run these before opening the PR:

```bash
.venv/bin/python -m pytest tests/test_llm_providers.py -v
.venv/bin/python -m pytest tests/test_llm_runtime.py -v
.venv/bin/python -m pytest tests/test_images.py -v
.venv/bin/python -m pytest tests/test_config.py -v
.venv/bin/python -m pytest tests/test_converter_integration.py -v -k "blank or llm or image"
.venv/bin/python -m pytest tests/ -v
```

---

## Final Verification Checklist

Do not open the PR until all of these are true:

- the new prompt file exists and matches this spec
- the runtime still preserves PR 1 blank behavior
- per-page DPI is actually used in rendering, not just stored in metadata
- current consulting-slide analysis still works through the new provider contract with one `global` image
- tiles and highlights exist as reusable infrastructure but are not wired into the existing prompts
- provider calls are rate-limited and retried through `folio/llm/runtime.py`
- cache writes happen incrementally after each miss
- token usage is normalized and recorded in stage metadata
- full pytest suite passes

---

## What Not to Do

- Do not reintroduce Set-of-Mark as a branch or feature flag.
- Do not hardcode the original proposal’s outdated classification list.
- Do not change prompt text just because the provider contract changed.
- Do not make histogram blankness authoritative again.
- Do not send tiles through the current consulting-slide prompts.
- Do not switch Google to unstable API surfaces just to get per-image media resolution.
- Do not add frontmatter schema fields in this PR.
- Do not convert this into a diagram extraction PR.
