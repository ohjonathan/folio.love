# PR D Phase B Adversarial Review

## 1. Assumption Attack

| Assumption | Why It Might Be Wrong | Impact If Wrong |
|---|---|---|
| Fingerprint granularity is safe at one fingerprint per source document | Applicable. High risk. The spec hashes all target passages for a source into one `provenance_input_fingerprint` and uses that as the skip marker, while `--limit` and progress reporting are defined per pair, not per source. Evidence: [PR D:334](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L334), [PR D:490](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L490), [PR D:1051](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1051), [PR D:1125](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1125). | One changed target blows the cache for every pair under that source. More seriously, partial runs can mark a source “done” without all pairs being evaluated, or force full re-evaluation of already-completed pairs. |
| The production library has enough canonical relationships to make PR D useful now | Applicable. High risk. PR D admits candidate pairs come “primarily” from human-populated canonical relationships and that the system can degrade to a no-op when the graph is sparse. The approved production vault is still evidence-only with 0 interaction notes, and current evidence notes do not emit canonical relationship fields yet. Evidence: [PR D:164](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L164), [PR D:220](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L220), [PR C:152](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L152), [Vault report:66](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L66), [Baseline memo:329](/Users/jonathanoh/Dev/folio.love/docs/product/tier3_baseline_decision_memo.md#L329). | PR D can ship as a mostly empty pipeline on the approved baseline, with cost/complexity but little actual provenance output. |
| One LLM call per pair will fit in context | Applicable. Critical risk. The spec assumes “typical” pairs are small, but the validated corpus includes dense 137-slide notes up to 393,335 characters. PR D has no overflow estimator, truncation rule, sharding rule, or fallback mode. Evidence: [PR D:225](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L225), [PR D:852](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L852), [Vault report:59](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L59), [Vault report:95](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95). | Large but valid pairs will fail, truncate silently, or return degraded matches. The spec’s main runtime path breaks on exactly the kind of dense decks the product already has. |
| Confirmed links can safely persist forever once written | Applicable. High risk. Confirmed links are never modified by provenance, while stale handling only mentions fingerprints and proposals. Link identity is slide/index based, not content-hash based. Evidence: [PR D:568](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L568), [PR D:1026](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1026), [PR D:1083](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1083). | After `folio refresh`, a confirmed link can point to the wrong claim or stale slide with no surfacing, violating the architecture’s trust requirement that facts trace to current sources. |
| Re-running the same pair will produce a stable, mergeable proposal set | Applicable. Major risk. The spec only suppresses exact duplicates and unchanged rejections. It does not define what happens when the same pair is re-run and returns a different pending proposal set. Evidence: [PR D:730](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L730), [PR D:739](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L739), [PR D:1074](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1074). | Pending proposals can drift, accumulate contradictory variants, or oscillate between runs. Review UX becomes noisy and non-deterministic. |
| `--force` is enough to let users retry rejected pairs | Applicable. Major risk. The spec explicitly says `--force` bypasses document skip but still respects unchanged rejection bases. Only content/profile change expires a rejection. Evidence: [PR D:472](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L472), [PR D:666](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L666), [PR D:1080](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1080). | Users can be stuck with a bad rejection decision and no explicit retry path, especially if they want to test prompt tweaks without changing the resolved profile name. |
| Atomic writes are enough to make concurrent `enrich` and `provenance` safe | Applicable. Major risk. Both commands write the same note atomically, but neither spec defines locking, version checks, or field-level merge on concurrent writes. Evidence: [PR C:821](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L821), [PR C:832](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L832), [PR D:739](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L739), [PR D:750](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L750). | Last-write-wins can silently drop proposals, fingerprints, or body/frontmatter updates even though each individual write is “atomic.” |

## 2. Failure Mode Analysis

| Failure | How It Happens | Would We Notice? |
|---|---|---|
| Pair-level progress is lost or corrupted | A source has multiple targets; a run stops after some pairs; source-level fingerprint state cannot represent “partially complete.” | Sometimes. `status` may look clean, but remaining pairs can be skipped or reprocessed with no explicit partial marker. |
| Large pair overflows context | Dense source claims plus dense target passages exceed model context; spec still sends one prompt. | Usually only as per-pair error. Silent truncation or lower-quality matches may not be obvious. |
| Confirmed link becomes stale after refresh | Source claim order changes or target slide content changes; confirmed links persist by slide/index only. | Probably not. The spec has no stale flag or review surface for confirmed links. |
| Pending proposals fork | Re-run returns different matches/rationales for the same pair; spec does not say replace, append, or reconcile. | Partially. Reviewers will see noisy pending items, but the system has no rule to classify them as churn. |
| Rejected pair cannot be retried | User runs `--force`, but unchanged `basis_fingerprint` still suppresses the pair. | Yes, but only as “nothing happened.” There is no explicit “suppressed because unchanged rejection” retry workflow. |
| Concurrent enrich/provenance loses updates | Both processes read the old file, mutate different fields, then atomically overwrite the whole note. | Not reliably. Each command can succeed, yet one command’s changes disappear. |

## 3. Edge Case Inventory

- `--limit 1` on a source with three targets: the spec does not define partial completion state.
- Source claim reorder within the same slide: `source_claim_index` changes even if semantics do not.
- Target slide content changes but slide number stays constant: confirmed link still looks valid.
- Multiple relationship fields pointing to the same target: pair dedupe is tested, but fingerprint blast radius still stays source-wide.
- Very dense evidence notes with sparse actual claims: prompt still carries every extracted passage block.
- Interaction targets are allowed in extraction logic, but the approved production vault currently has none.
- Protected documents (`L1+`, `reviewed`, `overridden`) are skipped, which can block re-evaluation of high-value curated notes.

## 4. Blind Spot Identification

- The motivating story is “deliverable assertion back to evidence,” but v1 claim extraction only covers evidence and interaction notes, not analysis or deliverable notes. That is a scope mismatch, not just a future enhancement. Evidence: [PR D:64](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L64), [PR D:80](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L80).
- The protection rule `curation_level != L0` conflicts with the ontology’s framing of provenance as part of higher-curation synthesized work. Evidence: [PR D:1017](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1017), [Architecture:114](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L114).
- The spec leans on Dataview-queryable frontmatter for usability, but the validated daily-use vault had no Dataview plugin installed. Evidence: [PR D:88](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L88), [Vault report:184](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L184).
- Trust/reviewability requires current source traceability and durable human corrections; stale confirmed links violate both if not surfaced. Evidence: [Architecture:120](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L120).

## 5. Risk Assessment

Overall risk level: **High**.

This spec is not just missing polish. It has unresolved lifecycle problems in idempotency, retry semantics, stale-state handling, and concurrency. Those are trust-surface failures, and this feature sits directly on the trust surface.

## 6. Issues Found

**Critical**
1. Source-level fingerprinting is incompatible with pair-level `--limit`, interruption recovery, and progress semantics. The spec needs pair-level state or a source-level execution model, not both. Evidence: [PR D:353](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L353), [PR D:712](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L712), [PR D:1108](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1108).
2. No context-budget fallback is defined for dense real-library pairs, despite validated 90-slide and 137-slide notes. One-call-per-pair is therefore not a safe default contract. Evidence: [PR D:225](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L225), [Vault report:95](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L95).

**Major**
3. Confirmed links have no stale detection or surfacing, even though they are stored using unstable positional identifiers. Evidence: [PR D:568](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L568), [PR D:1028](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1028), [PR D:1085](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1085).
4. Proposal reconciliation is undefined when re-running produces different pending results for the same pair. The spec only handles exact duplicates and rejections. Evidence: [PR D:730](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L730), [PR D:739](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L739).
5. Bootstrap utility is unproven on the approved baseline. Current production is evidence-only, with 0 interaction notes in active use, and canonical relationship density is likely very low. Evidence: [PR D:172](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L172), [PR C:152](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L152), [Vault report:66](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L66).
6. Concurrent `enrich` and `provenance` runs can silently clobber each other because atomic write is not the same as coordinated write. Evidence: [PR C:828](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L828), [PR D:745](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L745).

**Minor**
7. `--force` does not actually let operators retry an unchanged rejection; it only re-runs the document around that suppression rule. Evidence: [PR D:472](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L472), [PR D:1080](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1080).
8. The stated user value and the implemented source scope are misaligned: the spec promises deliverable-to-evidence traceability but only defines extraction for evidence and interaction sources. Evidence: [PR D:64](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L64), [PR D:319](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L319).

## 7. Verdict

**Verdict: Block**

Unblock requirements:

1. Redesign idempotency/progress so the unit of fingerprinting matches the unit of execution and `--limit`.
2. Add an explicit context-budget policy: preflight estimation plus deterministic fallback when a pair is too large.
3. Define stale confirmed-link handling, including how changed claims/passages are surfaced to the reviewer.
4. Define pending-proposal reconciliation semantics for reruns and a true operator retry path for rejected pairs.
5. Add a concurrency guard or single-writer rule for `enrich` and `provenance`.
6. Prove that the approved production baseline has enough canonical pair density to justify shipping PR D now, or narrow the v1 claim accordingly.
