---
id: claude_code_prompt_diagram_pr6_output_assembly
type: atom
status: draft
ontos_schema: 2.2
generated_by: codex
created: 2026-03-15
---

# Implementation Prompt: Diagram Extraction PR 6 - Output Assembly, Standalone Notes, Freeze, and Review History

**For:** Developer Agent Team (CA lead + spawned developers)  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Grounded against:** merged PR 1-5 runtime in `folio/`, `docs/validation/obsidian_transclusion_test_result.md`, `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr5_rendering.md`, and the live deck assembly/frontmatter code in `folio/output/` and `folio/converter.py`  
**Branch:** `codex/diagram-pr6-output-assembly` from `main` (`99c3c32`)  
**Current suite baseline:** `1007 passed, 3 skipped; 1010 collected`  
**Primary test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `feat(diagrams): description`  
**PR title:** `feat: add diagram output assembly and freeze support`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, grounds in the live repo, and owns final verification.
2. Developers implement in the task order below. Do not implement from the proposal alone; PR 4 and PR 5 introduced important runtime drift.
3. The CA lead verifies each slice with targeted tests, then runs the full suite before opening the PR.
4. Keep PR 6 assembly-only. Do not modify extraction prompts, rendering logic, or caching behavior beyond the frozen-note bypass described here.

---

## What This PR Completes

PR 6 is the final production assembly layer for diagrams.

After this PR:

- diagram pages produce standalone diagram notes inside the vault
- deck notes transclude diagram sections from those standalone notes
- frozen diagram notes can bypass the diagram pipeline on reprocessing
- deck frontmatter and tag aggregation include diagram metadata
- review-heavy and abstained diagram states are surfaced honestly in output

This PR does **not** change extraction quality, deterministic rendering algorithms, provider/runtime behavior, or the consulting-slide prompts.

---

## Settled Repo Reality

Do not reopen these decisions.

1. **Obsidian transclusion is a closed gate.**  
   `docs/validation/obsidian_transclusion_test_result.md` records a pass, including a real PR 5 Mermaid renderer test. Use `![[note#section]]`. Do not implement inline Mermaid fallback logic.

2. **Standalone diagram notes are auxiliary vault notes, not registry entries.**  
   The registry currently only indexes deck markdown files because it relies on `source`, `source_hash`, and `source_type`. Standalone diagram notes must not carry those deck fields.

3. **Rendering already happens before review-state assessment.**  
   In `folio/converter.py`, PR 5 rendering runs after PR 4 extraction and before `analysis.assess_review_state()`. Preserve that ordering.

4. **PR 6 assembles from existing diagram fields.**  
   Do not re-run `graph_to_mermaid()`, `graph_to_prose()`, or table rendering while emitting notes. Use `DiagramAnalysis.mermaid`, `description`, `component_table`, and `connection_table` as already populated by PR 5.

5. **Mixed pages still skip consulting Pass 2 in the live runtime.**  
   `converter.py` skips `analyze_slides_deep()` for all diagram-like slides, including `mixed`. For frozen mixed pages, preserve that current behavior. “Keep consulting-slide content” means keep the existing Pass 1-derived inherited fields, not add a new Pass 2 route.

6. **Group membership must reconcile both `group.contains` and `node.group_id`.**  
   PR 5 rendering already does this because PR 4 regrouping only updates `node.group_id`. Any PR 6 aggregation over graph/group membership must follow the same rule.

7. **Supported diagrams may still be abstained or review-heavy.**  
   Valid runtime states include:
   - `abstained=True`, `graph=None`
   - `abstained=True`, `graph` present
   - `review_required=True` with `review_questions`
   - low-confidence nodes and sweep discoveries inside an otherwise rendered graph

8. **`SlideAnalysis.from_dict()` remains the only deserialization entry point for cached/runtime analysis payloads.**  
   Do not add a parallel diagram-analysis reconstruction path for normal analysis deserialization.

---

## Read Before Writing

Read these in order before editing code:

1. `docs/proposals/diagram-extraction-proposal.md`
2. `docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr5_rendering.md`
3. `docs/validation/obsidian_transclusion_test_result.md`
4. `folio/converter.py`
5. `folio/pipeline/analysis.py`
6. `folio/pipeline/diagram_extraction.py`
7. `folio/output/diagram_rendering.py`
8. `folio/output/frontmatter.py`
9. `folio/output/markdown.py`
10. `folio/tracking/registry.py`
11. `tests/test_frontmatter.py`
12. `tests/test_pipeline_integration.py`
13. `tests/test_converter_integration.py`
14. `tests/validation/validate_frontmatter.py`

---

## Current Codebase Reality

### Current output path

`FolioConverter.convert()` currently:

1. resolves deck directory and deck markdown path
2. reads existing deck frontmatter
3. normalizes to PDF
4. inspects pages
5. extracts images
6. extracts text
7. runs consulting Pass 1
8. applies blank override
9. promotes diagram/mixed slides to `DiagramAnalysis`
10. runs PR 4 diagram extraction
11. runs PR 5 deterministic rendering
12. optionally runs consulting Pass 2 deep for non-diagram slides only
13. computes review state
14. generates deck frontmatter
15. assembles the deck markdown
16. writes the deck markdown
17. upserts the deck registry entry

PR 6 must keep the core ordering:

- extraction / rendering
- `assess_review_state()`
- standalone-note emission
- deck frontmatter generation
- deck markdown assembly
- registry upsert

### Current `DiagramAnalysis` surface

`DiagramAnalysis` already contains:

- `diagram_type`
- `graph`
- `mermaid`
- `description`
- `component_table`
- `connection_table`
- `uncertainties`
- `diagram_confidence` and backward-compatible `extraction_confidence`
- `confidence_reasoning`
- `review_questions`
- `review_required`
- `abstained`
- `_extraction_metadata`

Do **not** add `human_overrides`, `folio_freeze`, or `_review_history` to the runtime dataclass. Those are standalone-note frontmatter fields only.

### Current markdown/frontmatter assumptions

- `folio/output/markdown.py` only knows how to render the main deck note.
- `folio/output/frontmatter.py` only generates deck frontmatter (`type: evidence`).
- `tests/validation/validate_frontmatter.py` only validates deck-style notes today.
- `registry.rebuild_registry()` only indexes markdown files with `source` and `source_hash`.

PR 6 should extend these carefully without changing deck-note authority semantics.

---

## Implementation Tasks

Implement in this order.

### 1. Add standalone diagram note module

Create a new module at `folio/output/diagram_notes.py`.

It should own:

- stable standalone note naming
- standalone note frontmatter assembly
- standalone note body assembly
- frozen-note discovery
- frozen-note frontmatter parsing
- frozen-note graph hydration from markdown tables

Define these helper dataclasses in that module:

```python
@dataclass(frozen=True)
class DiagramNoteRef:
    basename: str          # basename without .md, used for Obsidian links
    path: Path
    has_diagram_section: bool
    has_components_section: bool


@dataclass
class FrozenDiagramPayload:
    analysis: DiagramAnalysis
    note_ref: DiagramNoteRef
    frontmatter: dict[str, Any]
```

Export these functions:

```python
def build_note_basename(created_date: str, deck_slug: str, page_number: int) -> str: ...

def discover_frozen_notes(
    deck_dir: Path,
    deck_slug: str,
    created_date: str,
    page_profiles: dict[int, Any],
) -> dict[int, FrozenDiagramPayload]: ...

def emit_diagram_notes(
    deck_dir: Path,
    deck_slug: str,
    deck_title: str,
    created_date: str,
    analyses: dict[int, SlideAnalysis],
    page_profiles: dict[int, Any],
) -> dict[int, DiagramNoteRef]: ...
```

Use `created_date` in `YYYYMMDD` form. Derive it from the deck’s preserved `created` value when available, else current UTC date. This keeps note links stable across reconversions.

### 2. Standalone note naming and frontmatter

Standalone notes live in `deck_dir`, beside the main deck markdown and `slides/`.

Filename pattern:

`{created_yyyymmdd}-{deck_slug}-diagram-p{page_number:03d}.md`

Examples:

- `20260314-system-design-review-diagram-p007.md`
- `20260314-system-design-review-diagram-p008.md`

Use repo-reality note fields, not proposal placeholders:

- `source_deck` is the deck markdown basename as a wiki-link, e.g. `[[system_design_review]]` if the deck markdown file is `system_design_review.md`
- `source_page` is the integer page number
- image embed always uses `slides/slide-{page:03d}.png`

Standalone note title is deterministic:

- `"{Deck Title} — {Diagram Type Label} (Page {n})"`
- `architecture` -> `Architecture`
- `data-flow` -> `Data Flow`
- `unsupported` -> `Unsupported`
- unknown/other values -> title-case the hyphen-normalized string

Populate standalone-note frontmatter with these fields, in this order:

```yaml
type: diagram
diagram_type: architecture
title: "System Design Review — Architecture (Page 7)"
source_deck: "[[system_design_review]]"
source_page: 7
extraction_confidence: 0.93
confidence_reasoning: "..."
review_required: false
review_questions: []
abstained: false
folio_freeze: false
components:
  - API Gateway
  - Order Database
technologies:
  - Kong
  - PostgreSQL
tags:
  - diagram
  - architecture
  - system
  - design
  - review
human_overrides: {}
_review_history: []
_extraction_metadata:
  ...
```

Rules:

- `components` are deduped sorted node labels from the graph
- `technologies` are deduped sorted raw technology values from the graph, not wiki-link strings
- `extraction_confidence` comes from `diagram_confidence`
- `folio_freeze` defaults to `false`
- `human_overrides` defaults to `{}`
- `_review_history` defaults to `[]`
- `_extraction_metadata` is copied from `DiagramAnalysis._extraction_metadata` if present

Preserve on non-frozen reprocessing:

- `human_overrides`
- `_review_history`
- `folio_freeze`
- any unknown user-authored frontmatter keys not explicitly managed by PR 6

Managed keys above should be overwritten from the new runtime analysis on non-frozen reconversion.

### 3. Standalone note body template

Use this body structure exactly. Section names are fixed because deck-note transclusion depends on them.

For a normal rendered diagram note:

````md
# {title}

Extracted from {source_deck}, page {page_number}.

## Diagram

```mermaid
{analysis.mermaid}
```

## Components

{analysis.component_table}

## Connections

{analysis.connection_table}

## Summary

{analysis.description}

## Extraction Notes

> No uncertainties flagged.

---

![[slides/slide-{page:03d}.png]]
````

Populate `## Extraction Notes` like this:

- if `uncertainties` or `review_questions` exist, render each as a separate blockquote line
- else if `abstained=True` and `graph is not None`, render a blockquote explaining this is an unverified candidate extraction
- else render `> No uncertainties flagged.`

For `abstained=True` and `graph is not None`:

- keep the same section names
- insert this line immediately before `## Diagram`:

  `> Candidate extraction rendered for reviewer context. This diagram abstained from final acceptance.`

For `abstained=True` and `graph is None`:

- render only:
  - title
  - source line
  - abstention explanation from `confidence_reasoning` or a fallback message
  - extraction notes if `review_questions` exist
  - source image embed
- omit `## Diagram`, `## Components`, `## Connections`, and `## Summary` entirely

The standalone note emitter must never call PR 5 renderers again. If `mermaid`, `description`, or table fields are missing on a non-frozen rendered graph, surface that as an extraction-note warning and keep the note otherwise valid.

### 4. Extend deck markdown assembly

Update `folio/output/markdown.py`.

Change the public assembly signature to:

```python
def assemble(
    title: str,
    frontmatter: str,
    source_display_path: str,
    version_info: VersionInfo,
    slide_texts: dict[int, Union[str, SlideText]],
    slide_analyses: dict[int, SlideAnalysis],
    slide_count: int,
    version_history: list[dict],
    *,
    slide_classifications: dict[int, str] | None = None,
    diagram_note_refs: dict[int, DiagramNoteRef] | None = None,
) -> str:
```

Also extend `_format_slide()` to accept:

```python
def _format_slide(
    ...,
    classification: str | None = None,
    diagram_note_ref: DiagramNoteRef | None = None,
) -> str:
```

Do **not** import `PageProfile` into the output layer. In `converter.py`, pass a plain `slide_classifications = {n: profile.classification}` map extracted from `page_profiles`.

Deck slide behavior:

- non-diagram slides: unchanged
- pure `diagram` slides:
  - keep image
  - suppress the generic `### Analysis` block entirely
  - if `diagram_note_ref.has_diagram_section` is true, append:

    ```md
    ![[{note_basename}#Diagram]]

    ![[{note_basename}#Components]]

    *Full details: [[{note_basename}]]*
    ```

  - if `has_diagram_section` is false, append only:

    `*Full details: [[{note_basename}]]*`

- `mixed` slides:
  - preserve current consulting-slide `### Analysis`
  - append the same diagram transclusion block after it

Do not transclude `Connections` into the deck note. Keep that in the standalone note only.

### 5. Freeze detection and bypass

Implement freeze detection in `folio/converter.py` after:

- `deck_dir` is resolved
- `deck_name` is known
- existing deck frontmatter is read
- page inspection has run

Use the created-date prefix derived from the existing deck frontmatter’s `created` field if present, else current UTC date, so the expected standalone note path stays stable across reconversions.

Build these slide sets:

- `frozen_diagram_slides`: classification `diagram` and frozen note exists
- `frozen_mixed_slides`: classification `mixed` and frozen note exists
- `all_frozen_diagram_slides`: union of the two

Freeze semantics are decision-complete:

- frozen pure `diagram` slides:
  - exclude from consulting Pass 1
  - exclude from PR 4 diagram extraction
  - exclude from PR 5 rendering
  - exclude from standalone-note rewrite
  - hydrate a `DiagramAnalysis` directly from the frozen note and insert it into `slide_analyses`

- frozen `mixed` slides:
  - keep current consulting Pass 1 behavior
  - keep current Pass 2 skip behavior for mixed slides
  - skip PR 4 diagram extraction for that slide
  - skip PR 5 rendering for that slide
  - skip standalone-note rewrite
  - overlay diagram fields from the frozen note onto the pass-1-derived `DiagramAnalysis`

Do not create a new deep-pass path for mixed slides. Preserve existing runtime semantics.

### 6. Frozen-note hydration rules

Hydrate a `DiagramAnalysis` from the frozen note like this:

1. Parse standalone note frontmatter.
2. Read:
   - `diagram_type`
   - `extraction_confidence`
   - `confidence_reasoning`
   - `review_required`
   - `review_questions`
   - `abstained`
   - `_extraction_metadata`
3. Parse the `## Components` table:
   - create `DiagramNode` entries
   - `Component` -> `label`
   - `Type` -> `kind`
   - `Technology` -> raw technology value after stripping `[[...]]`
   - `Group` -> temporary flat group membership
   - `Source` -> `source_text`
   - `Confidence` -> float if parseable else `1.0`
4. Parse the `## Connections` table:
   - create `DiagramEdge` entries
   - `From` / `To` map to node IDs by label lookup
   - `Direction` maps:
     - `→` -> `forward`
     - `←` -> `reverse`
     - `↔` -> `bidirectional`
     - `—` or `?` -> `none`
   - parse confidence if available
5. Derive flat `DiagramGroup` objects from the `Group` column in the Components table.
6. Do **not** parse Mermaid for grouping or graph reconstruction.

If tables are malformed or missing:

- hydrate whatever partial graph can be recovered
- keep `mermaid`, `description`, `component_table`, and `connection_table` from the frozen note body if you can extract them by section
- log a warning
- do not fail the conversion

For frozen-note overlay on mixed pages:

- preserve inherited consulting-slide fields from the fresh Pass 1 result
- replace only the diagram-specific fields with the frozen-note authority:
  - `diagram_type`
  - `graph`
  - `mermaid`
  - `description`
  - `component_table`
  - `connection_table`
  - `diagram_confidence` / `extraction_confidence`
  - `confidence_reasoning`
  - `review_required`
  - `review_questions`
  - `abstained`
  - `_extraction_metadata`

### 7. Emit notes after review-state assessment

After `review_assessment = analysis.assess_review_state(...)` and before deck frontmatter generation:

- call `emit_diagram_notes(...)`
- pass the final `slide_analyses`
- pass the `page_profiles` map so the emitter can determine which slides are diagram-like
- do not let note emission mutate `slide_analyses` in a way that would change review flags already computed

For frozen slides, `emit_diagram_notes()` should return the `DiagramNoteRef` from the existing note without rewriting the file.

### 8. Extend deck frontmatter

Update `folio/output/frontmatter.py`.

Keep deck frontmatter `type: evidence`. Do not change deck type semantics.

Add these deck-level fields:

- `diagram_types`
- `diagram_components`

Populate them from diagram analyses:

- `diagram_types`: deduped sorted `diagram_type` values from `DiagramAnalysis` instances with non-empty graphs or abstained-with-graph states; exclude `"unknown"`
- `diagram_components`: deduped sorted node labels from all `DiagramAnalysis.graph.nodes`

Extend `_collect_unique()` to support these virtual fields:

- `"diagram_type"`
- `"diagram_component"`
- `"diagram_technology"`

Rules for `_collect_unique()`:

- preserve current evidence-gating behavior for normal slide fields like `framework` and `slide_type`
- for diagram virtual fields, ignore the evidence-gating shortcut and aggregate directly from `DiagramAnalysis.graph`
- non-diagram analyses contribute nothing to diagram virtual fields

Change `_generate_tags()` to:

```python
def _generate_tags(
    frameworks: list[str],
    slide_types: list[str],
    title: str,
    *,
    diagram_types: list[str] | None = None,
    diagram_technologies: list[str] | None = None,
) -> list[str]:
```

Tag rules:

- existing framework and title-word behavior stays
- add `diagram` when any diagram page exists
- add each diagram type as a normalized tag
- add each raw technology name as a slugified tag:
  - lowercase
  - spaces/underscores -> hyphens
  - strip `[[` / `]]`
  - do not use wiki-link strings as tags

### 9. Validation and registry rules

Do not make standalone notes registry entries.

Keep this invariant by design:

- standalone notes must not include `source`, `source_hash`, or `source_type`
- `registry.rebuild_registry()` will therefore continue to ignore them automatically

Extend `tests/validation/validate_frontmatter.py` with a diagram-note validation branch:

- allow `type: diagram`
- do not force diagram notes through deck-note required fields
- validate diagram-note-specific required fields:
  - `type`
  - `diagram_type`
  - `title`
  - `source_deck`
  - `source_page`
  - `review_required`
  - `review_questions`
  - `abstained`
  - `folio_freeze`
  - `tags`
  - `_review_history`
- treat `_extraction_metadata`, `components`, and `technologies` as optional but type-checked when present

Do **not** change the existing deck-note validation path.

---

## Exact Deck Transclusion Snippet

Use this exact structure for diagram content in the main deck markdown:

```md
### Page 7

![Page 7](slides/slide-007.png)

![[20260314-system-design-review-diagram-p007#Diagram]]

![[20260314-system-design-review-diagram-p007#Components]]

*Full details: [[20260314-system-design-review-diagram-p007]]*
```

In the actual codebase, the main deck note still uses `## Slide N` headers, not `### Page N`, so preserve the current deck structure and only inject the transclusion block under the existing slide section.

For graphless abstained notes:

```md
![Slide 7](slides/slide-007.png)

*Full details: [[20260314-system-design-review-diagram-p007]]*
```

---

## Exact Standalone Note Body Contract

Use this contract verbatim in the implementation:

````md
# {Title}

Extracted from [[{deck_slug}]], page {page_number}.

{optional abstained-with-graph caveat}

## Diagram

```mermaid
{mermaid}
```

## Components

{component_table}

## Connections

{connection_table}

## Summary

{description}

## Extraction Notes

> {uncertainty or default note}

---

![[slides/slide-{page:03d}.png]]
````

Graphless abstained notes omit `Diagram`, `Components`, `Connections`, and `Summary`.

---

## Tests

### Add new tests

Create `tests/test_diagram_notes.py` covering:

1. full standalone note emission
2. abstained note with `graph=None`
3. abstained note with graph present
4. review-heavy note with uncertainties and review questions
5. stable filename generation from preserved `created` date
6. frontmatter preservation of `human_overrides`, `_review_history`, and `folio_freeze`
7. frozen-note hydration from Components and Connections tables
8. malformed frozen-note degradation with warning and partial graph

### Extend existing tests

Extend `tests/test_converter_integration.py` for:

1. pure diagram page uses standalone note + deck transclusions instead of generic analysis
2. mixed page preserves consulting analysis and appends diagram transclusions
3. abstained no-graph page emits image + full-details link only
4. frozen pure diagram page causes no LLM call for that slide
5. frozen mixed page still uses consulting Pass 1 and skips diagram pipeline
6. reconversion preserves existing note `human_overrides`

Extend `tests/test_pipeline_integration.py` for:

1. `_format_slide()` pure diagram path
2. `_format_slide()` mixed diagram path
3. `_format_slide()` graphless abstained path

Extend `tests/test_frontmatter.py` for:

1. deck-level `diagram_types`
2. deck-level `diagram_components`
3. diagram-aware `_collect_unique()`
4. diagram-aware `_generate_tags()`

Extend `tests/test_registry.py` or add a focused test proving standalone diagram notes are ignored by registry rebuild because they do not carry `source` and `source_hash`.

Extend `tests/validation/validate_frontmatter.py` coverage for `type: diagram`.

Keep the existing Mermaid parser harness in `tests/mermaid` unchanged.

### Smoke commands

Run these before opening the PR:

```bash
.venv/bin/python -m pytest tests/test_diagram_notes.py -v
.venv/bin/python -m pytest tests/test_frontmatter.py tests/test_pipeline_integration.py tests/test_converter_integration.py tests/test_registry.py -v
.venv/bin/python -m pytest tests/ -v
```

Optional manual smoke after tests pass:

- convert a PDF with at least one `diagram` page and one `mixed` page into a temp target
- confirm standalone notes are created
- confirm deck note transclusion references point at the expected note basenames
- re-run with one diagram note manually edited to `folio_freeze: true` and confirm the note is not rewritten

---

## Important Non-Goals

Do **not** do any of the following in PR 6:

- change PR 4 extraction prompts
- change PR 5 deterministic rendering logic
- change diagram caches
- change provider/runtime behavior
- add registry entries for standalone diagram notes
- re-run rendering inside the note emitter
- add inline Mermaid fallback logic
- add multi-diagram-per-page support
- change consulting-slide analysis semantics beyond the deck assembly rules above

Keep PR 6 narrowly focused on output assembly, standalone-note authority, frozen-note bypass, and deck/frontmatter integration.
