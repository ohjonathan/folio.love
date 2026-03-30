# Reviewer 1: Peer Review for Folio Provenance Linking Spec Rev 5

Primary artifact reviewed: [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md)

Reference set checked against:
- [docs/specs/folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md)
- [docs/product/02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md)
- [docs/product/04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md)
- [docs/architecture/Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md)
- [docs/specs/v0.5.1_tier3_entity_system_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/v0.5.1_tier3_entity_system_spec.md)
- [PRD_PhaseB_B2_Consolidation_R4.md](/Users/jonathanoh/Dev/folio.love/PRD_PhaseB_B2_Consolidation_R4.md)

## 1. Completeness Check

Rev 5 is materially more complete than Rev 4. The governance package is now much closer to a real approval bundle: the spec includes explicit appendices for roadmap, ontology, refresh, checklist, and PRD amendments, and the main body now covers the missing surfaces Round 4 called out. The CLI contract, data model, stale lifecycle, sharding ceiling, dry-run parity intent, and test plan are all present.

The remaining completeness problem is not missing sections. It is that some of the most important sections still do not compose into a trustworthy end-to-end lifecycle. In particular, the stale-repair path, state surfacing, and review semantics still have internal contradictions or unsafe shortcuts. So this is no longer “underspecified everywhere,” but it is still not complete enough to approve.

## 2. Quality Assessment

The design is stronger on determinism and operational framing than Rev 4. Pair ordering is now defined, the within-pair shard ceiling is explicit, and the spec is more honest that PR D is an infrastructure slice with an evidence-lineage pilot rather than the originally envisioned deliverable-to-evidence feature.

The main quality problem is that the provenance anchor is still too mutable for the stale lifecycle the spec wants to support. Rev 5 hashes and repairs against per-slide `### Analysis` blocks, but those blocks are enrich-managed machine output in [docs/specs/folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) §D10 and §10. That makes “stale” too easy to trigger for reasons unrelated to underlying evidence, and it weakens the trustworthiness of both the link itself and the repair UX.

## 3. UX Review

Rev 5 improves operator UX meaningfully: pagination is explicit, stale review has doc-level batch actions, protected-note repair now warns before bypassing protection, and dry-run is much closer to a useful planning tool.

The remaining UX issue is state clarity. The spec promises stable IDs, deterministic ordering, visible stale states, and first-class repair actions, but several of those promises are only partially operationalized. The result is that an operator can likely use the happy path, but the review surface still looks brittle under churn: queued re-evaluations are not cleanly surfaced, orphan handling is internally inconsistent, and the semantics of “review” mix a one-shot CLI command with an interactive session model without fully defining either.

## 4. Issues Found

### Critical

1. **`re-evaluate` still bypasses renewed human confirmation for changed content.** In [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §10 step 8 and §13.5, if the next run re-proposes the same coordinates, the spec auto-promotes the link back to `confirmed`. That is an implicit auto-confirmation path after content drift. It conflicts with the spec’s own human-confirmation posture in §6 D6, §13, §18, and Appendix E FR-509, and with the roadmap’s “Human confirmation step for proposed provenance links” in [docs/product/04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md). Same coordinates are not enough to prove semantic equivalence after the hashed content changed.

2. **The target “evidence passage” is an enrich-managed mutable surface, so stale detection will generate false churn.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §6 D4, §11.2, and §9.5 define the target passage as the per-slide `### Analysis` block and hash the full passage content. But [docs/specs/folio_enrich_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md) §D10 and §10 explicitly allow enrich to rewrite those `### Analysis` subtrees. Routine enrich reruns on the target note can therefore stale provenance links even when the underlying deck evidence did not materially change.

3. **`refresh-hashes` is still not verifiable enough for the actual hashed surfaces.** In [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §9.1 and §13.5, stale review relies on persisted snapshots, but the stored material is truncated to 200 characters, the sample stores only a `source_claim_snapshot` even though §9.5 hashes `claim_text + "|" + supporting_quote`, and the target snapshot is described as a summary rather than the full hashed passage. The operator still cannot reliably compare the exact prior hashed content to the current content before choosing `refresh-hashes`.

### Major

1. **Orphan repair is internally contradictory.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §13.5 says orphaned links may use `re-evaluate`, while §14.4 says orphaned links support only `remove` and `acknowledge`.

2. **The status/review surface does not cleanly expose `re_evaluate_pending`, which undermines stale/orphan review at scale.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §14.3 says `re_evaluate_pending` is visible in `status` and `review --stale`, but §8.10’s status table has no column or count for it, and §13.5’s stale ordering omits it.

3. **“Stable proposal IDs” are asserted but not specified.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §8.9 and §13.1 rely on stable `proposal_id` values for deterministic ordering and safe `confirm range`, but §9.2 never defines how proposal IDs are derived or stabilized across reruns and sharded merges.

4. **The review interaction model is under-specified for implementation and automation.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §8.2, §8.9, and §13.2 define `folio provenance review ...` as a command, but the actual mutation verbs are shown as in-session actions (`confirm`, `reject`, `next`, `prev`, `quit`) rather than CLI subcommands or flags. The spec never states whether `review` launches an interactive REPL/TUI, how those actions are parsed, or what the non-interactive equivalent is. This also diverges from the explicit non-interactive confirmation pattern in [docs/specs/v0.5.1_tier3_entity_system_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/v0.5.1_tier3_entity_system_spec.md) §11.1.

### Minor

1. **The stale-state taxonomy is inconsistent across sections.** [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §8.10 presents Fresh, Stale, Acknowledged, and Orphaned as visible states, while §14.3 presents Fresh, Stale, Acknowledged, and Re-evaluate pending, and §18 later says “Stale links: three visible states.”

2. **`acknowledge-doc` does not cover the full stale-review workload.** In [docs/specs/folio_provenance_spec.md](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md) §13.5, batch actions exist for `remove-doc` and `acknowledge-doc`, but only the removal action explicitly includes orphaned links.

## 5. Positive Observations

- The approval package is substantially stronger. Rev 5 does real work to reconcile the spec with the roadmap, ontology, refresh contract, kickoff checklist, and PRD.
- The dry-run contract is much better. Including stale-check preview and protected-note re-evaluate warnings is the right correction to the Rev 4 parity gap.
- The shard ceiling is a real improvement. Rev 5 no longer leaves dense-pair runtime unbounded.
- The spec is more candid about product reality. Framing PR D as provenance infrastructure plus an evidence-lineage pilot is aligned with the current corpus.

## 6. Verdict

**Request Changes**

Rev 5 is close, but the remaining problems are still substantive. The stale-repair path is not trustworthy enough yet, mainly because the spec still auto-reconfirms in one branch and still anchors the target side to an enrich-managed mutable passage.
