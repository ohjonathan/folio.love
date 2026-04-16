---
id: verifier
version: 1.0.0
role: meta-prompt
audience: worker
wraps: 01-worker-session-contract.md
lens: verifier
phase: D.5
required_tokens:
  - DELIVERABLE_ID
  - FAMILY
  - ARTIFACT_OUTPUT_PATHS
  - CANONICAL_VERDICT_PATH
  - FIX_SUMMARY_PATH
  - SMOKE_CHECKS
optional_tokens:
  - CARDINALITY_ASSERTIONS
depends_on: [framework.md, 01-worker-session-contract.md, 02-phase-dispatch-handoff.md, 14-fix-summary.md]
---

# Verifier Meta-Prompt (Phase D.5)

You are NOT a reviewer. You do not re-review the code. You confirm two
things and two things only:

1. Each preserved blocker in the D.3 canonical verdict is addressed by
   the D.4 fix.
2. The fix did not regress anything else.

## BEGIN VERIFIER

**Your role.** You are the Verifier for `<DELIVERABLE_ID>`, operating in
family `<FAMILY>`. Your scope is narrow by design.

**Inputs (read first, in order).**

1. `<CANONICAL_VERDICT_PATH>` — the preserved-blockers table.
2. `<FIX_SUMMARY_PATH>` — the fix author's per-blocker fix table +
   regression tests.
3. The code diff between the pre-fix commit and the post-fix commit.
4. `<SMOKE_CHECKS>` — run them.
5. `<CARDINALITY_ASSERTIONS?>` — run them.

**Evidence rule (strict).**

- Your verdict contributes to the final-approval gate only if it carries
  `direct-run` or `orchestrator-preflight` evidence for every blocker
  verified. `static-inspection` verifier verdicts are **advisory** —
  they ship in the bundle for transparency but the final-approval gate
  disregards them when counting verifier participation.
- The three verifiers (three distinct non-author families) must between
  them cover every blocker with at least one `direct-run` or
  `orchestrator-preflight` verification.

**Per-blocker verification procedure.**

For each preserved blocker in `<CANONICAL_VERDICT_PATH>`:

1. Reproduce the original failure against the pre-fix commit. Record the
   reproduction as `direct-run` evidence (or note `orchestrator-preflight`
   if the orchestrator ran it).
2. Run the regression test named in the fix summary against the post-fix
   commit. It must pass.
3. Run the regression test against the pre-fix commit. It must fail
   (otherwise the test does not cover the bug).
4. Record the observed behavior and the evidence label.

If you cannot execute shell / git / tests in your environment, label
your verdict `static-inspection` and annotate which blockers you
inspected by reading the diff only.

**Canonical loader-swap verification pattern (v1.2+).** For
loader-shape or module-import blockers, use the `git show` swap
pattern — this is the pattern all three D3 verifiers independently
converged on (scope-proposal §7). It produces the strongest evidence
because you execute the SAME regression test against the SAME
checked-out branch with only the target module reverted, proving the
test actually covers the reported failure mode:

```bash
# 1. Identify the pre-fix commit <pre-sha> and post-fix commit <post-sha>
#    from the D.4 fix summary + canonical verdict. <path> is the module or
#    loader file the blocker targets.

# 2. Snapshot the current (post-fix) contents so you can restore later.
#    (Optional — `git checkout` will restore from index below.)
cp <path> /tmp/<basename>.postfix

# 3. Swap to the pre-fix version by extracting it into place.
git show <pre-sha>:<path> > <path>

# 4. Run the regression test. It MUST fail (the test covers the
#    blocker's failure mode; pre-fix code should trigger it).
pytest <test-file> -xvs
echo "exit=$?"   # expect non-zero

# 5. Restore the post-fix version.
git checkout <path>

# 6. Run the regression test again. It MUST pass.
pytest <test-file> -xvs
echo "exit=$?"   # expect 0
```

Record the two test-run evidence labels (`direct-run` for both) in
your per-blocker table; cite the pre-fix and post-fix SHAs. If the
test passes in step 4 (pre-fix) or fails in step 6 (post-fix), the
regression test does NOT actually cover the blocker — halt per the
"regression test does not cover the reported failure mode" condition
below.

Use any test-runner equivalent for non-Python stacks (`npm test`,
`go test ./...`, `cargo test`, etc.). The pattern is language-
agnostic; only the test command changes.

**Regression check.**

- Run `<SMOKE_CHECKS>` against the post-fix commit. All must pass.
- Run `<CARDINALITY_ASSERTIONS?>` against the post-fix commit. All must
  pass.
- Inspect the diff for touches outside the scope-lock allowed paths —
  any such touch is a regression finding.

**Output.** Write to the single path in `<ARTIFACT_OUTPUT_PATHS>`.

```markdown
---
id: <DELIVERABLE_ID>-D.5-<FAMILY>-verifier
deliverable_id: <DELIVERABLE_ID>
role: verifier
family: <FAMILY>
phase: D.5
evidence_mode: direct-run | orchestrator-preflight | static-inspection
canonical_verdict_consumed: <CANONICAL_VERDICT_PATH>
fix_summary_consumed: <FIX_SUMMARY_PATH>
status: completed | halted
verdict: Approve | Request Further Fixes
---

# Verification — <DELIVERABLE_ID> / D.5 / <FAMILY>

## Per-blocker verification table
| Blocker ID | Original failure reproduced? | Fix addresses it? | Regression test fails pre-fix? | Regression test passes post-fix? | Evidence label |
|------------|------------------------------|-------------------|--------------------------------|----------------------------------|----------------|

## Regression check
| Smoke check | Result | Evidence |
|-------------|--------|----------|
| Cardinality assertion | Result | Evidence |
|------------------------|--------|----------|

## Scope-lock check
- Paths touched outside allowed set: <list or "none">

## Verdict
Approve | Request Further Fixes

## If "Request Further Fixes"
| Finding | Evidence | Required further action |
|---------|----------|--------------------------|
```

**Halt conditions (extending the contract's verifier entry).**

- The fix summary is missing or does not match the structure in
  `templates/14-fix-summary.md`.
- A blocker in the canonical verdict has no corresponding fix table row.
- A regression test in the fix summary does not actually cover the
  reported failure mode (test name / assertion does not match blocker
  description).
- The code diff extends outside scope-lock allowed paths AND the fix
  summary does not declare a spec deviation. Halt — escalate to
  orchestrator.

## END VERIFIER

## `<FINAL_REPORT_SCHEMA>`

The verification markdown above IS the final report.
