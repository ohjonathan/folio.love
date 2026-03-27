---
id: tier2_real_library_rerun_session_log
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_real_library_rerun
created: 2026-03-27
---

# Session Log — Tier 2 Real Library Rerun

## Preflight — 2026-03-27

### Environment

- **Machine:** Managed macOS laptop (Apple Silicon)
- **Branch:** main
- **Python:** 3.12.13
- **folio-love:** 0.2.0
- **Disk:** 291 GB available (34% used)

### Library Target

- **Production library:** `<PRODUCTION_LIBRARY>` (115 decks, NOT modified by this run)
- **Scratch validation library:** `<SCRATCH_LIBRARY>` (new, empty)
- **Config:** `<RERUN_CONFIG>` → `library_root: ../<SCRATCH_LIBRARY>`

### Model Decision

- **Profile:** `anthropic_haiku45` (claude-haiku-4-5-20251001)
- **Routing bypassed:** explicit `--llm-profile anthropic_haiku45` on every command
- **Flags:** `--passes 2 --no-cache`

### Source Inventory

- **Total files:** 161 (149 PDFs + 12 PPTXs)
- **Total directories:** 93
- **Total batch invocations:** 94 (83 PDF + 11 PPTX)
- **Source root:** `<SOURCE_ROOT>`

### Credential Status

- `ANTHROPIC_API_KEY`: NOT SET — must be exported before execution
- `ANTHROPIC_BASE_URL`: NOT SET — must be exported before execution
- Gateway: managed provider gateway

**RESOLVED:** `ANTHROPIC_API_KEY` loaded from `~/folio.love/.env` (length: 108).
No gateway base URL configured — using default Anthropic API endpoint directly.

### Preflight Test Conversion

- **File:** `DIR_019/DOC_PREVIEW_001.pdf`
- **Profile:** `anthropic_haiku45`
- **Result:** SUCCESS (exit=0, ~86s)
- **Output:** `<SCRATCH_LIBRARY>/DIR_019/doc_preview_001/`
- **Registry:** Created in scratch library (`<SCRATCH_LIBRARY>/registry.json`)
- **Pass 2:** Skipped (no slides above density threshold — expected for single-page PDF)
- **Conclusion:** Pipeline operational, scratch library routing confirmed.

### PPTX Decision

12 PPTX files in scope across 11 directories. Most are org charts (likely
abstention targets). PowerPoint automation via `--dedicated-session` requires
Terminal.app TCC permissions. Runner script will attempt from Cursor first with
`--no-dedicated-session` as fallback.

[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] # Execution Run: pdf
[2026-03-27 01:54:37] Started: 2026-03-27T01:54:37.633576
[2026-03-27 01:54:37] Phase: pdf
[2026-03-27 01:54:37] Profile: anthropic_haiku45
[2026-03-27 01:54:37] Dry run: True
[2026-03-27 01:54:37] PDF directories: 83
[2026-03-27 01:54:37] PPTX directories: 11
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] ============================================================
[2026-03-27 01:54:37] PHASE A: PDF BATCH CONVERSIONS
[2026-03-27 01:54:37] ============================================================
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [1/83] DIR_ROOT (root, 1 PDF)
[2026-03-27 01:54:37]   CMD: folio batch "<SOURCE_ROOT>" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [2/83] DIR_001 (5 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_001" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [3/83] DIR_002 (3 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_002" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [4/83] DIR_003 (1 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_003" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [5/83] DIR_004 (2 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_004" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [6/83] DIR_005 (1 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_005" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [7/83] DIR_006 (2 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_006" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [8/83] DIR_007 (3 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_007" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [9/83] DIR_008 (1 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_008" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [10/83] DIR_009 (12 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_009" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [11/83] DIR_010 (1 PDFs)
[2026-03-27 01:54:37]   CMD: folio batch "DIR_010" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 01:54:37]   DRY-RUN: skipped
[2026-03-27 01:54:37] 
[2026-03-27 01:54:37] [12/83] DIR_011 (1 PDFs)
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] # Execution Run: pptx
[2026-03-27 01:54:44] Started: 2026-03-27T01:54:44.371229
[2026-03-27 01:54:44] Phase: pptx
[2026-03-27 01:54:44] Profile: anthropic_haiku45
[2026-03-27 01:54:44] Dry run: True
[2026-03-27 01:54:44] PDF directories: 83
[2026-03-27 01:54:44] PPTX directories: 11
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] ============================================================
[2026-03-27 01:54:44] PHASE B: PPTX BATCH CONVERSIONS
[2026-03-27 01:54:44] ============================================================
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [1/11] DIR_083 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_083" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [2/11] DIR_005 (2 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_005" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [3/11] DIR_084 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_084" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [4/11] DIR_085 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_085" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [5/11] DIR_086 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_086" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [6/11] DIR_087 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_087" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [7/11] DIR_088 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_088" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [8/11] DIR_089 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_089" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [9/11] DIR_090 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_090" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [10/11] DIR_091 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_091" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] [11/11] DIR_092 (1 PPTXs)
[2026-03-27 01:54:44]   CMD: folio batch "DIR_092" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 01:54:44]   DRY-RUN: skipped
[2026-03-27 01:54:44] 
[2026-03-27 01:54:44] ============================================================
[2026-03-27 01:54:44] SUMMARY: 0 success, 0 error, 0 timeout, 0 exception, 0.0h total
[2026-03-27 01:54:44] Finished: 2026-03-27T01:54:44.371608
[2026-03-27 01:54:44] ============================================================
[2026-03-27 01:57:58] 
[2026-03-27 01:57:58] # Execution Run: pdf
[2026-03-27 01:57:58] Started: 2026-03-27T01:57:58.638100
[2026-03-27 01:57:58] Phase: pdf
[2026-03-27 01:57:58] Profile: anthropic_haiku45
[2026-03-27 01:57:58] Dry run: False
[2026-03-27 01:57:58] PDF directories: 83
[2026-03-27 01:57:58] PPTX directories: 11
[2026-03-27 01:57:58] 
[2026-03-27 01:57:58] ============================================================
[2026-03-27 01:57:58] PHASE A: PDF BATCH CONVERSIONS
[2026-03-27 01:57:58] ============================================================
[2026-03-27 01:57:58] 
[2026-03-27 01:57:58] [1/83] DIR_ROOT (root, 1 PDF)
[2026-03-27 01:57:58]   CMD: folio batch "<SOURCE_ROOT>" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 02:10:15]   SUCCESS: exit=0 elapsed=736.5s
[2026-03-27 02:10:15] 
[2026-03-27 02:10:15] [2/83] DIR_001 (5 PDFs)
[2026-03-27 02:10:15]   CMD: folio batch "DIR_001" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 02:40:15]   TIMEOUT after 1800.0s
[2026-03-27 02:40:15] 
[2026-03-27 02:40:15] [3/83] DIR_002 (3 PDFs)
[2026-03-27 02:40:15]   CMD: folio batch "DIR_002" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:00:50]   SUCCESS: exit=0 elapsed=1235.1s
[2026-03-27 03:00:50] 
[2026-03-27 03:00:50] [4/83] DIR_003 (1 PDFs)
[2026-03-27 03:00:50]   CMD: folio batch "DIR_003" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:15:02]   SUCCESS: exit=0 elapsed=851.9s
[2026-03-27 03:15:02] 
[2026-03-27 03:15:02] [5/83] DIR_004 (2 PDFs)
[2026-03-27 03:15:02]   CMD: folio batch "DIR_004" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:18:13]   SUCCESS: exit=0 elapsed=191.3s
[2026-03-27 03:18:13] 
[2026-03-27 03:18:13] [6/83] DIR_005 (1 PDFs)
[2026-03-27 03:18:13]   CMD: folio batch "DIR_005" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:37:31]   SUCCESS: exit=0 elapsed=1158.3s
[2026-03-27 03:37:31] 
[2026-03-27 03:37:31] [7/83] DIR_006 (2 PDFs)
[2026-03-27 03:37:31]   CMD: folio batch "DIR_006" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:44:43]   SUCCESS: exit=0 elapsed=432.1s
[2026-03-27 03:44:43] 
[2026-03-27 03:44:43] [8/83] DIR_007 (3 PDFs)
[2026-03-27 03:44:43]   CMD: folio batch "DIR_007" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 03:46:04]   SUCCESS: exit=0 elapsed=80.4s
[2026-03-27 03:46:04] 
[2026-03-27 03:46:04] [9/83] DIR_008 (1 PDFs)
[2026-03-27 03:46:04]   CMD: folio batch "DIR_008" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:05:04]   SUCCESS: exit=0 elapsed=1140.1s
[2026-03-27 04:05:04] 
[2026-03-27 04:05:04] [10/83] DIR_009 (12 PDFs)
[2026-03-27 04:05:04]   CMD: folio batch "DIR_009" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:13:43]   SUCCESS: exit=0 elapsed=519.6s
[2026-03-27 04:13:43] 
[2026-03-27 04:13:43] [11/83] DIR_010 (1 PDFs)
[2026-03-27 04:13:43]   CMD: folio batch "DIR_010" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:14:12]   SUCCESS: exit=0 elapsed=28.4s
[2026-03-27 04:14:12] 
[2026-03-27 04:14:12] [12/83] DIR_011 (1 PDFs)
[2026-03-27 04:14:12]   CMD: folio batch "DIR_011" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:16:27]   SUCCESS: exit=0 elapsed=135.5s
[2026-03-27 04:16:27] 
[2026-03-27 04:16:27] [13/83] DIR_012 (2 PDFs)
[2026-03-27 04:16:27]   CMD: folio batch "DIR_012" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:36:35]   SUCCESS: exit=0 elapsed=1207.8s
[2026-03-27 04:36:35] 
[2026-03-27 04:36:35] [14/83] DIR_013 (1 PDFs)
[2026-03-27 04:36:35]   CMD: folio batch "DIR_013" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:44:21]   SUCCESS: exit=0 elapsed=465.6s
[2026-03-27 04:44:21] 
[2026-03-27 04:44:21] [15/83] DIR_014 (1 PDFs)
[2026-03-27 04:44:21]   CMD: folio batch "DIR_014" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:45:03]   SUCCESS: exit=0 elapsed=42.1s
[2026-03-27 04:45:03] 
[2026-03-27 04:45:03] [16/83] DIR_015 (1 PDFs)
[2026-03-27 04:45:03]   CMD: folio batch "DIR_015" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:45:37]   SUCCESS: exit=0 elapsed=34.0s
[2026-03-27 04:45:37] 
[2026-03-27 04:45:37] [17/83] DIR_016 (1 PDFs)
[2026-03-27 04:45:37]   CMD: folio batch "DIR_016" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:46:00]   SUCCESS: exit=0 elapsed=22.8s
[2026-03-27 04:46:00] 
[2026-03-27 04:46:00] [18/83] DIR_017 (1 PDFs)
[2026-03-27 04:46:00]   CMD: folio batch "DIR_017" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:51:39]   SUCCESS: exit=0 elapsed=339.2s
[2026-03-27 04:51:39] 
[2026-03-27 04:51:39] [19/83] DIR_018 (1 PDFs)
[2026-03-27 04:51:39]   CMD: folio batch "DIR_018" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 04:53:21]   SUCCESS: exit=0 elapsed=101.8s
[2026-03-27 04:53:21] 
[2026-03-27 04:53:21] [20/83] DIR_019 (1 PDFs)
[2026-03-27 04:53:21]   CMD: folio batch "DIR_019" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:10:06]   SUCCESS: exit=0 elapsed=1004.9s
[2026-03-27 05:10:06] 
[2026-03-27 05:10:06] [21/83] DIR_020 (1 PDFs)
[2026-03-27 05:10:06]   CMD: folio batch "DIR_020" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:10:26]   SUCCESS: exit=0 elapsed=19.9s
[2026-03-27 05:10:26] 
[2026-03-27 05:10:26] [22/83] DIR_021 (1 PDFs)
[2026-03-27 05:10:26]   CMD: folio batch "DIR_021" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:11:09]   SUCCESS: exit=0 elapsed=43.4s
[2026-03-27 05:11:09] 
[2026-03-27 05:11:09] [23/83] DIR_022 (1 PDFs)
[2026-03-27 05:11:09]   CMD: folio batch "DIR_022" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:11:57]   SUCCESS: exit=0 elapsed=47.6s
[2026-03-27 05:11:57] 
[2026-03-27 05:11:57] [24/83] DIR_023 (1 PDFs)
[2026-03-27 05:11:57]   CMD: folio batch "DIR_023" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:12:47]   SUCCESS: exit=0 elapsed=50.4s
[2026-03-27 05:12:47] 
[2026-03-27 05:12:47] [25/83] DIR_024 (2 PDFs)
[2026-03-27 05:12:47]   CMD: folio batch "DIR_024" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:16:03]   SUCCESS: exit=0 elapsed=195.9s
[2026-03-27 05:16:03] 
[2026-03-27 05:16:03] [26/83] DIR_025 (1 PDFs)
[2026-03-27 05:16:03]   CMD: folio batch "DIR_025" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:17:20]   SUCCESS: exit=0 elapsed=77.1s
[2026-03-27 05:17:20] 
[2026-03-27 05:17:20] [27/83] DIR_026 (6 PDFs)
[2026-03-27 05:17:20]   CMD: folio batch "DIR_026" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:25:45]   SUCCESS: exit=0 elapsed=504.9s
[2026-03-27 05:25:45] 
[2026-03-27 05:25:45] [28/83] DIR_027 (1 PDFs)
[2026-03-27 05:25:45]   CMD: folio batch "DIR_027" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:44:36]   SUCCESS: exit=0 elapsed=1131.3s
[2026-03-27 05:44:36] 
[2026-03-27 05:44:36] [29/83] DIR_028 (6 PDFs)
[2026-03-27 05:44:36]   CMD: folio batch "DIR_028" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:51:16]   SUCCESS: exit=0 elapsed=400.2s
[2026-03-27 05:51:16] 
[2026-03-27 05:51:16] [30/83] DIR_029 (1 PDFs)
[2026-03-27 05:51:16]   CMD: folio batch "DIR_029" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:52:11]   SUCCESS: exit=0 elapsed=54.3s
[2026-03-27 05:52:11] 
[2026-03-27 05:52:11] [31/83] DIR_030 (1 PDFs)
[2026-03-27 05:52:11]   CMD: folio batch "DIR_030" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 05:59:57]   SUCCESS: exit=0 elapsed=466.6s
[2026-03-27 05:59:57] 
[2026-03-27 05:59:57] [32/83] DIR_031 (2 PDFs)
[2026-03-27 05:59:57]   CMD: folio batch "DIR_031" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:20:47]   SUCCESS: exit=0 elapsed=1249.9s
[2026-03-27 06:20:47] 
[2026-03-27 06:20:47] [33/83] DIR_032 (1 PDFs)
[2026-03-27 06:20:47]   CMD: folio batch "DIR_032" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:28:39]   SUCCESS: exit=0 elapsed=471.7s
[2026-03-27 06:28:39] 
[2026-03-27 06:28:39] [34/83] DIR_033 (1 PDFs)
[2026-03-27 06:28:39]   CMD: folio batch "DIR_033" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:29:24]   SUCCESS: exit=0 elapsed=45.3s
[2026-03-27 06:29:24] 
[2026-03-27 06:29:24] [35/83] DIR_034 (1 PDFs)
[2026-03-27 06:29:24]   CMD: folio batch "DIR_034" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:29:59]   SUCCESS: exit=0 elapsed=35.3s
[2026-03-27 06:29:59] 
[2026-03-27 06:29:59] [36/83] DIR_035 (11 PDFs)
[2026-03-27 06:29:59]   CMD: folio batch "DIR_035" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:38:45]   SUCCESS: exit=0 elapsed=525.5s
[2026-03-27 06:38:45] 
[2026-03-27 06:38:45] [37/83] DIR_036 (1 PDFs)
[2026-03-27 06:38:45]   CMD: folio batch "DIR_036" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 06:57:49]   SUCCESS: exit=0 elapsed=1144.3s
[2026-03-27 06:57:49] 
[2026-03-27 06:57:49] [38/83] DIR_037 (1 PDFs)
[2026-03-27 06:57:49]   CMD: folio batch "DIR_037" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:17:28]   SUCCESS: exit=0 elapsed=1178.9s
[2026-03-27 07:17:28] 
[2026-03-27 07:17:28] [39/83] DIR_038 (1 PDFs)
[2026-03-27 07:17:28]   CMD: folio batch "DIR_038" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:18:02]   SUCCESS: exit=0 elapsed=33.6s
[2026-03-27 07:18:02] 
[2026-03-27 07:18:02] [40/83] DIR_039 (1 PDFs)
[2026-03-27 07:18:02]   CMD: folio batch "DIR_039" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:18:26]   SUCCESS: exit=0 elapsed=24.7s
[2026-03-27 07:18:26] 
[2026-03-27 07:18:26] [41/83] DIR_040 (1 PDFs)
[2026-03-27 07:18:26]   CMD: folio batch "DIR_040" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:24:25]   SUCCESS: exit=0 elapsed=358.2s
[2026-03-27 07:24:25] 
[2026-03-27 07:24:25] [42/83] DIR_041 (1 PDFs)
[2026-03-27 07:24:25]   CMD: folio batch "DIR_041" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:25:53]   SUCCESS: exit=0 elapsed=88.0s
[2026-03-27 07:25:53] 
[2026-03-27 07:25:53] [43/83] DIR_042 (1 PDFs)
[2026-03-27 07:25:53]   CMD: folio batch "DIR_042" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:26:11]   SUCCESS: exit=0 elapsed=18.2s
[2026-03-27 07:26:11] 
[2026-03-27 07:26:11] [44/83] DIR_043 (1 PDFs)
[2026-03-27 07:26:11]   CMD: folio batch "DIR_043" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:26:55]   SUCCESS: exit=0 elapsed=43.7s
[2026-03-27 07:26:55] 
[2026-03-27 07:26:55] [45/83] DIR_044 (1 PDFs)
[2026-03-27 07:26:55]   CMD: folio batch "DIR_044" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:27:03]   SUCCESS: exit=0 elapsed=8.6s
[2026-03-27 07:27:03] 
[2026-03-27 07:27:03] [46/83] DIR_045 (1 PDFs)
[2026-03-27 07:27:03]   CMD: folio batch "DIR_045" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:27:54]   SUCCESS: exit=0 elapsed=51.2s
[2026-03-27 07:27:54] 
[2026-03-27 07:27:54] [47/83] DIR_046 (2 PDFs)
[2026-03-27 07:27:54]   CMD: folio batch "DIR_046" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:31:20]   SUCCESS: exit=0 elapsed=205.5s
[2026-03-27 07:31:20] 
[2026-03-27 07:31:20] [48/83] DIR_047 (1 PDFs)
[2026-03-27 07:31:20]   CMD: folio batch "DIR_047" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:34:52]   SUCCESS: exit=0 elapsed=211.9s
[2026-03-27 07:34:52] 
[2026-03-27 07:34:52] [49/83] DIR_048 (1 PDFs)
[2026-03-27 07:34:52]   CMD: folio batch "DIR_048" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:35:18]   SUCCESS: exit=0 elapsed=26.3s
[2026-03-27 07:35:18] 
[2026-03-27 07:35:18] [50/83] DIR_049 (1 PDFs)
[2026-03-27 07:35:18]   CMD: folio batch "DIR_049" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:40:27]   SUCCESS: exit=0 elapsed=309.0s
[2026-03-27 07:40:27] 
[2026-03-27 07:40:27] [51/83] DIR_050 (1 PDFs)
[2026-03-27 07:40:27]   CMD: folio batch "DIR_050" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:45:12]   SUCCESS: exit=0 elapsed=284.5s
[2026-03-27 07:45:12] 
[2026-03-27 07:45:12] [52/83] DIR_051 (1 PDFs)
[2026-03-27 07:45:12]   CMD: folio batch "DIR_051" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:56:09]   SUCCESS: exit=0 elapsed=657.4s
[2026-03-27 07:56:09] 
[2026-03-27 07:56:09] [53/83] DIR_052 (1 PDFs)
[2026-03-27 07:56:09]   CMD: folio batch "DIR_052" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 07:56:24]   SUCCESS: exit=0 elapsed=15.3s
[2026-03-27 07:56:24] 
[2026-03-27 07:56:24] [54/83] DIR_053 (2 PDFs)
[2026-03-27 07:56:24]   CMD: folio batch "DIR_053" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:02:36]   SUCCESS: exit=0 elapsed=371.3s
[2026-03-27 08:02:36] 
[2026-03-27 08:02:36] [55/83] DIR_054 (1 PDFs)
[2026-03-27 08:02:36]   CMD: folio batch "DIR_054" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:03:18]   SUCCESS: exit=0 elapsed=42.0s
[2026-03-27 08:03:18] 
[2026-03-27 08:03:18] [56/83] DIR_055 (1 PDFs)
[2026-03-27 08:03:18]   CMD: folio batch "DIR_055" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:03:46]   SUCCESS: exit=0 elapsed=28.6s
[2026-03-27 08:03:46] 
[2026-03-27 08:03:46] [57/83] DIR_056 (1 PDFs)
[2026-03-27 08:03:46]   CMD: folio batch "DIR_056" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:04:15]   SUCCESS: exit=0 elapsed=28.9s
[2026-03-27 08:04:15] 
[2026-03-27 08:04:15] [58/83] DIR_057 (2 PDFs)
[2026-03-27 08:04:15]   CMD: folio batch "DIR_057" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:06:58]   SUCCESS: exit=0 elapsed=163.2s
[2026-03-27 08:06:58] 
[2026-03-27 08:06:58] [59/83] DIR_058 (1 PDFs)
[2026-03-27 08:06:58]   CMD: folio batch "DIR_058" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:11:42]   SUCCESS: exit=0 elapsed=284.0s
[2026-03-27 08:11:42] 
[2026-03-27 08:11:42] [60/83] DIR_059 (1 PDFs)
[2026-03-27 08:11:42]   CMD: folio batch "DIR_059" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:12:57]   SUCCESS: exit=0 elapsed=74.2s
[2026-03-27 08:12:57] 
[2026-03-27 08:12:57] [61/83] DIR_060 (1 PDFs)
[2026-03-27 08:12:57]   CMD: folio batch "DIR_060" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:13:55]   SUCCESS: exit=0 elapsed=58.2s
[2026-03-27 08:13:55] 
[2026-03-27 08:13:55] [62/83] DIR_061 (1 PDFs)
[2026-03-27 08:13:55]   CMD: folio batch "DIR_061" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:14:49]   SUCCESS: exit=0 elapsed=54.2s
[2026-03-27 08:14:49] 
[2026-03-27 08:14:49] [63/83] DIR_062 (11 PDFs)
[2026-03-27 08:14:49]   CMD: folio batch "DIR_062" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:25:15]   SUCCESS: exit=0 elapsed=626.4s
[2026-03-27 08:25:15] 
[2026-03-27 08:25:15] [64/83] DIR_063 (1 PDFs)
[2026-03-27 08:25:15]   CMD: folio batch "DIR_063" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 08:44:12]   SUCCESS: exit=0 elapsed=1136.9s
[2026-03-27 08:44:12] 
[2026-03-27 08:44:12] [65/83] DIR_064 (1 PDFs)
[2026-03-27 08:44:12]   CMD: folio batch "DIR_064" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:05:17]   SUCCESS: exit=0 elapsed=1264.9s
[2026-03-27 09:05:17] 
[2026-03-27 09:05:17] [66/83] DIR_065 (1 PDFs)
[2026-03-27 09:05:17]   CMD: folio batch "DIR_065" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:05:57]   SUCCESS: exit=0 elapsed=39.4s
[2026-03-27 09:05:57] 
[2026-03-27 09:05:57] [67/83] DIR_066 (1 PDFs)
[2026-03-27 09:05:57]   CMD: folio batch "DIR_066" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:08:23]   SUCCESS: exit=0 elapsed=146.6s
[2026-03-27 09:08:23] 
[2026-03-27 09:08:23] [68/83] DIR_067 (1 PDFs)
[2026-03-27 09:08:23]   CMD: folio batch "DIR_067" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:12:56]   SUCCESS: exit=0 elapsed=272.7s
[2026-03-27 09:12:56] 
[2026-03-27 09:12:56] [69/83] DIR_068 (2 PDFs)
[2026-03-27 09:12:56]   CMD: folio batch "DIR_068" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:18:52]   SUCCESS: exit=0 elapsed=356.2s
[2026-03-27 09:18:52] 
[2026-03-27 09:18:52] [70/83] DIR_069 (1 PDFs)
[2026-03-27 09:18:52]   CMD: folio batch "DIR_069" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:19:08]   SUCCESS: exit=0 elapsed=15.7s
[2026-03-27 09:19:08] 
[2026-03-27 09:19:08] [71/83] DIR_070 (1 PDFs)
[2026-03-27 09:19:08]   CMD: folio batch "DIR_070" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:21:00]   SUCCESS: exit=0 elapsed=112.4s
[2026-03-27 09:21:00] 
[2026-03-27 09:21:00] [72/83] DIR_071 (1 PDFs)
[2026-03-27 09:21:00]   CMD: folio batch "DIR_071" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:40:26]   SUCCESS: exit=0 elapsed=1165.7s
[2026-03-27 09:40:26] 
[2026-03-27 09:40:26] [73/83] DIR_072 (1 PDFs)
[2026-03-27 09:40:26]   CMD: folio batch "DIR_072" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:40:35]   SUCCESS: exit=0 elapsed=8.5s
[2026-03-27 09:40:35] 
[2026-03-27 09:40:35] [74/83] DIR_073 (1 PDFs)
[2026-03-27 09:40:35]   CMD: folio batch "DIR_073" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:40:41]   SUCCESS: exit=0 elapsed=6.7s
[2026-03-27 09:40:41] 
[2026-03-27 09:40:41] [75/83] DIR_074 (5 PDFs)
[2026-03-27 09:40:41]   CMD: folio batch "DIR_074" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:44:14]   SUCCESS: exit=0 elapsed=213.0s
[2026-03-27 09:44:14] 
[2026-03-27 09:44:14] [76/83] DIR_075 (2 PDFs)
[2026-03-27 09:44:14]   CMD: folio batch "DIR_075" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:48:47]   SUCCESS: exit=0 elapsed=272.9s
[2026-03-27 09:48:47] 
[2026-03-27 09:48:47] [77/83] DIR_076 (3 PDFs)
[2026-03-27 09:48:47]   CMD: folio batch "DIR_076" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:50:34]   SUCCESS: exit=0 elapsed=106.9s
[2026-03-27 09:50:34] 
[2026-03-27 09:50:34] [78/83] DIR_077 (1 PDFs)
[2026-03-27 09:50:34]   CMD: folio batch "DIR_077" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:50:42]   SUCCESS: exit=0 elapsed=7.5s
[2026-03-27 09:50:42] 
[2026-03-27 09:50:42] [79/83] DIR_078 (1 PDFs)
[2026-03-27 09:50:42]   CMD: folio batch "DIR_078" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:50:58]   SUCCESS: exit=0 elapsed=16.2s
[2026-03-27 09:50:58] 
[2026-03-27 09:50:58] [80/83] DIR_079 (1 PDFs)
[2026-03-27 09:50:58]   CMD: folio batch "DIR_079" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:51:03]   SUCCESS: exit=0 elapsed=5.5s
[2026-03-27 09:51:03] 
[2026-03-27 09:51:03] [81/83] DIR_080 (1 PDFs)
[2026-03-27 09:51:03]   CMD: folio batch "DIR_080" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 09:52:08]   SUCCESS: exit=0 elapsed=64.7s
[2026-03-27 09:52:08] 
[2026-03-27 09:52:08] [82/83] DIR_081 (2 PDFs)
[2026-03-27 09:52:08]   CMD: folio batch "DIR_081" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 10:11:18]   SUCCESS: exit=0 elapsed=1149.9s
[2026-03-27 10:11:18] 
[2026-03-27 10:11:18] [83/83] DIR_082 (1 PDFs)
[2026-03-27 10:11:18]   CMD: folio batch "DIR_082" --pattern "*.pdf" --llm-profile anthropic_haiku45
[2026-03-27 10:14:51]   SUCCESS: exit=0 elapsed=213.6s
[2026-03-27 10:14:51] 
[2026-03-27 10:14:51] ============================================================
[2026-03-27 10:14:51] SUMMARY: 82 success, 0 error, 1 timeout, 0 exception, 8.3h total
[2026-03-27 10:14:51] Finished: 2026-03-27T10:14:51.843937
[2026-03-27 10:14:51] ============================================================
[2026-03-27 10:28:44] 
[2026-03-27 10:28:44] # Execution Run: pptx
[2026-03-27 10:28:44] Started: 2026-03-27T10:28:44.860367
[2026-03-27 10:28:44] Phase: pptx
[2026-03-27 10:28:44] Profile: anthropic_haiku45
[2026-03-27 10:28:44] Dry run: False
[2026-03-27 10:28:44] PDF directories: 83
[2026-03-27 10:28:44] PPTX directories: 11
[2026-03-27 10:28:44] 
[2026-03-27 10:28:44] 
[2026-03-27 10:28:44] ============================================================
[2026-03-27 10:28:44] PHASE B: PPTX BATCH CONVERSIONS
[2026-03-27 10:28:44] ============================================================
[2026-03-27 10:28:44] 
[2026-03-27 10:28:44] [1/11] DIR_083 (1 PPTXs)
[2026-03-27 10:28:44]   CMD: folio batch "DIR_083" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:29:16]   SUCCESS: exit=0 elapsed=31.7s
[2026-03-27 10:29:16] 
[2026-03-27 10:29:16] [2/11] DIR_005 (2 PPTXs)
[2026-03-27 10:29:16]   CMD: folio batch "DIR_005" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:36:53]   SUCCESS: exit=0 elapsed=457.4s
[2026-03-27 10:36:53] 
[2026-03-27 10:36:53] [3/11] DIR_084 (1 PPTXs)
[2026-03-27 10:36:53]   CMD: folio batch "DIR_084" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:37:25]   SUCCESS: exit=0 elapsed=31.8s
[2026-03-27 10:37:25] 
[2026-03-27 10:37:25] [4/11] DIR_085 (1 PPTXs)
[2026-03-27 10:37:25]   CMD: folio batch "DIR_085" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:37:56]   SUCCESS: exit=0 elapsed=30.3s
[2026-03-27 10:37:56] 
[2026-03-27 10:37:56] [5/11] DIR_086 (1 PPTXs)
[2026-03-27 10:37:56]   CMD: folio batch "DIR_086" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:38:25]   SUCCESS: exit=0 elapsed=29.0s
[2026-03-27 10:38:25] 
[2026-03-27 10:38:25] [6/11] DIR_087 (1 PPTXs)
[2026-03-27 10:38:25]   CMD: folio batch "DIR_087" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:38:50]   SUCCESS: exit=0 elapsed=25.9s
[2026-03-27 10:38:50] 
[2026-03-27 10:38:50] [7/11] DIR_088 (1 PPTXs)
[2026-03-27 10:38:50]   CMD: folio batch "DIR_088" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:39:26]   SUCCESS: exit=0 elapsed=35.1s
[2026-03-27 10:39:26] 
[2026-03-27 10:39:26] [8/11] DIR_089 (1 PPTXs)
[2026-03-27 10:39:26]   CMD: folio batch "DIR_089" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:39:57]   SUCCESS: exit=0 elapsed=31.6s
[2026-03-27 10:39:57] 
[2026-03-27 10:39:57] [9/11] DIR_090 (1 PPTXs)
[2026-03-27 10:39:57]   CMD: folio batch "DIR_090" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:40:28]   SUCCESS: exit=0 elapsed=30.9s
[2026-03-27 10:40:28] 
[2026-03-27 10:40:28] [10/11] DIR_091 (1 PPTXs)
[2026-03-27 10:40:28]   CMD: folio batch "DIR_091" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:41:02]   SUCCESS: exit=0 elapsed=33.8s
[2026-03-27 10:41:02] 
[2026-03-27 10:41:02] [11/11] DIR_092 (1 PPTXs)
[2026-03-27 10:41:02]   CMD: folio batch "DIR_092" --pattern "*.pptx" --llm-profile anthropic_haiku45
[2026-03-27 10:43:28]   SUCCESS: exit=0 elapsed=146.6s
[2026-03-27 10:43:28] 
[2026-03-27 10:43:28] ============================================================
[2026-03-27 10:43:28] SUMMARY: 11 success, 0 error, 0 timeout, 0 exception, 0.2h total
[2026-03-27 10:43:28] Finished: 2026-03-27T10:43:28.939901
[2026-03-27 10:43:28] ============================================================
