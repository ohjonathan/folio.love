# Reviewer 3 Adversarial Review: Folio Provenance Linking Spec Rev 4

## 1. Assumption Attack

| Assumption | Why It Might Be Wrong | Impact If Wrong |
|---|---|---|
| The “single approval package” resolves governance drift | The spec amends the roadmap, ontology, and refresh contract, but the active Tier 3 kickoff checklist still defines PR D as deliverable-to-evidence provenance | Team builds/reviews against conflicting scope and exit criteria |
| `re-evaluate` is a safe semantic repair path | The action deletes the confirmed link immediately, but the spec does not define any persisted re-evaluate queue/state | Confirmed provenance can be lost without a replacement path |
| `link_status` is enough to model stale lifecycle | `stale` is not stored, only inferred; `acknowledged_stale` is sticky and suppresses reproposals forever at the same coordinates | Broken links can become invisible after later content drift |
| Claims sharding keeps runtime “practical” | `--limit` caps pairs, not shard calls; both-axes overflow creates a call matrix with no hard ceiling | Single dense pair can blow up cost/latency |
| `O_CREAT|O_EXCL` lock meaningfully solves concurrency | It is local-only, advisory, PID-based, and not defined against PID reuse or external writers | False contention and write races remain possible |
| Infrastructure-first acceptance is sufficient | Current criteria allow zero real-output on the real corpus and do not require end-to-end stale repair on production-like notes | Spec can “pass” without proving the risky parts work |

## 2. Failure Mode Analysis

| Failure | How It Happens | Would We Notice? |
|---|---|---|
| Confirmed link disappears during `re-evaluate` | User runs `re-evaluate`; link is removed; next run fails/skips/never happens | Yes, but only after missing provenance is noticed |
| Protected-note bypass never triggers | Spec references a “re-evaluate queue” but defines no persisted queue field | Maybe not; it looks like a no-op bug |
| Dense pair causes token/cost explosion | Claims overflow + passage overflow triggers matrix sharding on a 137-slide note | Yes, via runtime/cost spike, but too late |
| Acknowledged stale link masks later semantic drift | Human acknowledges once; same slide/index changes again; dedupe keeps suppressing reproposals | Weakly; status still shows acknowledged, but no resurfaced proposal |
| Orphaned-but-still-recoverable link cannot be repaired | Slide/claim moved, old anchor gone, `re-evaluate` disallowed for orphaned links | Yes, but only as manual cleanup burden |
| Review surface gets noisier, not clearer | `provenance_link_stale` adds more flags onto an already 94%-flagged corpus | Barely; users likely ignore flags altogether |

## 3. Edge Case Inventory

- Single oversized claim: the spec defines oversized-passage fallback, not oversized-claim fallback.
- Slide renumbering that preserves semantics but changes anchors.
- Claim insertion earlier on a slide shifting `source_claim_index`.
- Target content moved to a different slide, making link “orphaned” but still semantically recoverable.
- Re-evaluate on protected notes when the only persisted signal is a cleared fingerprint.
- Multiple shard outputs disagreeing on confidence for the same pair with no consistency threshold.
- `acknowledged_stale` links after content reverts or drifts again.
- Lock file left behind with recycled PID.
- Refresh producing `stale_pending` proposals with no explicit review/status UX.

## 4. Blind Spot Identification

- The spec does not account for the already saturated review-state surface in the real vault.
- Governance repair is aimed at the roadmap, but the active kickoff checklist remains contradictory.
- Acceptance criteria optimize for infrastructure existence, not operational proof on the retained production library.
- The semantic-repair path is more destructive than the visual-refresh path, but the spec treats them as sibling review actions.

## 5. Risk Assessment

**Overall risk level: High.**

- Availability/cost attack: High severity, medium likelihood. A single adversarially dense note can trigger many LLM calls because sharding is unbounded.
- Integrity/regression risk: High severity, high likelihood. `re-evaluate` can delete the only confirmed link before replacement state exists.
- Governance drift risk: Medium-high severity, high likelihood. Current planning docs still disagree on what PR D is.
- UX/reviewability risk: Medium severity, high likelihood. More stale flags land on a corpus that is already 94% flagged.

## 6. Issues Found

### Critical

1. **`re-evaluate` is not durable and is probably not implementable as specified.**  
   The spec says `re-evaluate` removes the link from `provenance_links` and clears the pair fingerprint, while protected-note repair depends on a later “re-evaluate queue” check. But no queue field or persisted marker exists in the data model, and the only defined action is destructive deletion. That means the claimed fix for semantic repair and protected-note bypass is not actually specified end-to-end. See [folio_provenance_spec.md:406](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L406), [folio_provenance_spec.md:530](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L530), [folio_provenance_spec.md:688](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L688), [folio_provenance_spec.md:709](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L709).

2. **Claims-sharding fallback still has an unbounded within-pair cost surface.**  
   The spec explicitly allows claims sharding, then claims-plus-passages matrix sharding, while also deferring `--max-calls`. `--limit` only controls pairs, not shard calls. On the real vault, evidence notes already reach 393,335 characters and 137 slides, so the “practical runtime” claim is not credible without a hard abort/ceiling contract. See [folio_provenance_spec.md:113](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L113), [folio_provenance_spec.md:138](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L138), [folio_provenance_spec.md:621](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L621), [tier2_real_vault_validation_report.md:95](//Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95).

### Major

1. **Governance packaging is still incomplete against the active project docs.**  
   Rev 4 claims governance is resolved as a single package, but the current roadmap and Tier 3 kickoff checklist still describe PR D as deliverable-to-evidence provenance. Appendix A only patches the roadmap; it does not patch or explicitly supersede the kickoff checklist, which remains an active planning artifact. See [folio_provenance_spec.md:67](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L67), [folio_provenance_spec.md:987](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L987), [04_Implementation_Roadmap.md:427](//Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L427), [04_Implementation_Roadmap.md:458](//Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L458), [tier3_kickoff_checklist.md:91](//Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L91), [tier3_kickoff_checklist.md:195](//Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L195).

2. **`acknowledged_stale` can permanently suppress valid reproposals after later drift.**  
   The new `link_status` model stores reviewer intent, not actual freshness. Once a link is marked `acknowledged_stale`, dedupe suppresses reproposals at those coordinates and the state is never auto-cleared. If the claim/passage changes again, the system can keep an invalid link alive indefinitely. See [folio_provenance_spec.md:400](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L400), [folio_provenance_spec.md:514](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L514), [folio_provenance_spec.md:735](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L735), [folio_provenance_spec.md:887](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L887).

3. **Orphaned links are denied the one repair path that could recover them.**  
   The spec forbids `re-evaluate` for orphaned links, even though pair-wide re-matching does not require the old coordinates to remain valid. This strands moved-content cases as delete-or-acknowledge only. See [folio_provenance_spec.md:700](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L700), [folio_provenance_spec.md:743](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L743).

4. **Acceptance criteria are too weak for the risky parts of this spec.**  
   The revised criteria explicitly allow zero non-trivial yield on the current production baseline and require only correct behavior “when pairs exist.” That is not enough to validate stale repair, claims sharding, or concurrency against the real retained library. See [folio_provenance_spec.md:948](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L948), [tier2_real_vault_validation_report.md:95](//Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95).

5. **The new stale review flag likely worsens an already noisy review surface.**  
   The spec adds `provenance_link_stale`, but the real-vault validation already shows 94% of evidence notes are flagged. This is a blind addition to a review mechanism that is already near-useless as a triage surface. See [folio_provenance_spec.md:741](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L741), [tier2_real_vault_validation_report.md:98](//Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L98).

### Minor

1. **`stale_pending` exists in the data model but not in the review/status UX contract.**  
   The status model defines it, refresh can create it, but the review flow does not explain how operators see or clear it. See [folio_provenance_spec.md:442](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L442), [folio_provenance_spec.md:467](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L467), [folio_provenance_spec.md:776](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L776).

2. **The lock spec is better than Rev 3, but still underspecified operationally.**  
   It relies on PID liveness only and admits it is advisory/local-only. That is acceptable as a limitation, but not strong enough to treat as a broad concurrency guarantee. See [folio_provenance_spec.md:793](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L793).

3. **There is a spec hygiene error in the revision note.**  
   Rev 4 cites the lock fix as §16.5, but the lock section is §16.3. See [folio_provenance_spec.md:26](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L26), [folio_provenance_spec.md:793](//Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L793).

## 7. Verdict

**Block.**

**Unblock requirements:**

1. Specify a durable, persisted `re-evaluate` marker/queue and make the repair path atomic enough that confirmed links are not silently lost.
2. Add a hard within-pair shard/call ceiling or abort contract, plus explicit handling for oversized single claims.
3. Amend or explicitly supersede the active Tier 3 kickoff checklist in the same approval package, not just the roadmap.
4. Tighten acceptance criteria to require at least one seeded real-library end-to-end run covering: proposal generation, confirmation, stale detection, `refresh-hashes`, `re-evaluate`, and dense-pair sharding behavior.
