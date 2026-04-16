# LLM Development Framework — v1.2.0 (candidate)

A portable, project-agnostic meta-prompt framework for LLM-driven software development.
Drop this bundle into any repo, fill in the tokens in `tokens.md`, and you have a
working orchestration contract for cross-model LLM workers across a four-phase
development lifecycle (Spec → Spec Review → Implementation → Code Review),
with optional pre-A entry points (Proposal / Triage / Validation Run) and an
optional Product lens for user-facing deliverables.

> **Status note.** v1.1.1 released on `main` @ `4dfa01f`. v1.2.0 is a
> minor-release candidate under review on PR #TBD; merge SHA is `TBD`
> until the full 3-family canonical verdict reaches Approve. Adopters
> pulling today should anchor on v1.1.1 at `4dfa01f`; re-copy after
> v1.2.0 merges. Previous releases: v1.1.0 at `2ec49e7`, v1.0.0 at
> `1a1d9e5`. See `CHANGELOG.md` for the full release log.

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
- **`check-jsonschema` is required** (not optional). `scripts/verify-schema.sh`
  validates both example manifests against `manifest/deliverable-manifest.schema.yaml`
  using this tool. As of v1.1.1 the script fails hard (exit 1) if the tool is
  absent — silent-skip on missing dep was removed because it looked identical
  to a passing check.
- **The `infra-bootstrap` template is opt-in.** It parameterizes a
  control-plane host; fill its tokens only if you're standing one up.
- **The manifest generator is spec-only in v1.** Prompts are hand-
  composed from templates. See `manifest/generator-spec.md` and
  `ROADMAP.md` for the v2 implementation.

## Adopter onboarding (v1.2+)

This section replaces the v1.0 "10-minute adoption" checklist with a
durable flow: one variable to fill (`<adopter-repo-root>`), a bootstrap
script, per-language scope-lock starting points, and mechanical
preflights.

### 1. Drop the bundle into your repo

Copy `frameworks/llm-dev-v1/` into `<adopter-repo-root>/ops/llm-dev-v1/`
(or any path — the bundle is self-contained). Verbatim copy is the
recommended mode for your first deliverable. Subtree / submodule
alternatives live in the adoption handoff referenced by any
maintainer-authored project handoff.

### 2. Run the bootstrap

```bash
cd <adopter-repo-root>
bash ops/llm-dev-v1/examples/day-one.sh <deliverable-id>
```

`examples/day-one.sh` creates:
- `<MANIFEST_DIR>/<deliverable-id>.yaml` — manifest skeleton derived
  from `manifest/example-manifest.yaml` with `id` and `slug`
  substituted. Default `<MANIFEST_DIR>`: `<adopter-repo-root>/manifests/`
  (override via `MANIFEST_DIR` env var — convention is
  `frameworks/manifests/` for monorepos that host the bundle
  alongside manifests, `manifests/` for standalone adopter repos).
- `docs/trackers/<deliverable-id>.md` — empty tracker skeleton.
- `tokens.local.md` (alongside `tokens.md` inside the bundle copy) if
  absent — a starter fill file.

### 3. Fill `tokens.local.md`

Open `ops/llm-dev-v1/tokens.local.md` and populate at minimum:

- `<WORKSPACE>` — absolute path to `<adopter-repo-root>`.
- `<REPO_URL>`, `<DEFAULT_BRANCH>` — your VCS identity.
- `<CLI_CLAUDE?>` / `<CLI_CODEX?>` / `<CLI_CODEX_MODEL?>` /
  `<CLI_GEMINI?>` — your CLI invocations + the Codex model.
- `<TEST_COMMAND>` — your test runner (see per-language defaults
  below).
- `<MANIFEST_DIR>` — where your manifests live.

### 4. Preflight + verify-adopter

```bash
bash ops/llm-dev-v1/scripts/verify-tokens.sh --probe-codex-model <CLI_CODEX_MODEL>
bash ops/llm-dev-v1/scripts/verify-adopter.sh <MANIFEST_DIR>/<deliverable-id>.yaml
```

Both must pass before any worker dispatches. The Codex probe catches
the D3 FL#2 failure mode (model-access denied despite CLI working);
`verify-adopter` runs the four manifest-scoped conformance checks
(schema, P3, gate-categories, artifact-paths).

### 5. Dispatch

Follow the entry-point table in `playbook.md` (Proposal / Triage /
Validation / Phase 0). Workers use the templates under `templates/`.
Resume a halted session via `11-continuation-prompt.md`; run a
standalone review board via `03`/`04`/`05` + `06`.

### Per-language scope-lock starting points (v1.2+ appendix)

Scope-lock blocks (`scope.allowed_paths`, `scope.forbidden_paths`,
`scope.forbidden_symbols`) depend on your project's language. These
are starting points, not prescriptions.

**Python**
- `allowed_paths`: `src/<module>/`, `tests/test_<module>.py`.
- `forbidden_paths`: `migrations/`, `.github/`, secrets paths.
- `forbidden_symbols`: `requests.`, `httpx.`, `import asyncio` (for
  sync/offline modules); adjust per deliverable.
- `<TEST_COMMAND>`: `pytest -xvs`.

**TypeScript / Node.js**
- `allowed_paths`: `src/<feature>/`, `src/components/<feature>/`,
  `tests/<feature>.test.ts` (or `.spec.ts`).
- `forbidden_paths`: `node_modules/`, `.next/`, `dist/`, `build/`,
  `.github/`.
- `forbidden_symbols`: `any` (typed-out), `@ts-ignore`, raw `fetch(`
  if a project wrapper exists.
- `<TEST_COMMAND>`: `vitest run`, `jest --ci`, or `npm test`.

**Go**
- `allowed_paths`: `internal/<package>/`, `pkg/<package>/`, adjacent
  `*_test.go` files.
- `forbidden_paths`: `vendor/`, `.github/`.
- `forbidden_symbols`: `fmt.Println` (prefer a logger),
  `interface{}`, `time.Sleep` outside tests.
- `<TEST_COMMAND>`: `go test ./... -race`.

Other languages follow the same shape — source root + test path in
`allowed_paths`; generated code + dependency caches in
`forbidden_paths`; language anti-patterns in `forbidden_symbols`.
`verify-portability.sh` guarantees the bundle itself carries no
language-specific strings, so your scope-lock is adopter-local.

## Verification

The `scripts/` directory ships a conformance suite that the bundle
passes as-is. Run `bash scripts/verify-all.sh` after any change.

| Script                         | Checks                                                                                         |
|--------------------------------|------------------------------------------------------------------------------------------------|
| `verify-schema.sh`             | both example manifests (`example-manifest.yaml`, `example-user-facing-manifest.yaml`) validate against `manifest/deliverable-manifest.schema.yaml` |
| `verify-tokens.sh`             | every `<TOKEN>` used in templates is defined in `tokens.md`                                     |
| `verify-frontmatter.sh`        | each template's `required_tokens` + `optional_tokens` ⇔ body usage                             |
| `verify-p3.sh`                 | phases B.1 / D.2 / D.5 each have ≥3 distinct non-author families; user-facing manifests additionally assert Product role on B.1 / B.2 / D.2; v1.2+ manifests additionally require adversarial ≠ author provider (escape hatch: `gate_prerequisites` id prefix `G-xprov-adv-<phase>`) |
| `verify-pre-a.sh`              | (v1.1) if `pre_a` is declared, entry + artifact_path coherent and the matching `artifacts.*` path is declared |
| `verify-gate-categories.sh`    | `gate_prerequisites` covers the six required categories                                        |
| `verify-artifact-paths.sh`     | `canonical_verdict` / `family_verdict` / `verification` placeholder shapes valid                |
| `verify-portability.sh`        | no host-project strings in normative files                                                     |
| `verify-d6-gate.sh` (v1.2)     | parses a D.6 final-approval gate artifact and asserts every row is `PASSED` with an allowed evidence-class tag. Per-deliverable: `bash scripts/verify-d6-gate.sh <final-approval-path>`. `verify-all.sh` runs it against `examples/d6-gate-fixture.md` as a regression. |
| `verify-circuit-breaker.sh` (v1.2) | validates `review_rounds` schema and reports per-phase CB state (fires on ID overlap across rounds; quiescent on new IDs). Called by `verify-all.sh` on the two example manifests; adopters can invoke `bash scripts/verify-circuit-breaker.sh <manifest-path>` per-deliverable. |
| `verify-adopter.sh` (v1.2)     | unified adopter entrypoint. Runs schema / p3 / gate-categories / artifact-paths against a single adopter manifest path with `--manifest` flag. Per-deliverable: `bash scripts/verify-adopter.sh <manifest-path>`. |
| `verify-all.sh`                | runs all of the above; exit non-zero on any failure                                            |

## Adopter CI integration (v1.2+)

Adopters copying this bundle into their repo (or referencing it via
submodule / subtree) typically care about two different verification
surfaces:

- **The bundle itself.** Did the upstream copy land intact? `bash
  scripts/verify-all.sh` walks the bundle's own invariants (schema
  validity, token coverage, template frontmatter, portability, etc.)
  and the two bundled example manifests. Runs without args; exits
  non-zero on any gap. Appropriate in bundle-upgrade CI (when
  re-copying a new bundle version).
- **Your own manifest.** Does an adopter-authored deliverable manifest
  satisfy the framework's manifest-scoped invariants? `bash
  scripts/verify-adopter.sh <manifest-path>` runs the four
  manifest-scoped checks (schema, P3, gate-categories,
  artifact-paths) against a single adopter manifest path.
  Appropriate in per-deliverable CI.

Each of the four manifest-scoped scripts also accepts a
`--manifest <path>` flag if you want to invoke them individually. The
default (no flag) remains the bundle-maintainer behavior (validate
the two bundled examples) so existing `verify-all.sh` runs are
unchanged.

Example adopter CI pattern (GitHub Actions):

```yaml
- name: Validate adopter manifest
  run: bash ops/llm-dev-v1/scripts/verify-adopter.sh ops/manifests/my-deliverable.yaml
```

`verify-circuit-breaker.sh <manifest-path>` is runtime-state-aware
(reads `review_rounds`); invoke it post-round rather than in manifest
CI.

**Install dependencies**:

```bash
pipx install check-jsonschema
python3 -m pip install --user --break-system-packages pyyaml   # or use a venv
```

If a dependency is missing, individual scripts generally exit 2 and
`verify-all.sh` treats that as skipped (not failed) and prints which checks
were skipped so CI can catch the gap. **Exception (v1.1.1):**
`verify-schema.sh` now exits 1 (hard fail) when `check-jsonschema` is
absent — silent-skip on a missing validator was masking real schema
failures.

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
