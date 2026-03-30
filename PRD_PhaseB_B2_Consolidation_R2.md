# PR D Phase B Consolidation, Round 2

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|---|---|---|---|
| Reviewer 1 | Peer | Request Changes | ontology-illegal seed graph for evidence notes; undefined bidirectional `supersedes`; stale/orphan review path still incomplete |
| Reviewer 2 | Alignment | Request Changes | evidence-to-evidence scope still off-plan; candidate-pair contract still violates approved ontology; refresh/ontology amendments are still only proposed, not approved |
| Reviewer 3 | Adversarial | Block | seed model still misaligned with ontology/baseline; reruns can re-propose already-confirmed links; warning-only concurrency remains unsafe |

## 2. Blocking Issues

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| R2-BLK-01 | Evidence-only v1 still depends on `draws_from` / `depends_on` as primary provenance seeds even though the approved ontology restricts those fields to `analysis` / `deliverable`, not `evidence`. | Reviewer 1, Reviewer 2, Reviewer 3 | Ontology / Seed Model | Either change v1 to a seed model that is legal on evidence notes, or amend the ontology and upstream plan before approval. |
| R2-BLK-02 | Rev 2 still changes the approved feature from deliverable-to-evidence provenance to evidence-to-evidence provenance. This remains a roadmap/PRD scope change, not just a clarification. | Reviewer 2, Reviewer 3 | Roadmap / Scope | Amend the roadmap/PRD to authorize the narrowed slice, or realign the spec to the approved deliverable-to-evidence scope. |
| R2-BLK-03 | `supersedes` is now the only practical v1 seed on the approved baseline, but the “bidirectional comparison” semantics are still not representable in the one-way source→target pipeline or source-note storage model. | Reviewer 1, Reviewer 3 | Runtime / Data Model | Make `supersedes` one-way in v1, or define reverse-direction scope, storage, prompting, and review behavior explicitly. |
| R2-BLK-04 | Reruns can still re-propose already-confirmed links because confirmed links are immutable but are not used as a dedupe or suppression surface during reconciliation. | Reviewer 3 | Lifecycle / Data Integrity | Define confirmed-link dedupe/reconciliation semantics so changed pairs and `--force` cannot emit duplicates into `provenance_links`. |
| R2-BLK-05 | The stale/orphan lifecycle is still incomplete. `--stale` discovers problems, but the CLI action grammar, ID model, acknowledgement state, and `stale_pending` schema are not fully defined. | Reviewer 1, Reviewer 3 | Review Workflow / Lifecycle | Add first-class stale/orphan actions, IDs, and persisted state, and make the metadata schema allow every status the spec uses. |
| R2-BLK-06 | `provenance_links` and provenance refresh durability still depend on unapproved ontology and refresh-contract amendments. Rev 2 correctly calls that out, but that means the approval-ready authoritative contract still does not exist. | Reviewer 2 | Architecture / Governance | Land or approve the ontology and refresh amendments before treating the spec as final. |

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| R2-SF-01 | Pagination is still claimed in the revision note and resolution map, but no actual pagination contract exists in the CLI or review sections. | Reviewer 1 | Define page size, ordering, and next/prev behavior for large queues. |
| R2-SF-02 | `folio provenance status` defines coverage as confirmed non-stale links / total claims, which can exceed 100% when one claim has multiple confirmed links. | Reviewer 1 | Redefine coverage in terms of distinct claims with at least one confirmed non-stale link. |
| R2-SF-03 | Overflow sharding is still not deterministic enough for dense-pair stability. Overlap is mentioned but undefined, and the “single passage too large” case is not handled. | Reviewer 3 | Specify stable chunk construction, overlap rules, and single-passage overflow handling. |
| R2-SF-04 | The single-writer rule is only partially specified and only warning-tested. Cross-command overlap remains unsafe in practice. | Reviewer 1, Reviewer 3 | Strengthen enforcement or narrow the write model so overlapping commands cannot silently clobber frontmatter. |
| R2-SF-05 | The approved v1 relationship recommendation still differs from Rev 2’s operational seed model: architecture says start with `depends_on` / `draws_from` / `impacts`, but Rev 2 uses `supersedes` and excludes `impacts`. | Reviewer 2 | Either reconcile the architecture recommendation or explicitly document why PR D is intentionally diverging. |
| R2-SF-06 | Yield realism remains weak: Rev 2 is more honest, but the user-visible value is still near-zero on the approved baseline until humans seed relationships. | Reviewer 1, Reviewer 3 | Rename or frame the slice as infrastructure if that is the real deliverable, and update acceptance criteria accordingly. |
| R2-SF-07 | Prompt-injection resistance is not addressed at all, despite feeding free-form note content into the matching prompt. | Reviewer 3 | Add a prompt-safety assumption or mitigation note if the feature is expected to operate on arbitrary note content. |

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| R2-MN-01 | The namespace fix itself is good; the remaining problem is governance and lifecycle approval, not local structure. | Reviewer 2 |
| R2-MN-02 | Rev 2 is materially more internally aligned than Rev 1, especially around pair fingerprints, dedicated namespace, and the evidence-only extractor. | Reviewer 1 |
| R2-MN-03 | The PRD patch section is substantially better in Rev 2; the remaining documentation gap is scope authorization, not FR bookkeeping. | Reviewer 2 |

## 5. Agreement Analysis

Strong agreement:

- All three reviewers say Rev 2 is materially better than Rev 1, but still not approval-ready.
- All three reviewers converge on the same central blocker: the revised seed graph is still not legal or workable for evidence-only v1 under the current ontology and baseline.
- Two reviewers independently say the only practical current-baseline seed, `supersedes`, is still under-modeled.
- Two reviewers independently say the stale/orphan link path is improved in visibility but still incomplete as an operator workflow.

Disagreements or partial disagreements:

| Topic | Views | Recommendation |
|---|---|---|
| Whether evidence-only narrowing is an acceptable interim slice | Reviewer 1 sees it as a real internal improvement. Reviewer 2 says it is still an unauthorized roadmap/PRD scope change. Reviewer 3 says it may be acceptable only if treated as an infrastructure slice rather than the promised user-visible capability. | Treat this as a governance decision, not a wording tweak. Either authorize the narrower slice upstream or stop describing it as the approved PR D deliverable. |
| How complete the namespace fix is | Reviewer 2 says `_llm_metadata.provenance` is the right local fix, but lifecycle approval is still missing. Reviewer 1 sees architecture as generally stronger. Reviewer 3 focuses elsewhere. | Keep the namespace change, but do not count it as “fully resolved” until refresh and ontology amendments are actually approved. |
| Concurrency severity | Reviewer 1 calls the single-writer story only partially specified and tested. Reviewer 3 says warning-only PID checks are still high-risk operationally weak. Reviewer 2 does not foreground concurrency. | Do not smooth this over. The current story is still advisory, not protective. Either enforce more or explicitly narrow the safety claim. |

Resolution guidance under the review rules:

- The new round did not expose reviewer misunderstanding. The remaining issues are direct consequences of the revised text.
- The main disagreements are about how much governance change is acceptable, not whether the cited contradictions exist.

## 6. Required Actions for CA

| Priority | Action | Estimated Effort |
|---|---|---|
| 1 | Fix the seed model. Make the primary provenance-seed edges legal on the source/target document types that v1 actually uses, or amend the ontology and upstream planning docs to authorize the new model. | Large |
| 2 | Resolve the feature-scope mismatch with the roadmap/PRD: either authorize evidence-to-evidence as the approved PR D slice or restore deliverable-to-evidence scope. | Large |
| 3 | Make `supersedes` semantics explicit. Either narrow it to one-way provenance in v1 or define the reverse-direction execution/storage/review model completely. | Medium |
| 4 | Add confirmed-link dedupe/reconciliation semantics so reruns cannot recreate already-confirmed links. | Medium |
| 5 | Finish the stale/orphan workflow: stale-link IDs, command grammar, persisted acknowledgement state, and schema support for every status in the lifecycle. | Medium |
| 6 | Make overflow sharding deterministic and testable, including the “single passage too large” case. | Medium |
| 7 | Strengthen concurrency beyond warning-only PID advice, or lower the claimed safety bar. | Medium |
| 8 | Update review/status UX details: actual pagination and a coverage metric that cannot exceed 100%. | Small |

## 7. Risk Assessment

The CA still does not state an explicit risk level in the spec. Reviewer 3 again assigns **High** risk. Reviewer 1 and Reviewer 2 do not label risk numerically, but their remaining blockers reinforce that assessment: the seed graph is still illegal on the target doc type, the authorized scope is still unsettled, and lifecycle completion remains incomplete. No reviewer argued that Rev 2 is low risk.

## 8. Open Questions

| Open Question | Reviewer Positions |
|---|---|
| Q1: Confidence threshold for default review display | No reviewer challenged the `medium+` default directly in Round 2. Reviewer 1’s UX concerns were about pagination, stale-item grammar, and misleading coverage rather than the threshold itself. |
| Q2: `supersedes` as provenance seed | Reviewer 1 says `supersedes` is the first practical v1 seed on the current baseline but its bidirectionality is under-specified. Reviewer 2 says the approved relationship recommendation differs and Rev 2 is operationalizing `supersedes` earlier than the architecture suggests. Reviewer 3 says `supersedes` is the only realistic v1 seed but its bidirectional model is still not representable. Recommendation: include only if it is made one-way in v1 or fully modeled both ways. |
| Q3: `provenance_links` field naming | No reviewer objected to the name itself. Reviewer 2 says the real issue is that the field still lacks an approved ontology contract. |
| Q4: Protection rules for L1+ notes | Reviewer 2 says metadata-only handling is broadly compatible with enrich. Reviewer 3 raises repairability concerns for protected notes with stale/orphaned links. Recommendation: the metadata-only stance is acceptable, but the stale-link repair workflow has to be first-class. |
| Q5: Removed in Rev 2 | Rev 1 had a Q5 about `.overrides.json` sequencing. Rev 2 removes that open question and treats the sidecar boundary as settled. No reviewer re-opened it in Round 2. |
