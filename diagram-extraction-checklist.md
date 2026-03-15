# Diagram Extraction Implementation Checklist

**Started:** 2026-03-14
**Proposal:** Final — approved for implementation

---

## PR Sequence

- [x] **PR 1:** Page Inspection + Blank Fix + Coordinates + Set-of-Mark Validation (2-2.5 days) — **PR #19**
  - [x] CA prompt generated (orchestrator)
  - [x] CA implementation prompt generated (Claude Code)
  - [x] Developer implements — PR #19 created
  - [x] Review Team prompt generated (orchestrator)
  - [x] Review Team executes (Claude Code agent team)
  - [x] CA cross-check (Codex)
  - [x] Fixes if needed
  - [x] Decision output: Set-of-Mark viability verdict — **BLOCKING PR 2**
  - [x] Tests pass, no regressions on PR #19 final branch (`615 passed, 3 skipped`; current suite now collects 621 tests)
  - [x] Merged
  - Outcome: **SoM NOT VIABLE** -> PR 2 uses **tiles** (`global + quadrant crops`)
- [ ] **PR 2:** Provider Abstraction + DPI + Rate Limiting + Tiles Image Strategy (2.5-3 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged
- [ ] **PR 3:** Schema + Routing + Cache + Deserialization Factory (2-2.5 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged
- [ ] **PR 4:** Extraction Prompts + Pass A/B/C + Completeness Sweep + Confidence (5-7 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements (may split by day 3)
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged
- [ ] **PR 5:** Deterministic Rendering + Mermaid + Entity Resolution (2-2.5 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged
- [ ] **PR 6:** Output Assembly + Standalone Notes + Freeze + Review History (3-3.5 days)
  - [ ] CA prompt generated
  - [ ] CA implementation prompt generated
  - [ ] Developer implements
  - [ ] Review Team executes
  - [ ] CA cross-check + fixes
  - [ ] Tests pass, no regressions
  - [ ] Merged
- [ ] **Model Comparison Testing** (7-9 days, after PR 5)

---

## Manual Action Items

- [ ] **Week 1:** Test Obsidian transclusion with Mermaid blocks (15 min manual test)
  - Result: ___  (works / fallback to inline Mermaid)
- [x] **PR 1:** Provide 5-10 real corpus PDFs for Set-of-Mark validation
  - Location: `/Users/Jonathan_Oh/tmp/diagram_som_corpus`
  - Validation set: 8 PDFs, 25 diagram/mixed pages
- [ ] **PR 4:** Real corpus diagrams available for prompt iteration
- [ ] **Model Comparison:** 20-30 diagram pages from engagement materials
- [ ] **Model Comparison:** Two annotators for 5-page inter-annotator agreement

---

## Decision Log

| PR | Decision | Verdict | Date |
|----|----------|---------|------|
| PR 1 | Set-of-Mark viability (pypdfium2 bounding boxes) | **Not viable** — overall `0.76`, medium/dense `0.722`, systematic dense-page failures | 2026-03-14 |
| PR 1 | Obsidian transclusion with Mermaid | Pending manual test | ___ |
| PR 2 | Image strategy (SoM primary vs tiles fallback) | **Tiles** (`global + quadrant crops`) | 2026-03-14 |
| PR 4 | Split PR 4 by day 3? | ___ | ___ |

---

## Risks Realized

| Risk | PR | What Happened | Resolution |
|------|----|---------------|------------|
| pypdfium2 bounding boxes unreliable on dense pages | PR 1 | Real-corpus SoM validation failed the acceptance bar on dense material, driven by a systematic failure cluster in `dense_06_target_state_arch.pdf` | Lock PR 2 to tiles instead of Set-of-Mark |
| Raster-only blank detection needed separate handling | PR 1 | Review surfaced that structural blank detection alone would miss raster-only blank pages | Added `image_blank` + histogram confirmation path |
| Soft pdfium text failure could misclassify pages | PR 1 | Review surfaced cases where pdfium word extraction could return empty while pdfplumber still found text | Added pdfium -> pdfplumber fallback for counts/classification |

---

## Regressions / Issues

| Issue | PR | Status |
|-------|----|--------|
| `som_viable` is lexical-only, not spatial overlay validated | PR 1 | Known limitation; carry into PR 2 checklist and validation |
| `inspect_pages()` needed degraded per-page fallback instead of failing whole documents | PR 1 | Resolved in review fixes |
| `text_light` / `image_blank` classifications were added during review, so downstream prompts must use the merged runtime enums, not the original PR 1 draft | PR 1 | Resolved; treat merged code as source of truth |
