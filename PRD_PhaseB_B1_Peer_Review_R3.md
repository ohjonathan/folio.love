**1. Completeness Check**

Rev 3 is materially closer. The `supersedes`-only, one-way seed model is now locally implementable and ontology-legal for evidence notes in [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §6 D2, and it aligns with [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) §12.3. Confirmed-link dedupe is also now concrete in §10.6i and §15.4.

It is still not complete enough to approve. The main remaining gaps are lifecycle closure for `acknowledged_stale`, repairability on protected notes, stale-review UX at scale, and the fact that the governing reference docs are still not amended, so the spec is not yet an authoritative implementation contract against the current corpus and roadmap.

**2. Quality Assessment**

The spec is much cleaner than Rev 2. The scope is now honestly framed as infrastructure plus an evidence version-lineage pilot, the sharding rules in §12.6 are far more implementable, and the reconciliation rules in §15.4 are substantially better.

The remaining quality issues are mostly contract precision problems: one stale-state contradiction, one over-imported protection rule from enrich, one incomplete review-mode pagination contract, and one dry-run contradiction between §8.5 and §10.2.

**3. UX Review**

Pending-link review is improved. §8.9 and §13.1-§13.2 now define page size, batch actions, and a usable default review path for medium/high-confidence proposals.

The UX is still not fully usable at scale for all queues. The stale/orphan queue does not get the same explicit traversal contract, and the display ordering is not stable enough for `confirm range` to be dependable across large, tied-confidence result sets. More importantly, protected notes can accumulate stale links without a first-class path to regenerate replacements.

**4. Issues Found**

**Critical**

- **Governing contract is still unresolved, so this is not yet an approval-ready implementation spec.** The spec correctly says upstream amendments are required in §19.1 and §21, but the current references still disagree: [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md) “Week 19-20: Enrichment & Provenance” still defines PR D as “match deliverable claims against library evidence” and lists active relationship types as `depends_on`, `draws_from`, `impacts`; the same file’s Tier 3 exit criteria still say “Retroactive provenance links deliverable slides to evidence.” [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) §12.3 still has no `provenance_links` field, and [folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) §5.2 still says refresh does not preserve manually added relationship fields. Rev 3 is honest about this, but honesty is not resolution; against the current reference set, the contract is still incomplete.

**Major**

- **`acknowledged_stale` does not actually close the stale lifecycle.** In [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §13.5, `acknowledge` says the link persists and “staleness is noted.” But §14.3 defines a link as stale only when hashes differ and `acknowledged_stale` is `false`. That means acknowledged stale links disappear from the stale queue and stale counts in §8.10, with no separate “acknowledged stale” reporting surface and no rule for resurfacing them if content changes again. The new state currently functions as “silence this stale item,” not as a complete lifecycle state.

- **The protected-note rule is too strong for a frontmatter-only feature and leaves repair gaps.** §10 and §14.1 import enrich-style protection, so `curation_level != L0` or `review_status in {reviewed, overridden}` skips LLM evaluation entirely. But §14.5 says provenance does not mutate body content at all; it only writes frontmatter metadata. That is materially different from the body-mutation risk that drives protection in [folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) §14. As written, a protected note can keep stale/orphaned `provenance_links`, but stale review in §13.5 only allows `reconfirm`, `remove`, or `acknowledge`; it provides no first-class way to generate replacement proposals for a protected note. The workflow therefore gets weaker exactly when notes become more curated.

- **Stale/orphan review is still under-specified at scale.** Pending review has explicit pagination in §8.9 and §13.1-§13.2. Stale review does not. The stale example in §8.9 shows a page header, but gives no page size, no ordering rule, and no `next`/`prev` actions; §13.5 also omits navigation behavior. Since the command shape in §8.2 allows `--page`, this leaves stale-mode traversal ambiguous for large queues across many documents.

- **Review ordering is not stable enough for range-based actions.** §8.9 orders pending items by source document and confidence descending, but it does not define a deterministic tie-break inside equal-confidence items. That matters because §13.2 adds `confirm range prov-XXXX..prov-YYYY`, which depends on the displayed order being stable. With 50+ pending items, tied-confidence proposals can shift between pages or between reruns, making range confirmation error-prone.

- **The test plan still does not cover several of the new claims.** §17 now covers more ground, but it still does not test acknowledged-stale visibility semantics, stale-review pagination and ordering, protected-note stale repair behavior, or cross-command locking with `folio enrich` / `folio refresh` even though §6 D15 and §16.5 claim those commands share the same concurrency boundary. §17.13’s scale test also validates batching and shard planning, not the actual review UX for 50+ queued items.

**Minor**

- **`--dry-run` is internally inconsistent.** §8.5 says dry-run reports estimated call counts with shard counts for oversized pairs, but §10.2 says dry-run stops at step 6c, before context-budget estimation and sharding in §10.6d / §12.6. The implementer cannot tell whether dry-run includes sharding preflight or not.

**5. Positive Observations**

- The `supersedes`-only, one-way seed model in §6 D2 is a real improvement. It is now ontology-legal on evidence notes and no longer relies on `draws_from` / `depends_on` in contradiction with [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) §12.3.

- Confirmed-link dedupe is now concrete enough to be implementable. §10.6i and §15.4 define the suppression surface clearly, and §17.6 / §17.11 at least acknowledge the `--force` rerun case that was missing before.

- The infrastructure-slice framing is much more credible than Rev 2’s implied yield story. §1, §5.4, and §18 now describe the current-corpus reality directly instead of pretending the baseline will immediately deliver broad user-visible provenance.

- I did not find a new contradiction with [v0.5.1_tier3_entity_system_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/v0.5.1_tier3_entity_system_spec.md); the main remaining problems are in provenance lifecycle/UX and in the still-unamended roadmap/ontology/refresh contracts.

**6. Verdict**

Verdict: Request Changes
