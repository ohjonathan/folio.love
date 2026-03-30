# PR D Phase B Consolidation, Round 3

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|---|---|---|---|
| Reviewer 1 | Peer | Request Changes | governing contract still unresolved; stale lifecycle still incomplete at scale |
| Reviewer 2 | Alignment | Request Changes | roadmap/PRD scope still unapproved; ontology and refresh durability contracts still unapproved |
| Reviewer 3 | Adversarial | Block | governance preconditions still unmet; same-coordinate stale repair can semantically preserve wrong canonical links |

## 2. Blocking Issues

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| R3-BLK-01 | The approved roadmap/PRD still describes PR D as deliverable-to-evidence provenance using `depends_on` / `draws_from` / `impacts`, while Rev 3 specifies an evidence-to-evidence `supersedes`-based infrastructure slice. The spec now names this as a required amendment, but that means the governing scope is still not approved. | Reviewer 1, Reviewer 2, Reviewer 3 | Roadmap / Scope / Preconditions | Approve or land the roadmap/PRD amendment first, or realign the spec back to the currently approved PR D scope. |
| R3-BLK-02 | The storage and durability contract is still not authorized upstream. `provenance_links` is not in the approved ontology/frontmatter baseline, and the current refresh contract still does not preserve `provenance_links` or `_llm_metadata.provenance`. | Reviewer 1, Reviewer 2 | Ontology / Refresh Contract | Approve the ontology amendment and refresh passthrough amendment before treating this as an implementation-ready spec. |
| R3-BLK-03 | Same-coordinate stale handling is still semantically unsafe. Confirmed-link dedupe suppresses reproposals at the same coordinates even after content changes, and `reconfirm` only refreshes hashes from current content rather than re-validating the link semantically. | Reviewer 3 | Provenance Correctness / Lifecycle | Redesign stale confirmed-link repair so changed links can re-enter semantic review, or make `reconfirm` a true semantic confirmation flow instead of a hash refresh. |

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| R3-SF-01 | `acknowledged_stale` still does not close the lifecycle cleanly. Once acknowledged, a link drops out of stale detection/counts, but no separate surfaced state keeps it visible as intentionally non-fresh. | Reviewer 1, Reviewer 3 | Replace the boolean with an explicit surfaced lifecycle state that remains visible in review/status and has unambiguous coverage semantics. |
| R3-SF-02 | Protected-note behavior is still over-imported from enrich. Because provenance only writes frontmatter, skipping LLM reevaluation for L1 / reviewed notes leaves stale links on curated notes without a first-class replacement-proposal flow. | Reviewer 1 | Revisit whether enrich-grade protection should apply unchanged to a frontmatter-only feature, or add a repair/reproposal path for protected notes. |
| R3-SF-03 | Stale/orphan review still lacks a complete traversal contract at scale. Pending review has defined pagination, but stale review still lacks equally explicit page size, ordering, and navigation behavior. | Reviewer 1 | Define stale/orphan page size, ordering, `next` / `prev`, and ID stability so large queues remain operable. |
| R3-SF-04 | Pending review ordering is still not deterministic enough for `confirm range` when multiple items share confidence. | Reviewer 1 | Add a stable tie-break rule to the display order used by range-based batch actions. |
| R3-SF-05 | Dense-pair handling is deterministic now, but still not robust. Claims are never sharded, claims-only overflow hard-fails the pair, and oversized passages are front-truncated only. | Reviewer 3 | Add a fallback for claims-heavy pairs and define a less lossy oversized-passage strategy if dense real-library notes are in scope. |
| R3-SF-06 | The advisory lock is better than warning-only behavior but still overstated. The spec still relies on operator discipline and does not fully specify race-safe acquisition semantics. | Reviewer 1, Reviewer 3 | Either tighten the lock contract to something race-safe enough to justify the safety language, or lower the claim to match the remaining advisory behavior. |
| R3-SF-07 | The feature remains weak on immediate user value: Rev 3 openly says the approved baseline currently has zero canonical `supersedes`, so the slice yields nothing until humans seed version links first. | Reviewer 3 | Keep the infrastructure framing, but make acceptance criteria and rollout messaging explicit about low initial yield and manual seeding requirements. |
| R3-SF-08 | The test plan still misses newly introduced claims: acknowledged-stale visibility, stale pagination/order, protected-note repair, deterministic tie-breaking, and cross-command locking behavior. | Reviewer 1 | Expand the test matrix to cover every new lifecycle and concurrency claim introduced in Rev 3. |

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| R3-MN-01 | `--dry-run` is still internally inconsistent: one section says it reports shard counts, another says it stops before sharding preflight. | Reviewer 1 |
| R3-MN-02 | The implementation contract assumes singular `supersedes`, but Section 20 still leaves that cardinality open as a reviewer question. | Reviewer 3 |
| R3-MN-03 | `claim_hash` is based on `claim_text` alone, which may be too weak for stale detection and rejection-basis decisions when the quote or extraction context changes but the claim string does not. | Reviewer 3 |

## 5. Agreement Analysis

Strong agreement:

- All three reviewers say Rev 3 is materially better than Rev 2 and is now much more internally coherent.
- All three reviewers still say Rev 3 is not approval-ready.
- Reviewers 1, 2, and 3 converge on the same dominant blocker: the spec now correctly declares roadmap/PRD, ontology, and refresh amendments as prerequisites, but those upstream approvals are still missing.
- Reviewers 1 and 3 independently say the stale-link lifecycle is still not fully operable, even though Rev 3 improved the command grammar and visibility.

Disagreements or partial disagreements:

| Topic | Views | Recommendation |
|---|---|---|
| What is still blocking approval | Reviewer 1: the main remaining problem is unresolved governing contract, with several operability gaps still open. Reviewer 2: internal contract is mostly coherent now; the remaining blockers are almost entirely upstream authorization and compatibility. Reviewer 3: governance is still blocking, but there is also a substantive correctness bug in same-coordinate stale repair that independently blocks approval. | Treat governance as the shared blocker, but do not collapse Reviewer 3's semantic-staleness finding into a documentation issue. It is a separate implementation-level blocker that CA still needs to resolve. |
| Severity of `acknowledged_stale` | Reviewer 1: incomplete lifecycle and visibility semantics. Reviewer 3: explicit unblock requirement because the state is internally contradictory. Reviewer 2 does not foreground it. | Keep this visible as an unresolved lifecycle problem. If CA wants a narrow approval threshold, this is the first candidate to decide explicitly as blocker vs should-fix. |
| Protected-note handling | Reviewer 1: over-imported from enrich and leaves repair gaps. Reviewer 2: frontmatter-only provenance is broadly more compatible with enrich than Rev 2 was. Reviewer 3 focuses on stale correctness rather than protection policy. | CA should decide whether provenance inherits enrich protection unchanged or whether frontmatter-only behavior deserves a narrower protection rule. The current text is still too ambiguous to leave implicit. |
| Dense-pair fallback severity | Reviewer 1 does not foreground this. Reviewer 3 treats claims-only overflow and front-truncation as a real operational limit for large evidence notes. Reviewer 2 is neutral. | Keep the deterministic sharding improvements, but add explicit fallback or non-goal language before implementation so operators are not surprised by hard failures on dense pairs. |

Resolution guidance under the review rules:

- The shared blockers are factual inconsistencies between the current spec and the still-unamended governing docs. Those remain blocking until fixed.
- Reviewer 3's stale-repair objection is not a misunderstanding. It follows directly from the current dedupe and `reconfirm` rules and should be treated as a real blocker unless CA intentionally accepts that correctness risk.
- Remaining differences are primarily about prioritization and approval threshold, not about whether the cited text exists.

## 6. Required Actions for CA

| Priority | Action | Estimated Effort |
|---|---|---|
| 1 | Resolve the governance gap by approving or landing the roadmap/PRD amendment that authorizes the evidence-to-evidence infrastructure slice, or revert the spec to the currently approved deliverable-to-evidence scope. | Large |
| 2 | Approve or land the ontology amendment for `provenance_links` and the refresh-contract amendment that preserves `provenance_links` plus `_llm_metadata.provenance`. | Large |
| 3 | Redesign stale confirmed-link repair so coordinate-stable but semantically changed links can be revalidated instead of merely hash-refreshed. | Medium |
| 4 | Replace or fully specify `acknowledged_stale` so it remains visible in status/review and has clear coverage semantics. | Medium |
| 5 | Clarify whether protected notes should be fully skipped, partially reevaluated, or offered a dedicated repair/reproposal path for provenance metadata. | Medium |
| 6 | Finish stale/orphan review ergonomics: pagination, ordering, navigation, and deterministic tie-breaks for range actions. | Small |
| 7 | Either strengthen the lock acquisition contract or weaken the concurrency safety claim to match the still-advisory implementation. | Medium |
| 8 | Expand the test plan to cover the new lifecycle, ordering, dense-pair, and cross-command behaviors introduced in Rev 3. | Small |

## 7. Risk Assessment

The CA still does not state an explicit risk level in the spec. Reviewer 3 assigns **High** risk again and blocks the spec. Reviewers 1 and 2 do not assign a numeric label, but their findings reinforce that this is still above routine spec risk: the governing contract is not yet approved, refresh durability is not yet authorized, and the stale-link lifecycle still contains unresolved correctness and operability gaps.

This is the strongest current signal:

- Elevated risk is no longer coming from many internal contradictions. It is now concentrated in two places: unmet governance preconditions and one remaining correctness hole in stale confirmed-link repair.
- Because the preconditions in Section 21 are still unmet, approval now would effectively approve a contract the rest of the project documentation does not yet authorize.

## 8. Open Questions

Rev 3 Section 20 now contains only **Q1-Q3**. Q4-Q5 from earlier revisions no longer appear in the current spec.

| Open Question | Reviewer Positions |
|---|---|
| Q1: `supersedes` singular cardinality | Reviewer 3 is the only reviewer to press this directly in Round 3: the contract assumes singular everywhere, but the question remains open in Section 20. Reviewer 1 and Reviewer 2 do not challenge singular cardinality in this round. Recommendation: either accept singular as a fixed v1 constraint now or keep the question open but stop writing the rest of the contract as if it is already settled. |
| Q2: Confidence threshold for default review (`medium+`) | No reviewer challenged the `medium+` threshold directly in Round 3. Reviewer 1's UX concerns are about stale-review navigation and deterministic ordering, not the threshold itself. Recommendation: keep `medium+` unless CA wants more low-confidence review burden in the initial pilot. |
| Q3: Infrastructure slice framing | Reviewer 1 sees the infrastructure framing as a real improvement in honesty and credibility. Reviewer 2 says the framing is still off-plan until the roadmap/PRD amendment is approved. Reviewer 3 says the framing is honest but still confirms the slice is mis-sequenced against promised user value on the current baseline. Recommendation: do not treat this as resolved by prose alone; it requires explicit upstream authorization. |

