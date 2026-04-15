# LLM Development Framework — v1.1.0 (pending review board)

A portable, project-agnostic meta-prompt framework for LLM-driven software development.
Drop this bundle into any repo, fill in the tokens in `tokens.md`, and you have a
working orchestration contract for cross-model LLM workers across a four-phase
development lifecycle (Spec → Spec Review → Implementation → Code Review),
with optional pre-A entry points (Proposal / Triage / Validation Run) and an
optional Product lens for user-facing deliverables.

> **Status note.** v1.1.0 is scope-complete on branch
> `frameworks/llm-dev-v1.1` (PR #4) but still pending the canonical
> 3-family review board verdict. CHANGELOG status will flip to
> "Released" after the canonical verdict is `Approve`. Until then,
> adopters can use the v1.0.0 frozen baseline at commit
> `1a1d9e5` on `main`.

## What's in the bundle

| File / dir                              | What it is                                                                 |
|-----------------------------------------|----------------------------------------------------------------------------|
| `framework.md`                          | Doctrine: numbered principles, phase state machine, review board design    |
| `playbook.md`                           | Operator walkthrough: how to wire the templates together                   |
| `tokens.md`                             | Canonical `<ANGLE_UPPER>` substitution-token glossary                      |
| `templates/00-orchestrator-runbook.md`  | Meta-prompt for the orchestrator LLM session                               |
| `templates/01-worker-session-contract.md` | Canonical boilerplate every worker prompt inlines                        |
| `templates/02-phase-dispatch-handoff.md` | Phase-specific step-by-step dispatch instructions                         |
| `templates/03-review-board-peer.md`     | Peer reviewer meta-prompt ("is this good?")                                |
| `templates/04-review-board-alignment.md` | Alignment reviewer meta-prompt ("matches approved docs?")                 |
| `templates/05-review-board-adversarial.md` | Adversarial reviewer meta-prompt ("how does this fail?")                |
| `templates/06-meta-consolidator.md`     | Adjudicates family verdicts into a canonical verdict                       |
| `templates/07-final-approval-gate.md`   | Structured yes/no prerequisite gate before merge                           |
| `templates/08-retrospective.md`         | Post-merge orchestration report generator                                  |
| `templates/09-incident-postmortem.md`   | Root-cause investigation template                                          |
| `templates/10-infra-bootstrap.md`       | Control-plane setup meta-prompt with fallback chains                       |
| `templates/11-continuation-prompt.md`   | Resume-after-halt template                                                 |
| `templates/12-spec-author.md`           | Phase A spec author (10-section spec + two diagrams)                        |
| `templates/13-implementation-author.md` | Phase C implementation author                                               |
| `templates/14-fix-summary.md`           | Phase D.4 fix author (consumes D.3 canonical verdict)                       |
| `templates/15-verifier.md`              | Phase D.5 verifier (confirms each blocker addressed, no regression)         |
| `templates/16-proposal-review.md`       | Pre-A.proposal direction review (2-lens; playbook §13-aligned)              |
| `templates/17-triage.md`                | Pre-A.triage backlog categorization (3-lens; playbook §12-aligned)          |
| `templates/18-validation-run.md`        | Pre-A.validation observation protocol over deployed code (playbook §15.3 Validation/Observation Runs) |
| `templates/19-review-board-product.md`  | Product lens: "Is this the right thing to build/ship?" (user-facing only)   |
| `manifest/deliverable-manifest.schema.yaml` | Schema for a typed YAML manifest describing a deliverable (v1.1 adds optional `user_facing`, `pre_a`, `product_verdict`) |
| `manifest/example-manifest.yaml`        | v1.0.0-shape worked example (currency-converter; non-user-facing). Validates unchanged under v1.1 schema (backward-compat witness). |
| `manifest/example-user-facing-manifest.yaml` | v1.1-shape worked example (notification-preferences UI; `user_facing: true`, `pre_a` block, Product reviewer in B.1/B.2/D.2) |
| `manifest/generator-spec.md`            | Spec for a manifest→prompt-suite generator (implementation deferred to v2) |
| `examples/walkthrough-mini-deliverable.md` | End-to-end mental walkthrough — currency-converter (v1.0.0; non-user-facing path)            |
| `examples/walkthrough-user-facing.md`   | End-to-end mental walkthrough — notification-preferences (v1.1; user-facing path with pre-A.proposal + Product lens) |
| `CHANGELOG.md`                          | Version history                                                            |
| `ROADMAP.md`                            | Proposed trajectory for v1.x, v2, and speculative v3                       |
| `PROVENANCE.md`                         | Normative vs non-normative file inventory; downstream-adoption notes       |
| `LICENSE`                               | Apache License 2.0 (canonical text)                                        |
| `scripts/verify-*.sh`                   | Mechanical conformance suite (schema, tokens, frontmatter, P3, pre-A, portability) |

## Prerequisites (read before adopting)

- **≥4 model-family CLIs configured.** v1 requires one author family plus
  three distinct non-author families for every review board, with no
  degraded modes. A second variant of the same family (e.g., a smaller
  sibling model) counts as a distinct family so long as it is a separate
  CLI invocation.
- **Git + shell access** on the orchestrator host. Workers may have
  reduced capability (some families cannot execute shell); the
  orchestrator always does.
- **A YAML schema validator** for `manifest/example-manifest.yaml`
  (`check-jsonschema` works; see `scripts/verify-schema.sh`).
- **The `infra-bootstrap` template is opt-in.** It parameterizes a
  control-plane host; fill its tokens only if you're standing one up.
- **The manifest generator is spec-only in v1.** Prompts are hand-
  composed from templates. See `manifest/generator-spec.md` and
  `ROADMAP.md` for the v2 implementation.

## 10-minute adoption

1. Copy `frameworks/llm-dev-v1/` into your repo (or git-submodule it).
2. Open `tokens.md` and fill in the substitution values for your project
   (workspace path, branch convention, doc index tool, model CLIs, etc.).
3. Read `framework.md` end to end. It's short. It's the spine.
4. Pick your entry point in `playbook.md`:
   - New deliverable from scratch → write a manifest, then use
     `02-phase-dispatch-handoff.md`.
   - Resuming after an interruption → use `11-continuation-prompt.md`.
   - Running just a review board → use `03`/`04`/`05` + `06`.
5. Run `bash scripts/verify-all.sh` to confirm the bundle is internally
   consistent for your project's fill.
6. Dispatch.

## Verification

The `scripts/` directory ships a conformance suite that the bundle
passes as-is. Run `bash scripts/verify-all.sh` after any change.

| Script                         | Checks                                                                                         |
|--------------------------------|------------------------------------------------------------------------------------------------|
| `verify-schema.sh`             | both example manifests (`example-manifest.yaml`, `example-user-facing-manifest.yaml`) validate against `manifest/deliverable-manifest.schema.yaml` |
| `verify-tokens.sh`             | every `<TOKEN>` used in templates is defined in `tokens.md`                                     |
| `verify-frontmatter.sh`        | each template's `required_tokens` + `optional_tokens` ⇔ body usage                             |
| `verify-p3.sh`                 | phases B.1 / D.2 / D.5 each have ≥3 distinct non-author families; user-facing manifests additionally assert Product role on B.1 / B.2 / D.2 |
| `verify-pre-a.sh`              | (v1.1) if `pre_a` is declared, entry + artifact_path coherent and the matching `artifacts.*` path is declared |
| `verify-gate-categories.sh`    | `gate_prerequisites` covers the six required categories                                        |
| `verify-artifact-paths.sh`     | `canonical_verdict` / `family_verdict` / `verification` placeholder shapes valid                |
| `verify-portability.sh`        | no host-project strings in normative files                                                     |
| `verify-all.sh`                | runs all of the above; exit non-zero on any failure                                            |

**Install dependencies**:

```bash
pipx install check-jsonschema
python3 -m pip install --user --break-system-packages pyyaml   # or use a venv
```

If a dependency is missing the individual script exits 2; `verify-all.sh`
treats that as skipped (not failed) and prints which checks were
skipped so CI can catch the gap.

## Versioning

This bundle versions as a unit: `llm-dev-v1.MINOR.PATCH`. See `CHANGELOG.md`.
Breaking changes to template contracts bump the major (→ `llm-dev-v2/`).

## Provenance

Derived from an internal four-phase playbook and a post-mortem orchestration
report from a multi-model deliverable. Every numbered principle in
`framework.md` carries a provenance comment pointing back to its source.

## License

Apache License 2.0. See `LICENSE` at the bundle root for the full text.
Downstream adopters copying this bundle must retain `LICENSE` in the
downstream copy. Apache 2.0 is permissive, includes an explicit
patent grant, and is compatible with most commercial and open-source
licenses.

If your project uses a different license, Apache 2.0 §4 permits
redistribution and relicensing under its terms — include `LICENSE`,
preserve the copyright and NOTICE if/when one ships, and document any
modifications you make to the bundle. See `PROVENANCE.md` § License for
the framework-maintainer rationale.
