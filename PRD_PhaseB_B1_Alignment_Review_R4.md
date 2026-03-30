# Architecture Compliance

Rev 4 is directionally aligned with the shipped Tier 3 baseline on two important points. First, it keeps `.overrides.json` out of PR D and treats override persistence as a separate prerequisite, which is consistent with [FR-705](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md#L659) and the sequencing rule in [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L265). Second, its use of `supersedes` as the only currently legal evidence-note seed is consistent with the ontology’s current field applicability in [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L787) and with the PR C corpus-driven reorder already documented in [folio_enrich_spec.md §5.3](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L172).

The approval problem is that Rev 4 does not fully reconcile itself with the approved architecture corpus. The ontology still says relationships are stored as ID references and that v1 should start with `depends_on`, `draws_from`, and `impacts` in [Folio_Ontology_Architecture.md §6.3-§6.4](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L442). Appendix B only adds a `provenance_links` row and schema subsection in [folio_provenance_spec.md Appendix B](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1057); it does not amend the earlier architectural statements that Rev 4 now depends on. That leaves the ontology internally inconsistent even if this spec were approved as written.

# Roadmap Alignment

Rev 4 correctly anchors itself to the post-PR-C operational baseline described in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L429) and [tier3_baseline_decision_memo.md](/Users/jonathanoh/Dev/folio.love/docs/product/tier3_baseline_decision_memo.md#L227): PR C is shipped, the retained production library is the baseline, and per-stage routing is not a prerequisite. On that point, the spec is aligned with the latest approved product baseline, not the older kickoff wording.

The misalignment is scope. The approved roadmap still defines PR D as “match deliverable claims against library evidence” and the Tier 3 exit criterion as “Retroactive provenance links deliverable slides to evidence” in [04_Implementation_Roadmap.md §Week 19-20 / Tier 3 Exit Criteria](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L427). The kickoff checklist says the same in [tier3_kickoff_checklist.md §PR D](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L195). Rev 4 re-scopes PR D to an evidence-to-evidence `supersedes` pilot in [folio_provenance_spec.md §1-§4](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L47). That is a substantive roadmap change, not a clarification.

Appendix A is also incomplete as a roadmap fix. It patches the provenance bullet and exit criterion in [folio_provenance_spec.md Appendix A](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1022), but it does not patch the still-conflicting roadmap line “Relationship types active: depends_on, draws_from, impacts” in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L439), and it does not add `folio provenance` to the roadmap CLI map in [04_Implementation_Roadmap.md §Updated CLI Command Map](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L550). The roadmap would remain inconsistent after the proposed amendment set.

# Constraint Verification

Rev 4 respects several current constraints. It keeps PR D narrow, treats human confirmation as mandatory, preserves FR-705 separation, and uses `supersedes` because `depends_on` and `draws_from` are not legal on evidence notes under [Folio_Ontology_Architecture.md §12.3](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L787). Its refresh-preservation intent also matches the non-destructive lifecycle requirement already established for PR C in [folio_enrich_spec.md §15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1149).

The constraint failure is governance, not mechanics. Rev 4 states that roadmap, ontology, and refresh amendments are “approved as part of this spec package” in [folio_provenance_spec.md §21](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L987). The current approved corpus does not yet reflect those changes. Under the stated review mandate, that is still a deviation until the authoritative docs are actually amended or explicitly approved as a bundled corpus update.

# Backward Compatibility

The proposed runtime behavior is mostly conservative. Rev 4 preserves human-confirmed state, avoids body mutation, and keeps stale-link repair explicit in [folio_provenance_spec.md §9.8, §13.5, §14](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L467). That is compatible with the trust/reviewability model in [Folio_Ontology_Architecture.md §2.7](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L108).

The backward-compatibility gap is still the refresh contract. The approved enrich spec currently allows refresh passthrough only for human-confirmed canonical relationship fields and `_llm_metadata.enrich` in [folio_enrich_spec.md §15.2](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1149). Rev 4 depends on preserving `provenance_links` and `_llm_metadata.provenance` in [folio_provenance_spec.md §9.7-§9.8 and Appendix C](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L462). Until that upstream contract is actually amended, the spec is not backward-compatible with the approved refresh behavior.

# Consistency Check

Rev 4 is internally coherent on the stale-link lifecycle, confirmation flow, and `supersedes`-only pair model. It is also consistent with PR C’s documented “corpus-driven priority reordering” in [folio_enrich_spec.md §5.3, §13.2, §18.9](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L172).

It is not yet consistent with the full approved corpus:

- The PRD still has no approved `folio provenance` command family, no `routing.provenance`, no `provenance_links`, and no explicit refresh passthrough for provenance state in [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md#L409).
- The roadmap still describes PR D as deliverable-to-evidence provenance and omits `folio provenance` from the CLI map in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L427).
- The ontology still models relationship storage and v1 ordering in ways Appendix B does not fully amend in [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L442).
- The kickoff checklist still defines PR D as deliverable-claim linkage in [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L195).

# Deviation Report

## Critical

1. Governance is still unresolved in the approved corpus. Rev 4 treats the roadmap, ontology, and refresh changes as already approved package dependencies in [folio_provenance_spec.md §21](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L987), but the current authoritative documents still disagree on PR D scope, allowed frontmatter, and refresh passthrough in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L427), [Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L787), and [folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1149).
2. The roadmap amendment set is incomplete. Appendix A updates the provenance bullet and exit criterion, but leaves the conflicting “Relationship types active” statement and the Tier 3 CLI command map untouched in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L439). The roadmap would still not match the spec after the proposed patch.
3. The ontology amendment set is incomplete. Appendix B adds `provenance_links` to §12.3, but it does not amend the earlier architectural rules that relationships are stored as ID references and that v1 starts with `depends_on`, `draws_from`, and `impacts` in [Folio_Ontology_Architecture.md §6.3-§6.4](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L442). The spec therefore does not make the ontology approval-ready.

## Major

1. PRD amendment coverage is not explicit enough. Rev 4 lists impacted FRs in [folio_provenance_spec.md §19](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L959), but it does not provide exact amendment text for FR-402, FR-505, FR-604, FR-701, FR-706, or the new provenance command requirement. The current PRD remains materially incomplete for this feature in [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md#L409).
2. PR D scope still deviates from the approved PR map and checklist. The approved planning docs define PR D as deliverable-claim to evidence linking in [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L195) and [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L437). Rev 4 changes that to evidence-version-lineage provenance in [folio_provenance_spec.md §1](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L47). That may be strategically reasonable, but it is still a deviation pending explicit corpus updates.

## Minor

1. Rev 4 overstates readiness by marking amendment approval as a checked precondition in [folio_provenance_spec.md §21](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L989) before those upstream documents are actually amended.
2. The reference corpus itself is partially stale on current status. The roadmap and baseline memo treat PR C as shipped in [04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L429) and [tier3_baseline_decision_memo.md](/Users/jonathanoh/Dev/folio.love/docs/product/tier3_baseline_decision_memo.md#L361), while the kickoff checklist still describes PR C and vault validation as not yet complete in [tier3_kickoff_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L51). That does not invalidate Rev 4, but it does mean the approval package should explicitly state which late-March baseline documents supersede the older checklist wording.

# Verdict

Request Changes.

Rev 4 is closer on mechanics and on narrow-slice discipline, but it is not yet approval-ready as an alignment artifact. The main blocker is not the provenance pipeline itself; it is that the proposed appendix package does not fully amend every authoritative document surface it now contradicts. Until the roadmap, ontology, refresh contract, and PRD coverage are made explicitly consistent, this remains a governance deviation from the approved corpus.
