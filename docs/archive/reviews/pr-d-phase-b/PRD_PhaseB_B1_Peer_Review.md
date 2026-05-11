# PR D Phase B Peer Review

## 1. Completeness Check

The spec is directionally strong, but it is not complete enough to freeze implementation. The biggest gaps are in the operational contract, not the feature idea: `--limit` is specified as pair-scoped while idempotency is source-document-scoped (§8.6, §10, §15); interaction-note targets are mentioned in extraction (§11.3) but cannot be represented by the proposal/canonical schemas or prompt shape (§9.1, §9.3, §12.1); and the lifecycle for confirmed links after source/target drift is not defined (§13.3, §14.2, §15.4).

The spec also leaves `folio provenance status` materially underspecified. It exists in §8.2 and §18, but there is no output contract, metric definition, or guidance for how “coverage statistics” should treat pending, rejected, confirmed, stale, and orphaned links.

## 2. Quality Assessment

The spec does a good job reusing PR C patterns where they actually fit: canonical/proposed separation (§6 D7), enrich-style protection rules (§14.1), passthrough durability (§9.6, §14.2), and rejection suppression via `basis_fingerprint` (§9.5, §15.3). Those are solid quality choices.

The weaker parts are where the spec claims to “mirror” existing behavior but actually introduces a different problem shape. The entity system spec has a simple registry lifecycle with explicit states and clear non-rewrite semantics (§11.1-§11.4 of the entity spec). Provenance is harder because it stores claim-location pointers inside mutable notes, but the spec does not add the extra lifecycle rules that this harder problem requires.

## 3. UX Review

The review UX in §8.8 does not scale to the scenario you asked about: 50+ pending proposals across 20 source documents. A flat numbered list plus `confirm`, `reject`, `skip`, `quit`, `confirm all`, and `reject all` is workable for a toy queue, but not for a real consultant workflow.

What is missing for practical batch review is a way to narrow the queue before acting: per-document summaries, pagination, filters by confidence/source/target, stable proposal IDs, “review current document only”, range selection, and a way to inspect fuller target context before confirming. Q1 and Q4 being left open (§20.1, §20.4) makes this worse: the default noise floor and whether large documents can flood the queue are not actually settled.

## 4. Issues Found

**Critical**

1. `--limit` is not implementable as written because the batching unit and idempotency unit do not match. §8.6 and §16.2 define `--limit` in document-pair terms, but §10.6-§10.14 and §15.1-§15.2 store one `provenance_input_fingerprint` per source document, computed from all target passages for that source. If a source has 5 targets and the run stops after 2 pairs, the spec never says whether the source fingerprint is withheld, partially recorded, or split per pair. Any choice breaks another part of the contract: either remaining pairs get skipped incorrectly on the next run, or already-processed pairs get re-evaluated forever. `--force` does not fix this; it only bypasses document-level skip (§8.4, §15.3) and still leaves continuation semantics undefined.

2. Interaction-note targets are simultaneously in scope and unrepresentable. §11.3 explicitly defines passage extraction for interaction-note targets, but §9.1 and §9.3 require `target_slide` / `target_evidence.slide_number`, and §12.1 hardcodes passage labels as `Slide {N}`. There is no target-section identifier, no review rendering for non-slide targets, and no canonical schema for confirmed links to interaction sections. This is compounded by §20.2, which recommends deferring interaction-to-interaction provenance to v2. A developer will get stuck immediately on whether interaction targets are supported in v1 or not.

3. The confirmation lifecycle is incomplete once content changes after confirmation. §13.3 promotes a proposal into `provenance_links`, §14.2 says confirmed links are never modified by provenance runs, and §15.4 only talks about stale fingerprints/proposals. There is no state or repair path for a confirmed link whose `source_claim_index` or `source_finding_index` no longer points to the same claim after refresh/re-enrich, or whose target passage changed enough that the confirmed link is now orphaned. The same lifecycle hole exists for pending proposals: §10.11 only suppresses duplicates when the `basis_fingerprint` is unchanged, and §10.13 only says to store new proposals, so changed-basis proposals can accumulate stale pending entries instead of replacing them. This is the main data-integrity gap in the spec.

**Major**

1. The candidate-pair model is too broad and partly directionally wrong for provenance. §6 D2 and §10.4 treat `draws_from`, `depends_on`, `supersedes`, and `impacts` as equivalent provenance candidate edges. But the enrich spec says the current shipped corpus mainly emits `supersedes` for evidence notes and `impacts` for interaction notes, while `draws_from` / `depends_on` are not emitted for the current registry-managed corpus (§13.2 of the enrich spec). `supersedes` is version lineage, not evidence support; `impacts` means an interaction changes a target document, not that the target contains the upstream evidence supporting the interaction. Without per-relation directionality and eligibility rules, the queue will be noisy and semantically inconsistent.

2. The review UX does not provide enough batch-review machinery for real usage. §8.8 and §13.5 give only flat numbering and all-or-nothing bulk actions. For 50+ proposals across 20 documents, the missing pieces are filter/sort primitives, per-document queue summaries, stable identifiers, safer bulk scopes (`confirm doc`, `confirm range`, `reject target`), and resume/progress behavior for partially reviewed queues. As written, the command is likely to push users toward risky `confirm all`/`reject all` behavior.

3. Concurrency is not specified even though provenance shares write surfaces with enrich/refresh. The entity system spec explicitly adopts advisory locking for `entities.json` (§7.8 of the entity spec). Provenance only requires atomic note writes (§10.1), but that is not enough when `folio provenance`, `folio enrich`, and `folio refresh` can all mutate the same note frontmatter and `_llm_metadata.enrich` subtree. The test plan also misses the concurrent provenance/enrich scenario you called out. This needs either an explicit single-note lock/merge contract or an explicit “commands must not run concurrently” rule.

**Minor**

1. `folio provenance status` is underspecified. §8.2 and §18 require it, but the spec never defines what counts as “coverage”: per document, per claim, per candidate pair, or per confirmed link. It also does not define whether rejected or orphaned links count against coverage, so the command cannot be implemented consistently.

2. The test plan is broad, but it still misses several scenarios that the spec itself depends on: partial-source `--limit` continuation, `--limit` combined with `--force`, changed-basis pending proposal replacement, orphaned confirmed link detection, `--include-low` default visibility behavior, bulk review commands, and concurrency with enrich/refresh. Those are not edge polish items; they are where the current contract is weakest.

## 5. Positive Observations

- The canonical/proposed split is well chosen. Keeping proposals under `_llm_metadata.enrich.axes.provenance` and confirmed links in `provenance_links` is the right separation.
- Reusing enrich’s protection and passthrough model is sound. §14.1 and §14.2 align well with the enrich spec’s conservative human-edit posture.
- The spec is honest about bootstrap constraints (§5.3) and avoids pretending the current graph is denser than it is.
- The batch-per-pair LLM strategy (§6 D3, §12) is the right cost direction for v1, even though the surrounding state model still needs work.

## 6. Verdict

This should not be approved yet. The core idea is good, but the spec still has three implementation-blocking gaps: pair-scoped batching vs document-scoped idempotency, interaction-target schema contradictions, and an incomplete lifecycle for confirmed/pending links after note drift. Those need to be resolved before this is safe to hand to an implementer.

Verdict: Request Changes
