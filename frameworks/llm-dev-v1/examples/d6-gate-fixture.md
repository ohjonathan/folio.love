---
id: currency-converter-final-approval
deliverable_id: currency-converter
role: final-approval
status: passed
---

# Final-Approval Gate — currency-converter

Known-good fixture for `scripts/verify-d6-gate.sh` regression testing.
Mirrors the 10 `gate_prerequisites` of `manifest/example-manifest.yaml`
with the v1.2+ machine-readable gate table schema (Result =
`PASSED`/`FAILED`; Evidence class drawn from the allowed tag set
defined in `templates/07-final-approval-gate.md`).

This fixture is intentionally non-normative: its Reproduction commands
point at `docs/reviews/...` paths inside a hypothetical adopter repo,
and its evidence claims are illustrative rather than runnable from the
framework bundle. The fixture exercises the parser and the
row-validation logic only; no commands are executed during the
regression test.

## Gate table
| # | Prerequisite | Result | Evidence class | Reproduction |
|---|--------------|--------|----------------|--------------|
| 1 | Full test suite passes. | PASSED | test-pass | `pytest -xvs` |
| 2 | Scope lock intact: forbidden symbols absent from allowed paths. | PASSED | grep-empty | `! grep -rE 'requests\.\|httpx\.\|import asyncio' src/currency/` |
| 3 | No changes outside scope-lock allowed paths. | PASSED | grep-empty | `! git diff --name-only main..HEAD \| grep -vE '^(src/currency/\|tests/test_currency\.py$)'` |
| 4 | ISO table has exactly 20 entries. | PASSED | count-eq | `python -c 'from src.currency import CURRENCIES; assert len(CURRENCIES) == 20'` |
| 5 | Canonical B.3 verdict exists. | PASSED | file-exists | `test -f docs/reviews/currency-converter-B.3-verdict.md` |
| 6 | Canonical D.3 verdict exists. | PASSED | file-exists | `test -f docs/reviews/currency-converter-D.3-verdict.md` |
| 7 | D.5 verifier artifacts from all three non-author families exist. | PASSED | count-eq | `ls docs/reviews/currency-converter-D.5-*-verifier.md \| wc -l` |
| 8 | No unresolved blocker lines in any canonical verdict. | PASSED | grep-empty | `! awk '/^## Preserved blockers/,/^## /' docs/reviews/currency-converter-*-verdict.md \| grep -E '^- \*\*ID:\*\*'` |
| 9 | Working tree clean (no uncommitted changes). | PASSED | grep-empty | `! git status --porcelain \| grep .` |
| 10 | Branch ahead of main by ≥1 commit. | PASSED | count-gte | `git rev-list --count main..HEAD` |

## Failure diagnosis

All rows Result=PASSED with allowed evidence-class tags. No failure
diagnosis required for this fixture.

## Gate outcome

PASSED (10 rows, all PASSED, all evidence-class tags from the allowed
set: test-pass, grep-empty, count-eq, file-exists, count-gte).

## Recommended next action for orchestrator

If this artifact were a real final-approval for the currency-converter
deliverable: merge per P8 using a fresh non-local clone, `--no-ff`,
push from the fresh clone.

(This is a fixture — no merge is performed.)
