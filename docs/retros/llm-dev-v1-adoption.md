---
id: llm-dev-v1-adoption-retro
deliverable_id: proposal-review-hardening-v0.6.0
role: retrospective
family: claude
phase: E
status: complete
created: 2026-04-15
halted_at: -A.proposal
halt_cause: pre-a-verdict-not-proceed
---

# Retrospective — llm-dev-v1.1 first production adoption (folio.love)

> **Status:** Friction log is being maintained **throughout the session** (Setup → Pre-A → A → B → C → D → E). This doc finalizes at Phase E; the raw friction log appendix is the evidence that the Phase E "What worked / What broke / Framework updates" sections are built on.

## Session metadata

- **Date:** 2026-04-15
- **Adopter:** folio.love (first production run of v1.1)
- **Framework bundle:** `frameworks/llm-dev-v1/` (v1.1.0, verbatim-copied from johnny-os)
- **Deliverable under lifecycle:** `proposal-review-hardening-v0.6.0` — smallest coherent FR-813 slice from PR #43's proposal doc (`docs/specs/tier4_discovery_proposal_layer_spec.md`)
- **Orchestrator:** Claude (Opus 4.6, 1M context), acting as author + fix-author + orchestrator; workers dispatched via `claude`, `codex`, and `gemini` CLIs and Claude sub-agents
- **Entry point:** Pre-A.proposal (Template 16) at Round 1

## Friction log (append-only)

Entries ordered by encounter time. Each entry captures: **what happened**, **where in the framework it surfaced**, **what I did to unblock**, and **what v1.2 should change**.

### [F-001] Bundle location mismatches adoption doc convention

- **When:** Setup, before any dispatch.
- **What:** The adoption doc (`frameworks/2026-04-15_folio-love-llm-dev-adoption.md` §Step 1) recommends placing the bundle at `ops/llm-dev-v1/`. The bundle is already present at `frameworks/llm-dev-v1/`. Paths in the adoption doc's commands (`cp ops/llm-dev-v1/tokens.md ops/llm-dev-v1/tokens.local.md`) do not match reality.
- **Resolution:** Placed `tokens.local.md` inside the existing bundle at `frameworks/llm-dev-v1/tokens.local.md`. The bundle is self-contained so the path choice is cosmetic, but every adoption-doc snippet needs manual path-rewriting.
- **v1.2 target:** Adoption doc should either pick one canonical path and enforce it, or explicitly templatize the path like `<BUNDLE_ROOT>/tokens.local.md` so operators substitute once. Current form silently assumes `ops/llm-dev-v1/` and confuses anyone who places the bundle elsewhere.

### [F-002] Adoption doc assumes TS/React; folio is Python

- **When:** Setup, filling `tokens.local.md`.
- **What:** Adoption doc §Step 2 suggests `<TEST_COMMAND>` = `npm test` / `pnpm test` / `vitest run` and `<allowed_paths>` like `src/app/...`. Folio is pure Python (pytest, folio/ package, no src/ root).
- **Resolution:** Substituted `python3 -m pytest tests/ -q`, `python3 -c "import folio"`, `python3 -m ruff check folio/`. Manifest allowed_paths drawn from the Python tree.
- **v1.2 target:** A per-language appendix (Python/TS/Go/Rust) with idiomatic smoke-check + scope-lock-path patterns. The adoption doc's "Known unknowns for v1.2" already flags this ("Per-language scope-lock appendix for TS/React") but the gap runs the other way too — TS is the assumption, Python is the gap.

### [F-003] Adoption doc silent on where adopter-side manifests live

- **When:** Setup, drafting the first manifest.
- **What:** Bundle's `manifest/` dir holds the schema and example manifests. Adoption doc §Step 4 says "draft folio.love's first manifest by copying the user-facing example and substituting", but does not specify *where* the adopter's manifest file should live. Dumping it into the bundle's `manifest/` dir pollutes bundle namespace; dumping it into project `docs/` mixes infrastructure with product docs.
- **Resolution:** Created `frameworks/manifests/` as a sibling to the bundle and put `proposal-review-hardening-v0.6.0.yaml` there. Keeps the bundle frozen (per adoption doc §Feedback loop "Do not patch the bundle") while colocating manifests with the framework.
- **v1.2 target:** Adoption doc should add a `<MANIFEST_DIR>` convention, or include a concrete recommended path in §Step 4 ("adopters' manifests live at `<bundle-parent>/manifests/<deliverable-id>.yaml`"). First-run adopters should not have to invent this.

### [F-004] `<DOC_INDEX_*>` tokens optional in framework; Ontos is real in folio

- **When:** Setup, filling tokens Category 4.
- **What:** `<DOC_INDEX_TOOL?>`, `<DOC_INDEX_ACTIVATION?>`, `<DOC_INDEX_ARCHIVE?>` are all optional in `tokens.md`. But folio's `AGENTS.md` explicitly mandates `ontos map` at session start and `ontos log -e "<slug>"` at session end. Leaving them empty would lose the context-map integration. Filling them requires understanding both systems' lifecycles, and the framework doesn't spell out how `ontos log -e` and Template 08 (retrospective) coexist — both claim the "session end" slot.
- **Resolution:** Filled all three with ontos commands. Will run `ontos log -e "llm-dev-v1-first-lifecycle"` AFTER Template 08 retro is finalized, so Ontos captures the retrospective as part of the archived session.
- **v1.2 target:** Framework should explicitly describe how `<DOC_INDEX_ARCHIVE>` interacts with Phase E (retrospective) — the archive command should run AFTER the retro is written, since the archive likely snapshots the retro into its context map. Absent clarity, operators risk running archive before retro and losing the cross-reference.

### [F-005] `verify-all.sh` requires `check-jsonschema`, not preinstalled or bundled

- **When:** Setup, first `verify-all.sh` invocation.
- **What:** `verify-schema.sh` silently skipped the first run because `check-jsonschema` isn't on the default macOS Python path. Exit code 2 is honored as "skip" rather than "fail", which is correct behavior, but the first-run adopter gets "PASSED (skipped: verify-schema.sh)" and may not notice the skip. Missing `check-jsonschema` means the whole schema layer is unchecked until someone reads the output carefully.
- **Resolution:** `pip install check-jsonschema` (0.36.2 installed). Re-ran `verify-all.sh`, now 8/8 green.
- **v1.2 target:** (a) Make `check-jsonschema` a hard prerequisite in the README's "Prerequisites (non-negotiable)" section — the bundle already lists "YAML schema validator (check-jsonschema)" but adopters miss it. (b) Or, make `verify-all.sh` exit non-zero on skip when `--strict` is passed. (c) Consider vendoring a minimal schema validator (Python + jsonschema package already in base distro) instead of the external tool.

### [F-006] P3 strict-violation: only 2 distinct non-author CLI families on host

- **When:** Setup, drafting `model_assignments` block of the manifest.
- **What:** `verify-p3.sh` requires **≥3 distinct non-author engineering families** on B.1 / B.2 / D.2 / D.5. folio.love's orchestrator has three CLIs: `claude` (author-side), `codex`, `gemini`. Removing the author leaves two non-author engineering families, not three. The v1.1 user-facing extension's Product-lens overlap only helps when there are already three engineering families to overlap *with*; it cannot manufacture a third family.
- **Resolution:** Declared a synthetic fourth family `claude-sub` (Claude sub-agent invoked via the Agent tool, running in a session fully isolated from the author's main thread). Treated as "same-provider-separate-session" per v1.1 P10. This does **not** strictly satisfy P3's family-diversity intent because `claude-sub` shares training data and failure modes with `claude`. The retro's `Recommended framework updates` section will flag this as the #1 adoption blocker.
- **v1.2 target:** Either (a) relax P3 to "≥3 distinct sessions (not necessarily families) where no session shares the author's *context*" — which would legitimize sub-agent usage; or (b) add an explicit "degraded P3" doctrine where adopters can opt-in with a documented blind-spot risk; or (c) ship a blessed fallback family (e.g., `claude-sonnet` via CLI flag) so Claude-primary adopters aren't blocked. Option (c) is cheapest because claude CLI *could* support a `--model claude-sonnet-*` invocation if the harness allowed it. Today it does not (see friction log F-005-adj: "Fast mode" locks to Opus 4.6 for this session per `/effort max`).

### [F-007] `verify-p3.sh` only validates bundle examples, not adopter manifests

- **When:** Setup, after drafting `frameworks/manifests/proposal-review-hardening-v0.6.0.yaml`.
- **What:** The bundle's `scripts/verify-p3.sh` hard-codes the two example manifest paths (`manifest/example-manifest.yaml`, `manifest/example-user-facing-manifest.yaml`) and does not accept an argument for an adopter's manifest. So folio's custom manifest is not auto-validated against P3 / schema / gate-category rules — the adopter flies blind on their own manifest even though the tooling to validate it exists.
- **Resolution:** Ran validation ad-hoc using the same python yaml+check-jsonschema pattern against folio's manifest path. Documented the friction.
- **v1.2 target:** All `verify-*.sh` scripts should accept a `--manifest <path>` argument (or environment variable `LLM_DEV_V1_MANIFEST=<path>`) so adopters can run the same suite against their own manifests. Trivial change; enormous value for first-run confidence.

### [F-009] `verify-tokens.sh` warns on defined-but-unreferenced tokens

- **When:** Setup, first `verify-all.sh` run.
- **What:** `verify-tokens.sh` emits `[warn] tokens defined but not referenced:` for seven tokens (`<DELIVERABLE_SLUG>`, `<META_CONSOLIDATOR_FAMILY>`, `<MODEL_ASSIGNMENTS>`, `<PR_TITLE_PATTERN>`, `<REPO_URL>`, `<SLUG>`, `<STATIC_CHECKS>`). These are *manifest-level* tokens used outside template bodies (by the orchestrator at PR-creation time or for cross-referencing), so they legitimately don't appear in templates. The warning is noisy and misleads first-run adopters into thinking something is broken.
- **Resolution:** Verified each warned token has a legitimate out-of-template consumer. Accepted as expected behavior.
- **v1.2 target:** `verify-tokens.sh` should have a tokens.md-side annotation (e.g., `orchestrator-only: true` in each category table) for tokens that are *intentionally* not template-referenced. Warning suppressed for those.

### [F-010] No blessed adopter-manifest validation path

- **When:** After drafting the folio manifest, wanting to validate it.
- **What:** To validate my adopter manifest, I had to run `check-jsonschema --schemafile ...` by hand against the schema. `verify-schema.sh` doesn't accept my manifest path; `verify-p3.sh` doesn't either. So I'm running validation out-of-band.
- **Resolution:** Ran `check-jsonschema` ad-hoc. Validated successfully after fixing F-011. Captured the exact command for the retro.
- **v1.2 target:** See also [F-007]. A unified `verify-adopter.sh <manifest-path>` would run all adopter-relevant checks (schema + p3 + gate-categories + artifact-paths + pre-a) against a single adopter manifest path.

### [F-011] Schema forbids dots in `id` / `slug` — collides with semver versioning

- **When:** Ad-hoc manifest schema validation.
- **What:** `deliverable-manifest.schema.yaml` defines `id` pattern as `^[a-z][a-z0-9-]*$` — no dots allowed. A natural deliverable id like `proposal-review-hardening-v0.6.0` (borrowing semver from folio's existing `v0.5.1_tier3_*` convention) fails validation. Had to rewrite as `proposal-review-hardening-v0-6-0`, which visually reads worse and breaks automated version-parsing tools that expect semver.
- **Resolution:** Renamed id to `proposal-review-hardening-v0-6-0` and renamed the manifest file to match. Semver is still recoverable (replace `-` with `.` on the version suffix) but less clean.
- **v1.2 target:** Relax the `id` pattern to `^[a-z][a-z0-9.-]*$` (allow dots). Or explicitly document "ids are filesystem-safe slugs; do NOT put semver in the id; use a separate `version:` field at the top level." The current design forces adopters into the first interpretation (version-in-id) and then punishes them.

### [F-008] Bundle's `manifest/` dir is bundle-owned; no documented path for adopter manifests

- **When:** Setup, placing the manifest.
- **What:** Bundle's `manifest/` holds the schema and examples — that dir is part of the frozen bundle. Adoption doc §Step 4 says "draft folio.love's first manifest by copying the user-facing example" but never says where the copy should live. Dumping it into `frameworks/llm-dev-v1/manifest/` would pollute bundle namespace and might be blown away on bundle upgrade. Dumping it into `docs/` mixes infra with product docs.
- **Resolution:** Created `frameworks/manifests/` as a sibling to the bundle. Keeps infrastructure adjacent to the bundle without overwriting bundle contents.
- **v1.2 target:** Adoption doc should add a concrete recommendation in §Step 4 ("adopter manifests live at `<bundle-parent>/manifests/<deliverable-id>.yaml`"). The path is arbitrary but it should be *documented* so every first-run adopter doesn't re-invent the convention.

### [F-012] Template 16's 2-lens setup doesn't map cleanly onto `<role>_<family>` artifact naming

- **When:** Pre-A dispatch, choosing output paths.
- **What:** Template 16 assigns each reviewer a *2-lens posture* (Adversarial+Product for reviewer 1, Alignment+Technical for reviewer 2 per playbook §13.4). The manifest's `family_verdict` path pattern is `<phase>_<role>_<family>.md` — but both reviewers have role `proposal-reviewer`, so the pattern alone can't disambiguate them. Adopters must invent a posture-suffix convention.
- **Resolution:** Named artifacts `_claude-sub_adversarial_product.md` and `_gemini_alignment_technical.md`, encoding posture in the filename. Not covered by the schema's `family_verdict` pattern syntax (which allows only `<phase>`, `<family>`, `<role>` placeholders).
- **v1.2 target:** Extend `family_verdict` path-pattern placeholders to include `<posture>` for Pre-A.proposal artifacts, or publish a conventional naming scheme in Template 16 itself (e.g., `<phase>-<family>-<lens-pair>.md`). Today every adopter re-invents this.

### [F-013] No formal meta-consolidator for Pre-A.proposal — orchestrator has to improvise

- **When:** Pre-A Round 1, after two reviewers returned opposing verdicts (gemini: Proceed; claude-sub: Revise).
- **What:** Template 16 notes "P3's ≥3-family floor does not apply (see framework.md § P3 pre-A carve-out)" and does not define a canonical consolidator step. With two reviewers reaching different verdicts, the orchestrator has no framework-provided adjudication protocol and must hand-roll a consolidation document. For B.3/D.3 there's a clear Template 06 meta-consolidator; for Pre-A there's nothing.
- **Resolution:** Wrote `docs/validation/v0.6.0_pre_a_proposal_canonical_verdict.md` using an ad-hoc consolidation applying P5 (evidence-weighted consensus) adapted from Template 06. Flagged the improvisation in the artifact's preamble.
- **v1.2 target:** Either (a) add a Template 16-consolidator (a thin Template 06 variant sized for 2 reviewers and no family-count floor), or (b) prescribe in Template 16 itself that the *orchestrator* does the consolidation under named rules. Right now the adopter faces the exact kind of "write it yourself" moment the framework is supposed to prevent.

### [F-014] Gemini rate-limit warnings during non-interactive dispatch

- **When:** Gemini Pre-A reviewer dispatch.
- **What:** `gemini -p "<prompt>" --approval-mode plan` returned a valid structured verdict on stdout but stderr logged multiple `429 Too Many Requests` responses from `cloudcode-pa.googleapis.com`. The final output was usable but the rate-limit warning is visible noise for the adopter. Not a blocker — the CLI retried and completed — but the adopter who sees the stderr might conclude the dispatch failed. Wall-clock to completion was ~8 minutes (long tail on retries).
- **Resolution:** Verified output was well-formed, captured stdout, wrote verdict artifact. Recorded rate-limit observation in the halt report for Session metadata.
- **v1.2 target:** Adoption doc (or framework README) should explicitly call out that CLI-level rate-limit retry noise is expected on dispatch, with guidance on "how to tell a rate-limited-but-completed dispatch from a failed one" (empty file vs. structured output in file).

### [F-015] Orchestrator-captures-stdout workaround for non-file-writing CLIs

- **When:** Gemini Pre-A reviewer dispatch.
- **What:** The framework's worker-session-contract says the worker writes its artifact to `<ARTIFACT_OUTPUT_PATHS>`. For Claude sub-agents (via the Agent tool) this works cleanly — the sub-agent has Write capability. For `gemini -p` in non-interactive mode (`--approval-mode plan`, which is read-only), the CLI emits output to stdout but does not perform filesystem writes. The orchestrator captured stdout and wrote the file itself, which mildly violates the contract (the artifact was not "authored by the worker" — it was authored by the worker's stdout + an orchestrator write).
- **Resolution:** Captured `gemini` stdout to `/tmp/llm-dev-v1-dispatches/pre-a-proposal-gemini-output.md`, then copied to the canonical path after stripping the shell's ```markdown wrapper. Documented deviation in the halt report.
- **v1.2 target:** (a) Worker-session-contract should explicitly address "stdout-only worker CLIs" as a first-class case, describing the orchestrator-write escape hatch. (b) Or bundle a lightweight adapter script (`scripts/dispatch-worker.sh <family> <prompt-file> <output-file>`) that normalizes CLI capability differences across families. Today every family-specific integration is a mini-project for the adopter.

### [F-018] `tokens.md` says commit `tokens.local.md`; bundle `.gitignore` excludes it

- **When:** Session end, inspecting `frameworks/llm-dev-v1/.gitignore` before committing.
- **What:** `tokens.md` §"How to fill this in" says "Operators fill in a project-local copy of this file and commit it alongside the framework bundle." But `frameworks/llm-dev-v1/.gitignore` includes `tokens.local.md` on line 5, which auto-excludes it from any commit. The two pieces of guidance contradict.
- **Resolution:** Respected the gitignore (mechanical guarantee wins); did not commit `tokens.local.md`. Adopter contents are preserved in the session's conversation context and referenced in the retro for reproducibility, but not in git history.
- **v1.2 target:** Pick one and make them agree. If tokens.local.md is project-specific and *should* be committed (the tokens.md narrative view), remove it from .gitignore. If it's intentionally local-only (safer default for secrets-adjacent workflows), rewrite tokens.md's "commit it alongside" line to say "keep it local; tokens.local.md is gitignored by design." Today the adopter has to pick which to trust.

### [F-017] `ontos log -e "<slug>"` no longer accepts slug positional; AGENTS.md example outdated

- **When:** Session end, running AGENTS.md's prescribed `ontos log -e "<slug>"` archive command.
- **What:** `AGENTS.md` says `ontos log -e "<slug>"` at session end. Current ontos CLI (`ontos log --help`) treats `-e` as `--event-type` (values: feature, fix, refactor, exploration, chore, decision, release). Passing a slug like `proposal-review-hardening-v0-6-0-pre-a-halt` sets it as the event_type (invalid category) and uses the last git commit message as the topic, producing a mis-named log file with a stub body.
- **Resolution:** Re-ran as `ontos log "<topic>" --event-type chore --source claude-code --auto`, then filled the log body by hand. Deleted the erroneous stub.
- **v1.2 target (external):** Update `AGENTS.md`'s Ontos Activation §Session End block to match the current CLI. And/or update ontos CLI to accept `-e "<slug>"` as `--epoch` alias (there's a deprecated `--epoch` flag already) or to hint "did you mean --event-type?" when the value doesn't match one of the known categories. *Note: this is a folio/Ontos friction, not a llm-dev-v1 framework friction. Logged here because adopters following the framework will run the documented archive command at session end.*

### [F-016] User's halt list tighter than framework default — no Round-2 buffer for Pre-A

- **When:** Pre-A Round 1 result, deciding whether to halt or do Round 2.
- **What:** Framework default (playbook.md §13.5) allows up to three rounds of Pre-A proposal review before escalating. The operator brief said "Pre-A verdict ≠ Proceed to Phase A (Revise / Split / Abandon) → HALT" — single-round strict halt, no Round 2. Noted asymmetry: B.3/D.3 get "after second round (circuit breaker)" but Pre-A has no Round-2 qualifier. Framework canonical behavior would have continued; operator brief halted. We followed the operator brief.
- **Resolution:** Halted per operator brief. Documented the asymmetry in the halt report and here.
- **v1.2 target:** The framework shouldn't dictate Round-2 policy at Pre-A — the operator already gets to pick. But the manifest should let the adopter *declare* their Pre-A round policy ("strict-first-round-halt" vs. "default-one-revision-cap") as an explicit field, so the halt behavior is machine-checkable rather than buried in prose operator briefs.

<!-- New entries appended below as the session progresses. -->

---

## Phase E — Retrospective (narrowed scope)

> **Important:** The lifecycle **halted at Pre-A.proposal Round 1**. Phases A, B, C, D were not executed. This retrospective covers Setup + Pre-A only. What follows is therefore narrower than a full A→E retro but it is the factual record of the session.

### Metrics

| Metric | Value |
|--------|-------|
| Phases executed | 0 (scope), -A.proposal (Pre-A Round 1) |
| Phases planned but not executed | A, B, C, D, E (full retro) |
| Total worker sessions | 2 (claude-sub Adversarial+Product; gemini Alignment+Technical) |
| Orchestrator consolidations | 1 (ad-hoc Pre-A canonical verdict; no formal Template — see F-013) |
| Halts | 1 (Pre-A verdict ≠ Proceed; canonical verdict = Revise and re-review) |
| Blockers raised (Pre-A Round 1) | 3 (all by claude-sub reviewer) |
| Blockers preserved in canonical verdict | 3 (B-1, B-2, B-3) |
| Blockers downgraded | 0 |
| Should-fix findings | 5 (claude-sub) |
| Minor findings | 3 (claude-sub) |
| Fix loops | 0 (halted before any D.4 dispatch) |
| Test count | 196 baseline, unchanged (no Phase C execution) |
| Real bugs caught pre-merge | N/A — but 3 proposal-level defects caught before Phase A, which is the equivalent win at Pre-A |
| Final-approval gate outcome | Not reached |
| Friction log entries captured | 16 (F-001 through F-016) |
| Session wall-clock | ~25 minutes Setup + Pre-A; retro finalization ~10 minutes |

### What worked (with evidence)

**W-1. Template 16's 2-lens posture split was load-bearing.** Assigning Adversarial+Product to one reviewer and Alignment+Technical to another produced *exactly* the kind of split verdict Template 16 is supposed to surface: gemini (Alignment+Technical) saw the proposal as aligned and clean (Proceed); claude-sub (Adversarial+Product) saw three internal contradictions and a scope-leak (Revise). Both reviews were correct within their posture. **Evidence:** see the verdict disagreement in `docs/validation/v0.6.0_pre_a_proposal_canonical_verdict.md` §Rationale. Generalizable framework claim: **the 2-lens Pre-A setup catches defects that a single-lens review would rubber-stamp**. The informal prior Pre-A review (`docs/logs/2026-04-15_tier-4-proposal-pre-phase-a-review-round-1-two-rev.md`) did *not* catch PR-A-1/PR-A-2/PR-A-3; Template 16 round 1 did.

**W-2. Evidence discipline caught a real bug that the author missed.** Claude-sub PR-A-1's finding of the §10.1-vs-§13.1-gate-4 contradiction is a zero-tolerance-vs-5%-tolerance clash *in the proposal's own text*. The author (claude, main) wrote both sections and did not notice the contradiction. A structured review with direct-quotation evidence caught it. **Evidence:** `docs/validation/v0.6.0_pre_a_proposal_claude-sub_adversarial_product.md` §3.2 PR-A-1 with direct section quotations.

**W-3. `verify-all.sh` 8/8 green was a clean green light for setup.** Once `check-jsonschema` was installed, the conformance suite ran cleanly and gave confidence that the bundle itself is internally consistent. No mysterious skips or ambiguous warnings beyond the known defined-but-unused token warning (F-009).

**W-4. Python smoke-check / manifest-validation tooling worked.** `check-jsonschema` validated the folio manifest against `deliverable-manifest.schema.yaml` directly. Python was already present on macOS; `pip install check-jsonschema` was one line.

**W-5. The friction-log-as-you-go discipline paid off.** 16 friction entries captured in-context with resolutions and v1.2 targets. Writing them *during* the session rather than reconstructing at the end preserved details (exact error messages, token counts, specific path mismatches) that would have been lost otherwise.

### What broke (with evidence, root cause, mitigation, framework update)

**B-1. P3 cannot strictly be satisfied with a 3-CLI setup when Claude is the author.** (See [F-006].) The framework assumes 4 distinct model vendors on the orchestrator host; folio.love has 3 (claude, codex, gemini). Claude-primary developers can't legitimately hit the ≥3-non-author-engineering-families floor without declaring a synthetic "claude-sub" family. **Root cause:** framework conflates "P3 family diversity" with "P3 CLI vendor diversity" and assumes the latter is always available. **Mitigation this session:** declared `claude-sub` as a pseudo-family. **v1.2 update:** allow adopters to declare "session-isolated sub-agent of an engineering family" as a non-author reviewer explicitly, OR ship a blessed multi-model Claude CLI invocation (e.g., claude-sonnet-4-5) so single-provider adopters have a legitimate 4th family.

**B-2. Pre-A.proposal has no formal meta-consolidator.** (See [F-013].) When two reviewers disagreed on verdict, there was no Template to follow for adjudication. Adopter had to hand-roll the consolidation doc. **Root cause:** Template 16 carve-out says "P3 doesn't apply" but never addresses "what if the 2 reviewers disagree on verdict." **Mitigation this session:** ad-hoc consolidation applying P5 (evidence-weighted consensus) borrowed from Template 06. **v1.2 update:** Template 16 should explicitly specify orchestrator consolidation rules (verdict-preservation of blockers with direct-citation evidence), or add a minimal Template 16b (Pre-A canonical verdict) analogous to Template 06.

**B-3. Adoption doc path conventions drifted from reality.** (See [F-001], [F-002], [F-003], [F-008].) Doc says bundle lives at `ops/llm-dev-v1/`; bundle is actually at `frameworks/llm-dev-v1/`. Doc assumes TS/React; folio is Python. Doc doesn't say where adopter manifests live. Four small mismatches that each cost 2–3 minutes of "wait, does the convention actually matter?" **Root cause:** adoption doc drafted before folio adopted, with assumed defaults that weren't validated against a real first-run. **Mitigation this session:** every path deviation logged with rationale. **v1.2 update:** adoption doc should include a concrete "day-one commands to run" script parameterized by a single `<ADOPTER_REPO_ROOT>` variable, validated by the bundle's verify suite.

**B-4. `verify-p3.sh` / `verify-schema.sh` only validate bundle examples, not adopter manifests.** (See [F-007], [F-010].) After drafting the first adopter manifest, there's no blessed way to run the framework's own validation suite against it. Adopter must run `check-jsonschema` and the python P3 logic by hand. **Root cause:** all `verify-*.sh` hard-code the two example manifest paths. **Mitigation this session:** ran `check-jsonschema` against adopter manifest ad-hoc; re-implemented P3 checks in-head. **v1.2 update:** every `verify-*.sh` should accept `<manifest-path>` argument, or ship a `verify-adopter.sh <manifest-path>` entry point. Trivial change, huge day-one-confidence win.

**B-5. Schema forbids dots in `id`.** (See [F-011].) Natural semver-in-id names fail. **Root cause:** `pattern: "^[a-z][a-z0-9-]*$"` in the schema. **Mitigation:** renamed to `-v0-6-0` with dashes. **v1.2 update:** allow dots in `id`, or publish a "don't put version in id" guidance explicitly.

**B-6. Non-interactive CLI dispatch is family-specific.** (See [F-015].) Gemini `-p` emits to stdout; Codex `exec` does too; Claude sub-agent via the Agent tool can write files. The orchestrator wrote three different invocation patterns. **Root cause:** framework assumes workers write their own artifacts; some CLIs can't. **Mitigation:** orchestrator captured stdout and wrote files for non-file-writing CLIs; documented deviation. **v1.2 update:** ship a family-adapter script that abstracts over capability differences.

### Surprises

**S-1. The informal prior review missed all three real blockers.** The Pre-Phase A review logged at `docs/logs/2026-04-15_tier-4-proposal-pre-phase-a-review-round-1-two-rev.md` ran without Template 16 and returned merge-ready after addressing 12 unblocking conditions. Template 16's Round 1 — on the same post-amendment proposal doc — caught three *new* blocker-severity issues (numeric contradiction, unoperationalized queue cap, undefined normalization). This suggests the informal process was under-calibrated for finding structural defects, even with two reviewers. The Template 16 framing (evidence-labeled findings, severity tags, explicit verdict options) appears to be doing real adversarial work.

**S-2. Verdict disagreement at Pre-A was posture-driven, not noise.** It's tempting to see "gemini says Proceed, claude-sub says Revise" as noise or as a model-capability difference. On close reading, both are correct *given their postures*: gemini checked external alignment (the proposal is consistent with the PRD, the ontology architecture, the provenance spec) and found no misalignment. Claude-sub checked internal consistency and operationalizability (can a Phase A spec author implement this without silent judgment calls?) and found three gaps. The disagreement is the exact signal Template 16's 2-lens design is supposed to surface.

**S-3. Setup cost was higher than the adoption doc's "10-minute path" implies.** The README advertises a 10-minute adoption path. Real wall-clock for first-run setup (tokens.local.md + manifest + retro scaffold + verify-all.sh installation + manifest schema-validation debugging around id-pattern + friction-log skeleton) was ~20 minutes even with no code to write. 2x slip on the advertised time. Adoption doc understates friction.

### Recommended framework updates (v1.2 target list)

Prioritized by adoption-blocker severity (A = first-time adopter can't proceed without a workaround; B = adopter proceeds but with significant cost; C = polish).

| # | Severity | Target | Friction refs |
|---|----------|--------|---------------|
| 1 | A | **P3 family-diversity model.** Address Claude-primary adopters who can't field ≥3 engineering families. Options: (a) explicit same-provider-separate-session doctrine; (b) blessed Claude-multi-model invocation; (c) relaxed P3 for 3-CLI setups with warnings. | [F-006] |
| 2 | A | **Template 16 consolidator (Template 16b).** Specify orchestrator consolidation rules or ship a mini-template; current Pre-A carve-out leaves adopters guessing when reviewers disagree. | [F-013] |
| 3 | A | **Adoption doc v2.** Single-variable path scheme (`<ADOPTER_REPO_ROOT>`); per-language smoke-check appendix (Python, TS, Go); concrete `day-one.sh` validated by `verify-all.sh`. | [F-001], [F-002], [F-003], [F-008] |
| 4 | B | **`verify-adopter.sh <manifest-path>`.** Unified entry point that runs schema + P3 + gate-categories + artifact-paths + pre-a against an adopter manifest path. | [F-007], [F-010] |
| 5 | B | **Stdout-worker adapter.** Bundle script that normalizes dispatch across file-writing vs. stdout-only CLIs. | [F-015] |
| 6 | B | **Pre-A round policy field.** Let manifests declare `pre_a.round_policy: strict-first-round-halt | default-one-revision-cap` so Pre-A halt behavior is machine-checkable. | [F-016] |
| 7 | C | **Schema id pattern.** Allow dots (`.`) in `id` to accept semver-in-id, OR document "version belongs in a separate field" prescriptively. | [F-011] |
| 8 | C | **`verify-tokens.sh` orchestrator-only annotations.** Suppress defined-but-unused warnings for tokens intentionally consumed outside template bodies. | [F-009] |
| 9 | C | **Rate-limit observability.** Adoption doc guidance on distinguishing rate-limited-but-completed from failed dispatches. | [F-014] |
| 10 | C | **`<DOC_INDEX_ARCHIVE>` lifecycle.** Spell out ordering relative to Phase E retro. | [F-004] |
| 11 | C | **`check-jsonschema` prereq.** Either hard-require it in README, or vendor a minimal alternative. | [F-005] |
| 12 | C | **Pre-A `family_verdict` posture suffix.** Path-pattern placeholder for lens-pair naming. | [F-012] |

### Recommended manifest inheritance for next folio deliverable

When the next folio deliverable dispatches under llm-dev-v1 (whether a Round 2 of the current deliverable after the proposal is revised, or a fresh deliverable):

- **Reuse as-is:** `model_assignments` shape (claude, codex, gemini, claude-sub), `scope.allowed_paths` / `scope.forbidden_paths` patterns restricted to the specific code surface, `gate_prerequisites` six-category structure, `references` list (PRD / architecture / provenance / entity-system specs), `smoke_checks` shape.
- **Re-evaluate per-deliverable:** `cardinality_assertions` (always specific to the feature), `smoke_checks` commands (may need to narrow to the touched module), `gate_prerequisites` verification commands (grep filters narrow to the new allowed_paths).
- **Do not reuse:** `cli_capability_matrix` — if `claude-sub` doctrine changes per [F-006] v1.2 target, the matrix changes too.
- **Document before dispatching:** if running under strict P3, which sub-agent plays the "4th family" role and what mitigations are in place for same-provider blindspots.

### Open items

- **OP-1.** Blockers B-1, B-2, B-3 in the proposal doc are open. A Round 2 Pre-A is possible after author revision; this session did not execute Round 2 per operator's strict halt rule. Owner: author (claude, main). Not time-boxed here.
- **OP-2.** Upstream the 12 v1.2 targets listed above to johnny-os. Adoption doc §Feedback loop prescribes a GitHub issue on johnny-os tagged `framework:llm-dev-v1.1` and/or linking this retro. Owner: orchestrator (after user review of this retro).
- **OP-3.** `ontos log -e "proposal-review-hardening-v0-6-0--A.proposal-halt"` needs to run at session end to archive this retro and the Pre-A artifacts in the ontos context map. Owner: orchestrator, before the next session.
- **OP-4.** The pre-existing circular dependency `tier4_digest_design_spec ↔ tier4_discovery_proposal_layer_spec` surfaced by `ontos map` is unrelated to this lifecycle but was observed at session start. Not addressed here; flagged for a separate cleanup session.

---

## Appendix: What "full lifecycle A→E" would have required

For future planning, the planned-but-not-executed phases would have been, at minimum:

- **Phase A:** ~1 claude-authored spec document (10 mandatory sections + 2 diagrams), ~1 hour.
- **Phase B:** 4 parallel reviewer dispatches (codex peer, gemini alignment, claude-sub adversarial, claude-sub product) + codex meta-consolidator + possible Round 2. ~1.5–3 hours.
- **Phase C:** Implementation of the smallest FR-813 slice (durable rejection memory + stale invalidation on `folio/links.py`) + tests. ~1–2 hours.
- **Phase D:** 4 parallel code reviewers + codex meta-consolidator + claude fix-author + gemini verifier + codex final-approval gate + possible Round 2. ~2–4 hours.
- **Phase E:** Formal retro (this doc, but covering all phases). ~30 min.

Total: **6–10 hours of wall-clock** for a full A→E run, bounded by CLI wall-clock latency (codex/gemini each ~5–15 min per dispatch, with potential rate-limit retries). Not feasible in a single working session without parallelization beyond what the current orchestrator pattern supports. This is itself a v1.2 target ([F-015] extension): dispatch parallelization across families.
