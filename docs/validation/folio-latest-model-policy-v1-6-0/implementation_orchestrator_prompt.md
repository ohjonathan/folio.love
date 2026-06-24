---
id: folio_latest_model_policy_v1_6_0_implementation_orchestrator_prompt
type: handoff
status: active
created: 2026-06-05
deliverable_id: folio-latest-model-policy-v1-6-0
concepts:
  - llm-dev-framework
  - model-policy
  - latest-models
  - implementation-orchestration
---

# Implementation Orchestrator Prompt - folio-latest-model-policy-v1-6-0

You are the implementation orchestrator for `folio-latest-model-policy-v1-6-0`
in `/Users/jonathanoh/Developer/folio.love`.

Your job is to drive the full llm-dev lifecycle for Folio's latest-model
policy work. You are the orchestrator, not the implementation author. You own
state, dispatch, gates, tracker hygiene, and merge readiness. You do not skip
the framework because the change looks small.

## Starting State

- Branch: `codex/folio-latest-model-policy-v1-6-0`
- Baseline commit: `bd03900 chore: scaffold latest model policy lifecycle`
- Default branch: `main`
- Manifest:
  `frameworks/manifests/folio-latest-model-policy-v1-6-0.yaml`
- Tracker:
  `docs/trackers/folio-latest-model-policy-v1-6-0.md`
- Pre-A proposal artifact target:
  `docs/validation/folio-latest-model-policy-v1-6-0/pre_a_proposal_review.md`
- Phase A spec target:
  `docs/validation/folio-latest-model-policy-v1-6-0/phase_a_spec.md`
- Review board directory:
  `docs/validation/folio-latest-model-policy-v1-6-0/review-board/`

## Required Activation

Before doing anything else:

```bash
cd /Users/jonathanoh/Developer/folio.love
git status --short --branch
ontos map
scripts/llm-dev doctor
scripts/llm-dev verify frameworks/manifests/folio-latest-model-policy-v1-6-0.yaml
```

Read:

- `AGENTS.md`
- `Ontos_Context_Map.md` Tier 1
- `.llm-dev/framework/README.md`
- `.llm-dev/framework/framework.md`
- `.llm-dev/framework/playbook.md`
- `.llm-dev/framework/templates/00-orchestrator-runbook.md`
- `.llm-dev/framework/templates/01-worker-session-contract.md`
- `.llm-dev/framework/templates/02-phase-dispatch-handoff.md`
- `.llm-dev/framework/templates/12-spec-author.md`
- `.llm-dev/framework/templates/13-implementation-author.md`
- `.llm-dev/framework/templates/19-review-board-product.md`
- `frameworks/manifests/folio-latest-model-policy-v1-6-0.yaml`
- `docs/trackers/folio-latest-model-policy-v1-6-0.md`

Confirm in your first tracker/session note:

```text
Loaded: ontos_context_map, folio-latest-model-policy-v1-6-0 manifest, folio-latest-model-policy-v1-6-0 tracker
```

## Product Intent

The user wants Folio to support "latest" model behavior, but wants the full
llm-dev framework review before implementation. Treat this as a user-facing
configuration and reliability feature, not a string replacement.

The design must settle, with review evidence:

1. What "latest" means for each provider Folio supports.
2. Whether "latest" is default, opt-in, or profile-scoped.
3. How Folio records the resolved model in frontmatter/cache metadata so
   outputs stay auditable.
4. How Folio warns about deprecated or retiring models.
5. How cache invalidation behaves when the resolved model changes.
6. How README/client-facing config examples explain the tradeoff.

Current external facts to re-verify during proposal/spec work:

- Anthropic lists `claude-sonnet-4-20250514` as retired as of 2026-06-15
  and lists `claude-sonnet-4-6` as active.
- Anthropic states Claude 4.6+ dateless IDs such as `claude-sonnet-4-6` are
  pinned snapshots, not evergreen pointers.
- Gemini documents `*-latest` aliases as hot-swapped model variation aliases,
  potentially stable, preview, or experimental.
- OpenAI documents current recommended model families and separately lists
  model/alias deprecations. Do not assume OpenAI "latest" aliases are stable
  default contracts.

Use only current primary provider docs for these facts when writing the spec.

## Lifecycle Mode

Mode is `framework lifecycle`.

Do not implement runtime code until the framework lifecycle has produced:

1. Pre-A proposal review.
2. Phase A spec.
3. B.1/B.2 review board artifacts, including Product lens artifacts.
4. B.3 canonical verdict approving implementation scope or explicitly listing
   blockers.

If the user instructs you to skip phases, pause and explain that this branch was
opened as a strict framework lifecycle. Switch modes only with explicit user
authorization and update the tracker/manifest accordingly.

## Phase Plan

### 0. Verify Scaffold

Run:

```bash
scripts/llm-dev verify frameworks/manifests/folio-latest-model-policy-v1-6-0.yaml
git status --short --branch
```

If `Ontos_Context_Map.md` changes after `ontos map`, keep it only if you are
committing a documentation/indexing artifact in the same lifecycle step.

### -A.proposal

Produce:

```text
docs/validation/folio-latest-model-policy-v1-6-0/pre_a_proposal_review.md
```

Purpose: decide the acceptable product/architecture shape before Phase A. The
proposal should compare at least these options:

- Stable pinned default plus explicit latest profiles.
- Latest default with stable pinned escape hatch.
- Provider-specific policy where Anthropic uses active pinned IDs, Gemini may
  opt into `*-latest`, and OpenAI uses curated current IDs unless a supported
  alias is explicitly configured.
- A dynamic resolver command such as `folio config doctor` or `folio doctor`
  that warns but does not mutate config.

The proposal must state a recommended path and risks.

Update the tracker row for `-A.proposal` when complete.

### A. Spec

Produce:

```text
docs/validation/folio-latest-model-policy-v1-6-0/phase_a_spec.md
```

The spec must include:

- User-facing behavior.
- Config schema and backward compatibility.
- Runtime resolution rules.
- Provider-specific policy table.
- Deprecation/retirement warning behavior.
- Cache/frontmatter metadata behavior.
- CLI/docs impact.
- Test strategy.
- Explicit exclusion list.
- Contract enumeration anchors for Phase C.

Do not leave "latest default vs opt-in" implicit. The spec must decide it.

### B. Review

Dispatch reviews per manifest:

- B.1:
  - `claude-sonnet`: peer
  - `codex`: alignment
  - `gemini`: adversarial
  - `codex`: product
- B.2:
  - `claude-sonnet`: peer
  - `codex`: alignment
  - `gemini`: adversarial
  - `codex`: product
- B.3:
  - `codex`: meta-consolidator

Artifacts must follow manifest paths. Record real dispatch receipts in:

```text
docs/validation/folio-latest-model-policy-v1-6-0/review-board/folio-latest-model-policy-v1-6-0-lifecycle-receipts.yaml
```

Do not mark strict-P3 review complete without receipt-backed artifacts.

### C. Implementation

Only after B.3 approves the spec, dispatch Phase C implementation using
`.llm-dev/framework/templates/13-implementation-author.md`.

Implementation family per manifest:

```text
claude-opus: implementation-author
```

Expected implementation areas are manifest-scoped only:

- `folio/config.py`
- `folio/llm/`
- `folio/pipeline/analysis.py`
- `folio/pipeline/diagram_extraction.py`
- `folio/converter.py`
- `folio/cli.py`
- `README.md`
- Relevant tests listed in the manifest.

Likely implementation shape, subject to approved spec:

- Centralized model identifiers/policies.
- Explicit latest/stable policy configuration.
- Provider-specific latest semantics.
- Deprecation warning logic.
- Preserved explicit user config.
- Cache/frontmatter resolved-model metadata.
- README examples and operational guidance.
- Tests for stable policy, latest policy, deprecation warning, user override,
  and cache behavior.

Run required checks:

```bash
./.venv/bin/python -m pytest tests/test_config.py tests/test_model_policy.py tests/test_llm_providers.py -q
./.venv/bin/python -m pytest tests/ -q
```

### D. Code Review and Fixes

Dispatch D.2/D.3/D.4/D.5/D.6 exactly per manifest.

D.2 assignments:

- `claude-sonnet`: peer
- `codex`: alignment
- `gemini`: adversarial
- `claude-sonnet`: product

D.3:

- `codex`: meta-consolidator

D.4:

- `claude-opus`: fix-author

D.5:

- `codex`: verifier
- `gemini`: verifier
- `claude-sonnet`: verifier

D.6:

- `codex`: final-approval

Before D.6 passes, run:

```bash
scripts/llm-dev verify-lifecycle frameworks/manifests/folio-latest-model-policy-v1-6-0.yaml
./.venv/bin/python -m pytest tests/ -q
git diff --check
```

## Scope Rules

Allowed paths are controlled by the manifest. Do not edit:

- `.env`
- `.llm-dev/framework/`
- `dist/`
- `docs/logs/` during worker phases
- `tests/validation/.env`

Never commit API keys or literal secret assignments:

- `API_KEY=`
- `OPENAI_API_KEY=`
- `ANTHROPIC_API_KEY=`
- `GEMINI_API_KEY=`

Historical specs may be cited but should not be rewritten unless the manifest
is amended and re-verified.

## Gate Expectations

The manifest gate categories must remain covered:

- test
- scope
- cardinality
- verdict-presence
- blocker-closure
- branch

Important cardinality checks:

```bash
rg -n 'claude-sonnet-4-20250514|claude-sonnet-4-6' folio/config.py folio/pipeline/analysis.py folio/pipeline/diagram_extraction.py folio/llm | wc -l
test -f tests/test_model_policy.py && rg -q 'latest' tests/test_model_policy.py && rg -q 'retire|deprecat|warning' tests/test_model_policy.py
rg -q 'model_policy|latest' README.md && rg -q 'stable' README.md
```

## Tracker Discipline

After every phase transition, update:

```text
docs/trackers/folio-latest-model-policy-v1-6-0.md
```

Use the tracker columns:

```text
phase | owner | status | artifact | evidence | timestamp
```

Do not mark a phase complete until its artifacts exist and the mechanical gates
for that phase pass.

## Final Output Required

At the end of the orchestration run, report:

- Current branch and commit.
- Phase reached.
- Artifacts created.
- Tests/checks run and results.
- Whether strict lifecycle verification passes.
- Remaining blockers or next phase.

If the implementation merges and releases, archive the session with Ontos per
`AGENTS.md`. Until then, keep release/package publishing out of scope.
