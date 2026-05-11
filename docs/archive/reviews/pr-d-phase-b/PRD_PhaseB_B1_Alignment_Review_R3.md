## 1. Architecture Compliance

- Rev 3 fixes the Round 2 ontology-illegal seed problem. `supersedes` is legal on evidence because the approved ontology defines `supersedes` as applying to `all`, while `draws_from` and `depends_on` apply only to `analysis, deliverable` ([Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §12.3; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §6 D2).
- Making `supersedes` one-way in v1 also resolves the prior representability problem. The newer note as source and older note as target is now explicit and coherent with the data model ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §6 D2, §10, §13.3).
- But architecture compliance is still incomplete because the spec introduces a new canonical field, `provenance_links`, that does not exist in the approved ontology/frontmatter baseline. The spec itself says an ontology amendment is required before implementation ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §9.1, §21; [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md), FR-402).

## 2. Roadmap Alignment

- This is still off-plan today. The approved roadmap defines PR D as “match deliverable claims against library evidence,” says the active relationship types are `depends_on, draws_from, impacts`, and keeps the Tier 3 exit criterion as “Retroactive provenance links deliverable slides to evidence” ([04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md), “Week 19-20: Enrichment & Provenance”, “Tier 3 Exit Criteria”).
- Rev 3 narrows the slice to evidence-to-evidence version-lineage and explicitly says a roadmap/PRD amendment is required before implementation ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §1, §19.1, §21).
- That precondition is honest, but it does not cure the misalignment. It confirms the spec still depends on an unapproved scope change.

## 3. Constraint Verification

- Seed legality: passed. `supersedes`-only, newer→older v1 is legal under the current ontology ([Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §12.3).
- Relationship-recommendation coherence: partial. The ontology’s approved v1 recommendation still says start with `depends_on`, `draws_from`, and `impacts` ([Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §6.4). Rev 3 now documents the `supersedes` reordering clearly, so this is no longer an undisclosed contradiction, but it remains a deviation until upstream docs are amended.
- Coverage/status: passed. The revised coverage metric is now bounded correctly as distinct claims with at least one confirmed non-stale link ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §8.10).
- Stale-link fields: partial. `stale_pending` inside `_llm_metadata.provenance` is fine as internal metadata, and `provenance_link_stale` fits the open-ended `review_flags` model ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §9.3, §14.3; [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md), FR-704; [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §12.7). `acknowledged_stale`, however, lives inside the unapproved `provenance_links` field, so it is not yet part of the approved frontmatter model.
- Amendment status: failed. The refresh, ontology, and roadmap changes are still prerequisites only; none of the reference documents show them as approved ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §21).

## 4. Backward Compatibility

- The one-way `supersedes` model now fits the shipped enrich contract better than Rev 2 did. It respects enrich’s frontmatter-authoritative, human-owned graph model and the new confirmed-link dedupe rule closes the rerun duplication hole ([folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md), D7-D8; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §13.3, §15.4).
- Advisory locking is also an improvement over warning-only behavior and is no longer a backward-compatibility concern by itself ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §16.5).
- The remaining compatibility blocker is `folio refresh`. The shipped enrich/refresh contract preserves canonical relationship fields and `_llm_metadata.enrich`, not `provenance_links` or `_llm_metadata.provenance` ([folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md), §15.2). Rev 3 requires that contract to change, so refresh compatibility is still unapproved ([folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §9.7-9.8, §21).

## 5. Consistency Check

- Rev 3 does appear to have fixed the main Round 2 internal-contract problems: one-way `supersedes`, confirmed-link suppression, stale/orphan action grammar, pagination, coverage, deterministic sharding, and stronger concurrency handling are now explicitly specified ([PRD_PhaseB_B2_Consolidation_R2.md](/Users/jonathanoh/Dev/folio.love/PRD_PhaseB_B2_Consolidation_R2.md), §§2-6; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §§8-16, §22).
- The remaining blockers are no longer “the spec contradicts itself.” They are “the spec still requires unapproved upstream changes.”

## 6. Deviation Report

**Critical**
- Off-plan scope remains. The approved roadmap still defines PR D as deliverable-to-evidence provenance using `depends_on`, `draws_from`, and `impacts`, while Rev 3 implements evidence-to-evidence `supersedes` lineage instead ([04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md), Week 19-20 and Tier 3 Exit Criteria; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §1, §19.1, §21).
- The canonical storage and refresh durability contract is still unapproved. `provenance_links` is not in the approved ontology/frontmatter baseline, and current refresh compatibility does not preserve provenance state ([Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §12.3, §12.7; [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md), FR-402; [folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md), §15.2; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §9.1, §9.7-9.8, §21).

**Major**
- `supersedes`-first rollout is now legal and well-argued, but it still departs from the ontology’s approved v1 relationship recommendation to start with `depends_on`, `draws_from`, and `impacts` ([Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), §6.4; [folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md), §6 D2).

**Minor**
- None.

## 7. Verdict

Rev 3 is materially better and appears internally coherent, but it is still not approval-ready as an alignment review artifact. The seed model is now legal; the scope and storage contracts are not yet approved upstream. This should not be approved “contingent” on future amendments, because those amendments are the missing authoritative contract.

Verdict: Request Changes
