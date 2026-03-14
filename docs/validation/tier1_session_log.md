# Tier 1 Validation Run — Session Log

**Session date:** 2026-03-07 → 2026-03-08  
**Transcript ID:** [Tier 1 Validation Run](70775cfc-4386-4fe7-ab69-ed1c9c087f43)

---

## Phase 1: Read & Understand (15:53–16:00)

### Actions
1. Read `v0.1_Tier1_Validation_Run.md` — understood the 5-phase validation plan
2. Found 80+ real PPTX files in `sample_powerpoint/` (many with " copy" duplicates)
3. Explored project structure via subagent:
   - `folio/cli.py` — Click CLI with `convert`, `batch`, `status` commands
   - `folio/converter.py` — 10-stage pipeline orchestrator
   - `folio/pipeline/` — normalize, images, text, analysis stages
   - `folio/output/` — frontmatter.py, markdown.py
   - `folio/tracking/` — sources.py, versions.py
   - `docs/product/04_Implementation_Roadmap.md` — Tier 1 exit criteria
   - `docs/architecture/Folio_Ontology_Architecture.md` — frontmatter schema
4. Read `folio/config.py` — understood FolioConfig, LLM profiles, routing
5. Read `folio/pipeline/analysis.py` — understood LLM analysis, caching, fallback chain

### Key Findings
- Pipeline uses Anthropic Claude Sonnet 4 by default
- No `ANTHROPIC_API_KEY` set in environment initially
- Without API key, pipeline gracefully degrades to `SlideAnalysis.pending()` for all slides
- Existing `.venv` with Python 3.12.13 and folio installed
- No `folio.yaml` config file existed

---

## Phase 2: Build Test Corpus (16:00–16:05)

### Actions
1. Created `tests/validation/build_corpus.py` — selects 50 unique non-copy PPTX files
2. Created `tests/validation/corpus/` with symlinks to 50 selected decks
3. Created `folio.yaml` with:
   - `library_root: ./tests/validation/output`
   - `sources` pointing to corpus
   - `conversion.pptx_renderer: auto` (later changed to `powerpoint`)
4. Created `tests/validation/output/` and `docs/validation/` directories
5. Installed `uv` via Homebrew for Python management

### Corpus Selection (50 decks)
Alphabetically selected first 50 non-copy PPTX files from `sample_powerpoint/`. File sizes range from 0.1 MB (Building Blocks) to 71.4 MB (GenAI assessment).

---

## Phase 3: Run Validation (16:05–18:58)

### 3.0: Renderer Debugging (16:05–16:20)

**Problem:** Both LibreOffice and PowerPoint AppleScript failing from Cursor's terminal.

**LibreOffice diagnosis:**
```
soffice --headless --convert-to pdf ... → exit code 137 (SIGKILL)
```
- LibreOffice is installed at `/opt/homebrew/bin/soffice`
- macOS MDM policy blocks execution (SIGKILL on launch)
- User confirmed: "LibreOffice is blocked by McKinsey policy"
- Updated `folio.yaml`: `pptx_renderer: powerpoint`

**PowerPoint AppleScript diagnosis:**
```
osascript -e 'open POSIX file "/path/to/file.pptx"' → error -9074
```
- PowerPoint 16.106.3 installed and responsive (`version` command works)
- `open POSIX file` fails with error -9074 from Cursor's terminal
- `open -a "Microsoft PowerPoint" file.pptx` (Launch Services) works
- Root cause: **Cursor's terminal process lacks macOS Automation permission for PowerPoint**
- `save active presentation ... as save as PDF` hangs (also permission-related)

**Solution:** Run batch from Terminal.app instead of Cursor's integrated terminal.

### 3.1: Initial Batch Without API Key (16:20–16:30)

**Command:** `folio -v batch tests/validation/corpus --passes 1` (from Terminal.app)

**Result:** 38 succeeded, 12 failed. All analysis = `[pending]` (no API key).

**Failures (12):** All PowerPoint AppleScript errors:
- 2× timeout -1712 (first file + JO Pie Chart)
- 10× error -9074 (various template/unusual files)

**Decision:** User provided Anthropic API key. Aborted and restarted.

### 3.1: Single-Pass with LLM (16:30–18:06)

**Setup:**
- Created `tests/validation/.env` with `ANTHROPIC_API_KEY` (gitignored)
- Updated `run_batch.sh` to source `.env`
- Cleaned output directory
- Launched from Terminal.app

**Command:** `folio -v batch tests/validation/corpus --passes 1`

**Result:** 31 succeeded, 19 failed. **5,726 seconds (~95 min)**

**Successful (31 decks):**
- 602 total slides processed
- Real LLM analysis on every slide (Claude Sonnet 4)
- Evidence extraction with grounding validation
- Framework detection working (gantt, mece, process-flow, 2x2-matrix, etc.)

**Failed (19 decks):**
- 1× error -1728 ("object does not exist") — 20240402_Application Disposition
- 1× timeout -1712 — 20260312_CIO SteerCo_v3
- 17× error -9074 — consistent failures on template files and certain deck types

**Observation:** PowerPoint AppleScript interface degraded after ~31 conversions. Files that would normally succeed started failing with -9074 toward the end of the batch. This "AppleScript fatigue" pattern is consistent across runs.

### 3.2: Two-Pass with Depth (18:06–18:51)

**Problem:** Phase 3.2 started immediately after 3.1 but PowerPoint was dead. All 50 files failed in 6 seconds.

**Fix:** Killed PowerPoint, waited, relaunched. Created separate `run_phase32.sh` script.

**Command:** `folio -v batch tests/validation/corpus --passes 2` (from Terminal.app, fresh PPT)

**Result:** 19 succeeded, 31 failed. **2,697 seconds (~45 min)**

**Key observations:**
- `20240402_Application Disposition` succeeded this time (was failing in 3.1) — intermittent issue
- Successfully converted decks incremented to v2 (version tracking works)
- Pass 1 cache hit rate: 0% — PDF re-generation produces different image hashes, invalidating cache
- Pass 2 density scoring triggered on high-density slides (score > 2.0 threshold)
- Pass 2 added ~50% more evidence claims (deduplicated with pass-1)
- PowerPoint died again after 19 conversions (shorter lifespan than Phase 3.1)

**Cache invalidation root cause:** Each conversion generates a PDF in a new temp directory. The PDF bytes differ between runs (different internal timestamps, slightly different rendering). Since cache keys are image hashes (SHA256 of PNG extracted from PDF), the cache misses on every reconversion. The cache only helps within a single batch run.

### 3.3: Reconversion / Cache Test (18:51–18:52)

**Result:** 0 succeeded, 50 failed. 4 seconds.

**Cause:** PowerPoint crashed after Phase 3.2. The Phase 3.3 script launches PowerPoint but the fresh instance immediately returns -9074 for every file. PowerPoint needs more recovery time between heavy automation sessions.

### 3.4: Status Check

**Command:** `folio -v status`
**Result:** `Library: 31 decks, ✓ Current: 31`

---

## Phase 4: Validate Output Quality (18:52–19:10)

### Actions
1. Created `tests/validation/validate_frontmatter.py` — comprehensive validator
2. Ran against all converted output

### Initial Validation (Phase 3.1 output only)
- **31/31 PASS**
- Zero silent failures
- Zero unknown/pending slide types
- Grounding accuracy: 31/31 (100%)
- Median validation rate: 96%

### Post-Phase-3.2 Validation (updated output)
- First run: **32/32 PASS** but grounding accuracy dropped to 13/32

**Investigation:** Grounding mismatch — frontmatter `total_claims` was ~2x body evidence count. Suspected pipeline bug in two-pass evidence counting.

**Root cause found:** Validator regex bug, NOT pipeline bug:
```python
# Old (missed pass-2 evidence format):
r"^- \*\*(.+?) \((\w+)\):\*\*"
# Matches: "- **claim (high):**" but NOT "- **claim (high, pass 2):**"

# Fixed:
r"^- \*\*(.+?) \((\w+)(?:, pass \d+)?\):\*\*"
```

**Verified:** After fix, all evidence items (pass-1 and pass-2) correctly counted. Grounding accuracy restored to **32/32 (100%)**.

### Final Validation Results
| Metric | Value |
|--------|-------|
| Decks validated | 32 |
| Passed | 32 |
| Failed | 0 |
| Total slides | 612 |
| Total evidence | 2,904 |
| Avg validation rate | 93.4% |
| Median validation rate | 95.1% |
| Unknown types | 0 |
| Pending types | 0 |
| Grounding accuracy | 100% |

### Warnings (non-blocking)
- 1 non-standard slide_type: `timeline` (semantically valid, not in predefined enum)

---

## Phase 5: Report (19:10–19:20)

### Deliverables Created
| File | Purpose |
|------|---------|
| `docs/validation/tier1_validation_report.md` | Full validation report |
| `docs/validation/tier1_session_log.md` | This file |
| `tests/validation/build_corpus.py` | Corpus selection script |
| `tests/validation/run_batch.sh` | Phase 3.1 batch runner |
| `tests/validation/run_phase32.sh` | Phase 3.2 batch runner |
| `tests/validation/run_phase33.sh` | Phase 3.3 batch runner |
| `tests/validation/validate_frontmatter.py` | Output quality validator |
| `tests/validation/validation_results.json` | Machine-readable results |
| `tests/validation/run1_single_pass.log` | Phase 3.1 log |
| `tests/validation/run2_two_pass.log` | Phase 3.2 log |
| `tests/validation/run3_reconversion.log` | Phase 3.3 log |
| `tests/validation/run4_status.log` | Status command log |

### Gate Decision: CONDITIONAL PASS

---

## Issues Encountered & Debugging Notes

### Issue 1: LibreOffice Blocked by MDM
- **Symptom:** `soffice` exits with code 137 (SIGKILL)
- **Cause:** McKinsey MDM policy blocks LibreOffice execution
- **Resolution:** Set `pptx_renderer: powerpoint` in folio.yaml
- **Permanent fix needed:** Add pure-Python PPTX→PDF fallback

### Issue 2: Cursor IDE Lacks PowerPoint Automation Permission
- **Symptom:** `osascript -e 'open POSIX file ...'` returns error -9074
- **Cause:** macOS TCC (Transparency, Consent, and Control) blocks Cursor from sending AppleEvents to PowerPoint
- **Evidence:** Same commands work from Terminal.app; PowerPoint `version` query works (read-only AppleEvents allowed)
- **Resolution:** Run batch scripts from Terminal.app via `open -a Terminal script.sh`
- **Permanent fix needed:** Grant Cursor automation permission, or use non-AppleScript renderer

### Issue 3: PowerPoint AppleScript Error -9074 on Certain Files
- **Symptom:** 17 files consistently fail with error -9074 regardless of PowerPoint state
- **Affected file types:** McKinsey template files (IconGallery, SlideLibrary, Building Blocks, Lines_Textblocks_Trackersymbols), some workplan files, read-only files
- **Hypothesis:** Custom XML, non-standard slide masters, or embedded content that AppleScript's `open POSIX file` can't handle
- **Not tested:** Whether these files open via PowerPoint's File → Open GUI
- **Permanent fix needed:** Alternative open mechanism or pre-conversion to PDF

### Issue 4: PowerPoint AppleScript Fatigue
- **Symptom:** After 19–31 consecutive AppleScript-driven conversions, PowerPoint stops responding to ALL AppleScript events
- **Error pattern:** Files that normally succeed start returning -9074
- **Phase 3.1:** Survived 31 conversions before dying
- **Phase 3.2:** Survived 19 conversions before dying
- **Phase 3.3:** Dead on arrival (0 conversions)
- **Workaround:** Kill and restart PowerPoint between phases
- **Permanent fix needed:** Add delays between conversions, or use a more robust automation method

### Issue 5: Cache Invalidation on Reconversion
- **Symptom:** Phase 3.2 shows 0% cache hit rate despite Phase 3.1 having analyzed the same files
- **Cause:** Cache keys are SHA256 of extracted PNG images. Each run generates PDFs in a new temp directory, and PowerPoint produces subtly different PDF bytes each time (internal timestamps, rendering artifacts). Different PDFs → different PNGs → different hashes → cache miss.
- **Impact:** Every reconversion re-analyzes all slides via API (no cost savings, no speed improvement)
- **Permanent fix needed:** Use text hash + slide position as primary cache key, or persist images in deck directory and reuse

### Issue 6: folio.yaml Not Present Initially
- **Symptom:** No configuration file existed; pipeline would use defaults
- **Resolution:** Created `folio.yaml` with appropriate settings for validation run
- **Note:** The `library_root` was set to `./tests/validation/output` to isolate validation output

### Issue 7: pip Version Too Old for Editable Install
- **Symptom:** `pip install -e ".[dev,llm]"` failed — pip 21.2.4 doesn't support pyproject.toml editable installs
- **Resolution:** Used existing `.venv` which already had folio installed. Installed `uv` via Homebrew as a modern alternative.

### Issue 8: `-v` Flag Placement
- **Symptom:** `folio batch ... -v` → "No such option: -v"
- **Cause:** `--verbose` is on the top-level `folio` group, not on the `batch` subcommand
- **Resolution:** `folio -v batch ...` (flag before subcommand)

---

## Key Decisions Made

1. **Used real decks (Option A)** instead of generating synthetic ones — better validation of real-world behavior
2. **Ran from Terminal.app** instead of Cursor terminal — required for PowerPoint automation permissions
3. **Set `pptx_renderer: powerpoint`** — LibreOffice blocked by policy
4. **Classified PowerPoint failures as infrastructure issues, not pipeline bugs** — the pipeline correctly catches and reports every failure
5. **Did NOT fix any bugs** per validation instructions — only cataloged them
6. **Deleted `.env` file** after validation to protect API key
7. **Fixed validator regex** (not pipeline code) when grounding mismatch was traced to test tooling

---

## Reproduction Steps

To re-run this validation:

```bash
cd /Users/Jonathan_Oh/dev/folio.love
source .venv/bin/activate

# 1. Build corpus (if not already done)
python tests/validation/build_corpus.py

# 2. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Run from Terminal.app (NOT Cursor terminal)
# Single-pass:
folio -v batch tests/validation/corpus --passes 1 2>&1 | tee tests/validation/run1_single_pass.log

# Two-pass (restart PowerPoint first):
osascript -e 'tell application "Microsoft PowerPoint" to quit'
sleep 10
open -a "Microsoft PowerPoint"
sleep 5
folio -v batch tests/validation/corpus --passes 2 2>&1 | tee tests/validation/run2_two_pass.log

# 4. Validate output
python tests/validation/validate_frontmatter.py
```

**Important:** Restart PowerPoint between batch runs to avoid AppleScript fatigue.