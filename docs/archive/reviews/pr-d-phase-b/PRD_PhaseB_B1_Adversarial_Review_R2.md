# Reviewer 3: Adversarial Review, Round 2

## 1. Assumption Attack

| Assumption | Why It Might Be Wrong | Impact If Wrong |
|---|---|---|
| Evidence-only v1 can use `draws_from` / `depends_on` as primary provenance seeds | The spec itself says those fields apply to analysis/deliverable docs, not evidence docs, and v1 only extracts claims from evidence notes. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L182), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L240), [architecture](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L791), [enrich spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L176) | The primary seed model is unusable without either an ontology violation or a scope change; practical v1 collapses to `supersedes` only. |
| `supersedes` can be “bidirectional” inside the current one-source, one-note-write pipeline | The pipeline only evaluates source docs in scope and stores pair state on the source note. There is no defined place to persist the reverse-direction result when the reverse source is out of scope. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L251), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L490), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L792) | The only realistic v1 seed can produce half-modeled or inconsistent lineage behavior. |
| Pair fingerprints plus rejection suppression are enough to make reruns safe | Reconciliation only talks about pending and rejected proposals. Confirmed links are immutable and are never used to suppress duplicate re-proposals. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L396), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1086), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1128), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1207) | Reruns can resurrect already-confirmed links and duplicate canonical frontmatter. |
| `--stale` makes stale/orphaned links repairable | The spec says humans can re-confirm/remove/ignore stale links, but defines no CLI action for any of those operations. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1069), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1150) | Stale links become visible but still require undocumented/manual repair, so they can linger indefinitely. |
| §12.6 overflow handling is deterministic enough | It mentions overlapping shards without defining overlap, defines no stable chunking algorithm, and handles “claims alone too big” but not “one passage alone too big.” [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1035) | Dense real-library pairs can yield unstable proposal sets across reruns. |
| Warning-only PID checks are an operationally safe concurrency story | The spec explicitly keeps this as best-effort, non-blocking detection. The test plan only verifies the warning path. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L423), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1271), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1393) | Last-write-wins metadata loss remains a live failure mode, not a retired one. |

## 2. Failure Mode Analysis

| Failure | How It Happens | Would We Notice? |
|---|---|---|
| v1 produces almost no candidate pairs in practice | The validated vault is evidence-only in daily use, with 0 canonical relationship fields populated; the spec still depends on humans seeding legal relationships first. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L191), [vault validation](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L65) | Yes, but only as a no-op pipeline after implementation effort. |
| Already-confirmed links reappear as new pending proposals | A rerun on changed content or `--force` re-evaluates the pair; nothing suppresses matches already in `provenance_links`. | Partially. Reviewers would see duplicates, but the spec has no invariant preventing them. |
| Reverse `supersedes` provenance is lost or written inconsistently | The pair is seeded from one source note, but “bidirectional comparison” needs reverse-source persistence that is never defined. | Not reliably; behavior will vary by implementation. |
| Dense pairs produce unstable match sets | Shard boundaries are underdefined, overlap is mentioned but unspecified, and token estimation is heuristic-only. | Only indirectly, via proposal churn between reruns. |
| Stale/orphaned links remain in place indefinitely | `--stale` surfaces them, but no repair command is specified. | Yes, but only as recurring stale counts with no first-class fix path. |
| Concurrent runs silently clobber metadata | `refresh`, `enrich`, and `provenance` all read-then-write frontmatter; warning-only PID checks do not prevent overlap. | Maybe not until a user notices missing metadata. |

## 3. Edge Case Inventory

- Evidence notes manually seeded with `draws_from`/`depends_on` to bootstrap v1 would violate the current ontology rather than follow it.
- `A supersedes B`, only `A` is in scope, and the implementation tries to honor “bidirectional comparison.”
- A pair is re-run after one link was already confirmed and one unrelated slide changed.
- One target slide’s `### Analysis` block alone exceeds the context budget.
- A protected note has orphaned confirmed links and the operator wants to clean them up without hand-editing frontmatter.
- A source note loses a claim index but keeps nearby text, producing stale/orphan ambiguity.
- Operators run `folio refresh` and `folio provenance` on overlapping scope from separate shells.

## 4. Blind Spot Identification

- Prompt-injection resistance is not addressed. The prompt treats note content as inert data, but the notes themselves can contain instructions or adversarial text.
- There is no acceptance criterion requiring non-trivial yield on the validated baseline or requiring a seed workflow that respects the ontology.
- The review UX is CLI-first, but the validated environment has no Dataview and an over-broad review-state surface, so status/review discoverability carries more operational weight than the spec acknowledges. [vault validation](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L98), [vault validation](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L117)

## 5. Risk Assessment

Overall risk: **High**. Rev 2 improved the documentation, but it did not fully close the two biggest correctness risks: the seed model is still misaligned with the ontology/baseline, and reruns still lack a safe story for already-confirmed links. That means the design can still be “internally coherent on paper” while failing in the only realistic v1 operating mode.

| Attack Vector | Applicable? | Risk | Evidence |
|---|---|---|---|
| 1. Pair-level idempotency after redesign | Yes | High | Pair fingerprints help continuation, but confirmed links are outside suppression/reconciliation. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L396), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1207) |
| 2. Narrowed evidence-only scope | Yes | Medium-High | The spec now honestly states v1 yields zero output on the approved baseline until humans seed relationships. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L197) |
| 3. Context-budget fallback | Yes | High | Overflow exists, but not with deterministic enough chunking/overflow semantics for dense pairs. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1026), [vault validation](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95) |
| 4. Stale confirmed-link handling | Yes | Medium-High | Discoverability improved, repairability did not; no stale-link actions are defined. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1069), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1150) |
| 5. Proposal reconciliation and retry | Yes | High | Pending/rejected semantics are clearer, but confirmed-link duplication remains undefined. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L398), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1128) |
| 6. Single-writer rule | Yes | High | Still a warning-only policy sentence with PID-file heuristics, not enforcement. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L423), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1276) |
| 7. Scope realism | Yes | Medium-High | The motivating story is still deliverable/evidence provenance, while v1 is evidence/evidence infrastructure with near-zero baseline yield. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L45), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L197) |

## 6. Issues Found

- **Critical:** Evidence-only v1 still relies on ontology-invalid primary seed edges. The spec makes `draws_from` and `depends_on` the primary provenance seeds, but the ontology and PR C baseline restrict those fields to analysis/deliverable docs, while PR D v1 only extracts claims from evidence notes. The fallback suggestion to manually add those edges to evidence notes is therefore a schema violation, not a bootstrap path. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L182), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L197), [architecture](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L791), [enrich spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L176)\n- **Critical:** Reruns can re-propose already-confirmed links. Rev 2 defines replacement for pending proposals and suppression for rejected proposals, but says confirmed links are never modified and never uses them as a dedupe/suppression surface. A changed pair or `--force` can therefore emit an already-confirmed match again and append duplicates into `provenance_links`. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L396), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1086), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1128), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1207)
- **Major:** `supersedes` bidirectionality is still not representable. The spec says `supersedes` yields bidirectional comparison, but the command scopes only source docs, the prompt is one-way, and pair state is stored on the source note under `pairs[target_id]`. The reverse direction has no defined persistence model. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L251), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L490), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L804)
- **Major:** Stale/orphaned links are discoverable but not operably repairable. Rev 2 adds detection and `--stale`, but the action table still only covers pending proposals. “Re-confirm,” “remove,” and “ignore” exist as prose only. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1069), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1150)
- **Major:** §12.6 is still too underspecified for dense-pair stability. It does not define deterministic shard construction, mentions overlapping shard boundaries without defining overlap, and omits the case where one passage alone cannot fit with all claims. On this corpus, that is not hypothetical. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1026), [vault validation](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95)
- **Major:** The single-writer story is still operationally weak. Warning-only PID checks at library root do not protect overlapping scope, do not prevent writes, and are only tested as warnings. This is not meaningfully stronger than the old policy sentence. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L423), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1276), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1393)
- **Minor:** Rev 2 is more honest about scope realism, but the feature still under-delivers relative to the motivating story. The spec now describes an infrastructure slice with zero baseline yield until humans seed relationships, not a user-visible provenance capability. That is acceptable only if it is sequenced and named as such. [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L45), [provenance spec](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L197), [baseline memo](/Users/jonathanoh/Dev/folio.love/docs/product/tier3_baseline_decision_memo.md#L323)

## 7. Verdict

**Verdict: Block**

Unblock requirements:

1. Align the seed model with the ontology and v1 scope. Either make v1 explicitly `supersedes`-only for evidence notes, or amend the ontology/source scope and baseline story accordingly.
2. Define confirmed-link dedupe/reconciliation semantics so reruns cannot re-emit already-confirmed links.
3. Resolve the `supersedes` directionality gap. Either make it one-way, or define reverse-direction scope, storage, and write behavior explicitly.
4. Add first-class stale/orphan repair actions to the CLI contract.
5. Make overflow sharding deterministic enough to test, including the “single passage too large” case.
6. Strengthen concurrency beyond warning-only PID advice, or narrow the write model so overlapping commands cannot clobber note frontmatter."}}
