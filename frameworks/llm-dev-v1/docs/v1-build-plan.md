# Plan: Portable LLM Development Framework (`frameworks/llm-dev-v1/`)

## Context

We have three maturing inputs:

1. `docs/reference/llm-development-playbook.md` — a v3.6 playbook codifying four-phase development (Spec → Spec Review → Implementation → Code Review), three-lens review board (Peer / Alignment / Adversarial), and artifact contracts. Heavy coupling to a generic `INTERNAL_DOCS_DIR` variable pattern but still implicitly johnny-os-shaped.
2. `docs/reference/d2-authority-matrix-orchestration-report.md` — concrete learnings from running that playbook end-to-end against the D2 Authority Matrix: what broke (hardcoded smoke assertions, Ontos CLI drift, tracker ownership edge cases, manual mechanical validation), what held (anti-collapse boundary, evidence-weighted consensus, no-fast-forward merges, two-tier family→canonical verdict structure), and 12 crystallized recommendations topped by "deliverable-suite generator."
3. `ops/` — six artifacts that already embody meta-prompt patterns: orchestrator master runbook, worker session contract template, a phase-specific handoff, a cross-model CLI workflow case study, an incident postmortem, and an infra bootstrap runbook.

We want to extract a **portable, johnny-os-agnostic meta-prompt framework** that any project (not just johnny-os) can adopt. The framework must be **meta-prompt-shaped**: the primary readers are an orchestrator LLM and worker LLMs, with every johnny-os-specific detail replaced by explicit substitution tokens. The v1 bundle will then be reviewed by the LLM review board before being declared stable.

## Recommended Approach

Build a **self-contained bundle** at `frameworks/llm-dev-v1/` with a doctrine document, a set of parameterized meta-prompt templates, a playbook explaining how an operator (human or LLM) wires them together, and a YAML deliverable-manifest spec that upgrades the framework from "copy templates" to "generate prompt suites" (D2 report's #1 recommendation).

### Target directory layout

```
frameworks/llm-dev-v1/
├── README.md                         # What this is, how to adopt it in 10 minutes
├── framework.md                      # Doctrine: principles, roles, phase state machine, evidence discipline
├── playbook.md                       # How to use: operator walkthrough, token substitution, wiring examples
├── CHANGELOG.md                      # v1.0.0 baseline
├── tokens.md                         # Canonical substitution token glossary (extends ops template's 13 tokens)
├── templates/
│   ├── 00-orchestrator-runbook.md    # Meta-prompt: orchestrator charter, state machine, CLI dispatch, gate validation
│   ├── 01-worker-session-contract.md # Meta-prompt: binding contract every worker inherits (identity, allowed writes, halt, commit, final report)
│   ├── 02-phase-dispatch-handoff.md  # Meta-prompt: phase-specific step-by-step dispatch for active orchestrator
│   ├── 03-review-board-peer.md       # Meta-prompt: Peer reviewer role, "is this good?" lens
│   ├── 04-review-board-alignment.md  # Meta-prompt: Alignment reviewer role, approved-docs lens
│   ├── 05-review-board-adversarial.md# Meta-prompt: Adversarial reviewer role, "how does this fail?" lens
│   ├── 06-meta-consolidator.md       # Meta-prompt: adjudicates family verdicts → canonical verdict; blocker-preservation rule
│   ├── 07-final-approval-gate.md     # Meta-prompt: structured yes/no prerequisite gate (the "D.6 not a vibe" pattern)
│   ├── 08-retrospective.md           # Meta-prompt: produce orchestration report after merge
│   ├── 09-incident-postmortem.md     # Meta-prompt: root-cause template (summary→environment→symptom→repro→narrowing→fix options→regression guard)
│   ├── 10-infra-bootstrap.md         # Meta-prompt: control-plane setup with fallback chains (parameterized from mac-mini-foundation)
│   └── 11-continuation-prompt.md     # Meta-prompt: resume-after-halt template (reuse branch, produce only missing/fixes)
├── manifest/
│   ├── deliverable-manifest.schema.yaml  # JSON-schema-style spec for the YAML manifest
│   ├── example-manifest.yaml             # Worked example (a made-up deliverable, not D2-specific)
│   └── generator-spec.md                 # Spec for how a manifest → emits a prompt suite, tracker rows, validation plan, branch map
└── examples/
    └── walkthrough-mini-deliverable.md   # End-to-end walkthrough: manifest → templates filled → dispatch → merge
```

### What each artifact contains

**`framework.md` (doctrine)**
- Four-phase skeleton (Spec / Spec Review / Implementation / Code Review) as a portable state machine with explicit entry and exit criteria
- Three-lens review board (Peer / Alignment / Adversarial) with the literal role-instruction quotes from the playbook
- **Evidence discipline** (from D2 report): every worker claim labeled `direct-run | orchestrator-preflight | static-inspection | not-run`
- **Anti-collapse boundary**: worker vs orchestrator role separation, embedded as a quotable stanza
- **Evidence-weighted consensus** rule: "a single-family blocker with file:line + reproduction overrides two approvals"
- **Generated-file conflict policy**: regenerate from target; halt on non-generated conflict
- **Model-diversity rule**: minimum two model families per review board
- Numbered principles (8–12) so templates can reference them by number

**Meta-prompt templates (`templates/NN-*.md`)**
- Each has: a frontmatter block (id, version, required tokens, depends-on), a SUBSTITUTION TOKENS section, a BEGIN/END meta-prompt body, a role-specific halt-conditions catalog, and a final-report schema
- Tokens use `<ANGLE_UPPER>` (e.g., `<WORKSPACE>`, `<BRANCH>`, `<DELIVERABLE_ID>`, `<CLI_CLAUDE>`, `<CLI_CODEX>`, `<SCOPE_LOCK_PATHS>`, `<ARTIFACT_OUTPUT_PATHS>`, `<NO_TOUCH_PATHS>`, `<SMOKE_CHECKS>`, `<DOC_INDEX_TOOL>`)
- No references to Ontos, johnny-os paths, or D-numbered phases. Generic phase names: A (Spec), B (Spec Review), C (Implementation), D (Code Review), optionally 0 (Scoping) and E (Retrospective).
- `01-worker-session-contract.md` is the portable heir of `phase-1-worker-session-contract-template.md`; keeps BEGIN/END markers for inline expansion
- `00-orchestrator-runbook.md` is the heir of `phase-1-orchestrator-runbook.md` with Ontos-specific commands replaced by `<DOC_INDEX_TOOL>` hooks and the D2-specific deliverable numbering stripped
- `06-meta-consolidator.md` and `07-final-approval-gate.md` are new explicit templates — the D2 report flagged both as implicit in the playbook and worth surfacing

**`manifest/` (generator spec, per D2 recommendation #1)**
- `deliverable-manifest.schema.yaml` — typed schema: `id`, `slug`, `scope_lock_paths`, `forbidden_paths`, `cardinality` (e.g., matrix dimensions), `artifact_outputs`, `regression_guards`, `model_assignments` (per phase), `cli_capability_matrix`, `smoke_checks`, `gate_prerequisites`
- `generator-spec.md` — narrative spec for what a generator must emit from a manifest: populated prompt suite (templates with tokens substituted), tracker row set, validation plan (shell commands, not prose), branch/worktree map, dispatch preambles per phase. Generator implementation is **out of scope for v1** — we ship the spec so a future pass (or another agent) can implement it.
- `example-manifest.yaml` — a made-up mini deliverable (e.g., "add a currency-converter module") so it's demonstrably portable

**`playbook.md` (operator walkthrough)**
- "10-minute adoption" path: clone framework/, fill `tokens.md`, pick templates, dispatch
- Wiring examples: when to use `02-phase-dispatch-handoff` vs jumping straight into `00-orchestrator-runbook`
- Failure-mode catalog (from D2 report): hardcoded smoke assertions, CLI drift, tracker ownership violations, generated-file conflicts — each with the framework remediation

### Critical source files to reuse (not re-author)

- `/Users/jonathanoh/johnny-os/docs/reference/llm-development-playbook.md` — role definitions, phase structure, literal role-instruction quotes (§9.3, §10.4), review verdict context header (§16.5). Lift verbatim where it's already portable; parameterize where it references `INTERNAL_DOCS_DIR` etc.
- `/Users/jonathanoh/johnny-os/docs/reference/d2-authority-matrix-orchestration-report.md` — source of evidence-labeling rules, anti-collapse stanza, blocker-preservation rule, canonical-artifact protection stanza, merge-safety rule, generated-file conflict policy, final approval gate structure. Every heuristic in its §3 maps to a framework doctrine numbered principle.
- `/Users/jonathanoh/johnny-os/ops/phase-1-orchestrator-runbook.md` — structural parent of `00-orchestrator-runbook.md`; strip Ontos/D-numbering.
- `/Users/jonathanoh/johnny-os/ops/phase-1-worker-session-contract-template.md` — structural parent of `01-worker-session-contract.md`; already token-parameterized; extend token glossary and strip johnny-os-specific halt conditions.
- `/Users/jonathanoh/johnny-os/ops/d2-phase-a-orchestrator-handoff.md` — exemplar for `02-phase-dispatch-handoff.md`; generalize D2/Phase-A specifics to `<DELIVERABLE_ID>/<PHASE_ID>`.
- `/Users/jonathanoh/johnny-os/ops/2026-04-13-claude-cli-cross-model-agentic-workflow.md` — source of cross-model dispatch patterns; distill "reusable review algorithm" section into `framework.md` doctrine.
- `/Users/jonathanoh/johnny-os/ops/2026-04-12-ontos-mcp-stream-misrouting.md` — structural parent of `09-incident-postmortem.md`.
- `/Users/jonathanoh/johnny-os/ops/mac-mini-foundation.md` — structural parent of `10-infra-bootstrap.md`; parameterize hardware/IP specifics.

### What we will NOT do in v1

- Implement the manifest-to-prompt-suite generator (only ship its spec). This is explicitly staged for v2; building it now would balloon scope.
- Touch `docs/reference/llm-development-playbook.md` itself — the framework is a **derivative/portable** artifact. The source playbook stays as the johnny-os-flavored parent.
- Register the framework with Ontos (it lives at top-level `frameworks/`, outside `docs/` and `ops/`, intentionally excluded from Ontos scan — it's a shippable sub-artifact).
- Add CLAUDE.md-style auto-activation hooks to the framework (keep it tool-agnostic).
- Create `LLM review board` review artifacts up-front — that's the next step after the user accepts the bundle.

### Build sequence when we exit plan mode

1. Create directory skeleton + empty `CHANGELOG.md` + `README.md` stub.
2. Draft `framework.md` (doctrine, numbered principles, state machine). This is the spine.
3. Draft `tokens.md` (extend the 13 tokens from the worker contract to a full glossary).
4. Draft templates in dependency order: `01-worker-session-contract` → `00-orchestrator-runbook` → `02-phase-dispatch-handoff` → `03/04/05-review-board-*` → `06-meta-consolidator` → `07-final-approval-gate` → `08-retrospective` → `09-incident-postmortem` → `10-infra-bootstrap` → `11-continuation-prompt`.
5. Draft `manifest/deliverable-manifest.schema.yaml`, then `example-manifest.yaml`, then `generator-spec.md`.
6. Draft `examples/walkthrough-mini-deliverable.md` — dogfoods the manifest + templates against a toy deliverable (e.g., "currency converter").
7. Draft `playbook.md` last — it references every prior artifact.
8. Final self-review pass: verify zero occurrences of `johnny-os`, `Ontos`, `D1`/`D2`/`D3`, or `phase-1` strings inside any template body (outside frontmatter "derived-from" provenance lines).

## Verification

- **Portability check**: `rg -l 'johnny-os|Ontos|ontos|phase-1|D1|D2|D3|mac mini' frameworks/llm-dev-v1/templates frameworks/llm-dev-v1/framework.md frameworks/llm-dev-v1/playbook.md` should return empty (matches in CHANGELOG/README "derived-from" provenance are OK).
- **Token completeness check**: every `<ANGLE_UPPER>` token appearing in any template must be defined in `tokens.md`. Do a diff: `rg -oh '<[A-Z_]+>' frameworks/llm-dev-v1/templates | sort -u` vs tokens defined in `tokens.md`.
- **Schema sanity**: `example-manifest.yaml` must validate against `deliverable-manifest.schema.yaml` (manual check sufficient for v1; formal validator optional).
- **Dogfood**: walk the `examples/walkthrough-mini-deliverable.md` mentally — from manifest to orchestrator prompt to worker contracts to meta-consolidator → final approval. If any step requires a template we didn't build, loop back.
- **Traceability**: every numbered principle in `framework.md` must cite either the source playbook section (e.g., `[playbook §9.3]`) or the D2 report heuristic (e.g., `[D2 report §3: blocker preservation]`) in an internal-only comment block. This lets the review board audit provenance without cluttering reader-facing prose.
- **Review board readiness**: after build, package a review dispatch prompt (Claude + Codex + Gemini, Peer/Alignment/Adversarial × 3 families × core artifacts) — but that's the next task, not this plan.

## Open items deferred to post-plan execution

- Exact token list (we'll grow it as we draft templates; start from the worker contract's 13 and extend).
- Whether `10-infra-bootstrap.md` stays in v1 or ships in a separate `frameworks/infra-v1/` bundle — decide during step 4; if it starts pulling too much hardware-specific content, split it.
- Version numbering convention for templates within the bundle (likely mirror bundle version: `llm-dev-v1` → all templates v1.x.x, CHANGELOG at bundle level).
