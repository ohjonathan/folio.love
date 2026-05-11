# PR D Phase B Spec Review, Round 2

Primary artifact: [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md)  
Reference: [folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md)  
Reference: [v0.5.1_tier3_entity_system_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/v0.5.1_tier3_entity_system_spec.md)

## 1. Completeness Check

Rev 2 is materially better than Rev 1. The evidence-only extraction contract is much tighter, the dedicated `_llm_metadata.provenance` namespace is the right move, and pair-level fingerprints plus sharding make the runtime model more plausible.

It is still not complete enough to hand to implementation. Three lifecycle seams remain underdefined in ways that would force CA follow-up: the legality of the primary seed relationships on evidence notes, the actual execution model for “bidirectional” `supersedes`, and the stale-link review/acknowledgement path.

## 2. Quality Assessment

The spec’s architecture is generally stronger than the prior round. `§6 D10-D14`, `§9.2-§9.8`, and `§12.6` show good discipline around idempotency, refresh survival, and large-pair handling.

The remaining quality problem is internal consistency. Several claimed fixes are only half-landed: `§22` says pagination was added, but the CLI contract never defines it; stale review is described narratively in `§14.3-§14.4`, but the actionable command/state model from `folio entities confirm` in the entity spec’s `§8.4-§8.5` and `§11.1-§11.3` never materializes for stale provenance links.

## 3. UX Review

The updated review UX is improved for small and medium queues. Stable IDs, `--doc`, `--target`, range confirm, and per-document batching are all useful.

At the requested scale, it still does not really scale. For 50+ pending proposals across 20 source documents, there is no actual pagination contract, no stale-item command grammar, and the status “coverage” metric is misleading because it counts links, not covered claims. The operator experience is therefore better than Rev 1, but not yet production-ready.

## 4. Issues Found

### Critical

1. `§6 D2` still makes `draws_from` and `depends_on` the primary provenance seeds for evidence-to-evidence v1, and `§5.4` expects humans to add those edges, but the reference enrich spec explicitly says those fields remain reserved for ontology-eligible analysis/deliverable docs, not the evidence corpus (`folio_enrich_spec §5.3`, `§6 D6`). Rev 2 only adds an ontology precondition for `provenance_links` (`§9.1`, `§21`), not for evidence-note `draws_from` / `depends_on` applicability. As written, the primary seed strategy is not schema-legal on the target document type.

2. `supersedes` is labeled “bidirectional comparison” in `§6 D2`, `§10`, and `§17.3`, but the pipeline is still source-claim → target-passage only (`§10` steps 3-6, `§11`, `§12`). There is no defined reverse pass, no reverse storage model, and no review semantics for the opposite direction. This matters because `§5.4` says the first practical v1 yield comes from confirmed `supersedes` edges. The main usable seed on the current baseline is still under-specified.

3. The stale-link lifecycle is still not implementable end to end. `§14.3-§14.4` says `folio provenance review --stale` lets a human re-confirm, remove, or ignore stale/orphaned links, but `§13.2` defines actions only for pending proposals. There is no stale-link ID scheme, no command syntax for those actions, and no field in `§9.1` to persist “ignored/acknowledged” staleness. Separately, `§9.8` and `§15.5` introduce `stale_pending`, but `§9.2` and `§9.3` do not allow that status. The claimed stale-link and reconciliation fix still needs design work.

### Major

4. The spec claims pagination was added (`revision_note`, `§22` SF-02), but `§8.9` and `§13.2` never define any pagination behavior. There is no page size, cursor, ordering contract for proposals within a doc, or `next/prev` review flow. For the requested “50+ pending proposals across 20 source documents” scenario, the UX still depends on long scrolling or manual pre-filtering.

5. `§8.10` defines coverage as confirmed non-stale provenance links divided by total extractable claims. That metric breaks as soon as one claim has multiple confirmed links, which `§9.1`, `§12`, and `§13` all allow. Coverage can exceed 100%, so the status surface is not measuring “claim coverage” reliably. The numerator should be distinct source claims with at least one confirmed non-stale link.

6. The concurrency story is only partially specified and only partially tested. `§6 D15` and `§16.5` say `folio provenance`, `folio enrich`, and `folio refresh` must not overlap, but only PR D defines the `.folio_lock` convention; the reference enrich spec does not. `§17.13` tests only PID detection for a concurrent run attempt, not the cross-command overlap the spec calls unsafe. The “single-writer rule” is therefore not fully implementable or validated yet.

## 5. Positive Observations

- Narrowing v1 to evidence-to-evidence is a real improvement. `§1-§5`, `§11`, and `§18` are much more internally aligned than the prior round.
- Pair-level fingerprints, rejection suppression, and explicit reconciliation are the right direction. `§6 D10-D13` is far stronger than the earlier source-scoped design.
- `§12.6` is concrete enough to implement: the 80% preflight, shard-by-target-passages rule, and merge behavior are clear.
- The PRD patch section and review resolution map are high quality. `§19` and `§22` make upstream implications and revision intent unusually auditable.

## 6. Verdict

Rev 2 fixes a lot, but it does not yet clear the “complete, implementable, usable” bar. The remaining problems are not polish issues; they affect the legality of the seed graph, the actual semantics of the only practical v1 seed on today’s corpus, and the stale-link workflow that Rev 2 claims to have closed.

Verdict: Request Changes
