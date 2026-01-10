# Folio: Technical Architecture

**Version 1.0 | January 2026**  
**folio.love**

---

## 1. System Overview

### 1.1 Architecture Principles

Folio is built around one core principle: **conversion quality above all else**. The architecture prioritizes:

1. **Fidelity** - Never lose or corrupt source information
2. **Traceability** - Always maintain link to original source
3. **Portability** - Work across machines, sync services, platforms
4. **Simplicity** - Minimal dependencies, standard formats

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SOURCE FILES                             │
│  (PPTX, PDF - wherever they live: OneDrive, local, network)     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONVERSION PIPELINE                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Format   │→ │  Image   │→ │   Text   │→ │  LLM Analysis    │ │
│  │ Normalize│  │ Extract  │  │ Extract  │  │  (optional)      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FOLIO LIBRARY                              │
│  (Obsidian vault: Markdown files, images, metadata)             │
│                                                                  │
│  ClientA/Project1/deck.md  ←──── relative path ────→  source    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CONSUMPTION                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Obsidian │  │  Claude  │  │   Git    │                       │
│  │  Vault   │  │ Projects │  │  Diffs   │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Conversion Pipeline

The pipeline is the heart of Folio. Each stage must be rock-solid.

### 2.1 Stage 1: Format Normalization

**Input:** PPTX or PDF  
**Output:** PDF (normalized intermediate format)

```python
# PPTX → PDF via LibreOffice
subprocess.run([
    'libreoffice', '--headless', '--convert-to', 'pdf',
    '--outdir', temp_dir, source_path
])
```

**Why normalize to PDF?**
- Consistent rendering across platforms
- Single image extraction pipeline
- PDF is the "rendered" form of the deck

**Error handling:**
- LibreOffice timeout (60 seconds max)
- Corrupted files (catch and report, don't crash)
- Missing fonts (LibreOffice substitutes, log warning)

### 2.2 Stage 2: Image Extraction

**Input:** PDF  
**Output:** PNG images (one per page)

```python
from pdf2image import convert_from_path

images = convert_from_path(
    pdf_path,
    dpi=150,
    fmt='png'
)

for i, image in enumerate(images):
    image.save(f'slides/slide-{i+1:03d}.png')
```

**Configuration:**
- DPI: 150 (default), configurable for quality/size tradeoff
- Format: PNG always (lossless, good for text/diagrams)

**Quality checks:**
- Verify image dimensions are reasonable
- Verify file size is non-zero
- Log warning if image appears blank (mostly white pixels)

### 2.3 Stage 3: Text Extraction

**Input:** Original PPTX (preferred) or PDF  
**Output:** Structured text per slide

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert(source_path)

# Parse slide boundaries from HTML comments
slides = parse_slide_boundaries(result.text_content)
```

**MarkItDown output parsing:**
- Slide boundaries marked with HTML comments
- Tables converted to markdown format
- Bullet points preserved

**Fallback for PDF-only:**
- Use pdfplumber or PyMuPDF for text extraction
- Less reliable slide boundary detection
- Flag in metadata that source was PDF

### 2.4 Stage 4: LLM Analysis

**Input:** Slide image (base64)  
**Output:** Structured analysis

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64_image
                }
            },
            {
                "type": "text",
                "text": ANALYSIS_PROMPT
            }
        ]
    }]
)
```

**Analysis Prompt:**
```
Analyze this consulting slide and provide:

1. SLIDE TYPE: One of: title, executive-summary, framework, data, narrative, next-steps, appendix

2. FRAMEWORK: If a consulting framework is used, identify it: 2x2-matrix, scr, mece, waterfall, gantt, timeline, process-flow, org-chart, or "none"

3. VISUAL DESCRIPTION: Describe what you see that wouldn't be captured by text extraction alone. Include:
   - For matrices: axis labels, quadrant contents, positioning
   - For charts: chart type, axes, key data points
   - For diagrams: structure, flow, relationships
   - For tables: column/row structure if complex

4. KEY DATA: List specific numbers, percentages, dates, or metrics shown

5. MAIN INSIGHT: One sentence summarizing the "so what" of this slide

Format your response as:
Slide Type: [type]
Framework: [framework]
Visual Description: [description]
Key Data: [data points]
Main Insight: [insight]
```

**Error handling:**
- API timeout: Skip analysis, mark as pending
- API error: Retry once, then skip
- Rate limiting: Implement backoff
- Invalid response format: Log and use partial data

### 2.5 Stage 5: Assembly

**Input:** Images, text, analysis, source metadata  
**Output:** Complete markdown file with frontmatter

```python
def assemble_markdown(deck_name, slides, source_info, version_info):
    # Build frontmatter
    frontmatter = {
        'title': deck_name,
        'source': source_info['relative_path'],
        'source_hash': source_info['hash'],
        'version': version_info['version'],
        'converted': datetime.now().isoformat(),
        'client': source_info.get('client'),
        'project': source_info.get('project'),
        'type': 'deck',
        'status': 'current',
        'frameworks': extract_frameworks(slides),
        'slide_types': extract_slide_types(slides),
        'tags': extract_tags(slides)
    }
    
    # Build content
    content = []
    content.append(f"# {deck_name}\n")
    content.append(f"**Source:** `{source_info['relative_path']}`\n")
    # ... header info
    
    for slide in slides:
        content.append(format_slide(slide))
    
    content.append(format_version_history(version_info))
    
    return yaml_frontmatter(frontmatter) + '\n'.join(content)
```

---

## 3. Source Tracking

### 3.1 Path Resolution

Source paths are stored relative to the markdown file location:

```
Folio Library             Sources
──────────────────       ─────────
library/                  sources/
├── ClientA/              ├── ClientA/
│   └── Project1/         │   └── Project1/
│       └── deck/         │       └── deck.pptx
│           └── deck.md   │
│               ↓         │
│    source: ../../../../sources/ClientA/Project1/deck.pptx
```

**Path computation:**
```python
def compute_relative_path(markdown_path: Path, source_path: Path) -> str:
    """Compute relative path from markdown file to source file."""
    md_dir = markdown_path.parent
    rel_path = os.path.relpath(source_path, md_dir)
    # Normalize to forward slashes for cross-platform
    return rel_path.replace('\\', '/')
```

### 3.2 Hash Computation

```python
import hashlib

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file, return first 12 chars."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()[:12]
```

### 3.3 Staleness Detection

```python
def check_staleness(markdown_path: Path) -> dict:
    """Check if source file has changed since conversion."""
    frontmatter = parse_frontmatter(markdown_path)
    source_path = resolve_source_path(markdown_path, frontmatter['source'])
    
    if not source_path.exists():
        return {'status': 'missing', 'source_path': str(source_path)}
    
    current_hash = compute_file_hash(source_path)
    stored_hash = frontmatter['source_hash']
    
    if current_hash != stored_hash:
        return {'status': 'stale', 'stored_hash': stored_hash, 'current_hash': current_hash}
    
    return {'status': 'current'}
```

---

## 4. Data Model

### 4.1 Library Structure

```
folio_library/
├── folio.yaml                     # Configuration
├── registry.json                  # Global index
│
├── ClientA/
│   ├── Project1/
│   │   ├── market_sizing/
│   │   │   ├── market_sizing.md   # Main document
│   │   │   ├── slides/            # Slide images
│   │   │   │   ├── slide-001.png
│   │   │   │   ├── slide-002.png
│   │   │   │   └── ...
│   │   │   ├── version_history.json
│   │   │   └── .texts_cache.json  # For diff detection
│   │   │
│   │   └── competitive_analysis/
│   │       └── ...
│   │
│   └── Project2/
│       └── ...
│
├── Internal/
│   └── Templates/
│       └── ...
│
└── Research/
    └── Industry/
        └── ...
```

### 4.2 Registry Schema

```json
{
  "version": 1,
  "updated": "2026-01-10T14:30:00Z",
  "decks": [
    {
      "id": "clienta-project1-market_sizing",
      "path": "ClientA/Project1/market_sizing/market_sizing.md",
      "source": "../../../sources/ClientA/Project1/market_sizing.pptx",
      "source_hash": "abc123def456",
      "converted": "2026-01-10T14:30:00Z",
      "version": 2,
      "status": "current",
      "slide_count": 12,
      "frameworks": ["2x2-matrix", "scr"],
      "tags": ["market-sizing", "competitive"]
    }
  ]
}
```

### 4.3 Version History Schema

```json
{
  "deck_id": "clienta-project1-market_sizing",
  "versions": [
    {
      "version": 1,
      "timestamp": "2026-01-05T10:00:00Z",
      "source_hash": "abc123def456",
      "source_path": "../../../sources/ClientA/Project1/market_sizing.pptx",
      "note": "Initial conversion",
      "slide_count": 12,
      "changes": {
        "added": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "removed": [],
        "modified": [],
        "unchanged": []
      }
    },
    {
      "version": 2,
      "timestamp": "2026-01-10T14:30:00Z",
      "source_hash": "def789ghi012",
      "source_path": "../../../sources/ClientA/Project1/market_sizing.pptx",
      "note": "Updated market size figures",
      "slide_count": 12,
      "changes": {
        "added": [],
        "removed": [],
        "modified": [2, 5],
        "unchanged": [1, 3, 4, 6, 7, 8, 9, 10, 11, 12]
      }
    }
  ]
}
```

---

## 5. Technology Stack

### 5.1 Core Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| CLI | Click | Command-line interface |
| Text Extraction | MarkItDown | PPTX/DOCX text extraction |
| PDF Processing | pdf2image | PDF to PNG conversion |
| Image Processing | Pillow | Image handling |
| LLM | anthropic | Claude API client |
| Config | PyYAML | Configuration files |

### 5.2 System Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| LibreOffice | PPTX→PDF | `apt install libreoffice` / `brew install libreoffice` |
| Poppler | PDF→PNG | `apt install poppler-utils` / `brew install poppler` |

### 5.3 Python Package Structure

```
folio/
├── __init__.py
├── __main__.py          # CLI entry point
├── cli.py               # Click commands
├── converter.py         # Main conversion logic
├── pipeline/
│   ├── __init__.py
│   ├── normalize.py     # Format normalization
│   ├── images.py        # Image extraction
│   ├── text.py          # Text extraction
│   └── analysis.py      # LLM analysis
├── tracking/
│   ├── __init__.py
│   ├── sources.py       # Source path management
│   ├── versions.py      # Version tracking
│   └── registry.py      # Global registry
├── output/
│   ├── __init__.py
│   ├── markdown.py      # Markdown assembly
│   └── frontmatter.py   # YAML frontmatter
└── config.py            # Configuration management
```

---

## 6. Error Handling

### 6.1 Error Categories

| Category | Behavior | Example |
|----------|----------|---------|
| Fatal | Stop immediately, report | Missing LibreOffice |
| File Error | Skip file, continue batch | Corrupted PPTX |
| API Error | Retry once, skip if fails | Claude timeout |
| Warning | Log, continue | Missing font substitution |

### 6.2 Recovery Strategies

**Partial conversion:**
- If image extraction succeeds but LLM fails → save without analysis
- If text extraction fails → save with images only, flag for review

**Atomic writes:**
- Write to temp file first, then rename
- Never leave partial/corrupted output

**State recovery:**
- Registry tracks last successful state
- Can resume batch processing after interruption

---

## 7. Performance Considerations

### 7.1 Bottlenecks

| Stage | Bottleneck | Mitigation |
|-------|------------|------------|
| LibreOffice | Process startup | Batch multiple files per invocation |
| Image extraction | CPU/memory | Stream processing, don't load all pages |
| LLM analysis | API rate limits | Parallel requests within limits, caching |
| Disk I/O | Large images | SSD recommended, async writes |

### 7.2 Caching Strategy

**Analysis cache:**
- Cache LLM responses by image hash
- Reuse if same image appears again (unchanged slide)

**Text cache:**
- Store previous version text for diff comparison
- Only regenerate if hash changes

### 7.3 Parallelization

```python
from concurrent.futures import ThreadPoolExecutor

def batch_convert(files: List[Path], max_workers: int = 4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(convert_file, f): f for f in files}
        for future in as_completed(futures):
            file = futures[future]
            try:
                result = future.result()
                print(f"✓ {file.name}")
            except Exception as e:
                print(f"✗ {file.name}: {e}")
```
