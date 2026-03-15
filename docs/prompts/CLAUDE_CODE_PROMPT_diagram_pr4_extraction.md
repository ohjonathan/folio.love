---
id: claude_code_prompt_diagram_pr4_extraction
type: atom
status: draft
ontos_schema: 2.2
generated_by: codex
created: 2026-03-15
---

# Implementation Prompt: Diagram Extraction PR 4 - Extraction Prompts, Pass A/B/C, Completeness Sweep, and Confidence

**For:** Developer Agent Team (CA lead + spawned developers)  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Grounded against:** PR 1-3 merged runtime in `folio/`, the PR 4 readiness check, and `docs/validation/som_validation_20260314.json`  
**Branch:** `codex/diagram-pr4-extraction` from `main`  
**Primary test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `feat(diagrams): description`  
**PR title:** `feat: add diagram extraction passes and cache runtime`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, grounds in the live repo, and owns final verification.
2. Developers implement in the task order below. Do not parallelize dependent slices blindly; PR 4 is the first PR that joins `PageProfile`, rendered images, multi-image provider calls, and `DiagramAnalysis`.
3. The CA lead verifies each slice with targeted tests, then runs the full suite before opening the PR.
4. If by day 3 the PR is too large, stop and split exactly at the approved boundary:
   - `PR 4a`: Pass A + Pass B + sanity short-circuit
   - `PR 4b`: Pass C + completeness sweep + confidence

The intermediate state for the split is:

- `DiagramAnalysis.graph` populated
- `diagram_type` populated
- no final `verification_evidence`
- no final `confidence_reasoning`
- no final `review_questions`

Do not invent a different split boundary.

---

## Task Context

### What to Build

Build the first real diagram extraction runtime.

PR 4 is the first PR that:

- calls the LLM for diagram work
- wires tile images into real prompts
- wires highlight overlays into real prompts
- creates a separate diagram cache layer
- populates `DiagramAnalysis.graph`
- adds abstention paths for unsupported diagrams, sanity failures, and low-confidence results
- computes diagram-specific confidence and review questions
- stores per-page diagram extraction metadata

This PR does **not** add Mermaid generation, prose generation, standalone diagram note rendering, output assembly changes, or frontmatter schema changes.

### Why This PR Matters

PR 1, PR 2, and PR 3 each shipped a seam in isolation:

- PR 1: deterministic inspection, `PageProfile`, transforms
- PR 2: per-page rendering, multi-image providers, tiles, highlights
- PR 3: `DiagramAnalysis`, routing, diagram-safe cache/versioning

PR 4 is where those seams are finally connected:

`PageProfile -> rendered PNG -> ImageParts -> ProviderInput -> execute_with_retry() -> DiagramGraph -> DiagramAnalysis`

This is also the riskiest integration point in the roadmap. The coordinate-space join is the highest-risk area and must be tested end-to-end.

### Settled Repo Reality

Do not reopen these decisions.

1. **Tiles only.**  
   Set-of-Mark is out. `docs/validation/som_validation_20260314.json` closed that gate. There is no SoM fallback branch in PR 4.

2. **Current consulting-slide Pass 1 stays.**  
   `folio/pipeline/analysis.py::analyze_slides()` remains intact for the consulting-slide path. PR 4 layers diagram extraction on top of the current runtime; it does not replace it.

3. **Pass 2 deep stays skipped for diagram-like pages.**  
   `diagram`, `mixed`, and `unsupported_diagram` must continue to bypass `analyze_slides_deep()`.

4. **`ProviderInput` has one `prompt` string and no `system_prompt`.**  
   All diagram prompt content must fit inside `ProviderInput.prompt`.

5. **`PageProfile` is frozen and inspection does not emit `unsupported_diagram`.**  
   Do not try to mutate `PageProfile.classification`. Unsupported-type detection happens inside diagram extraction after Pass A.

6. **Current review state keys off `abstained`, not `review_required`.**  
   All PR 4 abstention paths must set `abstained=True`.

7. **Current tile/highlight helpers are infrastructure only.**  
   `prepare_images()` and `highlight_regions()` are only used in tests today. PR 4 is the first runtime caller.

8. **Current consulting-slide caches are off-limits.**  
   Do not modify `.analysis_cache.json` or `.analysis_cache_deep.json`.

### Scope Boundaries

Keep PR 4 focused on extraction.

- Build diagram extraction runtime and caching.
- Keep current consulting-slide analysis behavior unchanged for non-diagram pages.
- Reuse the existing provider/runtime layer.
- Reuse current `DiagramAnalysis` / `DiagramGraph` models.

### What Not to Build

- No Mermaid generation
- No diagram prose generation
- No component/connection tables
- No standalone diagram notes
- No frontmatter schema additions
- No output assembly changes
- No new CLI `--passes` values
- No changes to the consulting-slide caches
- No Set-of-Mark code

---

## Prerequisite: Real Diagram Corpus

Before prompt tuning begins, the developer must have real diagram PDFs supplied outside the repo.

Treat this as an external prerequisite, not a checked-in asset.

Minimum corpus:

- 5-10 real PDFs
- at least 2 `system_architecture`
- at least 2 `data_flow`
- simple, medium, and dense pages
- at least one mixed text + diagram page if available

Do not assume a hardcoded path in the repo. The dev harness must accept explicit PDF paths and output directories.

---

## Read Before Writing

Read these in order before editing code:

1. `docs/proposals/diagram-extraction-proposal.md`
2. `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr3_schema_cache.md`
3. `docs/validation/som_validation_20260314.json`
4. `folio/pipeline/analysis.py`
5. `folio/converter.py`
6. `folio/pipeline/inspect.py`
7. `folio/pipeline/images.py`
8. `folio/pipeline/image_strategy.py`
9. `folio/llm/types.py`
10. `folio/llm/runtime.py`
11. `folio/llm/providers.py`
12. `folio/config.py`
13. `tests/test_diagram_analysis.py`
14. `tests/test_converter_integration.py`
15. `tests/test_image_strategy.py`
16. `tests/test_analysis_cache.py`
17. `tests/test_frontmatter.py`
18. `tests/test_grounding.py`

Do not start from the original PR 4 brief alone. Start from the merged runtime.

---

## Current Codebase Reality

### Current Orchestration Flow

`folio/converter.py::FolioConverter.convert()` currently does:

1. normalize to PDF
2. `inspect.inspect_pages(pdf_path)`
3. `images.extract_with_metadata(..., page_profiles=page_profiles)`
4. hybrid blank gating:
   - `classification == "blank"` is structurally blank
   - `classification == "image_blank"` is blank only when histogram blankness agrees
5. `text.extract_structured(source_path)`
6. `analysis.analyze_slides(...)`
7. blank override to `SlideAnalysis.pending()` for confirmed blank slides
8. coerce `diagram` and `mixed` pages to `DiagramAnalysis`
9. optionally run `analysis.analyze_slides_deep(...)` with `skip_slides=blank_slides | diagram_like_slides`

PR 4 must insert diagram extraction **after** step 8 and **before** output/frontmatter assembly. Do not move the blank gate or the existing Pass 2 skip logic.

### Current Analysis and Cache Contracts

In `folio/pipeline/analysis.py`:

- `SlideAnalysis.from_dict()` is the polymorphic factory
- `DiagramAnalysis` already exists
- `match_nodes_by_iou()` already exists
- `_rewrite_edge_ids()` already exists
- `_extract_json()` only handles direct JSON and fenced JSON
- `_hash_image(image_path)` is the image-hash key function
- current caches are image-hash keyed with file-global prompt/version markers

Those consulting-slide caches are not suitable for diagram prompts because they have one top-level `_prompt_version` for the consulting prompts.

### Current Provider Contract

In `folio/llm/types.py`:

```python
@dataclass(frozen=True)
class ProviderInput:
    prompt: str
    images: tuple[ImagePart, ...] = ()
    max_tokens: int = 4096
    temperature: float = 0.0
    require_store_false: bool = False
```

There is no `system_prompt`. Do not add one in PR 4.

### Current Image Strategy

In `folio/pipeline/image_strategy.py`:

- `prepare_images(page_image, page_profile) -> list[ImagePart]`
- `highlight_regions(page_image, regions, colors=None, outline_width=None) -> Image.Image`
- `prepare_images()` returns:
  - `["global"]` for `text`, `text_light`, `blank`, `image_blank`
  - `["global", "tile_q1", "tile_q2", "tile_q3", "tile_q4"]` for `diagram`, `mixed`, `unsupported_diagram`

These functions have no runtime callers today.

### Current Coordinate Transform

In `folio/pipeline/inspect.py`:

- `DiagramNode.bbox` is expected to be PDF-space
- `pdf_to_pixel()` converts PDF points to rendered pixel coordinates
- `pixel_to_pdf()` exists as inverse

PR 4 must use these helpers for Pass C highlights. This is the highest-risk seam in the PR.

### Current Output Behavior

`frontmatter.py` and `markdown.py` are polymorphism-safe for `DiagramAnalysis`, but there is still no diagram-specific rendering path.

Therefore:

- PR 4 may populate `DiagramAnalysis`
- PR 4 may affect review flags
- PR 4 must not attempt to render Mermaid or diagram-only markdown sections

---

## Required Implementation

## 1. New Runtime Modules

Add these new modules:

- `folio/pipeline/diagram_extraction.py`
- `folio/pipeline/diagram_cache.py`
- `tools/diagram_iterate.py`

Keep public data models in `folio/pipeline/analysis.py`. Do not move `DiagramAnalysis` or `DiagramGraph` out of that module.

### `diagram_extraction.py` responsibilities

This module owns:

- inline diagram prompt strings
- diagram-stage JSON parsing
- Pass A execution
- Pass B execution
- deterministic mutation application
- sanity short-circuit
- Pass C execution
- completeness sweep
- confidence scoring
- deterministic bbox anchoring from `PageProfile.bounded_texts`
- deterministic inherited-field updates on `DiagramAnalysis`
- `_extraction_metadata` population

### `diagram_cache.py` responsibilities

This module owns:

- separate diagram cache file load/save helpers
- stage-specific version markers
- stage-specific dependency hashes
- per-entry serialization/deserialization for diagram stages

Do not refactor the consulting-slide cache helpers in PR 4.

### `tools/diagram_iterate.py` responsibilities

This is a dev-only harness, not a product CLI command.

It must:

- accept one PDF path
- optionally accept page subset
- accept `--pass a|b|c|sweep|full`
- accept `--no-cache`
- accept `--llm-profile`
- emit intermediate artifacts under `tmp/diagram_iter/<pdf-stem>/...`

Do not wire this into `folio/cli.py`.

---

## 2. `DiagramAnalysis` Extension and Review-State Behavior

### Extend `DiagramAnalysis`

Add to `DiagramAnalysis` in `folio/pipeline/analysis.py`:

```python
_extraction_metadata: dict[str, Any] = field(default_factory=dict)
```

Requirements:

- include it in `to_dict()`
- restore it in `from_dict()`
- ignore malformed/non-dict payloads by falling back to `{}` instead of crashing

Do not add `mermaid` or `description` generation in PR 4. If the LLM returns them, discard them.

### Extend `assess_review_state()`

Current review logic only understands:

- `pending`
- abstained diagrams
- evidence confidence / validation
- density-based pass-2 needs

PR 4 must also flag supported diagrams that remain review-worthy even when not abstained.

Add review flag behavior for non-abstained `DiagramAnalysis`:

- if `review_required` is true -> add `diagram_review_required_slide_{n}`
- if `review_questions` is non-empty -> add `diagram_open_questions_slide_{n}`

Keep existing abstention behavior unchanged:

- `abstained=True` still emits `diagram_abstained_slide_{n}`
- abstained diagrams remain excluded from provider-failure buckets

Do not add new frontmatter fields. Review-state changes must flow through the existing `review_flags` list only.

---

## 3. Converter Integration

Update `folio/converter.py`, but keep it as the orchestrator.

### Required flow

1. Keep current consulting-slide Pass 1 exactly as-is.
2. Keep blank override exactly as-is.
3. Keep coercion of `diagram` / `mixed` pages to `DiagramAnalysis`.
4. After that coercion, call the new diagram pipeline for `diagram` and `mixed` pages.
5. Keep `unsupported_diagram` inspect-level placeholder path intact as a safety net.
6. Keep `analyze_slides_deep()` skipped for diagram-like slides.

### Add a diagram stage call

Add a call with this effective behavior:

```python
slide_analyses, diagram_stats, diagram_meta = diagram_extraction.analyze_diagram_pages(
    pass1_results=slide_analyses,
    page_profiles=page_profiles,
    image_results=image_results,
    slide_texts=slide_texts,
    cache_dir=deck_dir,
    force_miss=no_cache,
    provider_name=profile.provider,
    model=profile.model,
    api_key_env=profile.api_key_env,
    fallback_profiles=fallback_profiles_list,
    all_provider_settings=all_provider_settings,
    slide_numbers=sorted(diagram_or_mixed_slides),
)
```

Adapt the exact signature to codebase conventions if needed, but preserve those inputs and outputs.

### Important converter constraint

Do **not** mutate `PageProfile.classification` to `unsupported_diagram`.

`PageProfile` is frozen and inspection does not emit that value. Unsupported detection in PR 4 is runtime analysis state only.

---

## 4. Separate Diagram Cache Layer

Build a diagram-specific cache layer in `folio/pipeline/diagram_cache.py`.

### File names

Use exactly these three cache files in `cache_dir`:

- `.analysis_cache_diagram_pass_a.json`
- `.analysis_cache_diagram_post_b.json`
- `.analysis_cache_diagram_final.json`

### Entry keys

Use `_hash_image(image_path)` from `analysis.py` as the entry key for all three files.

Do not invent a new top-level composite cache key.

### Top-level markers

Each file must store top-level markers similar to the existing consulting caches:

- `_cache_version`
- `_provider_version`
- `_model_version`
- `_schema_version`
- `_pipeline_version`
- `_image_strategy_version`
- a prompt-version marker for that stage

Use separate prompt-version markers per stage:

- `_diagram_prompt_version` in the Pass A file
- `_diagram_prompt_version` in the post-B file
- `_diagram_prompt_version` in the final file

The value differs by stage because the prompt text differs by stage.

### Version constants

Define diagram-stage version constants in `diagram_cache.py` or `diagram_extraction.py`:

- diagram cache format version
- diagram schema version (reuse current diagram schema version if still accurate)
- diagram extraction pipeline version, e.g. `pr4-extraction-v1`
- diagram image strategy version, e.g. `tiles-v1`
- per-stage prompt version derived from prompt text

Do not modify the consulting-slide cache constants for this work.

### Per-entry dependency hashes

Store stage-specific dependency hashes in each entry:

- Pass A:
  - `_text_inventory_hash`
  - `_page_profile_hash`
  - `_provider`
  - `_model`
- post-B:
  - `_pass_a_hash`
  - `_provider`
  - `_model`
- final:
  - `_post_b_hash`
  - `_provider`
  - `_model`

#### `_text_inventory_hash`

Hash the exact prompt text inventory string that Pass A / Pass B received.

#### `_page_profile_hash`

Build a deterministic stable signature from:

- `classification`
- `escalation_level`
- `render_dpi`
- `crop_box`
- `rotation`
- `word_count`
- `vector_count`
- `char_count`
- whether bounded texts were available

#### `_pass_a_hash`

Hash the normalized Pass A payload that feeds Pass B:

- `diagram_type`
- normalized nodes
- normalized edges
- normalized groups

#### `_post_b_hash`

Hash the normalized post-B graph and abstention-relevant state:

- `diagram_type`
- post-B graph
- whether sanity short-circuit triggered

### Durability

Preserve the same per-miss flush behavior as current analysis caches:

- after every resolved miss, write the cache file immediately
- never batch all page writes to the end only

Do not change the consulting-slide cache write behavior.

---

## 5. Dev Iteration Harness

Add `tools/diagram_iterate.py`.

Use `argparse`, not Click.

### Required CLI surface

Support:

```bash
.venv/bin/python tools/diagram_iterate.py /abs/path/file.pdf --page 3 --pass a --no-cache --llm-profile my_profile
```

Arguments:

- positional PDF path
- `--page` repeated or comma/range syntax
- `--pass a|b|c|sweep|full`
- `--no-cache`
- `--llm-profile`
- `--out-dir` optional, default under `tmp/diagram_iter/<pdf-stem>/`

### Required behavior

The harness must:

- normalize the source PDF path input only if needed; do not assume PPTX support
- run inspection and per-page rendering
- run the selected diagram stage(s)
- persist intermediate artifacts for inspection

Write these artifacts:

- raw provider response text per stage
- parsed JSON per stage
- normalized graph JSON snapshots
- mutation application log
- verification batch request/response JSON
- highlight overlay images
- completeness sweep request/response JSON
- final `DiagramAnalysis.to_dict()` snapshot

### Cache behavior

- `--pass a` should only require Pass A inputs
- `--pass b` should use a cached Pass A result when available
- `--pass c` should use cached post-B state when available
- `--pass sweep` should use cached final pre-sweep state when available
- `--no-cache` forces recomputation for the requested stage and prerequisites

Do not use the harness to write into library output directories.

---

## 6. Prompt Definitions

Keep prompt strings inline in `folio/pipeline/diagram_extraction.py`.

Do not create external prompt files or a prompt registry in PR 4.

### Pass A prompt: `DIAGRAM_EXTRACTION_PROMPT`

Pass A must request:

- `diagram_type`
- nodes
- edges
- groups

Allowed `diagram_type` values:

- `system_architecture`
- `data_flow`
- any other string is treated as unsupported

Pass A must explicitly instruct:

- Image 1 is the full page
- Images 2-5 are quadrant close-ups for reading labels only
- extract structure from Image 1
- use Images 2-5 only to read labels unclear in Image 1
- use exact label text, no paraphrasing
- `kind` must be from the allowed node set:
  - `service`
  - `datastore`
  - `queue`
  - `actor`
  - `boundary`
  - `unknown`
- `source_text` must be one of:
  - `pdf_native`
  - `vision`
  - `ocr`
- do not emit Mermaid
- do not emit prose
- do not emit numeric coordinates as a source of truth

Expected Pass A response shape:

```json
{
  "diagram_type": "system_architecture",
  "graph": {
    "nodes": [
      {
        "id": "anything",
        "label": "Auth Service",
        "kind": "service",
        "group_id": "anything_or_null",
        "technology": "Go",
        "source_text": "vision"
      }
    ],
    "edges": [
      {
        "id": "anything",
        "source_id": "anything",
        "target_id": "anything",
        "label": "gRPC",
        "direction": "->"
      }
    ],
    "groups": [
      {
        "id": "anything",
        "name": "VPC",
        "contains": ["anything"],
        "contains_groups": []
      }
    ]
  }
}
```

Do not trust returned IDs or coordinates. Normalize them in Python.

### Pass B prompt: `DIAGRAM_MUTATION_PROMPT`

Pass B must receive:

- the normalized Pass A graph JSON
- the global image only
- the same text inventory used for Pass A

Pass B must act as a visual critic and return **mutations only**, not a full rewritten graph.

Expected response shape:

```json
{
  "mutations": [
    {"action": "add_edge", "source_id": "node_3", "target_id": "node_7", "label": "gRPC", "direction": "->"},
    {"action": "remove_edge", "edge_id": "node_1_node_2", "reason": "not visible"},
    {"action": "relabel_node", "node_id": "node_3", "new_label": "Auth Service"},
    {"action": "change_direction", "edge_id": "node_3_node_7", "new_direction": "<->", "reason": "bidirectional arrowheads"},
    {"action": "regroup", "node_id": "node_8", "new_group_id": "group_2", "reason": "inside boundary"},
    {"action": "add_node", "label": "Redis", "kind": "datastore", "group_id": "group_2", "technology": "Redis", "source_text": "vision"},
    {"action": "remove_node", "node_id": "node_9", "reason": "not visible"}
  ]
}
```

Allowed actions are exactly:

- `add_edge`
- `remove_edge`
- `relabel_node`
- `change_direction`
- `regroup`
- `add_node`
- `remove_node`

Do not add `add_group`, `remove_group`, or full-graph rewrite actions in PR 4.

### Pass C prompt: `DIAGRAM_CLAIM_VERIFICATION_PROMPT`

Pass C receives:

- a highlighted global image
- a JSON array of claims

Expected response shape:

```json
{
  "results": [
    {
      "claim_id": "claim_1",
      "verdict": "confirmed",
      "confidence": 0.91,
      "evidence": "highlighted node label is clearly visible"
    }
  ]
}
```

Allowed verdicts are exactly:

- `confirmed`
- `rejected`
- `uncertain`

### Completeness prompt: `DIAGRAM_COMPLETENESS_PROMPT`

Completeness sweep receives:

- a local crop
- a JSON list of current nodes/edges already known in that region

Expected response shape:

```json
{
  "discoveries": [
    {
      "kind": "node",
      "label": "Audit Queue",
      "node_kind": "queue",
      "position_description": "bottom-right of the highlighted crop"
    },
    {
      "kind": "edge",
      "source_label": "API Gateway",
      "target_label": "Audit Queue",
      "direction": "->",
      "label": "events",
      "position_description": "diagonal line across the right side"
    }
  ]
}
```

Only dense pages run completeness sweep.

---

## 7. Diagram Extraction Execution Flow

Implement `analyze_diagram_pages(...)` in `diagram_extraction.py`.

Recommended signature:

```python
def analyze_diagram_pages(
    *,
    pass1_results: dict[int, SlideAnalysis],
    page_profiles: dict[int, PageProfile],
    image_results: list[ImageResult],
    slide_texts: dict[int, SlideText],
    cache_dir: Path | None,
    force_miss: bool,
    provider_name: str,
    model: str,
    api_key_env: str,
    fallback_profiles: list[tuple[str, str, str]] | None,
    all_provider_settings: dict[str, ProviderRuntimeSettings] | None,
    slide_numbers: list[int],
) -> tuple[dict[int, SlideAnalysis], CacheStats, StageLLMMetadata]:
    ...
```

Adapt exact typing if needed, but return updated analyses plus cache stats plus stage metadata.

### Stage ordering

For each slide in `slide_numbers`:

1. resolve `PageProfile`
2. resolve `ImageResult`
3. resolve current `DiagramAnalysis`
4. build or load Pass A state
5. if unsupported -> abstain and stop for this page
6. build or load post-B state
7. if sanity short-circuit -> abstain and stop for this page
8. build or load final state with Pass C
9. if dense -> run completeness sweep
10. compute confidence
11. update inherited fields
12. populate `_extraction_metadata`
13. store updated `DiagramAnalysis` back into `pass1_results`

Do not run diagram extraction on non-diagram slides.

---

## 8. Text Inventory and Bbox Anchoring

### Text inventory

Build a diagram text inventory string from `PageProfile.bounded_texts`.

Format:

- one item per bounded word
- preserve original text
- include only text, not coordinates

If `bounded_texts` is empty, fall back to `SlideText.full_text` and `SlideText.elements` from Stage 3 text extraction.

Do not fail the page when `bounded_texts` is empty. PR 1 and PR 2 explicitly allow partial page-profile degradation.

### Deterministic bbox anchoring

Do not trust numeric coordinates from the LLM.

Implement deterministic bbox anchoring in Python:

1. Normalize `PageProfile.bounded_texts` into reading order:
   - sort by top-to-bottom, then left-to-right in PDF space
   - for PDF coordinates that means sorting by `-bbox[3]`, then `bbox[0]`
2. Normalize node labels:
   - lowercase
   - collapse whitespace
   - strip surrounding punctuation
3. For each node:
   - first try exact phrase match against consecutive bounded-word spans
   - then try exact single-word match for short labels
   - then try fuzzy match with `SequenceMatcher` only when needed
4. If multiple matches exist, take the first reading-order match.
5. Union matched word boxes into one PDF-space bbox.
6. Set:
   - `node.bbox` to that union box
   - `node.source_text = "pdf_native"` when anchored from bounded text
7. If no match is found:
   - keep `node.bbox = None`
   - keep `source_text` from the parsed graph or default it to `vision`

Rerun bbox anchoring:

- after Pass A normalization
- after Pass B mutations
- after completeness discoveries are added

### Evidence policy for node-label anchors

For pure `diagram` pages:

- overwrite inherited `evidence` with deterministic node-label evidence derived from anchored nodes only
- each evidence item must use an exact anchored label string as `quote`
- if no anchored labels exist, keep `evidence=[]`

For `mixed` pages:

- keep the consulting-slide pass-1 evidence
- append deterministic node-label evidence for anchored diagram nodes

Do not fabricate edge quotes. Edge verification belongs in diagram-specific fields and `_extraction_metadata`, not in inherited slide evidence.

---

## 9. Pass A: Extract

### Image selection

Pass A image selection is driven by `PageProfile.escalation_level`, not Pass A output.

- `simple` -> send only the `global` image part
- `medium` / `dense` -> send all `prepare_images()` parts

Implementation path:

1. open `ImageResult.path` with PIL
2. call `prepare_images(page_image, page_profile)`
3. select either `[global]` or all 5 parts based on escalation
4. build `ProviderInput(prompt=..., images=tuple(selected_parts), ...)`
5. call `execute_with_retry(...)`

Do not call provider adapters directly.

### Pass A parsing and normalization

Implement a diagram-specific JSON extraction helper in `diagram_extraction.py`.

It must support:

- clean JSON
- fenced JSON
- leading preamble text before JSON
- trailing text after JSON

If parsing fails, do not crash the whole document. Convert the page to an abstained `DiagramAnalysis` with:

- `review_required=True`
- `abstained=True`
- candidate graph left as `None`
- `review_questions` containing a parse-failure note

### ID normalization

Do not trust Pass A IDs.

Normalize Pass A output as follows:

- nodes:
  - preserve LLM node order
  - assign `node_1`, `node_2`, ...
- groups:
  - preserve LLM group order
  - assign `group_1`, `group_2`, ...
- edges:
  - rewrite `source_id` / `target_id` through the new node ID mapping
  - ignore LLM edge IDs
  - derive edge IDs with `_rewrite_edge_ids()`

Then anchor node bboxes, then run IoU inheritance:

1. normalize graph
2. anchor bboxes from bounded text
3. if a cached prior graph exists, run `match_nodes_by_iou()`
4. rewrite node IDs through the IoU mapping
5. recompute edge IDs again with `_rewrite_edge_ids()`

### Unsupported diagram detection

Pass A must return `diagram_type`.

Supported types are exactly:

- `system_architecture`
- `data_flow`

Any other type must become an abstained `DiagramAnalysis`:

- `diagram_type="unsupported"`
- `abstained=True`
- `review_required=True`
- `graph=None`
- `review_questions=["Detected unsupported diagram type: <type>"]`

Do not proceed to Pass B or Pass C for unsupported types.

---

## 10. Pass B: Mutate

Pass B receives:

- normalized Pass A graph JSON
- global image only
- the same text inventory string

### Deterministic mutation application

Implement mutation application in Python, not in the model output.

For each mutation:

- validate the action
- validate referenced IDs before applying
- log applied vs rejected mutations

Action behavior:

- `relabel_node`
  - update `label`
  - do **not** change `id`
- `add_node`
  - assign next sequential `node_N`
  - anchor bbox after insertion
- `remove_node`
  - remove the node
  - remove all connected edges
- `add_edge`
  - validate source and target exist
  - add edge without trusting any LLM edge ID
  - recompute edge IDs with `_rewrite_edge_ids()`
- `remove_edge`
  - remove by `edge_id`
- `change_direction`
  - update the edge direction
- `regroup`
  - update `group_id`

After all mutations:

- rerun bbox anchoring for all nodes
- recompute edge IDs with `_rewrite_edge_ids()`

### Mutation accounting

Count mutated nodes and edges for the sanity threshold:

- node mutations:
  - `add_node`
  - `remove_node`
  - `relabel_node`
  - `regroup`
- edge mutations:
  - `add_edge`
  - `remove_edge`
  - `change_direction`

### Sanity short-circuit

After applying valid mutations:

- if mutated nodes > 30% of original node count
- or mutated edges > 40% of original edge count

then short-circuit:

- `abstained=True`
- `review_required=True`
- preserve the candidate post-B graph
- set `review_questions` to human-readable summaries of the mutation list
- skip Pass C and completeness sweep

Do not waste provider calls verifying a graph that already failed sanity.

---

## 11. Pass C: Claim-Level Verification

Pass C only runs when:

- diagram type is supported
- Pass B did not short-circuit

### Claim generation

Generate claims from the post-B graph:

- one node claim per node
- one edge claim per edge

Use deterministic claim IDs:

- `node:<node_id>`
- `edge:<edge_id>`

Node claim text should include:

- label
- kind
- technology when present

Edge claim text should include:

- source label
- target label
- direction
- edge label when present

### Verification depth

Use Pass A node count:

- `<= 10` nodes -> verify with the unmodified global image; no highlight required
- `11-25` nodes -> verify with highlighted global images
- `> 25` nodes -> verify with highlighted global images and then run completeness sweep

### Highlight behavior

For highlighted verification:

- nodes:
  - highlight the anchored node bbox when available
- edges:
  - highlight the source and target node bboxes
- if either required bbox is missing:
  - keep the claim in the batch
  - use the unmodified global image for that claim batch
  - do not fail the page

Convert PDF-space node boxes to pixel-space using:

- `pdf_to_pixel()`
- `PageProfile.crop_box`
- `PageProfile.rotation`
- `PageProfile.render_dpi`

When building pixel rectangles:

- transform all four corners
- normalize min/max after transform

### Batch size

Use batches of 15-20 claims.

Default target batch size: 18.

### Verification result handling

For each verification result:

- `confirmed`
  - keep the element
  - set `verification_evidence` to `verify_batch_<n>_claim_<m>`
  - for edges, set `evidence_bbox` to the union of source and target node bboxes when both exist
- `rejected`
  - remove the element from the graph
- `uncertain`
  - keep the element
  - lower element confidence to `min(existing_confidence, 0.5)`
  - append a specific review question

Do not remove a node just because its bbox was unavailable. Missing geometry is not automatic rejection.

---

## 12. Completeness Sweep

Run completeness sweep only when:

- `PageProfile.escalation_level == "dense"`
- Pass C completed without abstention

### Region strategy

Use explicit groups when available:

- for each `DiagramGroup`, define its region as the union of its contained node bboxes plus 10% padding

If there are no explicit groups:

- use the four fixed quadrants from the full rendered page image as completeness regions

This avoids adding a clustering algorithm in PR 4.

### Sweep behavior

For each region:

1. crop the region using `crop_region()`
2. gather the nodes and edges already present in that region
3. run the completeness prompt
4. normalize discoveries
5. add discovered nodes/edges at low confidence

Discovery rules:

- new nodes get `confidence=0.40`
- new edges get `confidence=0.40`
- any discovery forces `review_required=True`
- append a review question describing what the sweep found
- rerun bbox anchoring after adding discoveries
- recompute edge IDs after adding discoveries

If a discovery references labels not already in the graph, create new nodes as needed.

---

## 13. Confidence Scoring

Implement deterministic confidence scoring in `diagram_extraction.py`.

### Shared inputs

Compute:

- `verification_rate = confirmed_claims / max(1, total_claims)`
- `mutation_ratio = max(mutated_nodes / max(1, original_nodes), mutated_edges / max(1, original_edges))`
- `uncertainty_penalty = min(1.0, uncertain_claims / max(1, total_claims))`

### Text-rich path

Use this path when `PageProfile.word_count > 20`.

Compute text coverage as:

- normalize all bounded-text inventory tokens
- normalize all node-label tokens
- `text_coverage = matched_inventory_tokens / max(1, inventory_token_count)`

Then compute:

```text
score = (
    0.35 * text_coverage
    + 0.40 * verification_rate
    + 0.20 * (1.0 - mutation_ratio)
    + 0.05 * (1.0 - uncertainty_penalty)
)
```

### Text-poor path

Use this path when `PageProfile.word_count <= 20`.

Compute density plausibility as:

- `expected_nodes = max(1.0, page_profile.vector_count / 25.0)` when `vector_count > 0`
- otherwise `expected_nodes = max(1.0, len(graph.nodes))`
- `density_score = min(1.0, len(graph.nodes) / expected_nodes)`

Then compute:

```text
score = (
    0.55 * verification_rate
    + 0.25 * density_score
    + 0.15 * (1.0 - mutation_ratio)
    + 0.05 * (1.0 - uncertainty_penalty)
)
```

### Final score rules

- clamp score into `[0.0, 1.0]`
- round to 2 decimals for storage
- if final score `< 0.40`:
  - set `abstained=True`
  - keep the graph
  - keep `review_required=True`

### Confidence reasoning

Populate `confidence_reasoning` with a deterministic sentence that includes:

- text-rich or text-poor mode
- verification rate
- mutation ratio
- uncertainty count
- coverage or density score
- final score

Example shape:

`"Text-rich scoring: text coverage 0.78, verification rate 0.84, mutation ratio 0.12, uncertainty penalty 0.06, final confidence 0.79."`

Do not let the LLM generate this string.

---

## 14. Inherited `SlideAnalysis` Field Policy

PR 4 must preserve polymorphic compatibility without adding diagram rendering yet.

### Pure `diagram` pages

Overwrite inherited fields deterministically:

- `slide_type = "diagram"`
- `framework = "none"`
- `visual_description = "<Diagram type> with <N> nodes, <E> edges, <G> groups."`
- `key_data = "<N> nodes; <E> edges; <G> groups"`
- `main_insight = "Diagram extraction completed for a <diagram_type> page."`
- `evidence =` deterministic node-label evidence derived from anchored labels only, or `[]` if no anchored labels exist

Do not reuse consulting-slide prose for pure diagram pages.

### `mixed` pages

Keep inherited consulting-slide fields from Pass 1:

- `slide_type`
- `framework`
- `visual_description`
- `key_data`
- `main_insight`

Append deterministic diagram node-label evidence to the existing evidence list.

Do not let diagram extraction wipe mixed-page consulting-slide evidence.

### `description` and `mermaid`

Leave:

- `description = None`
- `mermaid = None`

PR 5 owns deterministic generation of those fields.

---

## 15. `_extraction_metadata` Population

Populate `_extraction_metadata` on each final `DiagramAnalysis`.

Use this shape:

```python
{
    "model": "<provider-model or model name>",
    "provider": "<provider>",
    "passes": ["extract", "mutate", "verify"],
    "text_sources": ["pdf_native", "vision"],
    "image_strategy": "tiles",
    "escalation_level": "<simple|medium|dense>",
    "schema_version": "<version>",
    "pipeline_version": "<version>",
    "verification_batches": 3,
    "claims_verified": 41,
    "claims_confirmed": 35,
    "claims_rejected": 4,
    "claims_uncertain": 2,
    "input_tokens": 12345,
    "output_tokens": 2345,
}
```

Rules:

- `passes` must reflect actual execution
  - e.g. `["extract", "unsupported_abstained"]`
  - `["extract", "mutate", "sanity_abstained"]`
  - `["extract", "mutate", "verify", "sweep"]`
- `text_sources` should be deduplicated from node `source_text` values plus whether bounded-text inventory existed
- token counts must be aggregated from all provider calls for that page
- do not surface `_extraction_metadata` in frontmatter yet

Do not modify `_llm_metadata` document frontmatter shape in PR 4.

---

## 16. Prompt Iteration Workflow

The developer must iterate the prompts on real diagrams using the dev harness.

### Required workflow

1. run Pass A repeatedly on representative pages until node/edge recall is acceptable
2. run Pass B on the same pages and tune mutation precision
3. validate highlight alignment visually before trusting Pass C results
4. tune Pass C on batched claims
5. tune completeness sweep only after Pass C is stable
6. only then finalize confidence weighting

### Required artifacts during tuning

Use the harness output directory to inspect:

- prompt text sent
- selected image roles
- raw provider response
- parsed payload
- normalized graph JSON
- highlighted verification images

Do not use `folio convert --no-cache` as the only prompt-iteration loop.

---

## 17. Test Plan

Add these new test files:

- `tests/test_diagram_extraction.py`
- `tests/test_diagram_cache.py`

Extend:

- `tests/test_converter_integration.py`
- `tests/test_frontmatter.py`
- `tests/test_grounding.py`

### `tests/test_diagram_extraction.py`

Cover:

1. JSON parsing
   - clean JSON
   - fenced JSON
   - preamble + JSON
   - malformed JSON
   - empty response

2. Pass A normalization
   - node renumbering to `node_1...`
   - group renumbering to `group_1...`
   - edge IDs derived by `_rewrite_edge_ids()`
   - unsupported type abstention

3. Bbox anchoring
   - exact phrase match
   - single-word match
   - fuzzy fallback
   - no match -> `bbox=None`
   - rerun after relabeling

4. Pass B mutation application
   - every allowed action
   - invalid referenced ID skipped and logged
   - unknown action skipped and logged
   - relabel does not change node ID
   - node removal removes connected edges

5. Sanity short-circuit
   - under threshold -> continue
   - node threshold trip -> abstained
   - edge threshold trip -> abstained
   - graph preserved
   - review questions populated

6. Pass C batching
   - claim generation
   - batches target 15-20 claims
   - confirmed -> keep + evidence
   - rejected -> remove
   - uncertain -> keep + lower confidence + review question

7. Completeness sweep
   - dense-only
   - explicit-group regions
   - quadrant fallback
   - low-confidence discoveries

8. Confidence scoring
   - text-rich path
   - text-poor path
   - below-floor abstention
   - `confidence_reasoning` includes actual numbers

### `tests/test_diagram_cache.py`

Cover:

1. load/save per stage
2. image-hash keying
3. version invalidation
4. per-entry hash invalidation
5. per-miss durability
6. no writes to consulting-slide caches

### Extend `tests/test_converter_integration.py`

Cover:

1. `diagram` / `mixed` pages still run consulting Pass 1
2. diagram extraction runs after Pass 1
3. Pass 2 deep still skips diagram-like slides
4. unsupported-type abstention now comes from Pass A, not inspect classification
5. blank gating remains unchanged

### Extend review/frontmatter tests

Cover:

1. supported diagram with `review_required=True` emits the new review flags
2. supported diagram with `review_questions` emits the new review flags
3. abstained diagram behavior is unchanged
4. no frontmatter schema changes are required

### Coordinate end-to-end test

Add a real rendered test, not a mock-only test:

1. create a page image
2. define a PDF-space bbox
3. convert it with `pdf_to_pixel()`
4. draw highlights with `highlight_regions()`
5. assert that pixels in the expected region changed

Do not stop at "function was called" assertions.

---

## 18. Smoke Commands

Run these before opening the PR:

```bash
.venv/bin/python -m pytest tests/test_diagram_extraction.py -v
.venv/bin/python -m pytest tests/test_diagram_cache.py -v
.venv/bin/python -m pytest tests/test_converter_integration.py -v -k "diagram or abstained or pass2"
.venv/bin/python -m pytest tests/test_frontmatter.py tests/test_grounding.py -v -k "diagram or review"
.venv/bin/python -m pytest tests/test_image_strategy.py tests/test_inspect.py -v
.venv/bin/python tools/diagram_iterate.py /abs/path/real.pdf --page 1 --pass a --no-cache --llm-profile <profile>
.venv/bin/python tools/diagram_iterate.py /abs/path/real.pdf --page 1 --pass c --no-cache --llm-profile <profile>
.venv/bin/python -m pytest tests/ -v
```

Do not quote a hardcoded total test count in comments or PR notes. Use the current suite state at runtime.

---

## 19. Delivery Notes

### If the PR remains whole

The final merged behavior must be:

- diagram/mixed pages get real diagram extraction
- unsupported types abstain after Pass A
- sanity failures abstain after Pass B
- supported pages reach Pass C and optionally sweep
- confidence and review questions are populated
- consulting-slide behavior for non-diagram pages remains unchanged

### If the PR splits at day 3

For `PR 4a`, ship:

- diagram cache layer
- iteration harness
- Pass A
- Pass B
- deterministic mutation application
- sanity short-circuit

For `PR 4b`, ship:

- Pass C
- completeness sweep
- confidence scoring
- final `_extraction_metadata`

Do not split at any other boundary.

---

## 20. Explicit Non-Goals

Do not do any of the following in PR 4:

- Mermaid generation
- prose generation
- component tables
- connection tables
- standalone diagram note assembly
- transclusion changes
- frontmatter schema expansion
- changes to `.analysis_cache.json`
- changes to `.analysis_cache_deep.json`
- Set-of-Mark code
- consulting-slide Pass 1 prompt changes
- consulting-slide Pass 2 prompt changes

