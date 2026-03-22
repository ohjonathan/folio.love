# Folio Upstream Feedback V2: Full Library Run Analysis

Field-tested findings from processing 161 files (149 PDFs, 12 PPTX) across a US Bank technology resilience engagement. This supplements `PROCESSING_REPORT.md` with root-cause analysis of performance issues and concrete improvement proposals.

**Run parameters:** 2-pass analysis, `--no-cache`, Claude Sonnet 4 (diagrams) + GPT-5.3 (analysis), QuantumBlack AI Gateway.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Files processed | 161 (160 OK, 1 corrupt PDF) |
| Total runtime | **15 hours 33 minutes** |
| Total slides analyzed | 1,700 |
| Diagram notes generated | 1,567 |
| Diagrams successfully extracted | ~97 (6.2% of attempts) |
| Diagrams abstained | ~1,470 (93.8% of attempts) |
| Wasted time on duplicates | **~5.6 hours** (36% of total) |
| Wasted time on text/table diagram extraction | **~6 hours** (estimated) |
| Effective processing time | **~4 hours** |

**The pipeline spent roughly 75% of its runtime on work that produced no useful diagram output.** Two root causes account for nearly all of it: (1) no content deduplication across identical files, and (2) diagram extraction runs on every "mixed" page regardless of whether Pass 1 already determined it's a text/table page.

---

## 1. Timing Analysis

### Top 14 slowest files (all >30 minutes)

| # | Duration | Slides | File | Root Cause |
|---|----------|--------|------|------------|
| 1 | 47m08s | 137 | FedNow DR change_request.pdf | ServiceNow export, 132 table pages |
| 2 | 34m37s | 137 | RTP DR change_request.pdf | Same template, different data |
| 3–13 | 30–34m each | 50 | Enterprise ITSM Change Management Procedure.pdf (x11) | **Identical file, 11 copies** |
| 14 | 31m17s | 90 | CHG0891889 detail and outcome.pdf | Change request export, 47 "data" + 39 "appendix" pages |

**11 copies of the same ITSM procedure document consumed 374 minutes (6.2 hours).** If deduplicated, this would have been ~34 minutes — **saving 340 minutes (5.7 hours).**

### Time-per-slide efficiency by document size

| Document Size | Files | Total Slides | Total Time | Avg per Slide |
|---------------|-------|-------------|------------|---------------|
| 1 page | 34 | 34 | 27m | 47.8s |
| 2–5 pages | 30 | 93 | 1h11m | 46.3s |
| 6–20 pages | 19 | 207 | 1h25m | 24.7s |
| 21–50 pages | 15 | 669 | 6h37m | 35.6s |
| 51+ pages | 3 | 324 | 1h53m | 20.9s |

**Observation:** Single-page documents have the highest per-slide cost (47.8s) because the fixed overhead (PDF normalization, image extraction, text extraction, cache I/O) dominates. But the 21–50 page bucket is disproportionately expensive (35.6s/slide) because it contains the ITSM and DR documents where every page goes through full diagram extraction and abstains.

### Duration distribution

| Bucket | Files | Note |
|--------|-------|------|
| <30s | 28 | Fast: cached duplicates, tiny PDFs |
| 30s–2m | 64 | Normal: 1-2 page diagrams with extraction |
| 2–5m | 23 | Normal: multi-page decks |
| 5–15m | 28 | Borderline: larger decks or complex diagrams |
| 15–30m | 4 | Slow: large non-diagram documents |
| >30m | 14 | Very slow: ITSM duplicates + huge exports |

---

## 2. Root Cause: Diagram Extraction on Non-Diagram Pages

### The pipeline flow

```
inspect.py: _classify_page() → "text" / "mixed" / "diagram" / "blank"
                                      ↓
converter.py: Only "mixed" and "diagram" pages → diagram extraction
                                      ↓
diagram_extraction.py: Pass A (LLM call with image) → classify → abstain or extract
```

### The problem

`inspect.py` classifies pages using structural PDF signals: `word_count`, `vector_count`, `has_images`. A page with extractable text AND vector graphics (like **table gridlines**) becomes `"mixed"`:

```python
# inspect.py line 320
if word_count > TEXT_MIN_WORDS and (vector_count > 0 or has_images):
    return "mixed"
```

**Any PDF page with both text and table gridlines is classified as "mixed" and triggers full diagram extraction.** This is correct for actual architecture diagrams embedded in text-heavy slides, but catastrophically wrong for:

- Tabular procedure documents (ITSM: 50 pages of tables → 50 diagram extraction calls → 50 abstentions)
- Form exports (ServiceNow change requests: 137 pages of form data → 137 extraction calls)
- Data tables (CHG0891889: 47 "data" pages → 47 extraction calls → 47 abstentions)

### Evidence from Pass 1

Pass 1 (`analysis.py`) already correctly identifies these pages. For the ITSM document, Pass 1's `visual_description` field says:

| Slide | slide_type | visual_description (excerpt) |
|-------|------------|------------------------------|
| 2 | appendix | "A structured table of contents page..." |
| 5 | framework | "A dense RACI matrix table..." |
| 10 | appendix | "A structured reference slide composed of multiple boxed tables..." |
| 14 | appendix | "A structured two-column table listing ServiceNow Change Task fields..." |
| 30 | appendix | "A dense, text-heavy policy document page... **no charts or diagrams**" |
| 41 | appendix | "A dense text slide with multiple sections and bullet lists; **no charts or diagrams**" |

**Pass 1 knows these are tables/text. But this information is never used to gate diagram extraction.** The diagram extraction decision is made entirely by `inspect.py`, which runs before Pass 1.

### Proposed fix: Post-Pass-1 diagram gating

Add a filtering step between Pass 1 and diagram extraction in `converter.py`:

```python
# After Pass 1, before diagram extraction
_SKIP_DIAGRAM_TYPES = {"data", "appendix", "title"}
_NO_DIAGRAM_PATTERNS = re.compile(
    r"no\s+(?:charts?|diagrams?|graphs?|visuals?)", re.IGNORECASE
)

diagram_extract_slides_filtered = set()
for slide_num in diagram_extract_slides:
    analysis = slide_analyses.get(slide_num)
    if analysis is None:
        diagram_extract_slides_filtered.add(slide_num)
        continue
    
    # Skip if slide_type is clearly non-diagram
    if (analysis.slide_type in _SKIP_DIAGRAM_TYPES 
        and analysis.framework in ("none", "")):
        logger.info("Slide %d: skipping diagram extraction (type=%s)", 
                     slide_num, analysis.slide_type)
        continue
    
    # Skip if visual_description explicitly says no diagrams
    vd = getattr(analysis, 'visual_description', '') or ''
    if _NO_DIAGRAM_PATTERNS.search(vd):
        logger.info("Slide %d: skipping diagram extraction (no diagrams in visual_description)", 
                     slide_num)
        continue
    
    diagram_extract_slides_filtered.add(slide_num)
```

**Estimated savings for this run:** The ITSM docs (50 pages each, 11 copies) plus the DR exports (137 + 137 pages) plus CHG0891889 (90 pages) would have skipped ~4,500 diagram extraction API calls. At ~20s per call, that's ~25 hours of API time saved (though much was sequential within files, the wall-clock savings would be ~6 hours).

---

## 3. Root Cause: No Content Deduplication

### The problem

The USB drive contained many duplicate files across organizational folders:

| File | Copies | Wasted Time |
|------|--------|-------------|
| Enterprise ITSM Change Management Procedure.pdf | 11 | ~340 min |
| Org Chart.pptx (various) | 5 | ~4 min |
| DevOps Pipeline Onpremise.pdf | 4 | ~1 min |
| On-Prem_Network_Diagram.pdf | 4 | ~0.5 min |
| Enterprise Systems Delivery Policy.pdf | 2 | ~6 min |
| MMC Wires API folder (entire subtree) | 2 | ~65 min |

Total estimated wasted time: **~5.6 hours** on processing identical content.

### Proposed fix: Content-hash deduplication in `folio batch`

Before the conversion loop, hash all candidate files and skip duplicates:

```python
import hashlib

def _file_hash(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

# In batch():
seen_hashes: dict[str, Path] = {}
for f in files:
    fhash = _file_hash(f)
    if fhash in seen_hashes:
        click.echo(f"⊘ {f.name} (duplicate of {seen_hashes[fhash].name}, skipped)")
        # Optionally: symlink the library output instead of re-converting
        continue
    seen_hashes[fhash] = f
    # ... proceed with conversion
```

For library output, the duplicate could either be skipped entirely or get a symlink/reference to the first conversion's output directory.

---

## 4. Root Cause: Tables Processed as Diagrams

### The problem

Many PDFs in this engagement were structured data exports:
- ServiceNow change request logs (form fields → table rows)
- Risk assessment matrices
- Service lists and incident logs
- RACI matrices

These are **tabular data**, not architecture diagrams. The pipeline has no concept of "table extraction" — it either extracts a diagram graph (nodes + edges) or abstains. When a table page enters diagram extraction:

1. Pass A sends the image to the LLM (~20s API call)
2. The LLM classifies it as "process" or "hierarchy" or "unsupported"
3. If "unsupported" → abstains immediately, but the API call was already made
4. If "process" → tries to extract nodes/edges from table cells → gets garbage → sanity check triggers → abstains

**Result:** Every table page costs ~20-40 seconds of LLM API time for zero useful output.

### Evidence

For the CHG0891889 document (90 pages, 31 minutes):
- 47 pages classified as `slide_type: data` by Pass 1
- 39 pages classified as `slide_type: appendix`
- Pass 1 visual descriptions consistently say: "structured report-style table", "text-heavy change request document", "no charts or diagrams"
- All 90 pages went through diagram extraction → all abstained
- Zero diagrams extracted

### Proposed fix: Table extraction mode

When Pass 1 identifies a page as `slide_type: data` with a visual description mentioning "table", route to a lightweight table extraction pipeline instead of diagram extraction:

```python
# Conceptual: after Pass 1
if analysis.slide_type == "data" and "table" in (analysis.visual_description or "").lower():
    # Extract structured tabular data (CSV-like)
    table_data = extract_table(image, slide_text)
    # Store as structured data, not graph
```

This would be especially valuable for this engagement where tabular data (risk assessments, service lists, incident logs) is important evidence but not architecture content.

---

## 5. Org Charts and Simple Diagrams

### Observed performance

Org charts and simple 1-page diagrams processed in **17–60 seconds each**, which is reasonable:

| File Type | Count | Avg Duration | Range |
|-----------|-------|-------------|-------|
| Org Chart (PPTX) | 7 | 49s | 40–60s |
| Org Chart (PDF) | 3 | 41s | 17–57s |
| Single-page architecture diagram | ~25 | 42s | 7–83s |

The overhead breakdown for a typical 1-page PDF diagram:
- PDF normalization + image extraction: ~2s
- Text extraction: ~2s
- Pass 1 analysis (GPT-5.3 API call): ~15s
- Diagram extraction Pass A (Sonnet API call): ~20s
- Pass B mutation + Pass C verification: ~5s
- Markdown generation + cache write: ~1s

**No major issue here.** The ~45s per page is the irreducible cost of two LLM API calls (analysis + diagram extraction). The only optimization would be to skip diagram extraction for org charts that Pass 1 already classified as `framework: org-chart`, since the current pipeline abstains on `hierarchy` type diagrams anyway.

---

## 6. Scanned PDFs and Evidence Validation

### The problem

Several source PDFs are scanned documents with zero extractable text. For these:
- `inspect.py` classifies all pages as `"image_blank"` or `"diagram"` (since word_count=0)
- Pass 1 analysis runs on the image → works fine (GPT-5.3 analyzes the visual)
- Evidence validation has no ground-truth text to match against → all claims are `unvalidated`
- `extraction_confidence` drops to 0.59 (the scanned-PDF penalty)

This is documented in UPSTREAM_FEEDBACK.md but is worth re-emphasizing: **14 files in this run had confidence 0.59 solely because they were scanned PDFs**, not because the analysis quality was poor. The text-based validation gate is producing false negatives.

### Proposed fix

When text extraction yields zero pages or zero words, skip evidence validation entirely and flag differently:

```python
if total_extracted_words == 0:
    # Scanned PDF — validation is meaningless
    analysis.validation_status = "skipped_no_text"
    analysis.extraction_confidence = 0.85  # Trust the visual analysis
```

---

## 7. Summary of Recommendations (Priority Order)

### P0: Content deduplication (saves ~36% of runtime)

- Hash files before conversion in `folio batch`
- Skip or symlink duplicates
- **Estimated savings for this run: 5.6 hours**

### P1: Post-Pass-1 diagram gating (saves ~39% of runtime)

- After Pass 1, check `slide_type` and `visual_description` before running diagram extraction
- Skip diagram extraction for `data`/`appendix` slides with `framework: none` and "no diagrams" in description
- **Estimated savings for this run: 6+ hours**

### P2: Table extraction mode (new capability)

- Route `slide_type: data` pages to a lightweight tabular extraction pipeline
- Output structured CSV/markdown tables instead of graph JSON
- Especially valuable for ServiceNow exports, risk matrices, service lists

### P3: Page count warning / sampling

- Documents with >50 pages should trigger a warning
- Consider sampling (e.g., analyze first 5 + last 5 + every 10th page) for very large exports
- Many 100+ page documents are data dumps, not slide decks

### P4: Scanned PDF confidence adjustment

- Don't penalize extraction_confidence when validation is skipped due to no extractable text
- Use a different flag (`validation_status: skipped_no_text`) instead of conflating with genuine validation failures

### P5: `inspect.py` threshold tuning

- The `vector_count > 0` threshold for "mixed" classification is too aggressive
- Table gridlines in PDFs produce hundreds of vectors, making every table page "mixed"
- Consider: if `word_count > 200` and `vector_count < 500`, classify as `"text"` even with vectors (likely a text document with table formatting)

---

## 8. What We Could Have Done Better

### As operators

1. **Should have deduplicated source files before running.** A simple `find ... -exec md5sum {} \; | sort` would have revealed the 11 identical ITSM copies. Running dedup first would have cut 5.6 hours.

2. **Should have separated document types.** The USB drive mixed architecture diagrams with procedure documents, change logs, risk assessments, and data exports. Running `folio convert` selectively on architecture/diagram folders first, then processing the rest, would have produced the most valuable output in the first 2 hours.

3. **Should have used `--passes 1` for text-heavy documents.** The 2-pass depth analysis adds time for documents where all the value is in Pass 1 text extraction, not diagram extraction. A selective approach: `--passes 2` for architecture folders, `--passes 1` for everything else.

4. **Should have set `default_passes: 2` in folio.yaml** instead of using `--passes 2` per-file, to avoid the overhead of parsing the flag 161 times.

### Token limit patching was correct

The token limit patches (Pass A: 16384→32768, Pass B: 4096→8192) prevented truncation failures. Zero JSON parse errors across 1,700 slides. The original 4096 limit would have caused failures on the dense architecture diagrams (SinglePoint 20-slide deck, GACH Azure TSA 4-page deck). **These patches should be upstreamed as defaults.**

---

## Appendix A: Complete File Timing (Top 40)

| # | Duration | Slides | s/slide | File |
|---|----------|--------|---------|------|
| 1 | 47m08s | 137 | 20.6 | FedNow DR change_request.pdf |
| 2 | 34m37s | 137 | 15.2 | RTP DR change_request.pdf |
| 3 | 34m06s | 50 | 40.9 | Wires/MMC Wires API/.../Enterprise ITSM...pdf |
| 4 | 33m24s | 50 | 40.1 | MMC Wires API/.../Enterprise ITSM...pdf |
| 5 | 32m59s | 50 | 39.6 | Wires/MMC Wires API/.../Enterprise ITSM...pdf |
| 6 | 32m53s | 50 | 39.4 | GACH/.../Enterprise ITSM...pdf |
| 7 | 32m24s | 50 | 38.9 | Common Transactions/.../Enterprise ITSM...pdf |
| 8 | 32m21s | 50 | 38.8 | openbanking/.../Enterprise ITSM...pdf |
| 9 | 31m45s | 50 | 38.1 | Zelle/.../Enterprise ITSM...pdf |
| 10 | 31m27s | 50 | 37.7 | Checks/Enterprise ITSM...pdf |
| 11 | 31m17s | 90 | 20.9 | CHG0891889 detail and outcome.pdf |
| 12 | 30m26s | 50 | 36.5 | External Transfers/.../Enterprise ITSM...pdf |
| 13 | 30m24s | 50 | 36.5 | MMC Wires API/.../Enterprise ITSM...pdf |
| 14 | 30m12s | 50 | 36.2 | Internal Transfers/.../Enterprise ITSM...pdf |
| 15 | 28m49s | 20 | 86.5 | SinglePoint Architecture.pdf |
| 16 | 26m40s | 44 | 36.4 | BCP/SCP SinglePoint.pdf |
| 17 | 18m02s | 18 | 60.1 | US Bank tech resilience kick-off.pdf |
| 18 | 16m46s | 33 | 30.5 | US Bank 5.0 Pre Certification Results.pdf |
| 19 | 14m40s | 36 | 24.4 | Internal transfers payment recovery.pdf |
| 20 | 14m26s | 46 | 18.8 | RTP change_request.pdf |

## Appendix B: Diagram Extraction Waste

For the Enterprise ITSM Change Management Procedure (50 pages, 11 copies):

**Every single page** went through diagram extraction. Pass A classified them as:

| diagram_type | Pages |
|--------------|-------|
| process | 32 (immediately abstained — unsupported) |
| unsupported | 14 (immediately abstained) |
| hierarchy | 3 (immediately abstained — unsupported) |
| state-machine | 1 (immediately abstained — unsupported) |

**None of these pages contain diagrams.** They are procedure text, RACI tables, revision history tables, and policy bullet points. Pass 1 correctly identified them as `appendix`, `framework`, `narrative`, and `data` — but this was ignored.

**Per-copy cost:** 50 Pass A API calls × ~20s = ~17 minutes of diagram extraction alone
**Total across 11 copies:** ~187 minutes = **3.1 hours** on a document with zero diagrams

## Appendix C: Recommended folio.yaml for This Engagement

```yaml
library_root: ./library

sources:
  - name: 20260310_USB
    path: ./20260310_USB
    target_prefix: ""

llm:
  profiles:
    anthropic_sonnet:
      provider: anthropic
      model: claude-sonnet-4-20250514
      api_key_env: ANTHROPIC_API_KEY
    openai_gpt53:
      provider: openai
      model: gpt-5.3-chat-latest
      api_key_env: OPENAI_API_KEY

  routing:
    default:
      primary: anthropic_sonnet
      fallbacks: [openai_gpt53]
    analysis:
      primary: openai_gpt53
      fallbacks: [anthropic_sonnet]
    diagram:
      primary: anthropic_sonnet
      fallbacks: [openai_gpt53]

conversion:
  image_dpi: 150
  image_format: png
  default_passes: 2

# PROPOSED: new config keys
# deduplication:
#   enabled: true
#   strategy: content_hash  # sha256 of file content
#   on_duplicate: skip      # or "symlink"
#
# diagram_extraction:
#   skip_slide_types: [data, appendix, title]
#   skip_if_no_diagram_description: true
#   max_pages_warn: 50
#   max_pages_hard: 200
```