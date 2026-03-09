# Tier 1 Validation — Raw Chat Log

> **Purpose:** Verbatim record of all human–AI interactions during both the original
> Tier 1 Validation Run (March 7, 2026) and the Tier 1 Rerun (March 8, 2026).
> Kept raw and unedited so future contributors can trace every decision, dead end,
> and breakthrough exactly as it happened.
>
> **Transcript IDs:**
> - Original run + rerun: `70775cfc-4386-4fe7-ab69-ed1c9c087f43`
>
> **Companion docs:**
> - [Session Log (Original)](tier1_session_log.md)
> - [Session Log (Rerun)](tier1_rerun_session_log.md)
> - [Validation Report (Original)](tier1_validation_report.md)
> - [Validation Report (Rerun)](tier1_rerun_report.md)

---

## Table of Contents

1. [Session 1: Original Tier 1 Validation Run (March 7)](#session-1-original-tier-1-validation-run-march-7)
   - [Phase 1–2: Setup and Corpus](#phase-12-setup-and-corpus)
   - [LibreOffice Blocked, PowerPoint -9074 Debugging](#libreoffice-blocked-powerpoint--9074-debugging)
   - [Switching to Terminal.app](#switching-to-terminalapp)
   - [Batch Run and API Key](#batch-run-and-api-key)
   - [Results and Report](#results-and-report)
2. [Session 2: Tier 1 Rerun (March 8)](#session-2-tier-1-rerun-march-8)
   - [Git Pull and Rerun Setup](#git-pull-and-rerun-setup)
   - [Sandbox Troubleshooting (5 Attempts)](#sandbox-troubleshooting-5-attempts)
   - [Full 50-Deck Run](#full-50-deck-run)
   - [Two-Pass and Final Validation](#two-pass-and-final-validation)

---

## Session 1: Original Tier 1 Validation Run (March 7)

### Phase 1–2: Setup and Corpus

**USER:**
> Execute @folio.love/v0.1_Tier1_Validation_Run.md; use files in @folio.love/sample_powerpoint/

**ASSISTANT:**
Read the validation run document. Found 80+ real PPTX files in `sample_powerpoint/` (many with "copy" duplicates). Selected 50 unique decks, created symlinks in `tests/validation/corpus/`. Set up `folio.yaml` with `pptx_renderer: powerpoint`, `library_root: ./tests/validation/output`. Folio already installed in `.venv`.

**ASSISTANT (discovery):**
No `ANTHROPIC_API_KEY` set. The pipeline will gracefully degrade — all analysis will be `[pending]`. Proceeded with conversion-only validation.

---

### LibreOffice Blocked, PowerPoint -9074 Debugging

**ASSISTANT:**
LibreOffice conversion failed — `soffice` is killed immediately (exit code 137 = SIGKILL). Likely MDM policy.

Fell back to PowerPoint AppleScript. First error:
```
PowerPoint conversion failed: AppleEvent timed out. (-1712)
```

Then consistent:
```
An error of type -9074 has occurred. (-9074)
```

Debugged extensively:
- Verified PowerPoint is running and responding to AppleScript (`get name of active presentation` works)
- The `open POSIX file` command in AppleScript consistently returns -9074
- Tried different files, different paths, direct copies to `/tmp/`
- Same error every time

**USER:**
> Do not use LibreOffice; it's blocked by McKinsey policy.

**ASSISTANT:**
Confirmed. Updated config to `pptx_renderer: powerpoint`. Continued debugging the AppleScript -9074 issue.

Key discovery: `open -a "Microsoft PowerPoint" <file>` (Launch Services) works — file opens in PowerPoint. But the AppleScript `open POSIX file` and `save as PDF` commands fail or hang. This is a TCC (Transparency, Consent, and Control) permission issue — **Cursor's terminal process does not have Automation permission for PowerPoint**.

---

### Switching to Terminal.app

**ASSISTANT:**
Created batch scripts and instructed user to run from Terminal.app (which has Automation permission). Launched:
```bash
cd /Users/Jonathan_Oh/dev/folio.love
source .venv/bin/activate
bash tests/validation/rerun_full_single_pass.sh
```

**ASSISTANT (monitoring):**
Terminal.app works. Conversions succeeding. 12 of 50 done after ~5 minutes. Pipeline fully functional: PDF normalization via PowerPoint, image extraction, text extraction all working. LLM analysis skipped (no API key).

38 of 50 done...

**USER:**
> Wait, why is LLM analysis being skipped? I can provide an Anthropic API Key.
>
> sk-proj-[REDACTED]

**ASSISTANT:**
That key has an `sk-proj-` prefix — that's an **OpenAI** key, not Anthropic. Anthropic keys start with `sk-ant-`. Would you like to:
1. Switch to OpenAI with that key?
2. Provide an Anthropic key instead?

Also: **please avoid pasting API keys directly in chat.** I'll set it as an environment variable only.

**USER:**
> Anthropic key: sk-ant-api03-fXqR_[REDACTED]-frTWkwAA

**ASSISTANT:**
Got it. Created `tests/validation/.env` (gitignored). Killed the current no-LLM run, cleaned output, relaunched with API key. The `.env` is sourced by the batch scripts.

---

### Batch Run and API Key

**ASSISTANT (monitoring):**
API calls working — HTTP requests to `api.anthropic.com` visible. 3 of ~38 decks done after 7 minutes. Rate limit: 50 requests/minute. Each slide = 1 API call.

7 decks... 10 decks... 19 decks...

**USER:**
> keep going

**ASSISTANT:**
Phase 3.1 complete: **31 succeeded, 19 failed** (95 min). 2 timeouts (-1712), 17 with error -9074.

Phase 3.2 (two-pass) launched automatically. **0 succeeded, 50 failed** — PowerPoint's AppleScript interface died after the 95-minute Phase 3.1 run. All -9074 in 6 seconds. PowerPoint became unresponsive to AppleScript after many consecutive operations.

Restarted PowerPoint. Ran Phase 3.2 again. **19 succeeded, 31 failed** — PowerPoint died again after ~45 min. Phase 3.3 (reconversion) also failed completely.

**ASSISTANT (validation):**
Ran `validate_frontmatter.py` on the 32 unique decks that converted:
- **32/32 PASS** — zero frontmatter errors, zero silent failures
- Grounding accuracy initially showed 13/32 match — investigated and found the validator's regex didn't capture pass-2 evidence format (`(high, pass 2)` vs `(high)`). Fixed the regex. **32/32 grounding accuracy after fix.**

---

### Results and Report

**ASSISTANT:**
**Result: CONDITIONAL PASS**
- 32/50 decks converted (18 failed due to PowerPoint -9074 / timeout)
- 0 silent failures across all 32 converted
- 612 slides, 2,904 evidence claims
- 100% frontmatter validation, 93.4% avg evidence validation rate
- PowerPoint AppleScript instability is the sole blocker

**USER:**
> Can you also generate the log file of all of our interactions? It will be very helpful when we are debugging.

**ASSISTANT:**
Created `docs/validation/tier1_session_log.md` — comprehensive chronological log with all issues, root causes, evidence, and fix recommendations.

---

## Session 2: Tier 1 Rerun (March 8)

### Git Pull and Rerun Setup

**USER:**
> Let's git pull the latest from https://github.com/ohjonathan/folio.love

**ASSISTANT:**
Pulled. Fast-forward from `eecd7f0` to `5508a4f`. Key changes across 20 files:
- `normalize.py`: Two-step `open -a` + AppleScript export (replaces `open POSIX file`)
- `cli.py`: `--dedicated-session` with preemptive restart every 15 conversions
- `converter.py`: `pptx_output_dir=deck_dir` to avoid sandbox dialogs
- New docs: managed Mac workflow guide, renderer proposal, rerun prompt

**USER:**
> Execute @folio.love/docs/validation/tier1_validation_rerun_prompt.md. Use the docs in @folio.love/sample_powerpoint/.
>
> Make sure you are recording everything. It's critical that we track all of those in case the needs of debugging. I will also share what I see on my side.

**ASSISTANT:**
Read rerun prompt. Set up tracking. Verified environment: Python 3.12.13, folio installed (editable) with all new code, exact same 50-deck corpus, Anthropic SDK 0.84.0. Need API key.

**USER:**
> sk-ant-api03-U_IdtcGb1SIgf-[REDACTED]-4xMb7wAA

**ASSISTANT:**
Stored in `tests/validation/.env`. Verified key (108 chars), PowerPoint 16.106.3 responsive, all 4 scripts executable. Launched Phase 3.1 preflight (17-file -9074 cohort) from Terminal.app.

---

### Sandbox Troubleshooting (5 Attempts)

#### Attempt 1: PR #10 default (`pptx_output_dir=deck_dir`)

**USER:**
> Ugh, I still have to manually give access to each powerpoint?

**ASSISTANT:**
Critical finding. The "Grant File Access" dialogs are macOS sandbox prompts. PowerPoint is trying to write the PDF into the output directory (`tests/validation/output/building_blocks`) and the sandbox requires manual permission for each folder. This breaks batch automation.

Recommended: Grant PowerPoint Full Disk Access in System Settings.

---

#### Attempt 2: Full Disk Access

**USER:**
> Okay, I just did your steps and turned the toggle ON.
>
> Open System Settings (it should already be open)
> Go to Privacy & Security > Full Disk Access
> Click the + button
> Navigate to /Applications/ and select Microsoft PowerPoint.app
> Toggle it ON

**ASSISTANT:**
Killed and relaunched PowerPoint to pick up the new entitlement. Relaunched preflight. First two files succeeded quickly (Building Blocks 9.0s, Data_Layers 16.2s) — looked promising...

**USER:**
> still getting it

**ASSISTANT:**
Full Disk Access isn't solving this. PowerPoint's App Sandbox overrides FDA. This is a definitive finding.

Killed PowerPoint. Relaunched. Still showing dialogs.

---

#### Attempt 3: Revert to temp directory

**ASSISTANT:**
Reverted `pptx_output_dir=deck_dir` in `converter.py`. Now PowerPoint writes to temp dir (`/var/folders/...`) — the path that worked in March.

**USER:**
> what if we halt the whole thing and start from scratch?

**ASSISTANT:**
Good call. Killed current run, cleaned output. Relaunched preflight with temp-dir path.

**USER:**
> nope, still

**ASSISTANT:**
Even temp dirs trigger it! Path shown: `/private/var/folders/h3/.../tmp5la69vvu`. Each conversion creates a new temp directory, so each triggers a new sandbox grant.

---

#### Attempt 4: Write PDF next to source file

**ASSISTANT:**
Changed `ppt_dir = source_path.parent` in `normalize.py`. Hypothesis: PowerPoint opened the file from that directory, so it has sandbox access there. Added `shutil.move()` to relocate PDF afterward.

**USER:**
> still

**ASSISTANT:**
Dialog appears for `sample_powerpoint/` directory. `open -a` gives PowerPoint *read* access to open the file, but NOT *write* access to the directory.

---

#### Attempt 5 (SOLUTION): Fixed staging directory

**ASSISTANT:**
Created `~/Documents/.folio_pdf_staging/` as a single fixed output directory for ALL PowerPoint PDFs. Changed `ppt_dir = Path.home() / "Documents" / ".folio_pdf_staging"` in `normalize.py`. Added `shutil.move()` to relocate PDF from staging to temp/output dir.

Launched preflight. First file (Building Blocks) took a while — stuck on dialog for the staging dir...

**USER:**
> Just granted access to "Sample output" folder

**ASSISTANT:**
That should be the only dialog for the entire batch. All subsequent files will reuse that same staging directory.

**RESULT:** Building Blocks and Data_Layers timed out (dialog casualties — they were waiting on the dialog before user granted access). But ALL remaining 15 files converted with **zero dialogs**.

**Phase 3.1 Preflight: 15/17 succeeded, 2 dialog casualties.**
- All 17 previously-failing -9074 files now convert with the `open -a` fix
- The 2 failures were timeout while waiting for staging-dir grant, not real conversion failures
- **FM1 (-9074 fix): CONFIRMED WORKING**

---

### Full 50-Deck Run

**ASSISTANT:**
Merged fatigue test with full Phase 4.1 run. Cleaned output, launched full 50-deck single-pass.

Monitoring progress:
- 8/50 done (10 min), all succeeding, no dialogs
- 13/50 done, approaching restart point
- **17/50 done, 1 restart event detected** — preemptive restart fired at file #15 as expected. Batch continued seamlessly.
- 22/50 done, zero failures, zero dialogs

**USER:**
> just question; do we really need 50? can we stop at 30 or is reaching 50 critical? This is just a question

**ASSISTANT:**
Per the rerun prompt, the Tier 1 gate is explicitly **"50 real decks converted with zero silent failures"** — intentionally strict. Stopping at 30 would give CONDITIONAL PASS at best (same as March). The run is fully automated and on autopilot — I'd recommend letting it finish.

**USER:**
> okay sounds good, let's keep going then. Let it finish to get the full 50/50 gate answer.

**ASSISTANT (monitoring):**
- 27/50 done. GenAI assessment (107 slides, 907s = 15 min) completed.
- 38/50 done. **CIO SteerCo_v3** (previously timed out in March): **now succeeds**. Building Blocks and Data_Layers: **now succeed** (dialog casualties from preflight convert fine in main run).
- 2 preemptive restarts fired (at #15 and #30), both seamless.
- 45/50 done. SlideLibrary (124 slides, 838s) completed.
- 47/50 done...

**50/50 SUCCEEDED. ZERO FAILURES. 3 RESTARTS. 7,026 seconds (~117 min).**

**919 total slides across 50 decks.**

---

### Two-Pass and Final Validation

**ASSISTANT:**
Launched Phase 4.2 (two-pass). While running, validated Phase 4.1 output:
- **49/50 PASS, 1 edge case** (`building_blocks` — 1-slide template with pending analysis)
- 100% grounding accuracy
- Median 95% evidence validation rate

**Phase 4.2 complete: 50/50 succeeded, 0 failures, 4,361s (~73 min).**

Ran staleness test: modified `SOW PS.pptx` (appended a byte), folio detected it as stale (`49 Current, 1 Stale`). Reverted, all 50 back to current.

Final validation on two-pass output: **49/50 PASS** (same building_blocks edge case). Pass-2 evidence doubled. Median validation rate 96%.

Deleted `.env` for security. Wrote `docs/validation/tier1_rerun_report.md` and finalized `docs/validation/tier1_rerun_session_log.md`.

---

## Final Gate Decision

| Metric | March 2026 Baseline | Rerun |
|--------|-------------------|-------|
| Automated PPTX conversions | 31/50 | **50/50** |
| Failures | 19 | **0** |
| -9074 fixes | 0/17 | **17/17** |
| Silent failures | 0 | **0** |
| Manual intervention | Required | **None** (one-time staging dir grant) |
| Total slides | 612 | **919** |
| Evidence claims (two-pass) | 2,904 | **5,505** |
| Preemptive restarts | N/A | **3 (seamless)** |

**Tier 1 Gate: PASS**

---

## Key Learnings for Future Runs

1. **Always run from Terminal.app** — Cursor's terminal lacks TCC Automation permission for PowerPoint.
2. **PowerPoint App Sandbox overrides Full Disk Access** — FDA does not grant write access to sandboxed Office apps.
3. **Use a fixed staging directory** (`~/Documents/.folio_pdf_staging/`) for all PowerPoint PDF output — one sandbox grant covers the entire batch.
4. **PowerPoint AppleScript fatigues after ~30-45 min** of continuous operation — preemptive restarts (every 15 conversions via `--dedicated-session`) prevent this.
5. **`open -a` (Launch Services) for opening, AppleScript for exporting** — the two-step approach eliminates -9074 errors from `open POSIX file`.
6. **Cache invalidation on re-normalization** — each PDF regeneration produces different image hashes, so analysis cache shows 0% hit rate on reconversion. This is expected behavior, not a bug.
7. **Always record interactions** — this chat log exists because debugging PowerPoint sandbox issues required tracing back through every attempt and its exact result.
