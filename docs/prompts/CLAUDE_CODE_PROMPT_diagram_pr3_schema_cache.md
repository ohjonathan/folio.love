---
id: claude_code_prompt_diagram_pr3_schema_cache
type: atom
status: draft
ontos_schema: 2.2
generated_by: codex
created: 2026-03-15
---

# Implementation Prompt: Diagram Extraction PR 3 - Schema, Routing, Cache, and Deserialization

**For:** Developer Agent Team (CA lead + spawned developers)  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Grounded against:** `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr2_provider_dpi_tiles.md`, `docs/validation/som_validation_20260314.json`, and the merged runtime in `folio/`  
**Branch:** `codex/diagram-pr3-schema-cache` from `main`  
**Test baseline:** `693 tests collected`  
**Primary test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `feat(diagrams): description`  
**PR title:** `feat: add diagram analysis schema, routing, and cache foundation`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, grounds in the live repo, and owns final verification.
2. Developers implement in the order defined below. Do not parallelize dependent refactors blindly; PR 3 crosses public data models, cache serialization, converter routing, and output compatibility.
3. The CA lead verifies each slice with the targeted tests, then runs the full suite before opening the PR.

---

## Task Context

### What to Build

Build the PR 3 data-model foundation for diagram extraction:

- polymorphic deserialization so diagram payloads are never dropped
- `DiagramAnalysis(SlideAnalysis)` plus nested graph dataclasses
- spatial IoU helpers for cross-run node ID inheritance
- converter routing that excludes diagram pages from the current Pass 2 path
- cache versioning extensions for diagram schema and pipeline dimensions
- output compatibility so diagram analyses survive markdown/frontmatter assembly

This PR does **not** add diagram prompts, Pass A/B/C execution, Mermaid generation, or standalone diagram-note output.

### Why This PR Matters

PR 4 through PR 6 depend on this shape being correct:

- PR 4 needs a place to store diagram extraction results
- PR 4 and PR 6 need cross-run ID inheritance so human overrides survive reprocessing
- PR 5 needs a stable graph object for deterministic Mermaid/prose generation
- PR 6 needs polymorphic analyses to flow through output assembly without being dropped

The highest-risk failure mode in this PR is silent diagram data loss during deserialization. That is why the factory and call-site audit are the first deliverable.

### Settled Repo Reality from PR 1 and PR 2

Do not reopen these:

1. **Use the live PR 1 classification set.**  
   The repo now uses:
   - `blank`
   - `image_blank`
   - `text`
   - `text_light`
   - `diagram`
   - `mixed`
   - `unsupported_diagram`

   Do not hardcode the pre-PR1 enum list from the original proposal.

2. **Hybrid blank gating is already live.**  
   In `folio/converter.py`:
   - structural blanks are `classification == "blank"`
   - `image_blank` is blank **only if** histogram blankness agrees

   PR 3 must preserve this behavior exactly.

3. **`inspect_pages()` degrades per-page.**  
   Some `PageProfile` entries may be partial or fallback profiles. Routing must not assume every page has complete inspection data.

4. **`per_slide_providers` is the provenance source of truth.**  
   PR 2 review hardened this. Do not invent a competing per-pass summary path in PR 3.

5. **Partial-progress cache durability is an invariant.**  
   Pass 1 and Pass 2 already flush cache after every resolved miss. PR 3 must preserve that exact behavior.

6. **The current runtime still sends one `global` image only.**  
   PR 2 added tiles and highlights as infrastructure, but the existing consulting-slide prompts still run through a single-image `global` path. PR 3 does not change that.

### Scope Boundaries

Keep PR 3 narrow.

- Build the types and routing needed to hold diagram results safely.
- Keep the current consulting-slide Pass 1 behavior for now.
- Exclude diagram pages from the current Pass 2 consulting-slide analysis.
- Ensure output consumers tolerate `DiagramAnalysis`.

### What Not to Build

- No diagram extraction prompts
- No Pass A / Pass B / Pass C execution
- No Mermaid generation
- No output assembly redesign
- No standalone diagram notes
- No provider/runtime refactor beyond preserving PR 2 invariants
- No new frontmatter fields for diagram review state

### One Important Superseded Review

`docs/prompts/diagram_consolidation_review.md` recommended a union type (`SlideAnalysis | DiagramAnalysis`).

That recommendation is obsolete for PR 3.

The settled design is:

- `DiagramAnalysis` **inherits from** `SlideAnalysis`
- `SlideAnalysis.from_dict()` is a **polymorphic factory**
- downstream compatibility is achieved through subclassing plus `isinstance(...)` where model-type branching is needed

Do not implement the older union-type recommendation.

---

## Read Before Writing

Read these in order before editing code:

1. `docs/proposals/diagram-extraction-proposal.md`
   - Focus on PR 3, the stable-ID rationale, and the mixed-page collision notes.
2. `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr2_provider_dpi_tiles.md`
3. `folio/pipeline/analysis.py`
4. `folio/converter.py`
5. `folio/output/frontmatter.py`
6. `folio/output/markdown.py`
7. `folio/pipeline/inspect.py`
8. `tests/test_grounding.py`
9. `tests/test_analysis_cache.py`
10. `tests/test_converter_integration.py`
11. `tests/test_frontmatter.py`
12. `tests/test_pipeline_integration.py`

Do not start from the original PR 3 brief alone. Start from the merged repo.

---

## Current Codebase Reality

### Analysis Models and Cache Live in `folio/pipeline/analysis.py`

This is the public import surface today. Keep it stable in PR 3.

Current state:

- `SlideAnalysis` lives here
- `SlideAnalysis.to_dict()` / `from_dict()` are slide-only and diagram-unaware
- pass-1 cache-hit deserialization currently routes through `SlideAnalysis.from_dict(...)`
- pass-1 and pass-2 caches already use SHA-256-based image hashes
- `_ANALYSIS_CACHE_VERSION` is currently `2`
- cache metadata currently includes:
  - `_cache_version`
  - `_prompt_version`
  - `_model_version`
  - `_provider_version`
  - `_extraction_version`

PR 3 is therefore **not** a migration off Python `hash()`. It is a stable cache-versioning extension for schema/pipeline dimensions.

### Converter Flow

`FolioConverter.convert()` currently does:

1. normalization
2. `inspect.inspect_pages(pdf_path)`
3. image extraction
4. hybrid blank detection
5. text extraction
6. `analysis.analyze_slides(...)`
7. blank override to `SlideAnalysis.pending()` for confirmed blank slides
8. optional `analysis.analyze_slides_deep(...)` with `skip_slides=blank_slides`

PR 3 changes the routing around steps 6 through 8:

- `unsupported_diagram` must bypass both passes
- `diagram`, `mixed`, and `unsupported_diagram` must skip the current Pass 2 consulting-slide path
- mixed pages must still produce exactly one analysis object keyed by page number

### Output Consumers Still Assume `SlideAnalysis`

`folio/output/markdown.py` and `folio/output/frontmatter.py` both type analyses as `dict[int, SlideAnalysis]`.

They do not know about `DiagramAnalysis` yet.

PR 3 does **not** add diagram-specific rendering, but it must make these consumers polymorphism-safe so diagram analyses survive the existing output path instead of crashing or being dropped.

### Known Current Deserialization Sites

The CA already confirmed these live call sites:

1. `folio/pipeline/analysis.py`
   - pass-1 cache-hit path deserializes with `SlideAnalysis.from_dict(...)`
2. `tests/test_grounding.py`
   - direct round-trip and backward-compat deserialization tests

You must do a fresh repo grep before editing and include the final audited list in the PR summary or session log.

Use a command like:

```bash
rg -n "SlideAnalysis\\.from_dict|from_dict\\(d\\)|analysis_cache|to_dict\\(" folio tests
```

If you find any additional deserialize path, route it through the factory before merging.

---

## Required Data Model

Add the following public models in `folio/pipeline/analysis.py`. Keep names and semantics, but adapt minor implementation details to repo conventions if needed.

```python
@dataclass
class DiagramGroup:
    id: str
    name: str
    contains: list[str] = field(default_factory=list)
    contains_groups: list[str] = field(default_factory=list)


@dataclass
class DiagramNode:
    id: str
    label: str
    kind: str = "unknown"
    group_id: str | None = None
    technology: str | None = None
    source_text: str = "vision"
    bbox: tuple[float, float, float, float] | None = None
    confidence: float = 1.0
    verification_evidence: str | None = None


@dataclass
class DiagramEdge:
    id: str
    source_id: str
    target_id: str
    label: str | None = None
    direction: str = "->"
    confidence: float = 1.0
    evidence_bbox: tuple[float, float, float, float] | None = None
    verification_evidence: str | None = None


@dataclass
class DiagramGraph:
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    groups: list[DiagramGroup] = field(default_factory=list)
    schema_version: str = "1.0"


@dataclass
class DiagramAnalysis(SlideAnalysis):
    diagram_type: str = "unknown"
    graph: DiagramGraph | None = None
    mermaid: str | None = None
    description: str | None = None
    uncertainties: list[str] = field(default_factory=list)
    extraction_confidence: float = 0.0
    confidence_reasoning: str = ""
    review_questions: list[str] = field(default_factory=list)
    review_required: bool = False
    abstained: bool = False
```

### Data-Model Invariants

These are settled:

- `DiagramAnalysis` inherits from `SlideAnalysis`
- mixed pages use **one** `DiagramAnalysis` object keyed by slide number
- inherited `SlideAnalysis` fields hold the page’s consulting-slide text analysis
- diagram fields hold the diagram graph
- `mermaid` and `description` are deterministic downstream fields only; never accept them from LLM output
- node IDs are arbitrary (`node_1`, `node_2`, etc.), not hash-based
- edge IDs are derived from `source_id + target_id`
- nested groups are represented through `contains_groups`

### Serialization Requirements

Use explicit `to_dict()` / `from_dict()` methods for every diagram model.

Do **not** use raw `dataclasses.asdict()` for the public wire shape.

Required behavior:

- tuple bbox fields serialize cleanly and deserialize back to tuples
- missing diagram fields fall back to defaults
- unknown extra keys are ignored gracefully
- malformed nested values degrade to safe defaults instead of crashing
- `DiagramAnalysis.to_dict()` includes inherited `SlideAnalysis` fields plus diagram fields
- `SlideAnalysis.to_dict()` remains backward compatible for existing caches and tests

---

## Implementation Order

Implement in this order:

1. `SlideAnalysis.from_dict()` factory and deserialize call-site audit
2. diagram dataclasses and explicit serialization
3. IoU helpers and ID inheritance helpers
4. converter routing changes
5. cache metadata/signature extensions
6. output compatibility and tests

Do not start with converter or cache changes before the factory exists.

---

## File-by-File Instructions

### 1. `folio/pipeline/analysis.py`

This is the main PR 3 file.

#### A. Turn `SlideAnalysis.from_dict()` into a factory

Implement:

- a small set/constant of diagram marker fields
- `SlideAnalysis.from_dict(cls, d)` that:
  - returns `SlideAnalysis()` for empty or non-dict input
  - dispatches to `DiagramAnalysis.from_dict(d)` when any diagram marker field is present
  - otherwise preserves existing slide-only behavior

Use these diagram markers at minimum:

- `diagram_type`
- `graph`
- `mermaid`
- `description`
- `uncertainties`
- `review_required`
- `abstained`
- `extraction_confidence`
- `review_questions`

Treat `graph` alone as sufficient to route to `DiagramAnalysis`.

#### B. Add diagram dataclasses here

Keep the public import surface in `analysis.py`.

If you extract internal helpers to a private module, re-export the public classes from `analysis.py` and keep existing imports working.

#### C. Add diagram helper methods

Implement in `analysis.py`:

- bbox normalization helper
- IoU helper
- greedy node matching helper
- node-ID inheritance helper
- edge-ID rewrite helper
- a top-level public helper:

```python
def match_nodes_by_iou(
    new_nodes: list[DiagramNode],
    cached_nodes: list[DiagramNode],
    threshold: float = 0.80,
) -> dict[str, str]:
```

Algorithm:

1. consider only nodes with bboxes on both sides
2. compute all pair IoUs
3. sort candidate matches by highest IoU first
4. greedily assign one-to-one matches
5. inherit IDs only for `IoU >= threshold`
6. leave unmatched or no-bbox nodes untouched

When inherited node IDs change, edge IDs must be recomputed from the final `source_id` and `target_id`.

#### D. Add a minimal slide-number-aware Pass 1 API

Extend `analyze_slides(...)` with:

```python
slide_numbers: list[int] | None = None
```

Requirements:

- default `None` preserves current sequential behavior
- if provided, the list length must match `image_paths`
- cache results must be keyed by the real slide number from `slide_numbers`
- `stage_meta.per_slide_providers` and `per_slide_usage` must also use real slide numbers
- current callers that omit `slide_numbers` must remain unchanged

Do **not** change the consulting-slide prompt or provider call path in PR 3.

#### E. Keep Pass 2 keyed by real slide numbers

`analyze_slides_deep(...)` already works with slide-number-keyed pass-1 results.

Do not rewrite its public contract. Only make sure it works cleanly when:

- pass-1 results include `DiagramAnalysis`
- `skip_slides` now includes diagram-like pages
- some pages never went through pass 1 because they were `unsupported_diagram`

#### F. Extend cache versioning, do not replace page identity

Keep:

- pass-1 cache entries keyed by page-image SHA hash
- pass-2 cache entries keyed by `f"{image_hash}_deep"`

Do **not** replace this with a new document-level cache-key scheme.

Instead:

1. bump `_ANALYSIS_CACHE_VERSION` from `2` to `3`
2. add explicit version constants such as:
   - `_DIAGRAM_SCHEMA_VERSION = "1.0"`
   - `_DIAGRAM_PIPELINE_VERSION = "pr3-routing-v1"`
   - `_IMAGE_STRATEGY_VERSION = "global-only-v1"`
3. add stable SHA-256 signature helpers derived from:
   - prompt hash
   - diagram schema version
   - diagram pipeline version
   - image strategy version
   - provider name
   - model name

Recommended pattern:

```python
def _stable_signature(*parts: str) -> str:
    ...
```

Store these markers in both caches, for example:

- `_schema_version`
- `_pipeline_version`
- `_image_strategy_version`
- `_cache_signature`

Loaders must invalidate when any of these drift.

Keep existing markers too:

- `_prompt_version`
- `_model_version`
- `_provider_version`
- `_extraction_version`

PR 3 goal is explicit invalidation when the diagram schema/pipeline changes, not a wholesale cache rewrite.

#### G. Preserve partial-progress durability

Do not touch the current per-miss cache flush behavior except to carry the new metadata.

The following must remain true:

- page 1 success + page 2 failure still preserves page 1 on disk
- warm cache hits still populate `per_slide_providers`
- cache-hit and miss paths both preserve provider provenance

### 2. `folio/converter.py`

Add routing for diagram-aware analyses while preserving current blank handling.

#### A. Derive slide sets from live classifications

Compute at minimum:

- `structural_blanks`
- `image_blanks_confirmed`
- `blank_slides`
- `unsupported_diagram_slides`
- `diagram_like_slides` for classifications in `{"diagram", "mixed", "unsupported_diagram"}`
- `pass1_slide_numbers` for all slides except `unsupported_diagram`

Do not treat `text_light` as diagram-like.

#### B. Skip Pass 1 for `unsupported_diagram`

Build filtered pass-1 inputs:

- `pass1_image_paths`
- `pass1_slide_numbers`

Call:

```python
analysis.analyze_slides(..., image_paths=pass1_image_paths, slide_numbers=pass1_slide_numbers)
```

Then insert placeholder analyses for `unsupported_diagram` slides before Pass 2.

Use an abstained `DiagramAnalysis` placeholder with:

- inherited slide fields sourced from `SlideAnalysis.pending("Diagram extraction pending — unsupported diagram type")`
- `diagram_type="unsupported"`
- `graph=None`
- `review_required=True`
- `abstained=True`

No LLM call should occur for these pages.

#### C. Coerce `diagram` and `mixed` pages to `DiagramAnalysis`

After pass 1 returns, but before Pass 2:

- replace pass-1 `SlideAnalysis` objects for `diagram` and `mixed` pages with `DiagramAnalysis`
- copy inherited slide-analysis fields across exactly
- initialize diagram fields to empty/default values

Do **not** create dual entries for mixed pages. The slide-number dict must still have one entry for that page.

If a page is already a `DiagramAnalysis`, leave it alone.

#### D. Exclude diagram pages from the current Pass 2 path

Pass 2 is still consulting-slide-specific.

Set:

```python
skip_slides = blank_slides | diagram_like_slides
```

and pass that to `analyze_slides_deep(...)`.

This means:

- `diagram` skips Pass 2
- `mixed` skips Pass 2
- `unsupported_diagram` skips Pass 2
- `text` and `text_light` keep existing behavior
- `image_blank` keeps current hybrid blank behavior

#### E. Preserve blank override behavior exactly

Do not widen the blank override beyond the current confirmed blank set.

The current post-pass-1 override to `SlideAnalysis.pending()` must still apply only to:

- structural blanks
- confirmed `image_blank` pages

Do not overwrite diagram/mixed analyses with blank placeholders.

### 3. `folio/output/frontmatter.py`

Keep output polymorphism-safe.

Implementation requirements:

- widen type annotations to accept `SlideAnalysis | DiagramAnalysis` where appropriate
- keep `_collect_unique()` and `_compute_grounding_summary()` working for both types
- do not add new frontmatter fields in PR 3
- do not special-case diagram analyses out of aggregate scans

If you need type branches, use `isinstance(analysis, DiagramAnalysis)`, not marker strings.

### 4. `folio/output/markdown.py`

Keep the current markdown shape.

Implementation requirements:

- widen type annotations to accept `SlideAnalysis | DiagramAnalysis`
- ensure `_format_slide()` accepts `DiagramAnalysis` without crashing
- keep current image embedding behavior unchanged
- keep inherited `SlideAnalysis` fields rendering as they do now

Do **not** add Mermaid or diagram-specific component tables in PR 3.

### 5. Tests

Add the new test module and expand existing ones as described below.

---

## Required Test Coverage

### 1. `tests/test_diagram_analysis.py`

Add a new focused test module covering:

- `DiagramAnalysis` round-trip through `to_dict()` / `from_dict()`
- `DiagramGraph` round-trip with nodes, edges, and nested groups
- tuple bbox fields round-trip as tuples
- partial diagram payloads deserialize safely
- malformed/unknown fields degrade gracefully
- empty dict behavior
- IoU helpers:
  - identical boxes -> match
  - slightly shifted boxes above threshold -> match
  - non-overlapping boxes -> no match
  - threshold boundary
  - greedy best-match resolution
  - nodes without bboxes -> no inherited IDs
- edge-ID rewriting after inherited node IDs

### 2. `tests/test_grounding.py`

Extend existing tests so:

- slide-only dicts still deserialize to `SlideAnalysis`
- diagram payloads deserialize to `DiagramAnalysis`
- `diagram_type` without `graph` still routes to `DiagramAnalysis`
- empty dict remains backward compatible

### 3. `tests/test_analysis_cache.py`

Add cache coverage for:

- diagram payload survives cache round-trip through the factory
- `_ANALYSIS_CACHE_VERSION == 3` behavior
- cache invalidates when schema version changes
- cache invalidates when pipeline version changes
- cache invalidates when provider/model changes
- stable signature helper is deterministic
- mixed old/new cache states degrade gracefully
- per-page durability remains intact after a later failure
- warm cache hits still populate `per_slide_providers`

### 4. `tests/test_converter_integration.py`

Add/extend tests to prove:

- `diagram` pages skip Pass 2
- `mixed` pages skip Pass 2
- mixed pages produce exactly one dict entry keyed by page number
- that mixed-page entry is a `DiagramAnalysis`
- `unsupported_diagram` produces an abstained `DiagramAnalysis`
- `unsupported_diagram` does not invoke pass 1 or pass 2
- `image_blank` hybrid blank gating is unchanged
- `text_light` existing behavior is unchanged

Prefer patch-based tests around `inspect.inspect_pages`, `analysis.analyze_slides`, and `analysis.analyze_slides_deep` rather than expensive full execution.

### 5. `tests/test_frontmatter.py` and `tests/test_pipeline_integration.py`

Add at least one proof that:

- frontmatter generation accepts `DiagramAnalysis`
- markdown slide formatting accepts `DiagramAnalysis`
- inherited slide-analysis fields are preserved in output consumers

No new markdown/frontmatter schema is required in PR 3.

### 6. Full Suite

The full existing suite must pass after the new tests land.

Do not quote stale totals in comments; use the current baseline (`693 tests collected`) only in the prompt and PR notes.

---

## Acceptance Criteria

PR 3 is done when all of the following are true:

1. Every deserialize call site routes through the factory.
2. Diagram payloads survive cache round-trips without silent field loss.
3. Mixed pages produce one `DiagramAnalysis` object, not two entries.
4. `unsupported_diagram` pages bypass both passes and remain present in output.
5. Diagram-like pages skip the existing Pass 2 consulting-slide analysis.
6. Cache invalidates deterministically on schema/pipeline drift while keeping page-image SHA identity.
7. Existing text-slide behavior remains unchanged.
8. Full test suite passes.

---

## Smoke Commands

Run these before opening the PR:

```bash
.venv/bin/python -m pytest tests/test_diagram_analysis.py -v
.venv/bin/python -m pytest tests/test_grounding.py -v
.venv/bin/python -m pytest tests/test_analysis_cache.py -v
.venv/bin/python -m pytest tests/test_converter_integration.py -v -k "diagram or blank or pass2"
.venv/bin/python -m pytest tests/test_frontmatter.py tests/test_pipeline_integration.py -v
.venv/bin/python -m pytest tests/ -v
```

---

## What Not to Do

- Do not add diagram extraction prompts.
- Do not wire tiles/highlights into runtime prompts.
- Do not generate Mermaid.
- Do not add output-assembly redesign.
- Do not move public analysis imports away from `folio/pipeline/analysis.py`.
- Do not replace the existing page-image SHA cache-entry identity with a different keying model.
- Do not change current blank-gating semantics.
- Do not reimplement retry/throttle logic from PR 2.

---

## Final Notes for the Developer Team

- Treat the merged repo as source of truth over older review docs.
- Be explicit in the PR summary about the deserialize call-site audit.
- Be explicit in the PR summary about the new cache metadata markers.
- Keep the implementation minimal: PR 3 is about data safety and routing correctness, not diagram extraction behavior yet.
