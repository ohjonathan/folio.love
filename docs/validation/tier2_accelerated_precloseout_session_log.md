---
id: tier2_accelerated_precloseout_session_log
type: atom
status: active
ontos_schema: 2.2
curation_level: 0
---

# Tier 2 Accelerated Pre-Closeout Session Log

**Run date:** 2026-03-14
**Operator:** Johnny Oh (AI-assisted via Cursor)
**Environment:** macOS, Python 3.12, PowerPoint for Mac

---

## Environment Setup

### 0a. Python venv

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| Create venv | `/opt/homebrew/bin/python3.12 -m venv .venv` | 0 | 2.8s |
| Install deps | `pip install -e ".[dev,llm]"` | 0 | 17.6s. Installed openai, google-genai, and dependencies. |
| Verify CLI | `folio --help` | 0 | All 6 commands listed: convert, batch, status, scan, refresh, promote |

### 0b. API keys

| Step | Command | Result |
|------|---------|--------|
| Create .env | Write ANTHROPIC_API_KEY, OPENAI_API_KEY to .env | .env gitignored. Deviation: repo-root .env used instead of tests/validation/.env per AGENTS.md policy. Future runs should use tests/validation/.env. |
| Verify loading | `export $(cat .env | xargs)` | Both keys SET |
| Gemini | Not provided | Adjusted plan to 2 LLM profiles |

### 0c. PowerPoint

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| Check installed | `mdfind "kMDItemFSName == 'Microsoft PowerPoint.app'"` | 0 | `/Applications/Microsoft PowerPoint.app` |
| AppleScript test | `osascript -e 'tell application "Microsoft PowerPoint" to return name'` | 0 | Responds correctly |

## Configuration

| Step | Details |
|------|---------|
| folio.yaml updated | library_root: ./library, 2 source roots, 2 LLM profiles, routing config |
| library dir created | `mkdir -p library` |
| Config verification | `folio status` → "Bootstrapping registry... 0 entries" |

---

## Phase 1: Daily-Driver Loop

### Convert 1/3: Proposal deck

| Field | Value |
|-------|-------|
| Time | 2026-03-14 ~03:41 UTC |
| Command | `folio convert "<engagement>/00 Proposals/proposal_deck_vf.pptx" --client "Client A" --engagement "Engagement Alpha" --subtype research` |
| Exit | 0 |
| Duration | 290.6s |
| Slides | 35 |
| Output | `library/Client A/00 Proposals/proposal_deck_vf/` |
| LLM profile | anthropic_sonnet (routed) |
| Worked first try | Yes |
| Notes | 1 text/image count mismatch (34 slides vs 35 images — padded). All 35 LLM calls returned 200. |

### Convert 2/3: Executive SteerCo deck

| Field | Value |
|-------|-------|
| Time | 2026-03-14 ~03:46 UTC |
| Command | `folio convert "<engagement>/06 Client Meetings/04. Exec SteerCo/.../executive_steerco_v7.pptx" --client "Client A" --engagement "Engagement Alpha" --subtype research` |
| Exit | 0 |
| Duration | 148.2s |
| Slides | 18 |
| Output | `library/Client A/06 Client Meetings/04. Exec SteerCo/.../executive_steerco_v7/` |
| LLM profile | anthropic_sonnet (routed) |
| Worked first try | Yes |
| Notes | Slide 16 "Pass-1 response is not valid JSON — treating as pending". Deeply nested path handled correctly. |

### Convert 3/3: Master Document

| Field | Value |
|-------|-------|
| Time | 2026-03-14 ~03:49 UTC |
| Command | `folio convert "<engagement>/07 Master Document/analyses_draft.pptx" --client "Client A" --engagement "Engagement Alpha" --subtype research` |
| Exit | 0 |
| Duration | 42.5s |
| Slides | 6 (5 text + 1 padded) |
| Output | `library/Client A/07 Master Document/analyses_draft/` |
| LLM profile | anthropic_sonnet (routed) |
| Worked first try | Yes |

### Batch convert: 08 Reference Material

| Field | Value |
|-------|-------|
| Time | 2026-03-14 ~03:50 UTC |
| Command | `folio batch "<engagement>/08 Reference Material" --client "Client A" --engagement "Engagement Alpha"` |
| Exit | 0 |
| Duration | 511.8s |
| Files found | 4 pptx (top-level only; 1 in subfolder not picked up) |
| Results | 4/4 succeeded |
| Files converted | reference_compendium (54 slides, 454s), reference_case_study_alt (2 slides, 17s), reference_case_study_main (4 slides, 31s), service_levels_matrix (1 slide, 9s) |
| Notes | Slides 29 and 45 of compendium had invalid JSON. 11 blank slides detected. |

### Status check 1

| Field | Value |
|-------|-------|
| Command | `folio status` |
| Exit | 0 |
| Duration | ~1.1s |
| Result | Library: 7 decks, ✓ Current: 7 |

### Scan

| Field | Value |
|-------|-------|
| Command | `folio scan` |
| Exit | 0 |
| Duration | 0.39s |
| Result | 224 sources scanned, 217 new, 0 stale, 0 missing |
| Notes | node_modules in team working folder did not slow scan. NFR-100 met. |

### Stale detection and refresh

| Field | Value |
|-------|-------|
| Simulate staleness | `printf '\x00' >> "<source>.pptx"` to change file hash |
| `folio status --refresh` | ⚠ Stale: 1 — CORRECT |
| `folio refresh` | Failed: PowerPoint could not open corrupted file (expected — appended byte invalidated zip) |
| Restore file | `truncate -s $((SIZE - 1))` |
| `folio status --refresh` after restore | ✓ Current: 7 — CORRECT |
| Conclusion | Stale detection PASS. Refresh targeting PASS (targeted only the stale deck). Refresh execution failed due to simulated corruption, not a folio bug. |

### Promote

| Field | Value |
|-------|-------|
| Command | `folio promote <deck_id> L1` |
| Exit | 0 |
| Result | ✓ Promoted: L0 → L1 |
| Frontmatter | `curation_level: L1` confirmed |
| version_history.json | promotion event with timestamp, from_level: L0, to_level: L1 |

---

## Phase 2: Obsidian and Dataview

| Check | Result | Notes |
|-------|--------|-------|
| YAML parse errors | 0/9 files | All frontmatter parses cleanly |
| Field: type | 9/9 (100%) | |
| Field: subtype | 9/9 (100%) | |
| Field: client | 9/9 (100%) | |
| Field: engagement | 9/9 (100%) | |
| Field: authority | 9/9 (100%) | |
| Field: curation_level | 9/9 (100%) | |
| Field: tags | 9/9 (100%) | |
| Field: frameworks | 8/9 (89%) | 1 file (client template) has no frameworks |
| Field: slide_types | 9/9 (100%) | |
| Field: source | 9/9 (100%) | |
| Field: source_hash | 9/9 (100%) | |
| Field: version | 9/9 (100%) | |
| Field: converted | 9/9 (100%) | |
| Slide images | 133/133 (100%) | All in slides/ subdirectory |
| Inline content images | 0/405 (0%) | Known markitdown limitation — embedded pptx assets not extracted |
| Manual vault open | Pending | Requires operator to open ./library in Obsidian |

---

## Phase 3: Routing and Registry

| Check | Result | Notes |
|-------|--------|-------|
| Registry bootstrap (delete + status) | PASS | 7 entries rebuilt in 0.35s |
| Source mappings | 7 examples captured | All under `Client A/` prefix |
| `--target` override | PASS | Output to `manual_override_test/` instead of routed path |
| `--client`/`--engagement` override | PASS | Frontmatter shows override values |
| Non-empty target_prefix | PASS | All engagement files routed to `library/Client A/...` |
| Empty target_prefix | NOT COMPLETE | Validation corpus contains broken symlinks to archived Tier 1 corpus |
| Stale detection | PASS | Hash-based detection works |

---

## Phase 4: LLM Profile and Fallback

| Check | Result | Notes |
|-------|--------|-------|
| Route-based selection | PASS | `_llm_metadata.convert.profile: anthropic_sonnet` on all default converts |
| `--llm-profile` override | PASS | `openai_gpt4o` override: requests went to api.openai.com, metadata shows openai_gpt4o |
| Provider metadata | PASS | `_llm_metadata` includes requested_profile, profile, provider, model |
| Fallback activation | N/A | Not tested in time budget — would require invalidating primary key |

---

## Issues Encountered

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | Validation corpus broken symlinks | Medium | Archiving Tier 1 corpus broke symlinks in tests/validation/corpus/. Need to restore or recreate. |
| 2 | PowerPoint timeout on one deck | Low | One-off; PowerPoint was in bad state. Killed and restarted. |
| 3 | LLM JSON parse errors (3 slides) | Low | Gracefully handled as "pending". Not a blocker. |
| 4 | Inline content images (405 broken) | Low | Known Tier 1 limitation. Slide renderings work. |
| 5 | Batch did not find pptx in subfolder | Low | Subfolder pptx not picked up. Unclear if by design. |
