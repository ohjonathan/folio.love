# PR D Phase B Consolidation, Round 5

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|---|---|---|---|
| Reviewer 1 | Peer | Request Changes | stale-repair path still not trustworthy; target anchor remains too mutable |
| Reviewer 2 | Alignment | Request Changes | approval package still does not fully reconcile the governing corpus |
| Reviewer 3 | Adversarial | Block | `re_evaluate_pending` can get stuck; over-ceiling pairs lack recovery semantics; live docs still contradict Rev 5 |

## 2. Blocking Issues

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| R5-BLK-01 | The approval package is still not self-complete. Even with Appendices A-E, the governing corpus remains inconsistent: the kickoff tracker still conflicts on sequencing authority and status; the roadmap still has at least one deliverable-centric surface; the baseline memo is still cited but unreconciled; and the PRD patch set is incomplete because FR-403 is still referenced but not actually amended, while FR-402 only gets a partial example. | Reviewer 2, Reviewer 3 | Governance / Approval Corpus | Land or explicitly supersede every conflicting source-of-truth document in the same approval change set, including the kickoff tracker authority sections, the remaining roadmap deliverable sentence, the baseline memo status, and the missing/partial PRD patches. |
| R5-BLK-02 | The stale-repair model is still not trustworthy. The peer reviewer found three linked issues: `re-evaluate` auto-promotes same-coordinate matches back to `confirmed` without renewed human confirmation, the target anchor is the enrich-managed `### Analysis` block so routine enrich churn can stale links spuriously, and `refresh-hashes` still does not preserve enough exact prior content to verify the same hashed surfaces humans are being asked to bless. | Reviewer 1 | Provenance Correctness / UX | Remove the auto-confirm path, anchor provenance to a less mutable evidence surface or justify the current one rigorously, and store/display enough immutable prior content to make `refresh-hashes` a real verification workflow. |
| R5-BLK-03 | The new non-destructive repair flow still has stuck-state failure modes. `re_evaluate_pending` depends on both link status and pair marker state with no self-heal invariant, and over-ceiling pairs can now abort before resolution without a documented recovery contract for pending stale/orphan repairs. | Reviewer 3 | Lifecycle / Runtime / Reliability | Define invariant repair rules for `re_evaluate_pending` state divergence, plus a surfaced terminal/error lifecycle and fallback for stale/orphan repairs that hit the shard ceiling. |

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| R5-SF-01 | Orphan repair is still internally contradictory: `re-evaluate` is allowed in §13.5 but disallowed in §14.4. | Reviewer 1, Reviewer 2 | Make the orphan policy consistent in one direction and align both sections. |
| R5-SF-02 | `re_evaluate_pending` is said to be visible in status/review, but the status table and stale ordering do not clearly expose it. | Reviewer 1 | Add an explicit status column/count and review ordering rule for pending re-evaluations. |
| R5-SF-03 | Stable `proposal_id` behavior is asserted but not specified, weakening deterministic ordering and `confirm range`. | Reviewer 1 | Define how proposal IDs are generated and stabilized across reruns and sharded merges. |
| R5-SF-04 | The review interaction model is still under-specified. The spec mixes one-shot CLI commands with in-session verbs but never defines whether `review` is interactive, what non-interactive equivalents exist, or how those mutations are invoked programmatically. | Reviewer 1 | Define the actual interface shape: REPL/TUI, explicit subcommands, or both. |
| R5-SF-05 | Seeded real-library validation is still too weak because dense/over-ceiling behavior is only exercised “if the seeded pair is sufficiently large.” | Reviewer 3 | Require the real-library gate to prove both sharded behavior and over-ceiling failure handling. |
| R5-SF-06 | Snapshot-based verification is still weak for dense notes because both claim and passage snapshots are truncated to 200 characters. | Reviewer 1, Reviewer 3 | Store enough immutable prior content to verify the exact hashed surfaces or explicitly downgrade `refresh-hashes` to a lighter-weight action. |
| R5-SF-07 | The stale/orphan lifecycle still has state-taxonomy inconsistencies across sections and acceptance criteria. | Reviewer 1, Reviewer 2, Reviewer 3 | Normalize the visible-state model across §8.10, §14.3, §14.4, and §18. |
| R5-SF-08 | The live refresh contract remains only conditionally aligned until Appendix C is treated as an actual superseding patch to the enrich spec. | Reviewer 2 | Land or formally supersede the live enrich refresh contract in the same approval package. |
| R5-SF-09 | Review-surface mitigation is still weak against a corpus that is already 94% flagged. | Reviewer 3 | Provide a dedicated provenance triage surface or more explicit operator guidance so the additive flag does not disappear into existing noise. |

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| R5-MN-01 | `acknowledge-doc` does not clearly cover orphaned links even though `remove-doc` does. | Reviewer 1 |
| R5-MN-02 | Appendix E ends with a malformed trailing line outside the quoted amendment block. | Reviewer 2 |
| R5-MN-03 | The security treatment is still thin for an LLM workflow touching author-controlled content. | Reviewer 3 |

## 5. Agreement Analysis

Strong agreement:

- All three reviewers say Rev 5 is materially better than Rev 4.
- No reviewer approved the spec.
- Reviewers 2 and 3 independently say the approval corpus is still not fully reconciled, even after the expanded appendix package.
- Reviewers 1 and 3 independently say the new stale-repair design still creates unsafe or stuck states, though they emphasize different parts of the workflow.

Disagreements or partial disagreements:

| Topic | Views | Recommendation |
|---|---|---|
| What is still most blocking | Reviewer 1 focuses on stale-repair trust: mutable evidence anchors, insufficient snapshots, and auto-reconfirmation. Reviewer 2 focuses on governance completeness. Reviewer 3 blocks on both governance and the new pending/ceiling failure modes. | Treat this as two distinct blocker clusters, not one. Governance is still incomplete, and the stale-repair model still is not trustworthy enough. |
| Whether Rev 5’s core architecture is basically settled | Reviewer 2 says the core v1 provenance shape is now substantially aligned. Reviewer 1 says the core anchor choice is still wrong because it points at mutable enrich output. Reviewer 3 focuses on lifecycle resilience rather than the graph shape itself. | Do not over-read Reviewer 2’s mechanical approval. The anchor choice and repair semantics still keep the design below proceed-ready. |
| Severity of the new shard ceiling | Reviewer 1 treats the ceiling as a real improvement. Reviewer 3 says it introduces a new bounded-but-unrepairable failure mode unless over-ceiling repairs have a terminal contract. Reviewer 2 does not foreground runtime here. | Keep the ceiling, but add explicit lifecycle handling for over-ceiling repairs before proceeding. |

Resolution guidance under the review rules:

- The approval-corpus findings are factual contradictions with live referenced docs, so they remain blocking.
- The stale-repair objections are not reviewer misunderstandings. They follow directly from Rev 5’s persisted state, auto-promotion rule, and target-anchor choice.
- Single-reviewer blockers were preserved: the mutable-anchor/auto-confirm concern from Reviewer 1 and the `re_evaluate_pending` / over-ceiling stuck-state concern from Reviewer 3 remain visible as independent blockers.

## 6. Required Actions for CA

| Priority | Action | Estimated Effort |
|---|---|---|
| 1 | Finish the approval package so every cited governing document is either patched or explicitly superseded, including the kickoff tracker authority/status sections, the remaining roadmap deliverable sentence, the baseline memo, and the missing/partial PRD FR coverage. | Large |
| 2 | Redesign stale repair so it never auto-confirms after drift and no longer depends on an enrich-managed mutable target surface for correctness. | Large |
| 3 | Add durable recovery rules for `re_evaluate_pending` divergence and for stale/orphan repairs that hit the shard ceiling. | Medium |
| 4 | Strengthen `refresh-hashes` verification with enough immutable prior content to review the actual hashed surfaces. | Medium |
| 5 | Specify the review interface concretely, including how mutation actions are invoked and how `re_evaluate_pending` is surfaced in status/review. | Medium |
| 6 | Tighten the real-library validation gate so it must exercise both sharded and over-ceiling paths. | Medium |

## 7. Risk Assessment

The CA still does not state an explicit risk level. Reviewer 3 again assigns **High** risk and blocks the spec. Reviewers 1 and 2 do not assign numeric labels, but neither approves.

The Round 5 signal is clearer than Round 4:

- The mechanical design and amendment package are closer.
- The remaining blockers are no longer broad “spec quality” complaints. They are concentrated in approval-corpus completeness and stale-repair correctness/lifecycle trust.
- Because all three reviewers still withheld approval and one still blocks at High risk, this is still not good to proceed.

## 8. Open Questions

Rev 5 Section 20 still contains only **Q1-Q2**.

| Open Question | Reviewer Positions |
|---|---|
| Q1: Confidence threshold (`medium+`) | No reviewer challenged `medium+` in Round 5. This remains effectively accepted. |
| Q2: Infrastructure-slice naming | Reviewer 2 says naming is no longer the real issue; the remaining problem is that the governing corpus is still not fully reconciled. Reviewer 1 accepts the infrastructure framing but still rejects the repair model. Reviewer 3 says the package remains brittle until the actual live docs match it. Recommendation: treat naming as settled enough; the unresolved problem is still the approval corpus plus repair correctness. |
