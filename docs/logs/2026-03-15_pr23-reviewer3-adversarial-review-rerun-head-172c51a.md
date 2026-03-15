---
id: log_20260315_pr23-reviewer3-adversarial-review-rerun-head-172c51a
type: log
status: active
event_type: 2026-03-15_pr23-reviewer3-adversarial-review-rerun-head-172c51a
source: codex
branch: codex/diagram-pr5-rendering
created: 2026-03-15
---

# pr23-reviewer3-adversarial-review-rerun-head-172c51a

## Context

Adversarial rerun review for PR #23 on branch `codex/diagram-pr5-rendering`
at `172c51a`, compared against `main` at `97f03b9`, after prior review
feedback was applied.

## Goal

Re-check merge readiness with emphasis on renderer failure modes the green
pytest suite could still miss:

- Mermaid/parser correctness beyond happy-path ASCII graphs
- semantic alignment between Mermaid, prose, and tables
- regrouped/nested-group behavior against the live PR 4 `node.group_id`
  drift
- malformed or partially inconsistent graphs that could still appear through
  extraction/runtime drift

## Decision

Block merge.

## Summary

The rerun passed the requested Python suites:

- `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
- `.venv/bin/python -m pytest tests/ -q`

Manual repros still found correctness gaps:

1. Non-ASCII-only node/group IDs can collapse to an empty Mermaid identifier,
   producing invalid Mermaid with no uncertainty.
2. `graph_to_prose()` ignores live `reverse` direction and currently describes
   `A <- B` as `A connects to B`.
3. `graph_to_prose()` still ignores PR 4 regroup state stored only in
   `node.group_id`, so regrouped boundaries disappear from prose even though
   Mermaid/component tables render them.
4. Mermaid still renders dangling edges as implicit phantom nodes instead of
   omit-and-flagging them.

## Key Decisions

- Treated proposal-contract behavior and manual breakage as the gate, not
  passing pytest alone.
- Ran Ontos activation first, then loaded Tier 1, proposal sections 11-13,
  and the PR 5 rendering prompt before auditing code.
- Installed the pinned Mermaid harness with `npm --prefix tests/mermaid ci`
  so parser-backed manual repros used the real Mermaid parser rather than the
  skip path.
- Used direct local graph repros for Mermaid injection, reserved words,
  Unicode/RTL/CJK labels and IDs, parallel edges, self-loops, regrouped
  groups, reverse edges, and dangling edges.

## Alternatives Considered

- Approve because the targeted renderer suite and full Python suite are green.
  Rejected because multiple semantic bugs remain outside current test
  coverage.
- Treat non-ASCII ID failure as irrelevant because PR 4 currently emits ASCII
  arbitrary IDs. Rejected because the renderer/test contract explicitly claims
  broader ID safety and the bug produces parser-invalid Mermaid with no flag.
- Ignore dangling-edge rendering because PR 4 usually validates mutations.
  Rejected because renderer hardening is supposed to omit-and-flag unsafe graph
  elements instead of inventing phantom Mermaid nodes.

## Impacts

- Prevents PR 5 from landing with prose that can contradict verified edge
  direction on live `reverse` edges.
- Prevents regrouped real-world graphs from silently losing boundary/group
  context in prose.
- Prevents silent Mermaid corruption for non-ASCII IDs and phantom-node
  rendering for dangling edges, both of which parser-green happy-path tests can
  miss.

## Testing

- `ontos map`
- `sed -n '1,220p' Ontos_Context_Map.md`
- `sed -n '730,860p' docs/proposals/diagram-extraction-proposal.md`
- `sed -n '1,240p' docs/prompts/CLAUDE_CODE_PROMPT_diagram_pr5_rendering.md`
- `git diff 97f03b9..172c51a -- folio/output/diagram_rendering.py tests/test_diagram_rendering.py tests/mermaid/validate.mjs tests/mermaid/package.json folio/converter.py folio/pipeline/analysis.py`
- `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
- `.venv/bin/python -m pytest tests/ -q`
- `npm --prefix tests/mermaid ci`
- multiple `.venv/bin/python - <<'PY'` manual repro scripts against
  `graph_to_mermaid()` / `graph_to_prose()` plus `node tests/mermaid/validate.mjs`
