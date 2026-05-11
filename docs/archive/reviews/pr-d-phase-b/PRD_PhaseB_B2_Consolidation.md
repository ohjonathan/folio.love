# PR D Phase B Consolidation

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|---|---|---|---|
| Reviewer 1 | Peer | Request Changes | `--limit` vs source-scoped fingerprinting; interaction-target schema contradiction; undefined stale/orphaned-link lifecycle |
| Reviewer 2 | Alignment | Request Changes | `provenance_links` not in approved ontology schema; provenance state coupled to `_llm_metadata.enrich`; roadmap drift from deliverable-to-evidence to evidence/interaction-source provenance |
| Reviewer 3 | Adversarial | Block | source-level fingerprinting incompatible with pair-level execution; no context-budget fallback for dense real-library pairs |

## 2. Blocking Issues

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| BLK-01 | `--limit` is pair-scoped, but idempotency and skip state are source-scoped via one `provenance_input_fingerprint` per source. Partial runs, interruption recovery, and continuation semantics are undefined. | Reviewer 1, Reviewer 3 | Idempotency / Runtime | Pick one execution unit and make `--limit`, progress, skip, and stored state all use that same unit. |
| BLK-02 | The spec says the roadmap slice is deliverable-to-evidence provenance, but the actual extraction contract only defines source claims for evidence and interaction notes. | Reviewer 2, Reviewer 3 | Roadmap / Scope | Either add deliverable claim extraction and align the rest of the contract, or explicitly narrow and rename the v1 slice. |
| BLK-03 | Interaction-note targets are simultaneously allowed and unrepresentable. The spec extracts interaction targets, but proposal and canonical schemas only support slide-based target identifiers. | Reviewer 1 | Data Model / Contract | Decide whether interaction targets exist in v1. If yes, add target-section identifiers, review rendering, and canonical schema. If no, remove them from extraction and prompt contracts. |
| BLK-04 | `provenance_links` is introduced as a new top-level canonical field, but the approved ontology schema does not currently allow it or define document-type applicability rules for it. | Reviewer 2 | Ontology / Schema | Amend the ontology first or change the design so canonical provenance state fits an approved schema. |
| BLK-05 | Provenance is a separate command, but its machine state is stored under `_llm_metadata.enrich.axes.provenance`, creating an unapproved coupling to enrich lifecycle and refresh semantics. | Reviewer 2 | Architecture / Lifecycle | Either define a formally shared enrich-provenance metadata contract or move provenance state into a dedicated namespace with its own refresh/stale rules. |
| BLK-06 | Confirmed-link and pending-proposal lifecycles are incomplete after refresh, re-enrich, or reruns. Orphaned confirmed links, changed-basis pending proposals, and replacement vs append semantics are undefined. | Reviewer 1, Reviewer 3 | Lifecycle / Data Integrity | Define stale confirmed-link detection, surfacing, repair flow, and pending-proposal reconciliation rules. |
| BLK-07 | One-call-per-pair has no context-budget policy or fallback, despite validated 90-slide and 137-slide notes in the production corpus. | Reviewer 3 | Runtime / LLM Contract | Add preflight token estimation plus a deterministic overflow fallback such as sharding or passage truncation rules. |

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| SF-01 | The candidate-pair model treats `draws_from`, `depends_on`, `supersedes`, and `impacts` as equivalent provenance seeds even though those edges do not mean the same thing and PR C currently seeds mostly `supersedes` and `impacts`. | Reviewer 1, Reviewer 2 | Define relation-type eligibility and directionality rules before implementation. |
| SF-02 | `folio provenance review` and `folio provenance status` are underspecified for real operator use: no filters, pagination, stable IDs, range actions, resume semantics, or coverage metric definition. | Reviewer 1 | Add a concrete review/status contract, not just command names and a toy transcript. |
| SF-03 | Bootstrap utility on the approved baseline is unproven because canonical relationship density is likely low and the production vault currently has 0 interaction notes in active use. | Reviewer 3, Reviewer 2 | Measure current candidate-pair density on the approved corpus or narrow the v1 value claim. |
| SF-04 | Concurrent `folio enrich`, `folio provenance`, and `folio refresh` runs can silently clobber note updates because atomic writes alone do not coordinate multiple writers. | Reviewer 1, Reviewer 3 | Add a single-writer rule, locking, or an explicit operational prohibition on concurrent runs. |
| SF-05 | The PRD patch mapping is incomplete or stretched: `FR-606` and likely `FR-403` are missing, and `FR-705` is being used beyond its current `.overrides.json` meaning. | Reviewer 2 | Rework the PRD patch set before approval. |
| SF-06 | The protection-rule story is inconsistent. Enrich still permits metadata updates on protected notes, but provenance claims to “inherit” enrich rules while fully skipping protected documents. | Reviewer 2, Reviewer 3 | Decide whether provenance should allow metadata-only work on protected notes or explicitly diverge from enrich. |
| SF-07 | Retry semantics for unchanged rejections remain awkward: `--force` still respects unchanged rejection bases, so operator retry is not explicit. | Reviewer 3 | Add an explicit retry path or make the CLI explain why nothing was retried. |

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| MN-01 | The spec says the provenance fingerprint model follows enrich “exactly,” but it is only analogous to the shipped enrich fingerprint contract. | Reviewer 2 |
| MN-02 | The passthrough implementation note is incomplete because refresh currently requires both extraction and injection helper changes, not just one helper. | Reviewer 2 |
| MN-03 | The spec leans on Dataview-queryable frontmatter for usability, but the validated daily-use vault did not have the Dataview plugin installed. | Reviewer 3 |

## 5. Agreement Analysis

Strong agreement:

- Two reviewers independently flagged the `--limit` / source-fingerprint mismatch as a blocker. This is the clearest multi-reviewer signal.
- Two reviewers independently flagged stale-link and rerun lifecycle gaps. Both focus on trust-surface failures rather than UX polish.
- Two reviewers independently flagged scope drift between the spec’s narrative and what the actual extraction contract supports.
- Multiple reviewers questioned whether PR C’s current relationship outputs are sufficient or semantically appropriate to seed provenance.

Disagreements or partial disagreements:

| Topic | Views | Recommendation |
|---|---|---|
| Reusing enrich patterns vs reusing the enrich namespace | Reviewer 1 says the canonical/proposed split and reuse of enrich-style protection and passthrough are good choices. Reviewer 2 says `_llm_metadata.enrich.axes.provenance` is a critical architectural deviation for a separate command. Reviewer 3 says the coupling creates stale/concurrency risk. | Keep the conceptual reuse if desired, but do not assume that justifies namespace reuse. Either formalize a shared lifecycle/schema contract or separate the namespaces. |
| How severe the current graph-density problem is | Reviewer 1 says the spec is honest about sparse bootstrap conditions but the relation semantics are too broad/noisy. Reviewer 2 says the baseline description is accurate but the spec overstates how much PR C currently seeds provenance. Reviewer 3 says utility on the approved baseline is unproven and may make PR D mostly empty. | Measure the actual current candidate-pair density and expected yield before approval. Facts should replace speculation here. |
| Whether the biggest gap is architecture or runtime | Reviewer 2 emphasizes ontology/schema/roadmap deviations. Reviewer 3 emphasizes idempotency, overflow, and stale-state failures. Reviewer 1 emphasizes implementability and lifecycle completeness. | Treat all three as blocking. The spec is not one fix away from approval; it needs coordinated scope, schema, and runtime changes. |
| Review-UX severity | Reviewer 1 treats the current review UX as a major practical problem. Reviewer 2 and Reviewer 3 do not center UX, though Reviewer 3’s proposal-instability findings imply more review noise. | Do not downgrade UX just because only one reviewer foregrounded it. The operator contract is part of the feature, and the current queue model is not ready for production-scale use. |

Resolution guidance under the review rules:

- No reviewer appears to have simply misunderstood the spec. The contradictions they point at are real textual contradictions or omissions.
- The major disagreements are about prioritization and boundary-setting, not whether the cited facts exist.

## 6. Required Actions for CA

| Priority | Action | Estimated Effort |
|---|---|---|
| 1 | Redesign execution state so the unit of fingerprinting, skip, progress, and `--limit` all match. | Large |
| 2 | Resolve source/target scope. Decide whether v1 is truly deliverable-to-evidence, whether interaction targets exist, and update extraction plus schemas accordingly. | Large |
| 3 | Amend the architecture contract: approve a canonical provenance field with type applicability, and decide whether provenance state stays under `_llm_metadata.enrich` or moves to its own namespace. | Large |
| 4 | Define stale-link, rerun, and reconciliation behavior for both confirmed and pending provenance records. | Large |
| 5 | Add a context-budget preflight and deterministic overflow fallback for dense document pairs. | Medium |
| 6 | Measure approved-baseline candidate-pair density and tighten eligible relationship types/directions so the pipeline is justified and semantically coherent. | Medium |
| 7 | Specify the operator surface: review filters/IDs/ranges, `status` coverage metrics, safer bulk actions, and an explicit concurrency/single-writer rule. | Medium |
| 8 | Rework the PRD patch implications to include the right FRs and stop stretching `FR-705`. | Small |

## 7. Risk Assessment

The CA did not state an explicit risk level in the spec. Reviewer 3 independently assigns **High** risk and justifies it with unresolved lifecycle, retry, stale-state, and concurrency failures on the trust surface. Reviewer 1 and Reviewer 2 did not label risk formally, but their findings reinforce that assessment by identifying blocking gaps in implementability, architecture, and roadmap alignment. No reviewer argued that the spec is low risk.

## 8. Open Questions

| Open Question | Reviewer Positions |
|---|---|
| Q1: Confidence threshold for default review display | Reviewer 1 says the default noise floor is still unsettled and tied to broader review-UX gaps. No reviewer explicitly endorsed either `medium+` or `high` only. |
| Q2: Interaction-to-interaction provenance | Reviewer 1 says the spec is contradictory because interaction targets are implemented in extraction but recommended for deferral in §20. Reviewer 3 notes interaction targets are not present in the approved production vault anyway. Recommendation: either defer cleanly and remove interaction-target support from v1, or fully specify it. |
| Q3: `provenance_links` field naming | Reviewer 2 says the naming question is secondary because any new top-level canonical field is currently a schema deviation. No reviewer defended `provenance` over `provenance_links`. |
| Q4: Maximum proposals per document | Reviewer 1 says the current queue model does not scale and needs filtering, pagination, stable IDs, and safer bulk review before the team can sensibly answer whether a cap is required. No reviewer explicitly supported a hard cap. |
| Q5: `.overrides.json` PR sequencing | No reviewer explicitly objected to keeping `.overrides.json` separate, but Reviewer 2 says the current PRD mapping wrongly stretches `FR-705` beyond body-override persistence. Recommendation: keep sequencing separate if desired, but do not treat confirmed provenance frontmatter as a subtype of override persistence. |
