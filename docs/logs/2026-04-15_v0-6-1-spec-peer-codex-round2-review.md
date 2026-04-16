---
id: log_20260415_v0-6-1-spec-peer-codex-round2-review
type: log
status: active
event_type: decision
source: codex
branch: feat/proposal-lifecycle-rename-v0-6-1-C-author-claude
created: 2026-04-15
---

# v0.6.1 spec peer codex round2 review

## Context

Goal: Re-review `docs/specs/v0.6.1_proposal_lifecycle_rename_spec.md`
v1.1 after Round 1 peer findings and verify whether B-1, B-2, and B-3
were closed against the current source files.

Relevant artifacts:
- `docs/validation/v0.6.1_spec_peer_codex.md`
- `docs/validation/v0.6.1_spec_peer_codex_round2.md`
- `folio/pipeline/enrich_data.py`
- `folio/enrich.py`
- `folio/links.py`
- `folio/graph.py`
- `folio/cli.py`
- `folio/provenance.py`

## Decision

Key Decisions:
- Approved spec v1.1 for the peer Round 2 closure scope.
- Marked B-1 closed because `cli.py:133` is now explicitly removed from
  relationship-proposal scope and provenance lifecycle migration is deferred
  as PROV-1 with namespace-separation rationale.
- Marked B-2 closed because v1.1 uses the `is None` raw-dict fallback and
  limits raw-dict readers to unchanged `"rejected"` comparisons.
- Marked B-3 closed because T-3b, T-7, and T-8 were added and existing test
  rewrite coverage is specified for the relationship-proposal fixtures.

## Rationale

Alternatives Considered:
- Require provenance proposal migration in this slice. Rejected because
  v1.1 now scopes the slice to relationship proposals, documents the separate
  provenance namespace, and carries provenance forward as a follow-up.
- Require raw-dict old-to-new mapping everywhere. Rejected for this slice
  because the only in-scope raw-dict readers compare to `"rejected"`, whose
  old and new values are identical; pending/queued comparisons flow through
  `RelationshipProposal.from_dict`.

## Consequences

Impacts:
- Added `docs/validation/v0.6.1_spec_peer_codex_round2.md`.
- No source files were modified.
- Ontos activation was attempted; `ontos map` failed on existing duplicate
  or invalid metadata, `python3 -m ontos map` was unavailable, and the
  existing `Ontos_Context_Map.md` was read.
