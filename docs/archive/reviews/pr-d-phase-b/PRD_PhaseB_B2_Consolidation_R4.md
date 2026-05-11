# PR D Phase B Consolidation, Round 4

## 1. Verdict Summary Table

| Reviewer | Role | Verdict | Blocking Issues |
|---|---|---|---|
| Reviewer 1 | Peer | Request Changes | stale-repair UX is not trustworthy; operator recovery paths still under-specified |
| Reviewer 2 | Alignment | Request Changes | approval package does not fully amend the approved roadmap, ontology, PRD, refresh contract, and checklist corpus |
| Reviewer 3 | Adversarial | Block | `re-evaluate` is not durable; within-pair sharding remains unbounded; governance package is still incomplete |

## 2. Blocking Issues

| Issue ID | Description | Flagged By | Category | Action Required for CA |
|---|---|---|---|---|
| R4-BLK-01 | The approval corpus is still internally inconsistent. Rev 4 bundles amendment text inside the spec, but the live roadmap, ontology, PRD coverage, refresh contract, and Tier 3 kickoff checklist do not yet fully reflect those changes. Appendix A does not patch every conflicting roadmap surface, Appendix B does not fully amend earlier ontology statements, and the checklist still defines PR D as deliverable-to-evidence provenance. | Reviewer 2, Reviewer 3 | Governance / Alignment / Preconditions | Amend or explicitly supersede every conflicting authoritative surface in the same approval package: roadmap bullet, relationship-types line, CLI map, ontology sections §6.3-§6.4 and §12.x, refresh contract, PRD FR text, and the kickoff checklist. |
| R4-BLK-02 | The stale-repair flow is still not trustworthy end to end. Peer review says humans lack persisted prior claim/passage text needed to verify a stale link before `refresh-hashes`. Adversarial review says `re-evaluate` deletes the confirmed link and relies on a later queue/state that is never actually modeled. Together, that means both repair branches remain unsafe: one is unverifiable, the other is not durably specified. | Reviewer 1, Reviewer 3 | Lifecycle / Data Integrity / UX | Persist enough repair context to support visual verification, and specify a durable `re-evaluate` marker/queue plus atomic semantics so stale-link repair cannot silently discard confirmed provenance. |
| R4-BLK-03 | Dense-pair runtime is still not bounded. Rev 4 adds claims sharding, but `--limit` only caps pairs, not shard calls, and both-axes overflow can create an unbounded matrix of LLM calls on large retained-library notes. | Reviewer 3 | Runtime / Cost / Scale | Add a hard within-pair shard/call ceiling or abort contract, and define oversized single-claim handling explicitly. |

## 3. Should-Fix Issues

| Issue ID | Description | Flagged By | Action |
|---|---|---|---|
| R4-SF-01 | `--dry-run` is still not behaviorally consistent with a real run because it stops before stale-link checks and `re-evaluate` processing that may trigger LLM work on protected notes. | Reviewer 1 | Clarify dry-run scope or make it model all LLM-triggering paths, then add an explicit parity test. |
| R4-SF-02 | The protected-note bypass is broader than it sounds. In singular-`supersedes` v1, “that pair only” is effectively the whole source note against its predecessor, so repairing one stale link can regenerate unrelated proposals on curated notes. | Reviewer 1 | Narrow the repair scope or document clearly that pair-level reevaluation reopens the whole note-target pair. |
| R4-SF-03 | Stale/orphan review still lacks scale tooling. Rev 4 adds pagination, but not doc/range batch actions, so churn-heavy cleanup remains one-by-one. | Reviewer 1 | Add batch actions for stale/orphan review or explicitly declare large-queue cleanup a manual non-goal. |
| R4-SF-04 | Deterministic ordering is still incomplete because the spec sorts primarily by “registry order,” but never defines a canonical registry sort. | Reviewer 1 | Define registry ordering precisely or replace it with a canonical sort key used everywhere. |
| R4-SF-05 | `acknowledged_stale` can suppress valid reproposals forever after later content drift because it encodes reviewer intent, not freshness, and never auto-clears. | Reviewer 3 | Define reclassification rules for later drift or make acknowledged links re-enter proposal eligibility under defined conditions. |
| R4-SF-06 | Orphaned links are denied pair-level `re-evaluate` even though semantic rematching may still recover them after anchors move. | Reviewer 1, Reviewer 3 | Either allow orphaned pair-level rematch or justify why delete-and-rerun is the only safe path. |
| R4-SF-07 | Acceptance criteria remain too weak for the risky parts of the design because zero meaningful output on the real corpus is still acceptable. | Reviewer 3 | Require at least one seeded real-library end-to-end run that exercises confirmation, stale detection, `refresh-hashes`, `re-evaluate`, and dense-pair sharding. |
| R4-SF-08 | The new stale review flag may worsen an already saturated review surface in the real vault. | Reviewer 3 | Explain how stale provenance flags interact with an already high-flag corpus, or keep them out of the primary triage surface. |
| R4-SF-09 | PRD amendment coverage is still not explicit enough. Rev 4 lists affected FRs but does not include exact amendment text for the command, routing, frontmatter, refresh, and provenance FR changes. | Reviewer 2 | Add exact PRD amendment text or explicitly route approval through a separate PRD patch artifact. |

## 4. Minor Issues

| Issue ID | Description | Flagged By |
|---|---|---|
| R4-MN-01 | Review-state integration remains ambiguous: the spec adds `provenance_link_stale`, but does not fully define how it interacts with `review_status: flagged` or how/when it clears. | Reviewer 1 |
| R4-MN-02 | `stale_pending` exists in the data model and refresh flow, but the review/status UX does not explain how operators see or clear it. | Reviewer 3 |
| R4-MN-03 | The lock contract is materially better than Rev 3 but still operationally narrower than the phrase “concurrency protection” suggests. | Reviewer 3 |
| R4-MN-04 | The revision note cites the lock fix as §16.5 even though the actual lock section is §16.3. | Reviewer 3 |
| R4-MN-05 | The spec marks amendment approval as a checked precondition before the authoritative upstream docs are actually amended. | Reviewer 2 |

## 5. Agreement Analysis

Strong agreement:

- All three reviewers say Rev 4 is materially better than Rev 3.
- No reviewer approved the spec.
- Reviewers 2 and 3 independently say governance is still not fully resolved because the bundled appendix package does not make the live approval corpus internally consistent.
- Reviewers 1 and 3 independently say the stale-link repair path is still not safe enough to trust, though they disagree on the specific failure mode.

Disagreements or partial disagreements:

| Topic | Views | Recommendation |
|---|---|---|
| Whether governance is now “resolved enough” | Reviewer 1 treats the appendix package as a real improvement and does not make governance the main blocker. Reviewer 2 says the package is still incomplete across roadmap, ontology, PRD, and checklist surfaces. Reviewer 3 says the checklist conflict alone is enough to keep governance unresolved. | Do not treat bundled amendment prose as self-validating. The package needs to patch or explicitly supersede every still-conflicting authoritative document. |
| What the main stale-repair blocker is | Reviewer 1: humans still cannot verify stale links because prior claim/passage text is not retained or surfaced. Reviewer 3: `re-evaluate` is destructive and lacks a durable queue/marker. | Treat both as blockers on the same workflow. One repair branch lacks trustable evidence; the other lacks durable state. |
| Severity of dense-pair handling | Reviewer 1 does not foreground sharding cost. Reviewer 3 treats it as a critical blocker due to unbounded call expansion on large real notes. Reviewer 2 focuses on governance, not runtime. | Keep this as a single-reviewer critical finding. Add an explicit ceiling or abort contract before implementation. |
| Whether protected-note repair is sufficiently scoped | Reviewer 1 says “pair only” is misleadingly broad in singular-`supersedes` v1. Reviewer 3 focuses on durability rather than scope breadth. Reviewer 2 does not foreground it. | Clarify that the unit of bypass is the whole note-target pair, or redesign repair to scope closer to the stale link being fixed. |

Resolution guidance under the review rules:

- Governance misalignment is a factual inconsistency with the current approval corpus and therefore remains blocking.
- The stale-repair objections are not reviewer misunderstandings. They follow directly from what Rev 4 persists and what it does not persist.
- The dense-pair cost finding is currently a single-reviewer blocker; it should still be carried forward unchanged rather than filtered out.

## 6. Required Actions for CA

| Priority | Action | Estimated Effort |
|---|---|---|
| 1 | Finish the approval package so every authoritative document surface is consistent: roadmap, CLI map, relationship-types line, ontology sections, PRD FR text, refresh contract, and kickoff checklist. | Large |
| 2 | Redesign stale repair as a durable, auditable workflow: persist verification context for humans, add a real `re-evaluate` queue/marker, and make repair atomic enough that confirmed provenance is not silently lost. | Large |
| 3 | Add a hard within-pair shard/call ceiling or explicit abort rule, including oversized single-claim handling. | Medium |
| 4 | Fix dry-run parity so it reflects all real LLM-triggering paths, especially protected-note `re-evaluate` behavior. | Medium |
| 5 | Tighten stale/orphan review ergonomics with batch actions and clearer operator-state surfaces (`stale_pending`, review flags, orphan rematch policy). | Medium |
| 6 | Clarify or narrow the scope of protected-note bypass so repairing one stale link does not implicitly reopen a whole curated note-target pair without warning. | Medium |
| 7 | Strengthen acceptance criteria with at least one seeded real-library end-to-end validation run that exercises the risky lifecycle branches. | Medium |

## 7. Risk Assessment

The CA still does not state an explicit risk level. Reviewer 3 again assigns **High** risk and blocks the spec. Reviewers 1 and 2 do not assign numeric labels, but both still reject approval because the remaining issues affect trustworthiness of repair and authority of the governing corpus, not cosmetic polish.

The signal in Round 4 is narrower but still strong:

- Architecture and core mechanics are much closer than before.
- The remaining objections concentrate in two places: unresolved approval-corpus alignment and unsafe/incomplete stale-repair semantics.
- Because no reviewer approved and one reviewer still blocks at High risk, this is not yet in “good to proceed” territory.

## 8. Open Questions

Rev 4 Section 20 now contains only **Q1-Q2**.

| Open Question | Reviewer Positions |
|---|---|
| Q1: Confidence threshold (`medium+`) | No reviewer challenged `medium+` in Round 4. This remains effectively accepted. |
| Q2: Infrastructure-slice naming | Reviewer 1 accepts the infrastructure framing as directionally correct. Reviewer 2 says naming alone does not resolve governance because the approval corpus still conflicts. Reviewer 3 says the package still leaves live planning documents contradictory. Recommendation: treat the naming question as subordinate to the governance-package fix. |
