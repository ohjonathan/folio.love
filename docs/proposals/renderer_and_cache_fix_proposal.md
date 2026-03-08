# Proposal: PPTX Renderer Reliability Fix

**Status:** Proposal (pre-spec) — Revision 7
**Date:** 2026-03-07 (revised 2026-03-08)
**Blocks:** Tier 1 exit criteria (50-deck validation)
**Relates to:** v0.4.0 multi-provider (no conflict)

---

## 1. Problem Statement

### 1.1 What's Broken

Tier 1 validation ran 50 real consulting PPTX decks through the folio pipeline. Results:

| Metric | Value |
|--------|-------|
| Decks tested | 50 |
| Succeeded | 32 |
| Failed | 18 |
| Failure stage | ALL normalization (PPTX → PDF) |
| Post-normalization failures | 0 |
| Slides processed (32 decks) | 612 |
| Evidence claims extracted | 2,904 |
| Evidence validation rate | 93.4% |
| Silent failures | 0 |

The pipeline logic is clean. The problem is entirely in the PPTX-to-PDF conversion stage.

### 1.2 Why It's Broken

**Four distinct failure modes in the PowerPoint AppleScript renderer:**

#### Failure Mode 1: AppleScript Error -9074 (17 files, consistent)

PowerPoint's `open POSIX file` AppleScript command fails with error -9074 for 17 specific PPTX files. Affected files include McKinsey template libraries (IconGallery, SlideLibrary, Building Blocks, Lines_Textblocks_Trackersymbols), files with custom XML and non-standard slide masters, read-only files, and workplan templates. These same files open normally via PowerPoint's GUI — the error is specific to the AppleScript `open POSIX file` interface.

The 17-file count is the validated count from the Tier 1 batch run, which ran from Terminal.app with proper TCC automation permission (see FM3). The full list of affected files is in `tier1_validation_report.md:41-57`.

Evidence: `tier1_validation_report.md:64-67`, `tier1_session_log.md:107-110`

#### Failure Mode 2: AppleScript Fatigue (cumulative)

After 19-31 consecutive AppleScript-driven conversions, PowerPoint stops responding to ALL AppleScript events. Files that normally succeed start failing with -9074 toward the end of a batch. Observed in:
- Phase 3.1: Survived 31 conversions before dying (`tier1_session_log.md:112`)
- Phase 3.2: Survived 19 conversions before dying (`tier1_session_log.md:130`)
- Phase 3.3: Dead on arrival — 0 conversions, 50 failures in 4 seconds (`tier1_session_log.md:136`)

Workaround: Kill and restart PowerPoint between batches. Not automated.

#### Failure Mode 3: TCC Automation Permission (per-terminal)

macOS TCC (Transparency, Consent, and Control) blocks Cursor IDE's terminal from sending AppleEvents to PowerPoint. Symptoms: `open POSIX file` returns -9074 from Cursor; the same command works from Terminal.app. PowerPoint's read-only AppleEvents (e.g., `get version`) work from both.

This is a one-time system setting, not a code issue. Running batch scripts from Terminal.app resolves it.

Evidence: `tier1_session_log.md:66-75`

#### Failure Mode 4: macOS App Sandbox Write Permission (confirmed but unlogged)

PowerPoint is a sandboxed macOS app. The current code path creates a `tempfile.TemporaryDirectory()` (e.g., `/private/var/folders/.../T/tmpd9owaka3`) at `converter.py:91` and tells PowerPoint via AppleScript to save the PDF there. PowerPoint's sandbox may block access to this arbitrary temp directory, triggering a **"Grant File Access"** dialog requiring manual user approval.

The architect confirmed this dialog **occurred during the Tier 1 batch run** but it was not captured in the session log — evidence is from a screenshot only, no log entry. This dialog appears when PowerPoint writes PDFs to unfamiliar temp directories. It may have contributed to some failures being attributed to -9074.

Evidence (user-provided screenshot):
```
┌─ Grant File Access ─────────────────────────────────┐
│ Additional permissions are required to access the   │
│ following files:                                     │
│                                                      │
│ /private/var/folders/h3/g7sjhkjs43765fn1n0kmgq...   │
│   /T/tmpd9owaka3                                     │
│                                                      │
│ Microsoft PowerPoint needs access to the folder     │
│ named "tmpd9owaka3". Select the item to grant       │
│ access.                                              │
│                                              [Select]│
└──────────────────────────────────────────────────────┘
```

**Logging gap:** The Tier 1 session log (`tier1_session_log.md`) and validation report (`tier1_validation_report.md`) do not mention this dialog. The architect confirmed it occurred but it was not instrumented. This gap means we cannot determine how many of the 18 failures were caused or worsened by this dialog.

#### LibreOffice: Blocked by MDM

LibreOffice headless (`soffice --headless --convert-to pdf`) is the primary renderer in "auto" mode. On the target environment (McKinsey managed macOS), LibreOffice is killed by MDM policy (exit code 137 = SIGKILL). Cannot be used.

### 1.3 Cache Invalidation on Reconversion

**Separate but related problem.** LLM analysis cache keys are based on `image_hash` = SHA256[:16] of PNG image bytes.

The chain:
1. Each PPTX → PDF conversion produces a subtly different PDF (timestamps, font substitution, rendering artifacts)
2. Different PDF → different PNG raster images via `pdf2image`
3. Different PNG → different `image_hash`
4. Different cache key → 100% cache miss

**Current cache structure** (from `folio/pipeline/analysis.py`):
- Pass 1 key: `image_hash` (with per-entry `_text_hash` validation for B1)
- Pass 2 key: `f"{image_hash}_deep"` (with `_text_hash` + `_pass1_context_hash` validation for B2)
- Global invalidation: `_cache_version`, `_prompt_version`, `_model_version`, `_provider_version`, `_extraction_version`

The per-entry validation hashes (`_text_hash`, `_pass1_context_hash`) are content-based and would survive reconversion, but they're validation hashes, not lookup keys. The lookup key remains `image_hash`, which is unstable across re-normalization.

Phase 3.3 of validation (cache reconversion test) could not run at all — PowerPoint crashed before processing any files.

### 1.4 Impact

| Impact | Severity |
|--------|----------|
| Error -9074: 17 files fail consistently | **P0 blocker** — must be resolved (automated conversion or documented operator workaround) per Tier 1 exit criteria |
| Sandbox dialog blocks unattended batch automation | **P0** — confirmed occurrence, blocks `folio batch` from running unattended |
| AppleScript fatigue limits batch size (19-31 files) | **P1** — no automated recovery, requires manual PowerPoint restart |
| Cache doesn't survive reconversion | **Deferred** — accepted limitation for v0.5.x; Approach J (Section 3) recommended as v0.5.1 follow-on spec. See Section 5 |

### 1.5 Roadmap Reconciliation

This is a renderer mitigation / operator-workaround proposal. It improves the managed-Mac failure path, but it does not by itself close every roadmap contract it touches. The following reconciliation is explicit so reviewers can assess what is improved, what remains out of scope, and which product decisions now constrain implementation.

1. **Week 1-2 (L147): "Pipeline that converts any PPTX/PDF without silent failures"** — Improved, not closed. Phase 0 targets the managed-Mac PPTX renderer failure surface; Phase 1 provides a supported PDF-first workaround for decks that still cannot be rendered automatically. Fully automatic PPTX coverage on managed Macs remains unresolved until Phase 0 results prove otherwise.

2. **Week 3 (L161): "Cached analysis persists across runs"** — Improved for fallback decks only. PDF-first decks use stable PDFs and therefore stable image hashes; automated PPTX reconversion still misses cache. Automated-PPTX cross-reconversion persistence remains unresolved until Approach J (v0.5.1 follow-on spec) or equivalent lands. See Section 5.

3. **Tier 1 Exit Criteria (L184): "50 real decks converted with zero silent failures"** — Automation required. This proposal enables an operator-assisted mitigation path for otherwise-unconvertible decks, but Tier 1 requires fully automated conversion. Manual/operator-exported PDF workflows do not count toward the 50-deck gate. Phase 1 therefore remains mitigation only.

4. **Tier 1 Gate (L419): "Zero silent conversion failures"** — Improved. This proposal preserves loud failures and adds clearer operator guidance/workarounds, but it does not claim full PPTX renderer closure on its own.

#### Tier 1 Counting Decision Surface

| Input Type | Tier 1 Status | Condition |
|---|---|---|
| Automated PPTX conversion | Counts | Existing route |
| Operator-exported PDF | Does not count | Mitigation only; Tier 1 requires full automation |
| Scanned PDF (avg <10 chars/page) | Does not count | Allowed as mitigation output; warning only, excluded from Tier 1 |
| Likely notes-page / portrait PDF | Does not count automatically | Warn + manual verification required before any Tier 1 candidate counting |
| Handout layout PDF | Does not count automatically | Advisory only; manual verification required before any Tier 1 candidate counting |

---

## 2. Codebase Investigation Findings

### 2.1 Pipeline Already Supports PDF Input

The pipeline is **weakly coupled** to PPTX. PDF input already works end-to-end:

| Stage | PPTX Path | PDF Path | Code |
|-------|-----------|----------|------|
| Normalize | LibreOffice/PowerPoint → PDF | Copy directly | `normalize.py:44-48` |
| Image extract | From normalized PDF | From input PDF | `images.py:29-129` (format-agnostic) |
| Text extract | MarkItDown (PPTX-native) | pdfplumber (PDF-native) | `text.py:148-158` |
| LLM analysis | Format-agnostic | Format-agnostic | `analysis.py` |
| CLI | `folio convert deck.pptx` | `folio convert deck.pdf` | `cli.py:51` |
| Batch | Default `*.pptx` pattern | Override with `--pattern "*.pdf"` | `cli.py:112` |

**Key design detail:** `converter.py:117` calls `text.extract_structured(source_path)` using the **original source file**, not the normalized PDF. For PPTX input, text comes from MarkItDown (high quality: slide boundaries, speaker notes, structural elements). For PDF input, text comes from pdfplumber (lower quality: page-level text, no speaker notes).

### 2.2 Text Quality Gap

The 93.4% evidence validation rate from Tier 1 reflects MarkItDown quality (PPTX path). Switching to PDF-only input would degrade text extraction:

| Feature | MarkItDown (PPTX) | pdfplumber (PDF) |
|---------|-------------------|-----------------|
| Slide boundaries | HTML comments / headers | Page breaks only |
| Speaker notes | Extracted | Not available |
| Structural elements | Title/body/note | Flat text |
| Slide numbering | Pattern-detected (5 strategies) | Page number |

This tradeoff is the key tension in approach selection.

### 2.3 python-pptx: Assessed and Found Inadequate

python-pptx was assessed during Tier 1 validation and found inadequate for production rendering. It cannot handle SmartArt, charts, gradients, or custom fonts — features prevalent in the consulting deck corpus. It remains a dev-only dependency for test fixtures. The Tier 1 validation report lists pure-Python fallback as a candidate for further investigation, but the rendering fidelity gap makes it unsuitable as a primary path.

### 2.4 Cache Key Design is Semantically Correct

The current `image_hash` cache key is the right key — the LLM analyzes the **image**, not the text. Two slides with identical text but different visual layouts should not share a cache entry. The problem is not the key design; it's that the same logical slide produces different images on re-normalization.

**If the PDF input is stable** (same PDF every time), image hashes are stable, and caching works correctly.

### 2.5 Source Tracking Model

The existing source tracking model is strictly single-source. Key contracts:

- **`SourceInfo` dataclass** (`sources.py:13-21`): `absolute_path`, `relative_path`, `file_hash` — all singular fields
- **`compute_source_info()`** (`sources.py:24-27`): takes `source_path: Path` and `markdown_path: Path` — single source
- **`converter.py:171`**: `source_info = sources.compute_source_info(source_path, markdown_path)` — one source_path
- **`compute_version()`** (`versions.py:141-148`): takes `source_hash: str` and `source_path: str` — singular
- **`VersionInfo`** (`versions.py:59-68`): contains `source_hash: str` and `source_path: str` — singular
- **`generate()`** (`frontmatter.py:13-30`): receives `source_relative_path: str`, `source_hash: str`, `source_type: str` — singular
- **`check_staleness()`** (`sources.py:67-71`): compares one `stored_hash` against one resolved file — singular

**Implication:** A future hybrid mode would require extending this model to track two sources (PDF + PPTX) without breaking the existing single-source contract. This is a non-trivial change touching sources, versions, frontmatter, and converter.

### 2.6 PDF Contract Assumptions

The pipeline makes implicit assumptions about PDF structure that become important when accepting user-provided PDFs:

- **`text.py` PDF extraction:** page order = slide order, 1-indexed, empty pages are skipped
- **`images.py`:** all pages converted via `convert_from_path()` (`images.py:76`), page order = slide order, image count is authoritative for slide count
- **Text reconciliation:** `reconcile_slide_count()` handles count mismatches between image extraction and text extraction (padding with empty SlideText)
- **Not handled:** notes pages, handout layouts, supplementary pages, scanned PDFs (no text layer)

**Implication:** Must define what constitutes a valid PDF input for the pipeline. Notes-page PDFs would have ~2× the expected page count, handout layouts would have multiple slides per page, and scanned PDFs would yield empty text extraction.

---

## 3. Approach Evaluation

| # | Approach | Fixes Sandbox Dialog? | Fixes -9074? | Fixes Fatigue? | Fixes Cache? | Text Quality | Effort | Risk |
|---|----------|-----------------------|-------------|----------------|-------------|-------------|--------|------|
| **A** | PDF-first input | Yes (sidesteps) | Yes (sidesteps) | Yes (sidesteps) | Yes (stable hashes) | **Degraded** (pdfplumber) | 1-2d | Low |
| **B** | python-pptx direct | N/A | N/A | N/A | No | **Poor** (no SmartArt/charts) | Med | High |
| **C** | Hybrid dual-input | Yes (sidesteps) | Yes (sidesteps) | Yes (sidesteps) | Yes (stable hashes) | **Preserved** (MarkItDown) | 5-7d | Med |
| **D** | Fix sandbox output dir | **Yes** (confirmed, unlogged) | No | No | No | None | 0.5d | Low |
| **E** | Fix AppleScript TCC | No (different problem) | No | No | No | None | One-time (not code) | Low |
| **F** | JXA / alt automation | Partial | Partial | Maybe | No | None | Med | High |
| **G** | Docker LibreOffice | Yes | Yes | Yes | Yes (deterministic) | None | 5+d | High (MDM may block Docker too) |
| **H** | Cache key redesign | No | No | No | Yes | None | 2-3d | Med |
| **I** | `open -a` + export automation | No | **Unknown** (spike needed) | No | No | None | 1-2d | Med |
| **J** | Image artifact reuse | No | No | No | **Yes** (stable PNGs) | None | 1d | Low |

### Approach Details

**A: PDF-First Input.** The pipeline already supports PDF. Users export PDFs manually from PowerPoint (File → Export → PDF), then run `folio batch ./pdfs --pattern "*.pdf"`. No code changes needed for conversion; only CLI documentation and workflow guidance. Tradeoff: text extraction via pdfplumber instead of MarkItDown.

**B: python-pptx Direct Extraction.** Assessed and found inadequate. Can't render SmartArt, charts, gradients, custom fonts. Would produce low-fidelity slide images unsuitable for consulting deck analysis.

**C: Hybrid Dual-Input.** Accept both PPTX and PDF for the same deck. Use PPTX for text (MarkItDown quality), PDF for images (stable, user-controlled). New CLI options: `--pptx-source` on convert, `--pptx-dir` on batch. Best-of-both-worlds but more complex. Effort revised upward (5-7d) to account for source tracking, staleness, and versioning changes identified in Section 2.5.

**D: Fix Sandbox Output Directory.** The architect confirmed the sandbox permission dialog occurred during the Tier 1 batch but it was not captured in the session log (evidence: screenshot only). Fix: write the intermediate PDF to `deck_dir` (already created by converter at line 81) instead of the temp directory. Clean up after image extraction.

**E: Fix AppleScript TCC.** This is a separate issue from the sandbox dialog. TCC (Transparency, Consent, and Control) blocks Cursor's terminal from sending AppleEvents to PowerPoint. Running from Terminal.app works. This is a one-time system setting, not a code change.

**F: JXA / Alternative Automation.** Replace AppleScript with JavaScript for Automation (JXA) or `open` shell command. May have a different permission model but still depends on PowerPoint GUI, still subject to fatigue. Marginal improvement for significant effort.

**G: Docker LibreOffice.** Run LibreOffice in a Docker container, bypassing MDM. Eliminates all platform dependencies. But Docker itself may be blocked by MDM policy. Heavyweight for a single-user CLI tool.

**H: Cache Key Redesign.** Change lookup key from `image_hash` to `text_hash + slide_position`. Would survive reconversion but doesn't fix any renderer problems. Also semantically wrong — LLM analyzes images, not text.

**I: `open -a` + Export Automation.** The validation log shows that `open -a "Microsoft PowerPoint" file.pptx` (Launch Services) bypasses TCC permission issues where `open POSIX file` fails (`tier1_session_log.md:71`). However, the evidence only demonstrates a TCC bypass (FM3) — opening files from Cursor's terminal. Whether Launch Services also resolves the file-specific -9074 errors (FM1) observed from Terminal.app is **unknown and requires a spike**. The 17 consistent -9074 failures occur from Terminal.app where TCC is not the issue; the root cause for those files may be file-intrinsic (custom XML, non-standard slide masters). Effort: 1-2d. Risk: Medium — outcome genuinely unknown until tested.

**J: Image Artifact Reuse.** If `slides/` in `deck_dir` already has images from a previous conversion of the same source (source_hash matches version_history), skip image extraction entirely. Existing PNGs produce the same `image_hash` → cache hits. Currently `images.extract()` (`images.py:102-116`) does an atomic swap, always regenerating images. Approach J would add a source-hash guard before extraction. This is aligned with the current cache model (no key changes needed) and requires ~1 day of effort. Not in scope for this proposal; recommended as v0.5.1 follow-on spec. See Section 1.5.

---

## 4. Recommendation: Spike + PDF-First Fallback (Two-Phase)

### Phase 0: Diagnostic Spike + Quick Fixes (2-3 days)

Phase 0 is a diagnostic spike — not a known-cause fix. It combines the highest-impact quick fixes with failure instrumentation to establish the empirical failure baseline reviewers require.

Four parallel work items:

#### 0a: Sandbox output directory fix

Write the intermediate PDF to `deck_dir` instead of `tempfile.TemporaryDirectory()` when PowerPoint is the renderer. This is a preventive fix — the sandbox dialog was confirmed to occur but its contribution to failures is unknown due to the logging gap.

**Code path (corrected from R3):** `converter.py:97` passes `tmpdir` to `normalize.to_pdf(source_path, tmpdir, ...)`. Inside `normalize.py`, `to_pdf()` computes `expected_pdf = output_dir / f"{source_path.stem}.pdf"` (line 55) — one path used by BOTH LibreOffice (line 60) and PowerPoint (lines 72, 76), including auto-fallback (lines 71-73). Changing `output_dir` from the converter side would redirect ALL renderers, including LibreOffice, which is incorrect.

**R3 error:** R3 stated "changing what `converter.py:97` passes as `output_dir` — for the PowerPoint renderer path only" and "No changes needed in `normalize.py`." Both are wrong. In auto mode, renderer selection and fallback live inside `normalize.to_pdf()`. Converter.py doesn't know which renderer will be used.

**Correct fix:** Add `pptx_output_dir: Path | None = None` keyword parameter to `normalize.to_pdf()`:

```python
# normalize.py — new signature:
def to_pdf(
    source_path: Path, output_dir: Path, *,
    pptx_output_dir: Path | None = None,
    timeout: int = 60, renderer: str = "auto"
) -> Path:
    ...
    expected_pdf = output_dir / f"{source_path.stem}.pdf"  # for LibreOffice
    pptx_pdf = (pptx_output_dir or output_dir) / f"{source_path.stem}.pdf"  # for PowerPoint

    if renderer_name == "libreoffice":
        try:
            _convert_with_libreoffice(..., expected_pdf)  # unchanged
        except NormalizationError:
            ...
            _convert_with_powerpoint(source_path, effective_timeout, pptx_pdf)  # uses pptx_pdf
            return pptx_pdf
    elif renderer_name == "powerpoint":
        _convert_with_powerpoint(source_path, effective_timeout, pptx_pdf)  # uses pptx_pdf
        return pptx_pdf
```

The final `if not expected_pdf.exists()` check at `normalize.py:79` must select the correct path variable based on which renderer ran. Add a `used_pptx_path` flag or track which path to check.

**Converter.py call site:**
```python
pdf_path = normalize.to_pdf(
    source_path, tmpdir,
    pptx_output_dir=deck_dir,  # NEW
    timeout=self.config.conversion.libreoffice_timeout,
    renderer=self.config.conversion.pptx_renderer,
)
```

**Cleanup:** Add `intermediate_pdf.unlink()` after image extraction succeeds (`converter.py:~108`).

**Sandbox access assumption:** PowerPoint sandbox access to `deck_dir` is assumed, not proven. `deck_dir` is under `library_root` which could be anywhere on disk. It is more likely accessible than `/var/folders/` temp dirs because `library_root` is typically a user-owned directory that PowerPoint has already interacted with. If blocked, fallback to `source_path.parent`.

**Rationale for `deck_dir`:**
- Avoids OneDrive sync churn and read-only source directories
- Explicit cleanup: `intermediate_pdf.unlink()` after image extraction succeeds
- The tempdir is still used for the LibreOffice path; for the PowerPoint path, `deck_dir` replaces it

**Files changed:**
- `folio/pipeline/normalize.py:17-85` — add `pptx_output_dir` parameter, split `expected_pdf` into renderer-specific paths (`expected_pdf` for LibreOffice, `pptx_pdf` for PowerPoint)
- `folio/converter.py:96-100` — pass `pptx_output_dir=deck_dir`
- `folio/converter.py:~108` — add `intermediate_pdf.unlink()` after image extraction

#### 0b: `open -a` investigation (spike, outcome unknown)

Test whether replacing `open POSIX file` with Launch Services (`open -a "Microsoft PowerPoint" <file>`) + AppleScript export avoids -9074 for the 17 failing template files.

**Evidence context:** `tier1_session_log.md:71` confirms `open -a "Microsoft PowerPoint" file.pptx` works where `open POSIX file` fails, but this was observed from **Cursor's terminal** — a TCC bypass (FM3). The 17 consistent -9074 failures occur from **Terminal.app** where TCC is not the issue. Whether Launch Services also resolves file-specific -9074 errors (FM1) is genuinely unknown.

**Success criteria:**
- If `open -a` opens AND exports 3+ of the 17 failing files from Terminal.app → addresses FM1, implement two-step approach in `normalize.py`
- If `open -a` opens but export fails → addresses nothing beyond FM3 (TCC), no further automation gain
- If `open -a` fails to open the files → confirms failure is file-intrinsic, not an AppleScript interface issue

**Scope:** Test on 3-5 files from the -9074 failure list, from Terminal.app.

#### 0c: Failure instrumentation

Add structured logging to `folio batch` to capture the observable conversion surface:
- Log each conversion: file name, renderer used, outcome, duration
- Limit outcome categories to what current runtime surfaces can actually expose: success, AppleScript error code (if available), timeout, unknown
- Output summary table at end of batch

This gives the observed failure baseline needed to scope Phase 1 accurately. It does **not** produce a perfect root-cause taxonomy.

**Limitation:** Instrumentation can capture AppleScript error codes and process timeouts but cannot detect GUI dialog presence programmatically. The macOS "Grant File Access" dialog is a modal sandbox prompt that does not surface in process exit codes or stderr. Phase 0a addresses the sandbox path preventively; any inferred sandbox contribution remains indirect.

**Follow-on spec requirement:** The eventual Phase 0 spec must define a small structured normalization outcome surface for batch orchestration, including:
- `renderer_used`
- `duration_ms`
- `error_code` if known
- `retryable` boolean

`folio batch` should consume this structured outcome instead of parsing human-readable exception strings.

#### 0d: Preemptive restart for fatigue resilience

**Why `get name` doesn't work:** It's a read-only AppleScript command exercising a different code path than `open POSIX file`. During fatigue, `open POSIX file` fails with -9074 while `get name` still succeeds (`tier1_session_log.md:69-71`). A health check that always passes is not a health check.

**New strategy (dedicated-session only):**
- **Precondition:** `folio batch` runs in a dedicated PowerPoint session with no unrelated presentations open and may own/restart the app process in that session. If this invariant is violated, fall back to manual batch boundaries rather than app-level restart automation.
- **Primary:** Preemptive restart every N=15 conversions (below the 19-31 observed fatigue threshold, per `tier1_session_log.md:112,130`). Track count in batch loop; after the 15th conversion, `quit` → 5s wait → relaunch.
- **Secondary:** On an unexpected -9074 during batch, restart + retry once. If retry succeeds, treat it as likely fatigue and reset the counter. If retry fails, classify it as unresolved -9074 and route the deck to Phase 1/manual handling rather than automatically calling it file-incompatible.
- Log all restarts (preemptive and reactive).

**Implementation note:** Restart logic goes in the batch loop (`cli.py`), not `normalize.py`. The normalize module stays stateless; the batch orchestrator owns process lifecycle. In the initial spike, 0d can work with the existing exception-based flow; the structured outcome from 0c makes this cleaner when the full spec lands.

**Phase 0 deliverables:**
- Sandbox output fix applied
- `open -a` investigation results (pass/fail on 3-5 -9074 files)
- Failure instrumentation in `folio batch`
- Preemptive restart resilience between conversions (every N=15, dedicated session only)
- Updated observed failure baseline from re-run of all 50 decks (with sandbox contribution remaining inferential, not directly measured)

### Phase 1: PDF-First Fallback for Unconvertible Files (1-2 days)

Phase 1 is a **mitigation workflow** for files that remain unconvertible after Phase 0. It does not, by itself, establish Tier 1 closure. Manual PDF export is a supported operator workaround, but those outputs do not count toward the 50-deck gate because Tier 1 requires full automation.

**Scoping depends on Phase 0 results:**
- If Phase 0b resolves all 17 files → Phase 1 becomes documentation-only (no code urgency)
- If Phase 0b resolves most but not all → Phase 1 provides a documented operator workaround for the remaining files (expected 0-5)
- If Phase 0b fails entirely → Phase 1 provides the operator workaround for all 17 files

In all cases, the operator exports the unconvertible PPTX files to PDF manually (File → Export → PDF) and runs `folio convert <deck>.pdf`. This is a supported mitigation workflow for files that cannot be automated. `normalize.py:130` already mentions `folio convert <deck>.pdf` as option 3 in the "no renderer" error message. These outputs remain valid library artifacts but do not close Tier 1.

**Text quality tradeoff:** Accepted for the files that can't be automated. These files have zero representation in the library today — pdfplumber-quality text is better than nothing.

**Product Tradeoff: PDF-Canonical Fallback Decks**

When a PPTX file falls back to PDF input (manual export), the PDF becomes the canonical source. This is a product-level tradeoff, not just an implementation detail.

- **Source identity:** `source` = PDF path, `source_hash` = PDF hash, `source_type` = `"pdf"` (via `_detect_source_type()` at `converter.py:303-317`).
- **Tradeoff:** PPTX changes are invisible until the operator re-exports the PDF. `check_staleness()` (`sources.py:67-96`) reports "current" for the unchanged PDF — technically correct but potentially misleading if the PPTX has been updated.
- **Impact:** This is an **ongoing operational requirement**, not a one-time setup. Every PPTX edit requires a manual re-export to update the library.
- **Lifecycle:** PDF-canonical status is permanent for a given deck. There is no automatic switchback. If automation improves (e.g., Phase 0b resolves the file's -9074), the operator can manually re-run with the PPTX to restore full automation.
- **Recommendation:** Acceptable as mitigation because these decks have zero library representation today. Pdfplumber-quality text with PDF-canonical tracking is strictly better than no representation, but it is not equivalent to restoring PPTX renderer reliability.
- **Version continuity:** Version history will be noisier when a deck switches source type/path (PPTX v1 → PDF v2), even if slide meaning is unchanged.
- Version history records the source_path change naturally (v1 PPTX → v2 PDF).
- No code changes to `sources.py`, `versions.py`, or `frontmatter.py` — the existing single-source model handles this correctly. This keeps the implementation narrow, but it is not product-neutral.

**Output-Compatibility Acceptance Criteria:**

1. Run ALL fallback decks through the full pipeline (not spot-check)
2. Evidence validation rate ≥80% per deck (below 93.4% baseline, accounting for pdfplumber degradation)
3. Frontmatter completeness: programmatic YAML check for all required fields
4. Zero silent failures
5. Cache stability: second run = 100% cache hit
6. Threshold breach: if any deck <80%, treat it as mitigation-only output. Phase 1 never contributes to the Tier 1 candidate count; if the automated corpus after Phase 0 remains <50, further automation work is needed.

**What to change:**
- Document the PDF-first workflow for managed Macs (README, new guide), including counting caveats and the dedicated-session restart assumption
- Update `folio batch` help text and examples to show `--pattern "*.pdf"`
- Enhance the `NormalizationError` message in `_select_renderer()` to point users to the PDF-first workflow when specific files fail
- Add CLI/log warnings for likely notes-page/portrait PDFs and scanned PDFs (no frontmatter changes)
- Optional: add a convenience `--pdf-dir` alias on `folio batch`
- **Define PDF input contract** (see Section 4.5): slides-only export is preferred; portrait/scanned/handout PDFs are warnings and counting exclusions, not global rejection rules

**Files changed:**
- `folio/cli.py` — batch help text, examples, optional `--pdf-dir`, restart/reporting assumptions
- `folio/converter.py` — warning surfacing for scanned/portrait PDF cases (no frontmatter changes)
- `folio/pipeline/normalize.py` — enhanced error message and PowerPoint-only output path fix; portrait-PDF warning only (no rejection)
- New: `docs/guides/managed_mac_workflow.md`

---

## 4.5 PDF Input Contract

Defines what constitutes a valid PDF input for the pipeline. Relevant for Phase 1 (PDF-first fallback).

### Supported

Slides-only PDF export (File → Export → PDF in PowerPoint). One page per slide. This is the only export mode that preserves the 1:1 page-to-slide mapping the pipeline assumes.

### Inputs Requiring Operator Review

| Input type | Symptom | Detection | Action |
|-----------|---------|-----------|--------|
| Likely notes pages / portrait PDF | Portrait aspect ratio (height > width) | First-page aspect ratio check | **Warn + exclude from automatic Tier 1 counting unless manually verified** |
| Scanned PDFs | No text layer | Avg text <10 chars/page after `text.extract_structured()` | **Warn + exclude from Tier 1 count** |
| Handout layouts | Multiple slides per page | Not reliably detectable | **Advisory only** (outside automated enforcement) |

### Enforcement Strategy

**Likely notes pages / portrait PDFs (warn + manual review):** Slides-only PDFs are usually landscape (width > height); notes-page PDFs are often portrait (height > width). Add a first-page aspect ratio check in `normalize.py:to_pdf()` after the PDF copy step (line 47). If the first page is portrait, emit a warning that the PDF may be a notes export. Continue conversion unchanged. Exclude it from automatic Tier 1 counting unless the operator manually verifies that it is an intentional portrait slide deck. Do **not** add `--allow-notes-pdf` in this proposal.

**Scanned PDFs (warn + exclude from Tier 1 count):** After `text.extract_structured()` in `converter.py`, check if average extracted text is <10 characters per page. If so, emit a warning in CLI/log output. The pipeline still processes scanned PDFs (image analysis is valid), but they are excluded from any Tier 1 candidate count. Evidence claims cannot be grounded against nonexistent text, so counting them would misrepresent pipeline quality. Track this exclusion in operator output/reporting, not frontmatter metadata. See the Tier 1 Counting Decision Surface (Section 1.5).

**Handout layouts (advisory):** Not reliably detectable from PDF structure alone. Document in the managed Mac workflow guide that users should export as "slides only," not handout layouts. Handout PDFs remain outside automated enforcement and outside automatic Tier 1 counting.

---

## 5. Cache Key Analysis (Deferred)

See Section 1.5 (Roadmap Reconciliation) for impact on the Week 3 deliverable ("Cached analysis persists across runs").

This proposal improves cache behavior only for PDF-first mitigation decks. Automated-PPTX reconversion cache persistence remains unresolved in v0.5.0 until Approach J (image artifact reuse, Section 3) or equivalent lands as a v0.5.1 follow-on spec.

### No Cache Key Change Needed

The cache invalidation problem is **solved as a side effect** of PDF-first input:

| Scenario | Image Hash Stable? | Cache Works? |
|----------|-------------------|-------------|
| Same PPTX, re-normalized by PowerPoint | No (different PDF each time) | **No** |
| Same PDF provided by user (Phase 1) | Yes (identical PDF → identical PNGs) | **Yes** |
| Same PDF + PPTX hybrid (future) | Yes (same PDF path) | **Yes** |

The current `image_hash` key is semantically correct — the LLM analyzes images, and images should be the cache identity. The fix is to make the image input stable (user-provided PDF), not to change the key.

`image_hash` remains the primary and only cache lookup key. No secondary index is needed for v0.5.x.

### Cache Behavior Under Automated PPTX Path

If the automated PPTX→PowerPoint→PDF path remains the primary conversion method (i.e., Phase 0 fixes resolve most failures), cache misses on reconversion are a **known accepted limitation** for v0.5.x.

**Cost:** ~$2-5 per 50-deck batch at current Claude Sonnet 4 pricing. Acceptable because reconversion is infrequent (typically triggered by prompt/model version bumps, not re-export) and LLM cost per batch is low.

**Why not fix it now:**
- Cache key redesign (Approach H) is semantically wrong — the LLM analyzes images, not text
- Approach J (image artifact reuse) solves it at the extraction layer with ~1 day of effort — see Section 3
- Image persistence in `deck_dir` would solve it but is out of scope for this proposal
- The PDF-first path (Phase 1) doesn't have this problem — same PDF always produces the same images

This limitation only matters if users regularly re-run automated PPTX conversion on the same decks. In practice, most reconversions will be triggered by config changes (`_cache_version`, `_prompt_version`, `_model_version`) which invalidate the cache regardless.

### If Cache Key Redesign Were Needed Later

A secondary lookup index could be added without changing the primary key:
```
Primary key:   image_hash (visual identity — current)
Secondary key: f"{text_hash}_{slide_position}" (content identity — fallback)
```
On miss by `image_hash`, check secondary key. Validate `_text_hash` matches. Return cached analysis if so.

**Recommendation:** Defer. PDF-first input eliminates the need for fallback decks. For the automated PPTX path, Approach J (v0.5.1 follow-on spec) provides the fix. See Section 1.5.

### Migration Story

No cache migration needed. Existing caches keyed by `image_hash` will:
- **Hit** if the same PDF is used (Phase 1 workflow)
- **Miss** if a different PDF is generated (old PowerPoint workflow) — correct behavior, triggers fresh analysis
- **Be invalidated** if `_cache_version`, `_prompt_version`, or `_model_version` changes — existing mechanism

---

## 6. Scope Assessment

### Spec Decomposition

| Deliverable | Type | Effort | Depends On |
|-------------|------|--------|-----------|
| Phase 0: Diagnostic spike + quick fixes + structured normalization outcome requirement | Spike (multi-commit) | 2-3d | Nothing |
| Phase 1: PDF-first mitigation workflow | Spec `v0.5.0_pdf_first_workflow_spec.md` | 2d | Phase 0 results; mitigation only, not Tier 1 counting |

Approach J (v0.5.1 follow-on): ~1 day, separate spec. Not included in this proposal's effort total.

### Interaction with v0.4.0 Multi-Provider

**No conflict.** Multi-provider (PR #8, merged) changed:
- `folio/pipeline/analysis.py` — provider abstraction, fallback chains
- `folio/config.py` — LLM profiles, routing
- `folio/llm/` — new provider package

This proposal changes different files/functions:
- `folio/pipeline/normalize.py:17-85` — `pptx_output_dir` parameter, renderer-specific paths, portrait-PDF warning (no rejection)
- `folio/converter.py` — input routing / warning surfacing (different section than LLM call routing), `pptx_output_dir` argument, structured normalization outcome plumbing
- `folio/cli.py` — batch restart/reporting, help text, examples

**PR #8 coupling note:** `_provider_version` and `_llm_metadata` were introduced by PR #8. Phase 0/1 don't conflict — no `analysis.py` or frontmatter schema changes are proposed.

### Should This Block v0.4.0?

No. v0.4.0 is merged. This work is v0.5.0. They proceed independently.

### Total Effort

**4-5 days** across both phases. Accounts for the normalize.py API change (Phase 0a), structured normalization outcome requirement (Phase 0c), dedicated-session restart handling (Phase 0d), canonical source policy, quantitative quality gate, and PDF contract/reporting changes (Phase 1).

---

## 7. Verification Plan

### Phase 0 Verification

1. Apply sandbox output directory fix
2. Re-run ALL 50 decks via `folio batch`
3. **Expected:** Zero "Grant File Access" dialogs
4. **Measure:** Observed failure count and change after Phase 0a. Sandbox contribution remains inferential, not directly measurable.
5. **Output:** Updated observed failure baseline that determines Phase 1 scoping
6. Verify failure instrumentation outputs summary table with renderer used, duration, observed AppleScript error code (if any), timeout, and unknown outcome categories — no direct `sandbox` bucket
7. Test `open -a` alternative on 3-5 files from the -9074 failure list
8. Verify preemptive restart works only in a dedicated PowerPoint session: run batch of >15 files, verify PowerPoint restarts at N=15 with logging. Test reactive restart: inject unexpected -9074, verify retry + recovery

### Phase 1 Verification

1. Export ALL unconvertible PPTX files to PDF manually via PowerPoint (File → Export → PDF, slides-only layout)
2. Run full pipeline on each: `folio convert <deck>.pdf`
3. **Expected:** All mitigation candidates convert successfully. These outputs remain mitigation-only and do not count toward Tier 1.
4. Evidence validation rate ≥80% per fallback deck (accounting for pdfplumber degradation below 93.4% baseline)
5. Frontmatter completeness: programmatic YAML check for all required fields on every output
6. Source provenance: verify `source_type="pdf"`, `source_hash` matches PDF file hash
7. Cache stability: run same batch again — **expected:** 100% cache hit rate on second run
8. Zero silent failures
9. Threshold breach: if any deck <80% evidence validation, keep it as mitigation-only output. If the automated corpus after Phase 0 remains <50, further automation work is needed
10. Verify scanned PDFs and likely notes-page / portrait PDFs are excluded from automatic Tier 1 counting and called out in CLI/log output
11. Verify operator-assisted PDFs are tallied separately from automated PPTX conversions and excluded from Tier 1 reporting

### Regression

- All 345+ existing tests must pass after each phase
- No changes to `analysis.py`, cache logic, or frontmatter schema — existing cache/frontmatter tests remain valid

---

## 8. Open Questions

### Resolved

1. **Source directory writability** (was Q1): Resolved — write intermediate PDF to `deck_dir`, not source directory. `deck_dir` is always writable (converter creates it at line 81). Avoids OneDrive sync churn and read-only source dirs.
4. **PDF contract handling** (was Q4): Resolved — likely notes-page / portrait PDFs are warned + excluded from automatic Tier 1 counting unless manually verified; scanned PDFs are warned + excluded; handout layouts remain advisory only. See Section 4.5.
7. **Approach J timing** (was Q7): Resolved — recommended as v0.5.1 follow-on spec. Not bundled with this proposal. See Section 1.5.
9. **Tier 1 scope:** Resolved — Tier 1 requires fully automated conversion. Operator-assisted PDF conversions do not count toward the 50-deck target; Phase 1 is mitigation only.
11. **Dedicated-session assumption:** Resolved — approved. `folio batch` may own and restart the entire PowerPoint app process when run in a dedicated session with no unrelated presentations open.

### Updated

2. **True error -9074 count:** Unknown until Phase 0 is applied and 50 decks re-tested. Phase 0b (`open -a` investigation) may resolve some or all of the 17.
3. **AppleScript fatigue:** Addressed by preemptive restart (Phase 0d) only when Folio owns a dedicated PowerPoint session. Otherwise the fallback is manual batch boundaries. Replaces both the proposed `killall` and the `get name` health-check approaches.

### New

5. **Reconversion cache stability:** Should image persistence in `deck_dir` be addressed in v0.6.x to stabilize cache keys for the automated PPTX path?
6. **`open -a` viability:** Does Phase 0b show Launch Services works from Terminal.app for the 17 failing files? The evidence (`tier1_session_log.md:71`) only proves TCC bypass (FM3), not FM1 resolution. Outcome determines Phase 1 scope.
8. **Portrait PDF verification workflow:** Some slide decks may use portrait orientation intentionally (e.g., mobile-format presentations). What operator evidence is sufficient to treat a portrait PDF as an intentional slide deck rather than a notes export?
10. **Preemptive restart interval:** Is N=15 the right threshold? The observed fatigue window is 19-31 conversions (`tier1_session_log.md:112,130`). N=15 provides a safety margin but adds ~20s overhead per restart. Tune based on Phase 0 empirical data.

---

## 9. Summary

| What | Fix | When |
|------|-----|------|
| Error -9074 (17 files) | `open -a` investigation (0b) + PDF-first fallback | Phase 0 + Phase 1 |
| Sandbox dialog (confirmed, unlogged) | `pptx_output_dir` parameter in `normalize.to_pdf()` — write PDF to `deck_dir` for PowerPoint renderer only | Phase 0a |
| AppleScript fatigue (19-31 files) | Preemptive restart every N=15 conversions + retry-on-failure, dedicated session only; otherwise manual batch boundaries | Phase 0d |
| Cache invalidation | Explicitly deferred — PDF-first helps fallback decks only; automated PPTX reconversion remains unresolved until Approach J (v0.5.1 follow-on spec) | Phase 1 mitigation / v0.5.1 |
| Tier 1 scope clarification | Counting decision surface documented; manual PDF fallback is mitigation-only because Tier 1 requires automation | Phase 1 constraint |
| Failure instrumentation | Structured logging of observable outcomes + structured normalization outcome requirement for the eventual spec | Phase 0c |
| Fallback deck provenance | Canonical source policy: PDF is source, single-source model handles correctly | Phase 1 (policy, no code change) |
| PDF contract | Portrait/scanned warnings + Tier 1 counting exclusions; handout advisory only | Phase 1 |

**Total effort: 4-5 days (Approach J: ~1 day additional, separate spec).** The diagnostic spike (Phase 0) establishes the observable failure baseline, adds the PowerPoint-only output-path fix, and defines the structured normalization outcome required for a robust batch spec. Phase 1 provides a documented operator workaround for unconvertible files with quantitative acceptance criteria (≥80% evidence validation, frontmatter completeness, zero silent failures, 100% cache hit on rerun for the same PDF). These fallback outputs remain mitigation-only and do not satisfy Tier 1 because Tier 1 requires fully automated conversion. No cache key redesign is needed — Approach J (v0.5.1 follow-on spec) remains the separate fix for automated PPTX reconversion caching. For hybrid dual-input mode (preserving MarkItDown text quality while using stable PDFs for images), see Section 10.

---

## 10. Future Work: Hybrid Dual-Input Mode

**Status:** Out of scope for this proposal. Included as a sketch for future planning if the PDF-first text quality gap proves unacceptable after Phase 1 deployment.

### Motivation

If pdfplumber text extraction quality degrades evidence validation rates below the 93.4% baseline established with MarkItDown, a hybrid mode would preserve text quality while still using stable user-provided PDFs for images.

### Key Design Questions

1. **Canonical source:** PDF-canonical (images drive cache keys, PDF changes trigger full reconversion) vs PPTX-canonical (text is primary, PDF is supplementary image source). Recommendation: PDF-canonical, because cache identity depends on image stability.

2. **Source tracking extension:** The existing model is strictly single-source (`sources.py`, `versions.py`, `frontmatter.py` — all singular). Extending to dual-source requires:
   - New `_conversion_metadata` block in frontmatter (follows `_llm_metadata` underscore-prefix convention)
   - `compute_auxiliary_source_info()` or extended signature in `sources.py`
   - Version history annotation for PPTX changes

3. **Staleness model:** `check_staleness()` returns exactly three values: `"current"`, `"stale"`, `"missing"` (`sources.py:80`). A dual-source model needs a way to express "PDF current but PPTX changed" without breaking the existing contract. Options: new `check_auxiliary_staleness()` function, or optional second return field.

4. **CLI surface:** `--pptx-source` on convert, `--pptx-dir` on batch. Batch pairing: `foo.pdf` → `foo.pptx`.

5. **Drift detection:** If PPTX slide count ≠ PDF page count, warn but proceed. `reconcile_slide_count()` already handles count mismatches.

### Estimated Effort

5-7 days (converter routing, source tracking, frontmatter, staleness, batch pairing, 25-35 new tests).

### Open Questions for Hybrid Spec

1. Should PPTX-only changes skip image extraction (auto-detect via auxiliary staleness)?
2. If `--pptx-dir` specified but no PPTX match for a PDF, fail or silent fallback?
3. What text quality threshold justifies the hybrid complexity?
4. Should `_conversion_metadata` include a `text_quality_score` for automated comparison?
5. How should drift detection interact with `reconcile_slide_count()`?
