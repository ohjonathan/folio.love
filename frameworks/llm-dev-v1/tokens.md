---
id: tokens
version: 1.0.0
role: glossary
---

# Substitution Token Glossary

Every template in `templates/` uses `<ANGLE_UPPER>` placeholders that an
operator (or the manifest generator) substitutes before dispatch. This
glossary is the canonical list. If a template references a token not listed
here, the template is invalid and must be amended.

Operators fill in a project-local copy of this file and commit it alongside
the framework bundle.

## Grammar (normative)

The token system is mechanically resolvable. A substitution pass must leave
zero `<ANGLE_UPPER>` strings in the dispatched prompt, except for
template-local schema placeholders explicitly reserved (currently only
`<FINAL_REPORT_SCHEMA>`).

### Syntactic forms

| Form            | Meaning                                                   | Resolution                                 |
|-----------------|-----------------------------------------------------------|--------------------------------------------|
| `<TOKEN>`       | **Required** scalar. Substitution with empty or undefined value is an error. | Substituted with the scalar from the fill. |
| `<TOKEN?>`      | **Optional** scalar. Renders empty string if undefined; templates must tolerate empty. | Substituted with the scalar or empty.      |
| `<TOKEN[]>`     | **List** token. Rendered as a newline-joined block inside a fenced code block or bullet list — never inline in a markdown table cell. | Substituted with the list elements; orchestrator wraps in `` ``` `` or prefixes with `- ` per template. |
| `<TOKEN:LIST>`  | Deprecated. Legacy spelling of `<TOKEN[]>`. Tokens currently spelled this way (see categories below) are valid but new templates use `[]`. | Equivalent to `<TOKEN[]>`. |
| `{{#if TOKEN}}…{{/if}}` | Conditional block. The body renders only if `TOKEN` is defined and non-empty. Used when an optional token appears inline in prose. | Orchestrator/generator removes the block or emits the body. |
| `{{#unless TOKEN}}…{{/unless}}` | Inverse conditional. Body renders only when `TOKEN` is undefined or empty. | Orchestrator/generator emits the body or removes it. |

### Multiline and list rendering

- Lists never render inline inside markdown tables. Templates that need a
  list token in a tabular context place the list in a fenced block
  immediately after the table, with a marker row.
- Multiline scalars (e.g., `<SMOKE_CHECKS[]>`) render with each element
  on its own line, indented to the context. The template dictates
  whether a bullet prefix is added.
- A list token that is empty renders as "(none)" inside a fenced block,
  not as blank.

### Forbidden patterns

- **Computed pseudo-tokens** (e.g., `<PHASE_ID+1>`). The orchestrator or
  generator must pre-compute and pass as a normal optional scalar
  (e.g., `<NEXT_PHASE_ID?>`). No arithmetic, no string concatenation, no
  slicing inside a token reference.
- **Nested tokens.** A token's value must not itself contain unresolved
  `<ANGLE_UPPER>` references. Nested references are a substitution
  failure.
- **Tokens inside code fences.** Fenced code blocks are substituted the
  same as prose; authors must not use `<ANGLE_UPPER>` to mean a literal
  placeholder in example code — escape with backticks or use a different
  placeholder notation (e.g., `{{placeholder}}`).

### Frontmatter coverage invariant

Every `<ANGLE_UPPER>` referenced in a template's body must appear in the
template's frontmatter `required_tokens` or `optional_tokens` list (or be
the allowed `<FINAL_REPORT_SCHEMA>` placeholder). Every entry in
`required_tokens`/`optional_tokens` must be referenced at least once in
the body. `scripts/verify-frontmatter.sh` enforces this mechanically.

## Notation (legacy shorthand used in category tables below)

- `<TOKEN>` — simple scalar substitution
- `<TOKEN:LIST>` — list (equivalent to `<TOKEN[]>` in the grammar above)
- `<TOKEN?>` — optional; templates must handle absence gracefully

---

## Category 1 — Workspace & VCS

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<WORKSPACE>` | Absolute path to the repo root on the orchestrator host | `/home/me/myrepo` |
| `<REPO_URL>` | Canonical git remote URL | `git@github.com:me/myrepo.git` |
| `<DEFAULT_BRANCH>` | Branch merges target | `main` |
| `<BRANCH_CONVENTION>` | Pattern for worker branches | `feat/<DELIVERABLE_ID>-<role>` |
| `<WORKTREE_ROOT>` | Directory where per-deliverable worktrees live | `/tmp/myrepo-worktrees` |
| `<PR_TOOL>` | CLI or API name for PR creation | `gh` |

## Category 2 — Identity & scope

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<DELIVERABLE_ID>` | Short unique id for the deliverable | `currency-converter` |
| `<DELIVERABLE_SLUG>` | Filesystem-safe slug | `currency-converter` |
| `<PHASE_ID>` | Phase letter (0,A,B,C,D,E) optionally with sub-step | `D.2` |
| `<NEXT_PHASE_ID?>` | Next phase identifier, pre-computed by the orchestrator | `D.3` |
| `<ROLE>` | Worker role label | `peer`, `alignment`, `adversarial`, `author`, `verifier`, `meta-consolidator`, `final-approval`, `retro` |
| `<FAMILY>` | Model family label | `claude`, `codex`, `gemini` |
| `<SCOPE_LOCK_PATHS:LIST>` | Paths the worker may touch | `src/currency/, tests/test_currency.py` |
| `<NO_TOUCH_PATHS:LIST>` | Paths the worker must not touch | `src/auth/, migrations/` |
| `<FORBIDDEN_SYMBOLS:LIST?>` | Strings that must not appear in the artifact | `pydantic, sqlite` |
| `<CARDINALITY_ASSERTIONS:LIST?>` | Runnable assertions (command + expected value) | `len(MATRIX) == 64` |

## Category 3 — Artifact locations

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<SPEC_DIR>` | Where specs live | `docs/specs/` |
| `<REVIEWS_DIR>` | Where review verdicts live | `docs/reviews/` |
| `<RETRO_DIR>` | Where retrospectives live | `docs/retros/` |
| `<INCIDENTS_DIR>` | Where postmortems live | `docs/incidents/` |
| `<LOGS_DIR>` | Where session logs live | `docs/logs/` |
| `<ARTIFACT_OUTPUT_PATHS:LIST>` | Exact output paths allowed for the current worker | `docs/reviews/currency-converter-D-claude-peer.md` |

## Category 4 — Tooling

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<DOC_INDEX_TOOL?>` | Project-specific documentation indexer | `ontos`, `docindex`, or empty |
| `<DOC_INDEX_ACTIVATION?>` | Command to run at worker start to load context | `ontos map` |
| `<DOC_INDEX_ARCHIVE?>` | Command to run at worker end to archive session. For Phase E retrospectives, runs as the final step **after** the retro is committed — see `templates/08-retrospective.md`. | `ontos log -e "<DELIVERABLE_SLUG>"` |
| `<CLI_CLAUDE?>` | CLI invocation for Claude worker | `claude --print --model claude-opus-4-6` |
| `<CLI_CODEX?>` | CLI invocation for Codex worker | `codex --no-interactive` |
| `<CLI_GEMINI?>` | CLI invocation for Gemini worker | `gemini --headless` |
| `<TEST_COMMAND>` | Full test suite command | `pytest -xvs` |
| `<SMOKE_CHECKS:LIST>` | Per-phase fast checks (name + command) | `import: python -c "import currency"` |
| `<STATIC_CHECKS:LIST?>` | Linters, typecheckers | `ruff check`, `mypy .` |

## Category 5 — Tracker & gates

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<TRACKER_PATH>` | Location of the phase-state tracker | `docs/trackers/currency-converter.md` |
| `<TRACKER_ROW_SCHEMA:LIST>` | Column names of the tracker | `phase, owner, status, artifact, evidence` |
| `<GATE_PREREQUISITES:LIST>` | Yes/no items for the final-approval gate | `full test suite passes; no spec deviations; scope lock intact` |

## Category 6 — Review board composition

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<REVIEW_BOARD_FAMILIES:LIST>` | Families participating in review | `claude, codex, gemini` |
| `<MODEL_ASSIGNMENTS:LIST>` | Family → role map for the current phase | `claude=peer, codex=alignment, gemini=adversarial` |
| `<META_CONSOLIDATOR_FAMILY>` | Family that consolidates the phase | `codex` |
| `<AUTHOR_FAMILY>` | Family that authored the artifact being reviewed (excluded from review of its own artifact) | `claude` |
| `<USER_FACING?>` | Whether the deliverable touches a user-facing surface (drives the Product lens requirement on B.1/B.2/D.2 per the v1.1 P3 extension). Default `false` matches v1.0.0 behavior. | `true`, `false` |
| `<PRODUCT_VERDICT_PATH?>` | Path to the Product-lens verdict, read by `06-meta-consolidator.md` when `<USER_FACING>` is true. Single path (one Product reviewer per phase). | `docs/reviews/billing-B.1-codex-product.md` |

## Category 7 — Commit & reporting

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<COMMIT_PREFIX>` | Prefix for commit messages | `feat(currency):` |
| `<PR_TITLE_PATTERN>` | Pattern for PR titles | `<DELIVERABLE_ID>: <PHASE_ID> — <short>` |
| `<HALT_REPORT_PATH>` | Where a halting worker writes its halt report | `docs/logs/<DATE>-<DELIVERABLE_ID>-<PHASE_ID>-halt.md` |
| `<FINAL_REPORT_SCHEMA>` | Schema the worker must match in its final report (defined per template) | (template-local) |
| `<DATE>` | Current date, ISO 8601 | `2026-04-15` |

## Category 8 — Review-board specific

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<AUTHOR_RISK_LEVEL?>` | Author-declared risk rating on the artifact being adversarially reviewed | `low`, `medium`, `high` |

## Category 9 — Incident postmortem

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<INCIDENT_DATE?>` | ISO date of the incident | `2026-04-12` |
| `<INCIDENT_SLUG?>` | Short slug for the incident | `api-timeout-cascade` |

## Category 12 — Dispatch preamble runtime facts

Used by `templates/02-phase-dispatch-handoff.md`. All optional; render
empty when the orchestrator has nothing to inject.

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<CLI_DRIFT_NOTES?>` | Live differences between documented CLI and observed CLI | `tool health → tool doctor` |
| `<PREFLIGHT_EVIDENCE?>` | Tracker rows the orchestrator already filled before dispatch | `G4=pass direct-run 2026-04-15T…` |
| `<RUN_ORDER_NOTES?>` | Phase-specific order or sequence hints | `Peer first, then Alignment, then Adversarial` |
| `<ARTIFACT_UNDER_REVIEW?>` | Path to the artifact the worker is reviewing or implementing against | `docs/specs/currency-converter-spec.md` |
| `<HALT_CATALOG_BLOCK>` | Inlined role-specific halt-catalog entry from `01-worker-session-contract.md` | (multiline block) |

## Category 11 — End-to-end authoring (templates 12–15)

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<SPEC_REFERENCE_PATH>` | Path to the approved spec the implementation author reads | `docs/specs/currency-converter-spec.md` |
| `<CANONICAL_VERDICT_PATH>` | Path to the canonical D.3 (or B.3) verdict | `docs/reviews/currency-converter-D.3-verdict.md` |
| `<FIX_SUMMARY_PATH>` | Path to the D.4 fix summary | `docs/reviews/currency-converter-D.4-fix-summary.md` |
| `<REFERENCE_DOCS?>` | Approved architecture / roadmap / strategy docs the spec author must consult | `docs/architecture.md, docs/roadmap.md` |
| `<SPEC_RISK_LEVEL?>` | Author-declared risk rating on the spec | `low`, `medium`, `high` |

## Category 10 — Infra bootstrap

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<CONTROL_PLANE_HOST?>` | Hostname of the orchestrator host | `mac-mini-1.local` |
| `<CONTROL_PLANE_OS?>` | OS name and version | `macOS 15.x` |
| `<SESSION_TOOL?>` | Terminal multiplexer / supervisor | `tmux`, `screen`, `systemd-run` |
| `<REMOTE_ACCESS_TOOL?>` | Remote access mesh / tunnel | `Tailscale`, `Wireguard`, direct SSH |
| `<POWER_RESILIENCE_TOOL?>` | UPS or smart-plug integration | `apcupsd`, `Shelly`, `Tasmota` |
| `<PACKAGE_MANIFEST?>` | Package bootstrap manifest | `Brewfile`, `apt-packages.txt`, `requirements.txt` |
| `<FAMILY_CLI_MAP?>` | YAML fragment mapping family → CLI invocation + capabilities. Used by `templates/10-infra-bootstrap.md` to avoid hardcoding specific model families. | (multiline YAML; see template 10 for example shape) |

## Orchestrator-only tokens (v1.1.1)

The tokens listed below are intentionally consumed **outside template bodies**
— they are read by the manifest generator, the orchestrator runbook, or
CHANGELOG/PR tooling rather than by worker-session templates. They are
legitimate definitions, but `scripts/verify-tokens.sh` will not find
corresponding `<ANGLE_UPPER>` references inside `templates/`, `framework.md`,
`playbook.md`, or `generator-spec.md`.

`verify-tokens.sh` reads this section at runtime and suppresses the
"defined but not referenced" warning for any token listed here.

Orchestrator-only tokens:

- `<DELIVERABLE_SLUG>` — filesystem-safe slug consumed by artifact-path
  construction in the orchestrator.
- `<META_CONSOLIDATOR_FAMILY>` — manifest-level role assignment read by the
  dispatch layer when selecting the B.3 / D.3 consolidator.
- `<MODEL_ASSIGNMENTS>` — manifest-level family → role map consumed by the
  orchestrator to construct each phase's launch prompt.
- `<PR_TITLE_PATTERN>` — PR-creation convention string; the orchestrator
  interpolates it when opening the merge request.
- `<REPO_URL>` — manifest-level VCS identity used by the orchestrator for
  clone / remote-tracking operations.
- `<STATIC_CHECKS>` — manifest-level linter/typechecker list; the
  orchestrator pipes it into its pre-merge smoke script.

If you add a new orchestrator-only token, append it to this list so
`verify-tokens.sh` keeps the unused-warning quiet without manual suppression.

## Category 13 — Pre-A variants (v1.1)

Used by templates `16-proposal-review.md`, `17-triage.md`, and
`18-validation-run.md` for the optional pre-Phase-A entry points.

| Token | Meaning | Example fill |
|-------|---------|--------------|
| `<PROPOSAL_DOC_PATH>` | Path to the proposal document under Pre-A.proposal review | `docs/proposals/new-billing-tier.md` |
| `<TRIAGE_INPUT_PATH>` | Path to the findings input (bug reports / audit output / backlog dump) for Pre-A.triage | `docs/triage/2026-04-q2-audit-findings.md` |
| `<VALIDATION_RUN_INPUT_PATH>` | Path to the run-input spec (what to observe, which target, expected measurements) for Pre-A.validation | `docs/runs/2026-04-load-test-plan.md` |
| `<VALIDATION_RUN_BUDGET?>` | Budget envelope for the validation run (wall-clock, API spend, sample size) | `60m wall-clock; $5 API spend; 1000 requests` |

---

## How to fill this in

1. Copy this file to `tokens.local.md` (git-ignored if you want).
2. Replace the "Example fill" values with your project's actual values.
3. When dispatching a worker, substitute every `<TOKEN>` reference in the chosen
   template with the value from your fill. The manifest generator (v2) will do
   this mechanically; v1 does it by hand.
4. A substitution pass must leave zero `<ANGLE_UPPER>` strings remaining in the
   dispatched prompt, excepting `<FINAL_REPORT_SCHEMA>` and other template-local
   placeholders explicitly marked in the template.
