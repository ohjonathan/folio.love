# 1. Architecture Compliance

- The move to `_llm_metadata.provenance` is the correct fix at the namespace level. It removes the direct lifecycle coupling that would have existed under `_llm_metadata.enrich`, and it fits the existing frontmatter-as-source-of-truth pattern in [Folio_Ontology_Architecture.md §6.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) and the enrich refresh model in [folio_enrich_spec.md §15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md).
- The spec is still not architecture-compliant overall. Under [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), `depends_on` and `draws_from` apply only to `analysis` and `deliverable`, while `impacts` applies to `interaction`. Rev 2 narrows v1 to evidence-to-evidence, but [folio_provenance_spec.md §§6 D2, 10](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) still makes `draws_from` and `depends_on` the primary provenance seeds for evidence notes. That is not allowed by the approved ontology.
- The approved v1 relationship recommendation also still differs. [Folio_Ontology_Architecture.md §6.4](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) says v1 should start with `depends_on`, `draws_from`, and `impacts`, then add `supersedes` later. Rev 2 instead makes `supersedes` operational and drops `impacts`.

# 2. Roadmap Alignment

- This is still misaligned with the approved plan. The roadmap’s Week 19-20 deliverable is “retroactive provenance linking: match deliverable claims against library evidence,” and the Tier 3 exit criterion is “Retroactive provenance links deliverable slides to evidence” in [04_Implementation_Roadmap.md Week 19-20 and Exit Criteria](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md).
- Rev 2 changes the feature to evidence-to-evidence provenance and sets `provenance_links` to `applies_to: [evidence]` in [folio_provenance_spec.md §§1, 4, 9.1](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md). That is a scope change, not a clarification. It needs a roadmap/PRD change before approval.

# 3. Constraint Verification

- Namespace/lifecycle: partially fixed. `_llm_metadata.provenance` solves the local namespace problem, but not the full refresh contract. The approved refresh contract in [folio_enrich_spec.md §15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) and [02_Product_Requirements_Document.md FR-505](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md) only covers canonical relationship fields plus `_llm_metadata.enrich`. Provenance passthrough is still only a proposed amendment in [folio_provenance_spec.md §19.6](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md).
- `provenance_links`: not approval-ready yet. Rev 2 correctly says an ontology amendment is required, but that means the approved contract is still missing. The field does not exist in [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), so the spec still depends on an unapproved schema addition.
- PRD patch mapping: improved. Adding FR-606 is aligned with [02_Product_Requirements_Document.md FR-606](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md); stopping the FR-705 stretch is correct given [FR-705](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md) is body-override persistence. FR-403 is acceptable as clarification, but it is not the main missing contract.

# 4. Backward Compatibility

- Protection rules are now broadly compatible. Rev 2’s metadata-only behavior for protected notes matches [folio_enrich_spec.md §§14.2-15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md): protected notes may skip body mutation while still accepting safe metadata/frontmatter updates.
- Stale-link detection is also directionally compatible with the existing review model. Adding a machine-generated stale flag is consistent with the additive review-flag approach in [02_Product_Requirements_Document.md FR-704](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md).
- The durability claim is still ahead of the approved contract. [folio_provenance_spec.md §§14.2, 21.6](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) says confirmed provenance survives re-conversion and implies refresh passthrough is already in place, but the approved/shipped refresh contract does not yet include `provenance_links` or `_llm_metadata.provenance`.

# 5. Consistency Check

- Internal consistency is improved, but not resolved.
- [folio_provenance_spec.md §10](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) says `depends_on` is a primary seed, then immediately filters targets to `type: evidence`. Under the ontology, `depends_on` points to context/dependency documents, not evidence, so that path is effectively dead.
- [folio_provenance_spec.md §5.4](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) says v1 output can start once humans add `draws_from` / `depends_on` edges, but [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md) does not allow evidence notes to own those fields.

# 6. Deviation Report

- Critical: Rev 2 still changes the approved feature from deliverable-to-evidence provenance to evidence-to-evidence provenance. This conflicts with [04_Implementation_Roadmap.md Week 19-20 and Tier 3 Exit Criteria](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md) and needs a roadmap/PRD change before the spec can be approved.
- Critical: The candidate-pair contract is still incompatible with the approved ontology. Evidence notes cannot legally own `depends_on` or `draws_from` per [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md), yet Rev 2 depends on them as primary seeds in [folio_provenance_spec.md §§6 D2, 10](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md).
- Major: The namespace fix is incomplete at the lifecycle level. Provenance-specific refresh passthrough and stale handling are only proposed in [folio_provenance_spec.md §19.6](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md); they are not part of the approved refresh contract in [folio_enrich_spec.md §15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) or [02_Product_Requirements_Document.md FR-505](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md).
- Major: `provenance_links` still has no approved ontology contract. Rev 2 is correct to call for an amendment, but that means the spec is still missing the authoritative schema/type-applicability approval in [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md).
- Minor: §19 is materially better now. FR-606 is a good addition, FR-705 is now handled correctly, and FR-403 is acceptable. The remaining documentation gap is not FR-403/606/705; it is the missing roadmap/PRD authorization for the new evidence-to-evidence scope.

# 7. Verdict

Verdict: Request Changes
