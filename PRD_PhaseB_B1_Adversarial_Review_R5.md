# Reviewer 3 Adversarial Review: Folio Provenance Linking Spec Rev 5

## Assumption Attack

| Assumption | Why It Might Be Wrong | Impact If Wrong |
|---|---|---|
| The appendix package is enough to resolve governance drift. | The live reference docs still say the old thing today: roadmap still frames PR D as deliverable-to-evidence and omits `folio provenance` and `supersedes` from the active relationship surface ([04_Implementation_Roadmap.md:437](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L437), [04_Implementation_Roadmap.md:439](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L439), [04_Implementation_Roadmap.md:464](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L464), [04_Implementation_Roadmap.md:558](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L558)); ontology still lacks `provenance_links` and still recommends a different v1 ordering ([Folio_Ontology_Architecture.md:465](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L465), [Folio_Ontology_Architecture.md:787](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L787)); enrich refresh still does not preserve provenance state ([folio_enrich_spec.md:1157](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1157)); kickoff checklist still describes deliverable-to-evidence provenance ([tier3_kickoff_checklist.md:92](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L92), [tier3_kickoff_checklist.md:195](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L195)). | High process risk: downstream implementation and future reviews can still follow contradictory sources. |
| `re_evaluate_pending` is durable because the spec stores both a link status and a pair marker. | Durability now depends on two separate state locations staying in sync: `provenance_links[].link_status` and `_llm_metadata.provenance.pairs[*].re_evaluate_requested` ([folio_provenance_spec.md:415](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L415), [folio_provenance_spec.md:547](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L547), [folio_provenance_spec.md:733](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L733)). The spec does not define a self-heal rule when they diverge. | High data-lifecycle risk: links can sit in `re_evaluate_pending` forever without ever being retried. |
| The hard shard ceiling makes dense pairs safe. | It bounds spend, but it does not define what happens to stale or `re_evaluate_pending` links when the pair aborts before producing results ([folio_provenance_spec.md:547](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L547), [folio_provenance_spec.md:667](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L667)). | High operational risk: the system can become bounded-but-unrepairable on exactly the dense notes that need repair. |
| 200-character snapshots are enough for trustworthy `refresh-hashes`. | The spec explicitly truncates both snapshots to 200 chars ([folio_provenance_spec.md:408](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L408)), while the real vault already contains very dense notes up to 393,335 chars ([tier2_real_vault_validation_report.md:96](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L96)). | Medium-high human-factors risk: reviewers may "verify" the wrong stale link. |
| Adding `provenance_link_stale` as an additive flag is harmless. | The real vault already has a 94% flagged rate, which the validation report says is too broad for useful triage ([tier2_real_vault_validation_report.md:98](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L98), [tier2_real_vault_validation_report.md:139](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L139)). | Medium product risk: stale provenance may disappear into existing review-noise. |
| Seeded real-library validation adequately proves the risky branches. | The spec only requires dense-pair sharding validation "if the seeded pair is sufficiently large" ([folio_provenance_spec.md:1040](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1040)). That leaves the new ceiling and over-ceiling error path optional in the only real-library gate. | Medium validation risk: the hardest new path can remain unexercised and still pass acceptance. |

## Failure Mode Analysis

| Failure | How It Happens | Would We Notice? |
|---|---|---|
| `re_evaluate_pending` link never resolves | Review action sets `link_status: re_evaluate_pending`, but `re_evaluate_requested` is missing, cleared early, or lost in a partial/manual edit. Step 8 only processes pairs with the marker ([folio_provenance_spec.md:547](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L547)). | Weakly. Status shows the pending link, but the spec gives no invariant checker or self-heal. |
| Dense pair becomes permanently unrepairable | A stale or orphaned link on a very large pair is sent to `re-evaluate`; the pair exceeds `max_shards_per_pair` and aborts ([folio_provenance_spec.md:667](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L667)). The spec does not define a terminal error state or fallback path for the pending link. | Partially. The pair errors, but the remediation contract is missing. Operators may see repeated failure with no documented escape hatch besides manual delete/ack. |
| Human refreshes the wrong stale link | `refresh-hashes` relies on persisted snapshots for visual verification ([folio_provenance_spec.md:748](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L748)), but those snapshots are truncated to 200 chars ([folio_provenance_spec.md:408](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L408)). | Not reliably. It can look successful while silently blessing the wrong linkage. |
| Drifted acknowledged links fall through batch tooling | The spec says `acknowledged_stale` can "effectively" re-enter stale state when hashes drift ([folio_provenance_spec.md:799](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L799)), but the persisted `link_status` does not change. Batch semantics are written in terms of stale/orphaned links, not computed effective state ([folio_provenance_spec.md:735](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L735)). | Maybe not. A naive implementation can miss these links entirely. |
| Implementation follows the wrong source of truth | Engineers read the live roadmap/checklist/ontology/enrich spec instead of the appendix package. Those documents still conflict with Rev 5 today ([04_Implementation_Roadmap.md:437](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L437), [tier3_kickoff_checklist.md:92](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L92), [folio_enrich_spec.md:1157](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1157)). | Probably late. You find out when code or later reviews align to the wrong contract. |
| Real-library gate passes without testing the new dangerous branch | The seeded pair is not actually dense, so neither sharding nor over-ceiling behavior is exercised ([folio_provenance_spec.md:1040](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1040)). | No, unless the validation plan explicitly records pair density and shard count. |

## Edge Case Inventory

- `re-evaluate` requested on a pair that already exceeds the shard ceiling.
- `re_evaluate_pending` link exists but the pair marker is false or absent.
- Pair marker is true but the link was manually removed.
- `acknowledged_stale` link drifts again and must be treated as stale even though `link_status` still says acknowledged.
- Orphaned link rematches to a different slide; old link is removed, but the replacement remains only a pending proposal.
- Protected-note `re-evaluate` regenerates unrelated proposals across the whole singular `supersedes` pair.
- Dense source note with one oversized claim plus many passage shards.
- Refresh runs before the appendix-based enrich refresh contract is actually landed in the live enrich spec.
- Review surface already saturated by existing flags, then provenance adds another additive flag.
- Real-library seeded run uses a convenient small pair and never tests the hard ceiling path.

## Blind Spot Identification

- The spec lacks an invariant-repair rule for mismatched `re_evaluate_pending` and `re_evaluate_requested` state.
- The spec lacks a terminal lifecycle state for "cannot be re-evaluated because pair exceeds ceiling."
- The stale-review contract assumes truncated snapshots are enough evidence for a human to safely bless new hashes.
- The batch-action contract does not explicitly say whether it operates on persisted `link_status` or computed effective state.
- The governance package is strong as patch prose but weak as live-document hygiene; the actual source corpus remains contradictory at review time.
- The acceptance gate does not require proof that the shard ceiling and over-ceiling failure mode were exercised on real-library structure.
- Security treatment is thin. "Same trust model as enrich" is not a real threat model for prompt injection or content-shaped denial of service ([folio_provenance_spec.md:679](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L679)).

## Risk Assessment

Overall risk level: High.

| Attack Vector / Risk | Applicability | Severity | Why |
|---|---|---|---|
| Operational DoS via dense note | Applicable | High | A single oversized pair can now be bounded, but it may also be impossible to repair once stale or orphaned because the spec stops at "abort the pair." |
| State desynchronization via partial/manual metadata edits | Applicable | High | The stale-repair flow depends on dual state with no specified reconciliation path. |
| Human false confirmation | Applicable | Medium-High | Truncated snapshots create a realistic path to approving the wrong refresh on long passages. |
| Governance drift / wrong implementation source | Applicable | Medium-High | The live roadmap, checklist, ontology, and enrich refresh contract still contradict the Rev 5 scope today. |
| Review-surface saturation | Applicable | Medium | The real vault already has a nearly unusable flagged surface; provenance adds more noise without a dedicated triage channel. |
| Prompt injection | Partially applicable | Low-Medium | Evidence content is author-controlled but still LLM-visible; the spec does not add meaningful mitigation beyond inheritance from enrich. |

## Issues Found

### Critical

1. The new shard ceiling can strand stale repairs instead of merely bounding cost. The spec now aborts pairs above `max_shards_per_pair` ([folio_provenance_spec.md:667](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L667)), but the `re-evaluate` resolution flow only describes success or "not re-proposed" outcomes ([folio_provenance_spec.md:547](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L547)). There is no contract for what happens when a stale or orphaned link is queued for re-evaluation and the pair errors before any proposals exist. That is a new stuck-state: bounded spend, unresolved link, no documented recovery semantics.

2. `re_evaluate_pending` still is not robust against state divergence. Rev 5 improves durability by storing the link and the queue marker, but processing still keys only off `re_evaluate_requested: true` ([folio_provenance_spec.md:547](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L547)). The spec never says "if any link in the pair is `re_evaluate_pending`, force repair regardless of marker state." Without that invariant, a partial write, manual frontmatter edit, refresh bug, or future migration bug can leave links permanently pending.

3. The approval corpus is still contradictory in the live documents being cited for verification. Rev 5 includes appendix patch text and says those amendments are part of the package ([folio_provenance_spec.md:1081](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1081)), but the actual roadmap, ontology, enrich spec, and kickoff checklist still conflict today ([04_Implementation_Roadmap.md:437](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md#L437), [Folio_Ontology_Architecture.md:465](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md#L465), [folio_enrich_spec.md:1157](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_enrich_spec.md#L1157), [tier3_kickoff_checklist.md:92](/Users/jonathanoh/Dev/folio.love/docs/validation/tier3_kickoff_checklist.md#L92)). If this is approved without landing those doc edits in the same change set or issuing an explicit supersession artifact, the source-of-truth package remains brittle.

### Major

1. Snapshot-based verification is still under-specified for dense real notes. The spec promises visual verification via persisted snapshots ([folio_provenance_spec.md:251](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L251), [folio_provenance_spec.md:748](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L748)), but it also caps those snapshots at 200 characters ([folio_provenance_spec.md:408](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L408)). On vault notes that are already hundreds of thousands of characters long ([tier2_real_vault_validation_report.md:96](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L96)), that is not enough to trust `refresh-hashes` as a safe human decision surface.

2. The seeded real-library validation gate is still too easy to satisfy. It requires dense-pair sharding only "if the seeded pair is sufficiently large" ([folio_provenance_spec.md:1043](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1043)). That means the real-library gate can pass without exercising the new ceiling or its failure mode. For the riskiest new control in Rev 5, that is too weak.

3. The review-surface mitigation is not convincing against the actual corpus. Rev 5 correctly avoids auto-setting `review_status: flagged` ([folio_provenance_spec.md:806](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L806)), but it still adds another review flag in a vault where 94% of notes are already flagged ([tier2_real_vault_validation_report.md:98](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_real_vault_validation_report.md#L98)). The spec does not provide a dedicated triage surface strong enough to offset that existing saturation.

### Minor

1. Acceptance criteria still contradict the main lifecycle model. The body of the spec says there are four visible states including `re_evaluate_pending` ([folio_provenance_spec.md:253](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L253)), but the acceptance criteria say "three visible states" ([folio_provenance_spec.md:1022](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L1022)). That ambiguity is small but avoidable in a review-sensitive workflow.

2. The security section is too thin for an LLM workflow touching author-controlled content. "Same trust model as enrich" ([folio_provenance_spec.md:679](/Users/jonathanoh/Dev/folio.love/docs/specs/folio_provenance_spec.md#L679)) is not a concrete threat model or abuse-case statement.

## Verdict

Block.

Unblock requirements:

1. Define an explicit recovery contract for over-ceiling pairs, including how stale and `re_evaluate_pending` links behave on pair error, what status the operator sees, and what manual fallback is supported.
2. Add an invariant/self-heal rule: any pair containing a `re_evaluate_pending` link must be reprocessed even if `re_evaluate_requested` is missing, or the spec must define a surfaced terminal inconsistency state and repair command.
3. Strengthen `refresh-hashes` evidence. Either store sufficient immutable old text to support real verification on dense passages, or explicitly downgrade the command and require a safer manual review path.
4. Land the actual roadmap, ontology, enrich-refresh, kickoff-checklist, and PRD amendments in the same approval change, or publish an explicit supersession artifact that downstream readers will treat as authoritative immediately.
5. Tighten the real-library gate so it must exercise both sharded behavior and the over-ceiling/error path, not just "if the seeded pair is sufficiently large."
