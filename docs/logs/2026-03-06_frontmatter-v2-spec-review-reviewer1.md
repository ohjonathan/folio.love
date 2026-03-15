---
id: log_20260306_frontmatter-v2-spec-review-reviewer1
type: log
status: active
event_type: decision
source: codex
branch: main
created: 2026-03-06
---

# frontmatter-v2-spec-review-reviewer1

## Context

Goal: Review `docs/specs/v0.1_frontmatter_v2_completeness_spec.md` for implementation readiness against the ontology and current codebase.

Reviewed inputs:
- Ontos context map and project docs
- Ontology architecture v2 and implementation roadmap v2
- All prior specs under `docs/specs/`
- Current implementation and full test suite

## Decision

Request changes.

Key decisions:
- Treat the document as a post-implementation reference, not an implementation spec.
- Require correction of the evidence field matrix against ontology Section 12 before approval.
- Require verification/backward-compatibility claims to match the actual codebase and tests.

## Rationale

Alternatives considered:
- Approve as-is because the evidence-path code is mostly implemented.
- Approve conditionally and rely on follow-up clarifications during implementation.

Why rejected:
- The document explicitly states that implementation is already complete, so it does not function as a start-implementation spec.
- The relationship-field applicability matrix is not fully accurate for evidence docs.
- The compatibility and verification sections overclaim coverage relative to the current CLI and tests.

## Consequences

Impacts:
- The spec should be revised before it is used as the basis for implementation or sign-off.
- The next revision should either become a true implementation spec (with remaining work, scope, tests, and file changes) or be renamed/repositioned as a reference document.
- Backward-compatibility guidance should be limited to behavior that exists today and is covered by tests.
