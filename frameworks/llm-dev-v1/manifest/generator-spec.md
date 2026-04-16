---
id: generator-spec
version: 1.0.0
role: specification
status: draft (v1: spec only; implementation deferred to v2)
---

# Deliverable-Manifest Generator — Specification

The generator consumes a deliverable manifest (YAML, validated against
`deliverable-manifest.schema.yaml`) and emits a complete orchestration-run
package: populated prompt suite, tracker rows, validation plan, branch map,
and dispatch preambles per phase. It eliminates prompt hand-cloning (P12)
and the resulting drift (hardcoded smoke assertions, stale identifiers).

**v1 ships the spec only.** No implementation. A future pass (or another
agent) implements a generator that conforms to this spec.

---

## Inputs

1. A manifest file: `deliverable-manifest.yaml` (validated against the
   schema).
2. A bundle root: path to `frameworks/llm-dev-v1/`.
3. A project-local token fill: `tokens.local.md` (or equivalent YAML).
4. An output directory.

## Outputs

The generator creates, under the output directory:

```
<out>/
├── prompts/
│   # v1.0 main-line dispatches
│   ├── phase-A-author-<family>.md           # full dispatch, tokens substituted
│   ├── phase-B.1-peer-<family>.md
│   ├── phase-B.1-alignment-<family>.md
│   ├── phase-B.1-adversarial-<family>.md
│   ├── phase-B.2-peer-<family>.md           # emitted only when B.2 is in model_assignments
│   ├── phase-B.2-alignment-<family>.md      # emitted only when B.2 is in model_assignments
│   ├── phase-B.2-adversarial-<family>.md    # emitted only when B.2 is in model_assignments
│   ├── phase-B.3-consolidate-<family>.md
│   ├── phase-C-author-<family>.md
│   ├── phase-D.2-peer-<family>.md
│   ├── phase-D.2-alignment-<family>.md
│   ├── phase-D.2-adversarial-<family>.md
│   ├── phase-D.3-consolidate-<family>.md
│   ├── phase-D.4-author-<family>.md
│   ├── phase-D.5-verifier-<family>.md       # one per verifying family
│   ├── phase-D.6-final-approval.md
│   ├── phase-E-retro.md
│   # v1.1 pre-A entry-point dispatches (emitted only when manifest declares pre_a)
│   ├── phase--A.proposal-proposal-reviewer-<family>.md       # template 16; pre_a.entry == "proposal"
│   ├── phase--A.triage-triage-author-<family>.md             # template 17; pre_a.entry == "triage"
│   ├── phase--A.validation-validation-run-author-<family>.md # template 18; pre_a.entry == "validation"
│   # v1.1 user-facing Product-lens dispatches (emitted only when user_facing: true)
│   ├── phase-B.1-product-<family>.md        # template 19; separate session per P10
│   ├── phase-B.2-product-<family>.md        # template 19; only when B.2 has a product role
│   └── phase-D.2-product-<family>.md        # template 19
├── tracker.md                                # initial tracker with rows keyed per phase
├── branch-map.md                             # branch + worktree plan per phase/role
├── validation-plan.sh                        # executable; one function per gate
├── dispatch-index.md                         # order and dependencies between prompts
└── manifest.resolved.yaml                    # manifest with tokens resolved, checked in for provenance
```

Each `prompts/*.md` is a dispatchable prompt: the relevant wrapping
template (`03`–`19` per the role-to-template picker in
`02-phase-dispatch-handoff.md` § "Read before acting" item 3) composed
with `02-phase-dispatch-handoff.md` and `01-worker-session-contract.md`,
with every token substituted from the manifest and the project-local
fill. A substitution pass must leave zero `<ANGLE_UPPER>` strings
remaining in a prompt, except `<FINAL_REPORT_SCHEMA>`.

---

## Substitution algorithm

1. Load manifest; validate against schema. Abort on schema error with a
   human-readable diagnostic pointing to the offending path + expected type.
2. Load token fill (project-local).
3. Build a token-resolution map:
   - Scalars from the token fill.
   - Derived tokens from the manifest (e.g., `<SCOPE_LOCK_PATHS[]>` ←
     `scope.allowed_paths`).
   - Per-phase, per-role, per-family tokens:
     - For family reviewers (roles peer / alignment / adversarial /
       verifier): `<ARTIFACT_OUTPUT_PATHS>` ← `artifacts.family_verdict`
       with `<phase>`, `<family>`, `<role>` filled.
     - For the meta-consolidator: `<ARTIFACT_OUTPUT_PATHS>` ←
       `artifacts.canonical_verdict` with `<phase>` filled (no
       `<family>` or `<role>` placeholders — enforced by invariant 10).
     - For D.5 verifiers: `<ARTIFACT_OUTPUT_PATHS>` ←
       `artifacts.verification` with `<family>` filled.
     - For the fix author (phase D.4): `<ARTIFACT_OUTPUT_PATHS>` ←
       `artifacts.fix_summary` (no placeholders).
     - **v1.1 — for the Product reviewer (role `product`, phases B.1 /
       B.2 / D.2 when `user_facing: true`):** `<ARTIFACT_OUTPUT_PATHS>`
       ← `artifacts.product_verdict` with `<phase>` and `<family>`
       filled (no `<role>` placeholder — enforced by
       `verify-artifact-paths.sh`). Token `<USER_FACING>` is set to
       `true`; `<PRODUCT_VERDICT_PATH>` is set to the resolved path
       for the meta-consolidator's 4-row intake (template 06).
     - **v1.1 — for the Proposal Reviewer (role `proposal-reviewer`,
       phase `-A.proposal`):** `<ARTIFACT_OUTPUT_PATHS>` ←
       `artifacts.proposal_verdict` (no placeholders;
       `pre_a.artifact_path` MUST equal this string per invariant 16
       coherence check). `<PROPOSAL_DOC_PATH>` is set from the
       upstream input (typically a `docs/proposals/<id>.md` path
       declared by the human operator).
     - **v1.1 — for the Triage Author (role `triage-author`, phase
       `-A.triage`):** `<ARTIFACT_OUTPUT_PATHS>` ←
       `artifacts.triage_report` (no placeholders;
       `pre_a.artifact_path` MUST equal this string).
       `<TRIAGE_INPUT_PATH>` is set from the upstream input (findings
       list path).
     - **v1.1 — for the Validation-Run Author (role
       `validation-run-author`, phase `-A.validation`):**
       `<ARTIFACT_OUTPUT_PATHS>` ← `artifacts.validation_run_report`
       (no placeholders; `pre_a.artifact_path` MUST equal this
       string). `<VALIDATION_RUN_INPUT_PATH>` and
       `<VALIDATION_RUN_BUDGET?>` are set from the upstream
       run-input spec.
4. For each entry in `model_assignments`:
   a. Pick the wrapping template per role:

      | Role label                 | Wrapping template                  |
      |----------------------------|------------------------------------|
      | `spec-author`              | `12-spec-author.md`                |
      | `implementation-author`    | `13-implementation-author.md`      |
      | `peer`                     | `03-review-board-peer.md`          |
      | `alignment`                | `04-review-board-alignment.md`     |
      | `adversarial`              | `05-review-board-adversarial.md`   |
      | `meta-consolidator`        | `06-meta-consolidator.md`          |
      | `fix-author`               | `14-fix-summary.md`                |
      | `verifier`                 | `15-verifier.md`                   |
      | `final-approval`           | `07-final-approval-gate.md`        |
      | `retro`                    | `08-retrospective.md`              |
      | `investigator`             | `09-incident-postmortem.md`        |
      | `infra-bootstrap`          | `10-infra-bootstrap.md`            |
      | `proposal-reviewer` (v1.1) | `16-proposal-review.md`            |
      | `triage-author` (v1.1)     | `17-triage.md`                     |
      | `validation-run-author` (v1.1) | `18-validation-run.md`         |
      | `product` (v1.1)           | `19-review-board-product.md`       |

   b. Inline `01-worker-session-contract.md` into `02-phase-dispatch-handoff.md`.
   c. Append the wrapping template's body.
   d. Substitute tokens.
   e. Emit.
5. Enforce P3 (model diversity): fail if the same family holds two roles in
   one phase, or if the author family is also a reviewer in the same phase.
6. Assemble the tracker: one row per dispatched prompt, plus orchestrator
   rows for gate runs.
7. Assemble the branch map per `branch_map` plus defaults.
8. Emit `validation-plan.sh`: one shell function per `gate_prerequisites`
   item, sourced by the orchestrator at phase-close time.

---

## Invariants the generator enforces

| #  | Invariant                                                                                              | Failure action                      | Enforced by |
|----|--------------------------------------------------------------------------------------------------------|-------------------------------------|-------------|
|  1 | Manifest validates against schema                                                                       | abort                                | `scripts/verify-schema.sh` |
|  2 | Every required token is defined in the fill                                                             | abort with missing-token list        | generator + `scripts/verify-tokens.sh` |
|  3 | No orphan tokens remain after substitution                                                              | abort with orphan-token list         | generator + `scripts/verify-tokens.sh` |
|  4 | Strict P3: phases `B.1`, `B.2` (when declared in `model_assignments`), `D.2`, `D.5` have ≥3 distinct non-author families | abort with conflict report           | `scripts/verify-p3.sh` |
|  5 | Author family does not hold any reviewer role on the same artifact in the same phase                   | abort                                | `scripts/verify-p3.sh` |
|  6 | `gate_prerequisites` covers ≥1 item in each of the six categories (test, scope, cardinality, verdict-presence, blocker-closure, branch) | abort | `scripts/verify-gate-categories.sh` |
|  7 | `cli_capability_matrix` has an entry for every family used in `model_assignments`                       | abort                                | generator |
|  8 | `scope.cardinality_assertions` and `smoke_checks.*.expect` conform to the expectation grammar            | abort                                | generator + `scripts/verify-schema.sh` |
|  9 | Every artifact output path is inside the project                                                        | abort                                | generator |
| 10 | `artifacts.canonical_verdict` contains `<phase>` and does NOT contain `<family>` or `<role>`             | abort                                | `scripts/verify-artifact-paths.sh` |
| 11 | `artifacts.family_verdict` contains `<phase>`, `<family>`, AND `<role>`; `artifacts.verification` contains `<family>` | abort                | `scripts/verify-artifact-paths.sh` |
| 12 | Every template body `<ANGLE_UPPER>` appears in that template's frontmatter, and vice versa              | abort                                | `scripts/verify-frontmatter.sh` |
| 13 | No computed pseudo-tokens (angle-bracketed identifiers containing arithmetic operators, e.g. PHASE_ID followed by `+1`) remain in any emitted prompt. See tokens.md § Forbidden patterns. | abort | `scripts/verify-tokens.sh` |
| 14 | Each `model_assignments` entry's phase id is a valid member of the schema's `phase_id` enum             | abort                                | `scripts/verify-schema.sh` |
| 15 | **Product presence (v1.1).** When `user_facing` is `true`: (a) at least one `model_assignments` entry for each of phases B.1, B.2, and D.2 has a `product` role in its `assignments`; (b) `artifacts.product_verdict` is declared (non-empty) in the manifest; (c) no phase has more than one `product` role across its entries (singular policy matches template 06's single `<PRODUCT_VERDICT_PATH>`). The Product family may overlap an engineering family from the same phase's other entries, but only if the Product assignment lives in a separate list entry (separate worker session per P10). | abort | `scripts/verify-p3.sh` (user-facing branch) |
| 16 | **Pre-A exit (v1.1).** When `pre_a` is set, its `artifact_path` is declared (non-empty; schema enforces `minLength: 1`) and the artifact exists (or is produced) before any Phase A dispatch is emitted. Generator performs a static check on the example; runtime check that the artifact is present before Phase A is the orchestrator's job. | abort on static failure | `scripts/verify-pre-a.sh` |
| 17 | **Pre-A-variant coherence (v1.1).** (a) `pre_a.entry == "triage"` with at least one finding dispositioned `fast-patch` (In-Scope + trivial per Template 17 §3.2) routes the generator to emit a Phase C-direct dispatch sequence (skipping A and B) for that finding, with the per-finding regression test as scope-lock. Findings dispositioned `rejected` per Template 17 §3.4 emit no dispatch — they record reasoning only. Findings dispositioned `In-Scope` (non-fast-patch) route to normal Phase A. Findings dispositioned `Deferred` emit no dispatch (backlog entry). (b) `pre_a.entry == "validation"` with verdict `Run exposed defect — escalate to hotfix or incident` (Template 18) halts the deliverable and routes per the verdict's §7 `Exit path` block — either `09-incident-postmortem.md` (critical/high severity) or Evidence-Based Patch via Phase A (medium/low severity). (c) `pre_a.entry == "proposal"` with verdict `Abandon direction` (Template 16) halts the deliverable with no downstream emission; verdict `Split into multiple proposals` routes back to Phase 0 with each split candidate re-entering at `-A.proposal`. | orchestrator (runtime) | orchestrator reads the pre-A artifact's verdict field and routes; no static script parses pre-A verdict bodies in v1 |

---

## What the generator does NOT do

- Execute dispatches. The orchestrator (human or LLM loaded with
  `00-orchestrator-runbook.md`) drives the dispatches.
- Mutate the manifest. The manifest is input; `manifest.resolved.yaml` is
  a derived snapshot.
- Run tests. The validation plan is emitted as a script; the orchestrator
  runs it.
- Call LLM APIs. The generator is pure text transformation.

---

## Implementation notes (for the v2 author)

- Prefer a language with robust YAML + templating (Python + Jinja2 is a
  pragmatic default; Rust + askama also reasonable).
- Keep the templating engine strict: unknown tokens raise, not silently
  stringify.
- Unit-test with `example-manifest.yaml`: resolving it must produce the
  full output tree, and every emitted prompt must contain zero
  `<ANGLE_UPPER>` strings beyond the allowed placeholder set.
- Provide a `--dry-run` that reports the substitution plan without writing.
- Exit non-zero on any invariant violation; never partially emit.

---

## Versioning coupling

The generator targets `manifest_version: 1.0.0`, `1.1.0`, `1.1.1`, or
`1.2.0`. Each higher version is backward-compatible with every lower
version's manifests. v1.1 additions (`user_facing`, `pre_a`,
`product_verdict`, pre-A phase enums, new role labels) are all optional
and default to v1.0.0 behavior when absent. v1.1.1 is a bundle-identity
bump with no new schema fields. v1.2 additions (`review_rounds[]`,
`cli_capability_matrix[].evidence_cap`,
`cross_provider_adversarial_passes[]`) are additive + optional; the
v1.2 P3 adversarial-family MUST-differ-provider invariant is enforced
by `verify-p3.sh` only when `manifest_version ≥ 1.2.0`. A manifest with
a higher version than the generator supports is rejected with a
message indicating the generator version gap. Breaking changes to the
manifest schema bump the bundle to `llm-dev-v2/` and the generator
follows.
