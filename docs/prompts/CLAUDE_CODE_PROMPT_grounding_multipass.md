---
id: claude_code_prompt_grounding_multipass
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Claude Code Prompt: Source Grounding & Multi-Pass Extraction

## Context

You are working on **Folio**, a Python CLI tool that converts consulting materials (PPTX decks, PDFs) into AI-native Markdown with structured frontmatter. The repo contains a working v0.1 package with a modular pipeline:

```
folio/
├── pyproject.toml
├── folio/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Click CLI: convert, batch, status
│   ├── config.py            # folio.yaml config loading
│   ├── converter.py         # Main orchestrator
│   ├── pipeline/
│   │   ├── normalize.py     # PPTX → PDF (LibreOffice headless)
│   │   ├── images.py        # PDF → PNG (pdf2image)
│   │   ├── text.py          # Text extraction (MarkItDown) with slide boundaries
│   │   └── analysis.py      # LLM analysis per slide (Claude API) with caching
│   ├── tracking/
│   │   ├── sources.py       # Source path hashing, staleness detection
│   │   └── versions.py      # Per-slide change detection, version history
│   └── output/
│       ├── frontmatter.py   # YAML frontmatter generation (Ontology v2 schema)
│       └── markdown.py      # Final document assembly
```

Read all source files before making any changes. Understand the full pipeline flow: `converter.py` orchestrates the stages in order (normalize → images → text → analysis → source tracking → version tracking → frontmatter → markdown assembly).

Read `docs/Folio_Ontology_Architecture_v2.md` for the full schema specification, authority tiers, relationship types, and design philosophy. Read `docs/04_Implementation_Roadmap_v2.md` for the tier structure and priorities.

---

## What to Build

Two features, implemented in this order. **Do not over-engineer.** The goal is practical improvements to the existing pipeline, not a new architecture.

---

### Feature 1: Source Grounding (Slide-Level with Quoted Evidence)

**Goal:** Every LLM extraction (framework detection, slide type classification, key insight) should cite which slide(s) and quote the specific text that supports it. This is a prompt engineering + output schema change, not a character-offset indexing system.

#### 1A. Update text extraction to preserve element structure

**File:** `folio/pipeline/text.py`

Currently `extract()` returns `dict[int, str]` — slide number to flat text. Upgrade the return type to preserve element-level structure without breaking the existing interface.

Create a new dataclass:

```python
@dataclass
class SlideText:
    """Extracted text for a single slide with element structure."""
    slide_num: int
    full_text: str           # All text concatenated (backward compat)
    elements: list[dict]     # [{"type": "title", "text": "..."}, {"type": "body", "text": "..."}, ...]
```

Element types to detect from MarkItDown output:
- `title` — first heading (H1/H2) in the slide block
- `body` — bullet points, paragraphs, regular text
- `note` — speaker notes if present (MarkItDown sometimes includes these)

Update `extract()` to return `dict[int, SlideText]`. Update all callers in `converter.py` and `versions.py` to use `.full_text` where they previously used the raw string, so nothing breaks.

The `elements` list is used by the grounding system in the analysis stage. Don't overthink the element type detection — a simple heuristic (first heading = title, everything else = body) is fine for v1. We'll refine as we see real MarkItDown output patterns.

#### 1B. Update LLM analysis to produce grounded outputs

**File:** `folio/pipeline/analysis.py`

This is the core change. Update the `ANALYSIS_PROMPT` and `SlideAnalysis` dataclass.

New `SlideAnalysis` fields:

```python
@dataclass
class SlideAnalysis:
    slide_type: str = "unknown"
    framework: str = "none"
    visual_description: str = ""
    key_data: str = ""
    main_insight: str = ""
    # NEW: grounding
    evidence: list[dict] = field(default_factory=list)
    # Each evidence dict: {"claim": str, "quote": str, "element_type": str, "confidence": str}
```

Update `ANALYSIS_PROMPT` to instruct the model to ground every claim:

```
For each finding below, you MUST include:
- The EXACT quote from the slide text that supports your finding (copy verbatim, 10-100 chars)
- Which element the quote comes from (title, body, or note)
- Your confidence: "high" if directly stated, "medium" if clearly implied, "low" if inferred

Respond in this exact format:

Slide Type: [type]
Framework: [framework or "none"]

Evidence:
- Claim: [what you found]
  Quote: "[exact text from slide]"
  Element: [title/body/note]
  Confidence: [high/medium/low]
- Claim: [next finding]
  Quote: "[exact text]"
  Element: [title/body/note]
  Confidence: [high/medium/low]

Visual Description: [describe non-text elements: charts, diagrams, layouts]
Key Data: [specific numbers, percentages, metrics]
Main Insight: [one sentence "so what"]
```

Update `_parse_analysis()` to parse the evidence blocks. Use a simple state-machine parser — when you see `- Claim:`, collect the following `Quote:`, `Element:`, `Confidence:` lines until the next `- Claim:` or section header.

**Important:** Add a `_validate_evidence()` function that checks whether each quoted string actually appears in the slide's extracted text (case-insensitive, whitespace-normalized fuzzy match). If a quote doesn't match, flag it with `"validated": false` in the evidence dict. Do NOT discard it — hallucinated citations still have value as indicators of what the model was looking at. But the validation flag lets downstream consumers filter by reliability.

For fuzzy matching, use a simple approach: normalize both strings (lowercase, collapse whitespace), then check if the normalized quote is a substring of the normalized slide text. If not a direct substring, check if 80%+ of the words in the quote appear in the slide text. Don't pull in a fuzzy matching library for this.

Update `SlideAnalysis.to_dict()` and `from_dict()` to handle the evidence field. Update the cache format — old caches without evidence should still load (default to empty list).

#### 1C. Update markdown output to display grounding

**File:** `folio/output/markdown.py`

In `_format_slide()`, after the Analysis section, if the analysis has evidence entries, render them:

```markdown
### Analysis

**Slide Type:** executive-summary  
**Framework:** scr  
**Visual Description:** ...  
**Key Data:** TAM $4.2B, CAGR 12%, NA 45% share  
**Main Insight:** ...

**Evidence:**
- **Framework detection (high):** "Our approach follows the Situation-Complication-Resolution structure" *(body)*
- **Market sizing (high):** "Addressable market estimated at $4.2B" *(body)*
- **Regional split (medium):** "North America represents 45%" *(body)*
```

Keep it compact. One line per evidence item: claim, confidence in parens, quote in quotes, element type in parens italic.

#### 1D. Update frontmatter with grounding summary

**File:** `folio/output/frontmatter.py`

Add a `grounding_summary` field to frontmatter that aggregates across slides:

```yaml
grounding_summary:
  total_claims: 12
  high_confidence: 8
  medium_confidence: 3
  low_confidence: 1
  validated: 10
  unvalidated: 2
```

This is a summary only. The full evidence lives in the markdown body per-slide. Don't bloat frontmatter with every grounding record — that's what the proposal doc suggested and it's wrong. Frontmatter is for queryable metadata; grounding detail is for the document body.

This enables Dataview queries like: `WHERE grounding_summary.unvalidated > 3` to find documents with unreliable extractions.

---

### Feature 2: Multi-Pass Extraction (Selective Depth)

**Goal:** Add an optional second analysis pass that goes deeper on high-density slides. Not the full three-pass system from the proposal — just a targeted depth pass triggered by density scoring.

#### 2A. Density scoring

**File:** `folio/pipeline/analysis.py`

After Pass 1 completes, score each slide's extraction density:

```python
def _compute_density_score(analysis: SlideAnalysis, text: SlideText) -> float:
    """Score slide complexity. Higher = more content worth a second look."""
    score = 0.0
    
    # Evidence count from Pass 1
    score += len(analysis.evidence) * 0.3
    
    # Text length (longer slides have more to find)
    word_count = len(text.full_text.split())
    if word_count > 150:
        score += 1.0
    elif word_count > 75:
        score += 0.5
    
    # Framework detected (frameworks usually have sub-components worth extracting)
    if analysis.framework != "none":
        score += 1.0
    
    # Data-heavy content
    if analysis.slide_type in ("data", "framework"):
        score += 0.5
    
    # Multiple data points mentioned
    data_indicators = sum(1 for c in analysis.key_data if c == ',')
    score += min(data_indicators * 0.2, 1.0)
    
    return score
```

Default threshold for triggering Pass 2: density score > 2.0. Make this configurable.

#### 2B. Depth pass implementation

**File:** `folio/pipeline/analysis.py`

New function:

```python
def analyze_slides_deep(
    image_paths: list[Path],
    pass1_results: dict[int, SlideAnalysis],
    slide_texts: dict[int, SlideText],
    model: str = "claude-sonnet-4-20250514",
    density_threshold: float = 2.0,
    cache_dir: Optional[Path] = None,
) -> dict[int, SlideAnalysis]:
```

For each slide above the density threshold, run a second API call with a targeted prompt that references Pass 1 results:

```
You previously analyzed this slide and found:
- Slide type: {pass1.slide_type}
- Framework: {pass1.framework}
- Key data: {pass1.key_data}

Now go deeper. For this slide, extract:
1. ADDITIONAL data points, metrics, or claims you missed in the first pass
2. RELATIONSHIPS between data points (e.g., "metric X supports conclusion Y")
3. ASSUMPTIONS stated or implied in the content
4. Any CAVEATS, risks, or qualifications mentioned

For each finding, quote the exact supporting text from the slide.

Format each as:
- Claim: [finding]
  Quote: "[exact text]"
  Element: [title/body/note]
  Confidence: [high/medium/low]
```

Merge Pass 2 results into Pass 1:
- Append new evidence items to the existing evidence list
- If Pass 2 finds a different slide_type or framework, don't overwrite — add a `pass2_slide_type` / `pass2_framework` field and log a warning. Conflicts are interesting, not errors.
- Deduplicate evidence: if two evidence items have quotes with >85% word overlap, keep the one with higher confidence. Use the same word-overlap matching from the validation step.
- Tag each evidence item with `"pass": 1` or `"pass": 2` so the output shows which pass found it.

#### 2C. Wire into the converter

**File:** `folio/converter.py`

Add a `passes` parameter to `FolioConverter.convert()`:

```python
def convert(
    self,
    source_path: Path,
    note: Optional[str] = None,
    client: Optional[str] = None,
    engagement: Optional[str] = None,
    target: Optional[Path] = None,
    passes: int = 1,  # NEW: 1 = breadth only, 2 = breadth + depth
) -> ConversionResult:
```

After the existing analysis stage (Pass 1), if `passes >= 2`:

```python
if passes >= 2 and slide_texts:
    logger.info("  Running depth pass on high-density slides...")
    slide_analyses = analysis.analyze_slides_deep(
        image_paths=image_paths,
        pass1_results=slide_analyses,
        slide_texts=slide_texts,
        model=self.config.llm.model,
        density_threshold=self.config.conversion.density_threshold,
        cache_dir=deck_dir,
    )
```

#### 2D. Update CLI

**File:** `folio/cli.py`

Add `--passes` option to `convert` and `batch` commands:

```python
@click.option("--passes", "-p", type=click.IntRange(1, 2), default=1,
              help="Analysis depth: 1=standard, 2=deep (selective second pass on dense slides).")
```

Pass it through to `converter.convert(passes=passes)`.

#### 2E. Update config

**File:** `folio/config.py`

Add to `ConversionConfig`:

```python
@dataclass
class ConversionConfig:
    image_dpi: int = 150
    image_format: str = "png"
    libreoffice_timeout: int = 60
    default_passes: int = 1          # NEW
    density_threshold: float = 2.0   # NEW
```

Load from `folio.yaml` under `conversion.default_passes` and `conversion.density_threshold`.

CLI `--passes` overrides config default.

#### 2F. Update markdown output for multi-pass

**File:** `folio/output/markdown.py`

When rendering evidence, show which pass found each item:

```markdown
**Evidence:**
- **Framework detection (high, pass 1):** "SCR structure applied to..." *(body)*
- **Revenue assumption (high, pass 2):** "Assumes 15% annual growth..." *(body)*
- **Risk caveat (medium, pass 2):** "Subject to regulatory approval" *(note)*
```

#### 2G. Update frontmatter grounding summary

**File:** `folio/output/frontmatter.py`

Add pass info to the grounding summary:

```yaml
grounding_summary:
  total_claims: 18
  high_confidence: 12
  medium_confidence: 4
  low_confidence: 2
  validated: 15
  unvalidated: 3
  pass_1_claims: 12
  pass_2_claims: 6
  pass_2_slides: 3      # How many slides triggered depth pass
```

---

## Testing

### Unit Tests

Create `tests/test_grounding.py`:

1. **Test evidence parsing.** Feed a mock LLM response string (in the new grounded format) into `_parse_analysis()`. Verify all evidence items are parsed with correct claim, quote, element, confidence.
2. **Test evidence validation.** Create a `SlideText` with known content. Create evidence with both matching and non-matching quotes. Verify `_validate_evidence()` correctly flags validated/unvalidated.
3. **Test density scoring.** Create `SlideAnalysis` objects with varying complexity. Verify density scores and threshold filtering behave as expected.
4. **Test evidence deduplication.** Create overlapping evidence items from two passes. Verify dedup keeps the higher-confidence version and merges correctly.
5. **Test backward compatibility.** Load an old-format analysis cache (without evidence field). Verify it loads with empty evidence list, no crash.

Create `tests/test_text_elements.py`:

1. **Test SlideText dataclass.** Verify `full_text` concatenates elements correctly.
2. **Test element type detection.** Feed MarkItDown output with headings and body text. Verify elements are typed correctly.
3. **Test backward compatibility.** Verify `versions.detect_changes()` still works correctly with the new `SlideText` type (it should use `.full_text`).

### Integration Test

Create `tests/test_pipeline_integration.py`:

1. Create a sample PPTX with python-pptx (title slide, data slide, framework slide, next steps).
2. Run `FolioConverter.convert()` with `passes=1`. Verify output has evidence blocks.
3. Run with `passes=2`. Verify additional evidence appears on dense slides. Verify no duplicate evidence.
4. Verify the markdown output renders evidence correctly.
5. Verify frontmatter grounding_summary is populated.

For all tests that involve LLM calls, mock the Anthropic client. Don't make real API calls in tests.

---

## Implementation Order

1. `SlideText` dataclass and text extraction update (1A)
2. Update callers for backward compat (1A continued)
3. Analysis prompt + evidence parsing + validation (1B)
4. Markdown evidence rendering (1C)
5. Frontmatter grounding summary (1D)
6. **Run tests, verify Pass 1 grounding works end-to-end**
7. Density scoring (2A)
8. Depth pass implementation (2B)
9. Converter + CLI + config wiring (2C-2E)
10. Multi-pass markdown/frontmatter updates (2F-2G)
11. **Run tests, verify Pass 2 works end-to-end**

Do steps 1-6 first, commit, then 7-11. Don't do them all at once.

---

## What NOT to Do

- **No character-level offset indexing.** Slide-level + quoted text is sufficient for now.
- **No Pass 3 (cross-slide analysis).** That requires section detection and grouped processing. We'll add it later if Pass 2 proves valuable.
- **No embedding-based semantic deduplication.** Word overlap matching is fine for v1.
- **No async/parallel API calls.** The current sequential pipeline is fine. Parallelism is a performance optimization we'll add when batch conversion speed becomes a bottleneck.
- **No separate grounding sidecar files.** Evidence lives in the markdown body. Summary lives in frontmatter. That's it.
- **No changes to the normalize or images pipeline stages.** Those are stable.
- **No new dependencies.** Everything here uses the existing stack (anthropic, click, pyyaml). If you think you need a new dependency, you're overcomplicating it.
