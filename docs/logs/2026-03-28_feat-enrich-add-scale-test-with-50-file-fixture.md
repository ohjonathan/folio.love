---
id: log_20260328_feat-enrich-add-scale-test-with-50-file-fixture
type: log
status: active
event_type: pr37-code-review-consolidation
source: cli
branch: feature/folio-enrich-core
created: 2026-03-28
---

# PR #37 `folio enrich` Core Code Review Consolidation

## Goal
Synthesize the findings of three independent reviewer agents (Peer, Alignment, Adversarial) against PR #37 to verify its spec compliance, safety, and implementation of `folio enrich`.

## Key Decisions
- **Blocked the PR**: The code review identified multiple critical safety and data integrity bugs that deviate from the approved spec.
- **Identified safety gate bypass**: The most critical issue (B1) is that `_update_related_section` bypasses the `body_safe` gate, mutating human-curated protected notes.
- **Identified YAML parsing structural bug**: Both Peer and Adversarial reviewers found `_replace_frontmatter` using naive `str.index("\n---", 4)`, which crashes or corrupts multi-line YAML blocks.

## Alternatives Considered
- *Approving with nits*: Not viable because the idempotency loops and body-safety mechanisms were broken under adversarial testing.
- *Fulfilling all roles sequentially vs in parallel contexts*: Executed reviewers sequentially using `claude` CLI to avoid Anthropic API concurrency limits, isolating their contexts perfectly.

## Impacts
- PR #37 must go back for Developer fixes before it can be merged.
- Seven specific Blocking issues (B1-B7) and four Should-Fix issues (S1-S4) were aggregated and assigned priority with clear test verification requirements.

## V2 Iteration
- **Goal**: Re-review `feature/folio-enrich-core` diff after developer attempted fixes.
- **Outcome**: The PR was blocked again (Needs Fixes). While prior issues like Proposal Cleanup and the original YAML parser crash were fixed, a new Regex-based block-scalar false positive corruption vector was identified. The Entity Fingerprinting issue persists unchanged.
## V3 Iteration
- **Goal**: Re-review `feature/folio-enrich-core` diff after developer attempted second round of fixes.
- **Outcome**: The PR was blocked for a third time (Needs Fixes). The YAML block-scalar and Tilde fence parsing issues were fixed. However, Reviewer 3 uncovered deeper data-corruption and operational bugs: Entity fingerprints reading stored values instead of recalculating, substring collision in wikilink insertion (`Engineering Department` vs `Engineering`), and protected notes running the full LLM pipeline (burning API budget). The Spec-Code contradiction on `## Impact` remains unresolved.
## V4 Iteration
- **Goal**: Final review to determine merge readiness.
- **Outcome**: The PR was definitively BLOCKED. It appears the developer did not address the critical idempotency and data-integrity defects flagged in V3 (entity false-skip, substring wikilink corruption, LLM budget bleed). Furthermore, Reviewer 3 uncovered a new fatal bug in the custom YAML frontmatter scanner that silently corrupts notes if multi-line YAML quoted strings contain a `---` substring.
## V5 Iteration
- **Goal**: Final review to determine merge readiness.
- **Outcome**: The PR was definitively BLOCKED. The developer successfully fixed the data integrity vulnerabilities (Entity confirmation false-skips, wikilink substring corruption). However, Reviewer 3 uncovered new vulnerabilities: 1. Falsely finding the YAML array marker `---` on escaped quotes `\"`. 2. Ignoring the human sidecar `.overrides.json`, destroying human corrections. 3. Falsely marking empty/failed analysis attempts as `status: executed` giving false success signaling.
- **Post**: Aggregated 3 Blocking issues and posted a final Block verdict to GitHub #37.