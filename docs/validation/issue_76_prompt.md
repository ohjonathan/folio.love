# Issue #76 — Implementation Prompt (scoped)

> Scoped extract of the orchestration prompt for Slice B. The full orchestration
> covered issues #75 and #76; this records the #76-relevant task as executed.

## Goal

Address GitHub issue #76 (`ohjonathan/folio.love`): add public slide-scoped /
retry-only diagram extraction, and expand diagram extraction so consulting
process flows, concept maps, and mixed diagrams are handled robustly — without a
full expensive reconversion when a few diagram slides hit transient failures.

## Requested capabilities

1. Public slide-scoped rerun options:
   `folio convert deck.pptx --slides 35,36,39 --diagrams-only`,
   `--retry-failed-diagrams`, `--retry-review-required-diagrams`.
2. Ergonomic cache/retry: persist/reuse successful diagram work; detect
   `provider_failure` from sidecar metadata; retry only failed/review-required
   notes; refresh affected deck frontmatter review flags and registry metadata.
3. Broader support: `concept-map` and `process` first-class; separate "cannot
   render Mermaid" from "cannot extract structure"; emit structured inventories
   (zones, lanes, stages, callouts, decisions, risks, relationships, components)
   even when Mermaid is unavailable; add schemas for common consulting visuals.
4. Provider-failure resilience: robust retry/backoff; reduced image-payload /
   lower-detail fallback; smaller semantic-inventory-only extraction; end-of-run
   retry-candidate summary.

## Implementation guidance (as given)

- First implement the public retry ergonomics and provider-failure detection path.
- Preserve current full-conversion behavior unless new flags are used.
- Use existing internal APIs: `diagram_extraction.analyze_diagram_pages`,
  `diagram_rendering.render_diagram_analyses`, `diagram_notes.emit_diagram_notes`.
- Parse sidecar `pass_a_parse_outcome: provider_failure` and `review_required: true`.
- For expanded diagram types, implement the **minimum robust** schema and
  rendering needed to stop treating `concept-map`/`process` as unsupported; if
  Mermaid cannot be produced, still emit useful structured inventory + review notes.

## Constraints

- No live LLM/provider/API calls required for regression tests.
- Two-branch / two-PR delivery; this slice on `feat/issue-76-diagram-retry-extraction`.
- Produce four Tier-validation artifacts in `docs/validation/`.
- Acceptance criteria either implemented or explicitly split with documented
  rationale (see the validation report's **Deferred** section).
