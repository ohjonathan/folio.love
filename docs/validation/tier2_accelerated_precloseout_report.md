---
id: tier2_accelerated_precloseout_report
type: atom
status: active
ontos_schema: 2.2
curation_level: 0
---

# Tier 2 Accelerated Pre-Closeout Validation Report

**Run date:** 2026-03-14
**Operator:** Johnny Oh (AI-assisted)
**Baseline branch:** main (commit fa37e3d)
**Source corpus:** Real engagement directory (54 pptx, 170 pdf)
**Library root:** ./library (fresh)

## 1. Executive Summary

| Item | Status | Notes |
|------|--------|-------|
| Command loop | PASS | convert, batch, status, scan, refresh, promote all functional |
| Obsidian / Dataview | PARTIAL | Frontmatter clean, slide images render, 405 inline content images broken (known Tier 1 limitation) |
| Routing / registry | PASS | Non-empty target_prefix works; empty prefix NOT COMPLETE (broken symlinks in validation corpus) |
| Promote | PASS | L0 → L1 with frontmatter and version_history update |
| LLM profiles / fallback | PASS | Route-based selection and --llm-profile override both verified; fallback N/A |
| Official 2-week criterion | NOT COMPLETE | By design — this is an accelerated 2-day run |
| Accelerated decision | **OPERATIONALLY READY; CONTINUE TIER 3 PLANNING, FULL TIER 2 CLOSEOUT STILL PENDING** | |

## 2. Tier 2 Checklist Snapshot

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | CLI handles full daily workflow | PASS | 3 converts, 1 batch (4/4), 2 status, 1 scan, 1 refresh trigger, 1 promote — all succeeded |
| 2 | Route-based LLM selection + override | PASS | Default routed to anthropic_sonnet; --llm-profile openai_gpt4o override confirmed in _llm_metadata |
| 3 | Multi-client library organized and navigable | PARTIAL | 9 decks, 1 client. 54 pptx available for future conversion. Below 100-deck / 5-client full target. |
| 4 | Obsidian opens library without errors | PARTIAL | 0 YAML parse errors, 133/133 slide images OK. 405 inline content images broken (known markitdown limitation, not a Tier 2 regression). Manual vault open required. |
| 5 | Dataview queries work for frontmatter fields | PASS | All required fields present: type, subtype, client, engagement, authority, curation_level, tags, frameworks (89%), slide_types — all at 100% except frameworks (1 file with none). |
| 6 | Multiple source roots | PARTIAL | Non-empty target_prefix PASS. Empty target_prefix NOT COMPLETE (validation corpus symlinks broken after archiving Tier 1 corpus). |
| 7 | Named LLM profiles + credential refs | PASS | 2 profiles (anthropic_sonnet, openai_gpt4o), credentials via env vars, no secrets in config. |
| 8 | 2+ weeks daily use | NOT COMPLETE | By design — accelerated run cannot satisfy this. |

## 3. Operational Findings

### What worked

- **Full command loop:** convert → batch → status → scan → refresh → promote all executed successfully on real engagement data.
- **Source root routing:** Engagement files correctly routed to `library/<Client>/<folder>/` with non-empty `target_prefix`. Deep nesting (4+ levels) handled correctly.
- **Registry operations:** Bootstrap from empty (0.35s), rebuild from scratch after deletion (0.35s, 7 entries recovered), status fast (<0.3s).
- **Scan performance:** 224 sources scanned in 0.39s, including walking through node_modules in a team working folder. NFR-100 easily satisfied.
- **Stale detection:** Hash-based (SHA256). Correctly detected modified source, correctly re-marked as current after restoration.
- **Promote:** L0 → L1 with proper validation, frontmatter update, and version_history event logging.
- **LLM profile routing:** `routing.convert.primary: anthropic_sonnet` used by default. `--llm-profile openai_gpt4o` override correctly bypassed routing. `_llm_metadata` in frontmatter records requested profile, actual profile, provider, and model.
- **Paths with spaces:** All paths with spaces (engagement directory, file names with spaces and special characters like brackets) handled correctly.

### What was awkward

- **Batch scope:** `folio batch` found 4 pptx in `08 Reference Material/` top level but not the 1 pptx in a subfolder. Unclear whether this is by design or a missing recursive walk.
- **PowerPoint timeout:** One convert timed out after 121s. This was a one-off after PowerPoint was in a bad state; not a systematic issue.
- **LLM JSON parse errors:** 3 slides across 2 decks returned non-valid JSON from the LLM (marked as "pending"). Not a blocker — the slides were still included — but affects analysis quality.
- **Inline content images:** 405 broken image links from markitdown text extraction. These are embedded pptx assets (logos, graphics) that markitdown references but never extracts. Known Tier 1 limitation, not a Tier 2 regression.

### What would block real daily use

No systematic blockers observed. The tool ran successfully on real engagement data across multiple folders, file types, and nesting depths.

## 4. Blockers

No product blockers identified.

### Minor issues (not blockers):

| Issue | Impact | Type |
|-------|--------|------|
| Validation corpus broken symlinks | Cannot test empty target_prefix routing | Process gap (archiving Tier 1 corpus broke symlinks) |
| Inline content images | Logos/graphics don't render in Obsidian | Known Tier 1 limitation — not a Tier 2 regression |
| Occasional LLM JSON parse failure | 3/133 slides had invalid JSON response | Minor quality issue, gracefully handled |

## 5. Recommendation

**OPERATIONALLY READY; CONTINUE TIER 3 PLANNING, FULL TIER 2 CLOSEOUT STILL PENDING**

Rationale:
- The full Tier 2 command loop works on real engagement data without manual repair or file surgery.
- Registry, routing, scan, refresh, and promote are operationally sound.
- LLM profile routing and override work as designed.
- No systematic blockers or data corruption observed.
- The official 2-week daily-driver criterion (checklist item 8) remains open by design.
- Multi-client library scale (checklist item 3) and empty target_prefix routing (checklist item 6) are PARTIAL and should be addressed during the ongoing Tier 2 window.

Tier 3 planning can safely begin in parallel while the full Tier 2 closeout validation period continues.

## Appendix A: Source-to-Output Path Mappings

| Source | Output |
|--------|--------|
| `00 Proposals/proposal_deck_vf.pptx` | `Client A/00 Proposals/proposal_deck_vf/` |
| `06 Client Meetings/04. Exec SteerCo/executive_steerco_v7.pptx` | `Client A/06 Client Meetings/04. Exec SteerCo/.../executive_steerco_v7/` |
| `07 Master Document/analyses_draft.pptx` | `Client A/07 Master Document/analyses_draft/` |
| `08 Reference Material/reference_compendium.pptx` | `Client A/08 Reference Material/reference_compendium/` |
| `08 Reference Material/reference_case_study_alt.pptx` | `Client A/08 Reference Material/reference_case_study_alt/` |
| `08 Reference Material/reference_case_study_main.pptx` | `Client A/08 Reference Material/reference_case_study_main/` |
| `08 Reference Material/service_levels_matrix.pptx` | `Client A/08 Reference Material/service_levels_matrix/` |
| `09 Meeting Notes/meeting_notes_deck.pptx` | `Client A/09 Meeting Notes/.../meeting_notes_deck/` |
| `02 Background Documents/client_template.pptx` (--target override) | `manual_override_test/` |

## Appendix B: Performance Measurements

| Operation | Time | Detail |
|-----------|------|--------|
| `folio status` (7 decks) | 0.3s | Registry load + display |
| `folio scan` (224 sources, incl. node_modules walk) | 0.39s | 2 source roots |
| `folio status --refresh` (7 decks, hash recheck) | 0.25-0.35s | SHA256 of all sources |
| Registry bootstrap from scratch | 0.35s | 7 entries rebuilt |
| Single convert (35 slides, Anthropic) | ~290s | Includes PowerPoint rendering + LLM analysis |
| Single convert (1 slide, OpenAI) | ~17s | Includes PowerPoint rendering + LLM analysis |
| Batch (4 files, 61 slides total) | ~512s | Anthropic, sequential |
