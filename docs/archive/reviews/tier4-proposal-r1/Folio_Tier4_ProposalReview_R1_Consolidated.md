# Folio Tier 4 Proposal Review — R1 · Consolidated

Consolidator identity: Claude Code + claude-opus-4-6 (orchestrator)
Review round: 1
Artifact: folio.love PR #43 (branch `codex/tier4-latent-discovery-proposal-layer` @ `5063279`)
Primary target: `docs/specs/tier4_discovery_proposal_layer_spec.md`
Method: LLM Development Playbook §13 — two independent reviewers dispatched in parallel via a single orchestrator message, each with a self-contained prompt, no knowledge of the other's existence. Both reviews are on disk verbatim; this document consolidates them per §13.4 (surface disagreements explicitly; do not synthesize).

Source reviews:
- [R1 · Adversarial · Product](./Folio_Tier4_ProposalReview_R1_Adversarial_Product.md) — Claude Code + claude-opus-4-6
- [R2 · Alignment · Technical](./Folio_Tier4_ProposalReview_R1_Alignment_Technical.md) — Claude Code + claude-sonnet-4-6

---

## 1. Verdict Summary Table

| Reviewer | Posture | Lens | Verdict | Blocking Issues (reviewer's own words) |
|---|---|---|---|---|
| R1 | Adversarial | Product | **Request Changes** | Spec has no user-centered problem statement (C-1); acceptance criteria are all documentation checks, not falsifiable (C-2); internal contradiction between "no new CLI command families" non-goal and FR-810 introducing `folio enrich diagnose` (C-3); default-exclude-flagged digest/synthesize rule with no override causes silent information loss (M-1); `input_fingerprint` staleness semantics unspecified (M-2); entity-merge mass-invalidates proposals with no dampener (M-3); bundle-rendering UX undefined (M-4); Tier 4 grew +4.5 weeks of infrastructure with no added user-visible surface (M-5); F-414/F-415 value rated High without evidence (M-6); `relates_to` deferred from FR-812 despite being highest-volume relation (M-7); no calibration floor before proposals surface (M-8) |
| R2 | Alignment | Technical | **Request Changes** | `v0.5.1_tier3_entity_system_spec.md` still classifies `folio entities merge` as "a future UX pass" while the command is shipped (M1); `folio_enrich_spec.md` contains no spec section for the `folio enrich diagnose` subcommand introduced by FR-810 (M2) |

Both reviewers arrive at the same verdict label — **Request Changes** — but their blocking-issue sets and the scale of required rework are materially different. That divergence is the load-bearing finding of this review round and is not collapsed below.

---

## 2. Product vs. Technical Disagreement

Per §13.4, disagreements between product-lens and technical-lens reviewers are preserved verbatim rather than averaged. This round surfaces six substantive disagreements. Every one is a case where R1 calls the thing an issue and R2 either does not raise it or explicitly considers the same area sound.

### D1 — Is the proposal motivated by a user problem?

> **R1 (Adversarial · Product):** "The revision does not begin from a user problem. It begins from an architectural worry. Read the spec's Overview and Goals and count the user-facing sentences: zero. … There is no 'before this PR' narrative showing what is broken for Johnny today that the latent/proposal/canonical boundary fixes." (§1)
>
> **R2 (Alignment · Technical):** Silent. R2's Architecture Compliance section (§1) treats the latent → proposal → canonical separation as "structurally compliant" and congruent with the ontology. R2 does not evaluate product motivation.

**Treatment:** preserved as blocker per R1; out of scope for R2's lens.

### D2 — Are the acceptance criteria falsifiable?

> **R1 (Adversarial · Product):** "All five items in Section 11 … are documentation checks, not product checks. … None of these measure whether the thing works for a user. A spec can satisfy all five with zero product value delivered. That is the definition of a non-falsifiable exit criterion." (§7)
>
> **R2 (Alignment · Technical):** Silent. R2 confirms that "every FR cited in the new crosswalk entries has a defined body in the PRD" (§3) and that the proposal spec is internally consistent, but does not evaluate whether the acceptance criteria are observable.

**Treatment:** preserved as blocker per R1; R2's lens does not test for this.

### D3 — Is the proposed scope right-sized?

> **R1 (Adversarial · Product):** "Tier 4 grew from 10+ weeks / 17.5 weeks estimated to 12+ weeks / 22 weeks. … That's an additional 4.5 weeks of effort for work that ships no new user-visible surface … F-414 and F-415 sit between digest and related-links, pushing user-facing surfaces out by ~6 roadmap weeks." (§3, §5)
>
> **R2 (Alignment · Technical):** Silent. R2's Roadmap Alignment (§2) confirms that every FR maps to a roadmap week but does not evaluate whether the total effort is justified.

**Treatment:** preserved as blocker per R1; R2 verifies internal mapping only.

### D4 — Is the default-exclude-flagged trust gate safe to ship?

> **R1 (Adversarial · Product):** "Silent information loss risk. If Johnny flags an interview as 'needs re-review' for a minor attribution question, it silently drops out of the daily digest. The digest spec lacks an `--include-flagged` override in v1 … There is no safety valve." (§4, M-1)
>
> **R2 (Alignment · Technical):** "Digest spec §5 rule 4 … applies the trust gate at input selection time. Digest spec §12 item 4 … reaffirms this. The `## Trust Notes` section requirement … makes the exclusion visible to the human reader. This is consistent with proposal spec §8 and FR-811." (§7)

**Treatment:** direct disagreement on the same rule. R1 says silent and unsafe; R2 says consistent and disclosed.

### D5 — How severe is the `folio enrich diagnose` introduction?

> **R1 (Adversarial · Product):** "Internal contradiction between 'no new CLI command families' (Non-Goals) and FR-810 adding `folio enrich diagnose`. Either remove FR-810 from this revision or drop the Non-Goal claim." (C-3)
>
> **R2 (Alignment · Technical):** "FR-810 introduces `folio enrich diagnose [scope] [--json] [--limit N]` as a new subcommand of `folio enrich`. The governing spec for the enrich command family (`folio_enrich_spec.md`) contains no mention of a `diagnose` subcommand. … This is not a backward compatibility break (adding a new subcommand does not break existing behavior), but it creates a spec coverage gap." (§6, M2)

**Treatment:** both reviewers noticed the new command. R1 treats the juxtaposition with the stated non-goal as a Critical contradiction; R2 treats it as a Major spec-coverage gap that is fixable by updating the enrich spec. Different severities, different fixes.

### D6 — Is the governing corpus outside this PR a blocker?

> **R2 (Alignment · Technical):** "`docs/specs/v0.5.1_tier3_entity_system_spec.md` lines 96, 519 … explicitly classifies `folio entities merge` as 'a future UX pass' and excludes it from v1. The roadmap names `folio entities suggest-merges` / `merge` as shipped Tier 4 foundation … The governing Tier 3 spec is factually incorrect relative to the shipped state." (M1)
>
> **R1 (Adversarial · Product):** Silent. R1 did not cross-check the Tier 3 entity spec against shipped state.

**Treatment:** preserved as blocker per R2; R1's adversarial product lens did not do this verification.

**Meta-observation on the disagreement pattern:** the two reviewers appear to have read different documents well. R1 read the product framing hard and found it thin. R2 read the cross-document alignment hard and found it mostly solid, with two specific corpus-completion gaps. Neither is wrong within their lens. Both must be satisfied to pass §13.

---

## 3. Aggregated Issue List

Deduplicated, grouped by severity. Attribution: **(R1)** means only R1 raised it, **(R2)** means only R2 raised it, **(both)** means both raised it independently.

### Critical

| ID | Attribution | Summary | Citation |
|---|---|---|---|
| C-1 | (R1) | No user-centered problem statement; the proposal opens from an architectural worry rather than an engagement moment. | `tier4_discovery_proposal_layer_spec.md:21-35`, `02_Product_Requirements_Document.md:891-906` |
| C-2 | (R1) | All five Acceptance Criteria in Section 11 are documentation checks, not falsifiable product outcomes. FR-810/811/812/813/814 lack measurable exit criteria. | `tier4_discovery_proposal_layer_spec.md:216-224`, `02_Product_Requirements_Document.md:1120-1240` |
| C-3 | (R1) | Internal contradiction: "No new CLI command families" non-goal coexists with FR-810 adding `folio enrich diagnose`. Either remove FR-810 or drop the non-goal. | `tier4_discovery_proposal_layer_spec.md:58`, `02_Product_Requirements_Document.md:1104-1108` |

### Major

| ID | Attribution | Summary | Citation |
|---|---|---|---|
| J-1 | (R2) | `v0.5.1_tier3_entity_system_spec.md` still classifies `folio entities merge` as "a future UX pass" while the command has shipped. Governing spec contradicts shipped state; PR #43 does not update the spec. | `v0.5.1_tier3_entity_system_spec.md:96`, `v0.5.1_tier3_entity_system_spec.md:519`, `04_Implementation_Roadmap.md:520` |
| J-2 | (R2) | `folio_enrich_spec.md` has no section for the `folio enrich diagnose` subcommand introduced by FR-810. No governing spec for eligibility predicate, output schema, or failure behavior. | FR-810 at `02_Product_Requirements_Document.md:1104-1125`; absence in `folio_enrich_spec.md` (entire document) |
| J-3 | (R1) | Default-exclude-flagged rule applied library-wide to digest/synthesize/traversal/search with no `--include-flagged` override in v1. Silent information loss: the operator cannot temporarily widen the input set without editing frontmatter. R2 considers this rule sound (see D4). | `02_Product_Requirements_Document.md:1127-1141`, `tier4_digest_design_spec.md:64`, `tier4_digest_design_spec.md:97` |
| J-4 | (R1) | `input_fingerprint` semantics for staleness unspecified. Prompt changes, model upgrades, and tokenizer differences can all flip fingerprints, rehydrating the review queue with previously-rejected proposals. | `tier4_discovery_proposal_layer_spec.md:99-100`, `tier4_discovery_proposal_layer_spec.md:150-156` |
| J-5 | (R1) | Entity-merge cascades mass-invalidate proposals via the stale rule. In a vault with regular hygiene, every merge triggers mass re-review. No dampener, throttle, or batch-mark-stale behavior is specified. | `tier4_discovery_proposal_layer_spec.md:152-156` |
| J-6 | (R1) | Bundle-rendering UX undefined. The `folio links review` surface must display `evidence_bundle`, `reason_bundle`, `trust_bundle`, and `schema_gate_result` per proposal; four structured fields cannot be reviewed effectively on a CLI without a rendering contract. | `tier4_discovery_proposal_layer_spec.md:90-100` |
| J-7 | (R1) | Tier 4 total effort grew from 17.5 weeks to 22 weeks (+4.5 weeks of infrastructure) with no user-visible delivery added in those weeks. F-414/F-415 push user-facing surfaces out by ~6 weeks. | `06_Prioritization_Matrix.md:115-117`, `06_Prioritization_Matrix.md:134`, `04_Implementation_Roadmap.md:541-567` |
| J-8 | (R1) | F-414/F-415 value rated "High" by the prioritization matrix with no evidence. The only cited mitigation is circular. | `06_Prioritization_Matrix.md:115-117`, `06_Prioritization_Matrix.md:225` |
| J-9 | (R1) | `relates_to` and `instantiates` deferred from FR-812 relation-schema validation, yet `relates_to` is where most LLM-suggested links will land. Validating only small-volume canonical relations misses the high-volume risk surface. | `02_Product_Requirements_Document.md:1159-1167` |
| J-10 | (R1) | No calibration floor, confidence threshold, or acceptance-rate gate before a proposal surfaces. Strategic memo demands the system "know what it doesn't know" but nothing in FR-813/FR-814 enforces a calibration signal. | `strategic_direction_memo.md:38`, `02_Product_Requirements_Document.md:1179-1240` |

### Minor

| ID | Attribution | Summary | Citation |
|---|---|---|---|
| N-1 | (both) | FR-814 lifecycle states bullet treats `expired` and `superseded` as alternatives (implying 7 states) while proposal spec §6 treats them as 8 distinct states. R1 raises as Mi-5, R2 raises as m1 — independent confirmation. | `02_Product_Requirements_Document.md:1226`, `tier4_discovery_proposal_layer_spec.md:115-116` |
| N-2 | (both) | Tier 4 Exit Criteria (10 items) and Tier 4 Gate in Quality Gates (9 items) are not identical: "documented as non-canonical and rebuildable" appears as an Exit Criterion but has no matching Quality Gate. R1 raises as Mi-7, R2 raises as m2 — independent confirmation. | `04_Implementation_Roadmap.md:601`, `04_Implementation_Roadmap.md:749` |
| N-3 | (R1) | Architecture doc uses a "shadow graph" hedge alongside formal terminology. Either commit to `latent discovery layer` or drop the term. | `Folio_Ontology_Architecture.md:150-151` |
| N-4 | (R1) | `expired` and `superseded` are described together as "bounded queue management" despite carrying different semantics (successor existence vs. time passage). | `tier4_discovery_proposal_layer_spec.md:115-116`, `tier4_discovery_proposal_layer_spec.md:129-130` |
| N-5 | (R1) | Rejection memory storage location and cross-machine persistence unspecified. On clone/rebase/migration, rejection memory may not survive, causing previously-rejected proposals to resurface. | `tier4_discovery_proposal_layer_spec.md:134-148` |
| N-6 | (R1) | The new log file's filename and event type do not match its content: filename says `update-readme-with-folio-ingest-enrich-provenanc` but the content documents Tier 4 proposal revision. | `docs/logs/2026-04-14_update-readme-with-folio-ingest-enrich-provenanc.md:1-11` |
| N-7 | (R1) | Digest spec claims alignment with the shared Tier 4 graph-ops foundation but demonstrates no interop — no worked example of a digest producing a proposal and having it confirmed through `folio links`. | `tier4_digest_design_spec.md:7-12`, `tier4_digest_design_spec.md:280-290` |
| N-8 | (R2) | Digest spec `revision` field jumps from 1 (PR #41) to 3 in PR #43 with no revision 2 and no corresponding `revision_note` entry. Revision audit trail has a gap. | `tier4_digest_design_spec.md` front-matter |
| N-9 | (R2) | Proposal spec's `depends_on` list does not include `folio_provenance_spec` or `folio_enrich_spec`, though the proposal contract pattern is architecturally descended from both. Reduces traceability. | `tier4_discovery_proposal_layer_spec.md:11-17` |
| N-10 | (R2) | FR-814 consumer list uses abbreviated names (`digest`, `synthesize`, `search`) while proposal spec §9 uses fully-qualified `folio digest`, `folio synthesize`, `folio search`. Weakens cross-document precision. | `02_Product_Requirements_Document.md` FR-814, `tier4_discovery_proposal_layer_spec.md` §9 |

Totals: **3 Critical (all R1), 10 Major (8 R1, 2 R2), 10 Minor (2 both, 5 R1, 3 R2)**. Two Minor items were found independently by both reviewers, which is the only overlap.

---

## 4. Independence Caveat

The LLM Development Playbook §13 prefers cross-vendor independence (Gemini / Codex / Claude or equivalents) so that model idiosyncrasies do not correlate. This round did not achieve that. Both reviewers ran on Claude:

- R1 used `claude-opus-4-6` under an `Adversarial · Product` prompt.
- R2 used `claude-sonnet-4-6` under an `Alignment · Technical` prompt.

Structural independence was preserved: the two reviewers ran concurrently in separate contexts, received non-overlapping prompts, and had no knowledge of each other's existence at any point. Neither could see the other's findings during or after its own run. But because both sit inside the same vendor's model family, shared training-data biases or shared failure modes are not fully controlled for.

Consequence for interpretation: **agreements between R1 and R2 (the two Minor items N-1 and N-2) are weaker evidence of validity than a cross-vendor confirmation would be.** Disagreements are not weaker evidence — they reflect different prompts and different lenses, and those factors are preserved cleanly. The disagreement pattern in §2 is therefore the most trustworthy output of this review.

If this round is rerun for high-stakes decisions, the recommended mitigation is to run at least one reviewer on a non-Claude model (e.g., Gemini 2.5 Pro or GPT-5) under the same prompt skeleton.

---

## 5. Recommended Next Step

The two reviewers arrive at the same verdict label but converge only on the 2 Minor agreements. Unblocking conditions differ materially. Both sets are quoted verbatim below; merge policy is stated after.

### R1's unblocking conditions (quoted verbatim)

> 1. **Open the spec with a user problem.** Replace Section 1 Overview with one engagement moment — e.g., Johnny reviews proposed links during SteerCo prep and the same rejected suggestion keeps reappearing, costing him N minutes per run. Name the user, the moment, the cost, and the expected post-change cost. If that problem cannot be articulated, the spec should be withdrawn.
> 2. **Resolve C-3.** Either remove FR-810 from this revision and defer `folio enrich diagnose` to a later slice, or remove "New CLI command families" from the Non-Goals. The two cannot both hold.
> 3. **Replace all documentation-check acceptance criteria with product-outcome criteria.** FR-810/811/812/813/814 each need at least one falsifiable outcome: a measurable review-queue size, an observed user decision time, a digest-usability test in real engagement context, or a minimum proposal acceptance rate. Soft criteria ("explicitly defined", "explicitly rebuildable", "strong enough") are rejected.
> 4. **Pin `input_fingerprint` semantics.** State exactly which inputs feed the fingerprint and which do not. Explicitly address prompt changes, model upgrades, and tokenizer differences. Without this pin, rejection memory is a fiction.
> 5. **Specify an `--include-flagged` override (or equivalent) for digest/synthesize/search/traversal.** The default-exclude-flagged rule cannot ship in v1 without a safety valve. If the valve is deferred, the default rule must be deferred with it.
> 6. **Add a review-queue bound.** Either a per-engagement cap, a per-producer silence threshold, or an auto-suppress rule when acceptance rate falls below N%. The "rejection memory before scaling proposal volume" mitigation is not a gate; it is an aspiration.
> 7. **Bring `relates_to` into FR-812 v1.** `relates_to` is where LLM-suggested links will concentrate. Governing `supersedes`/`impacts`/`draws_from`/`depends_on` while leaving `relates_to` ungoverned validates the small queues and ignores the big one.
> 8. **Shrink scope: drop FR-813 from this revision.** The latent discovery layer is naming a concept that has zero implementations. Formalize it when the first concrete producer (candidate merges from `folio entities suggest-merges`) actually starts generating non-link proposals. Keep FR-814 if you want, but cut its lifecycle states from 8 to 4 (`suggested`, `accepted`, `rejected`, `stale`) until a need for the other four is demonstrated.
> 9. **Remove the "shadow graph" hedge.** Either commit to the `latent discovery layer` naming or drop the term. The architecture doc cannot both define formal terminology and disavow the informal alternative in the same paragraph.
> 10. **Fix Mi-4.** Rename the log file or change its event type so filename and content match.
>
> If changes 1, 3, 5, 6, and 8 are made, this becomes a credible product revision rather than an architectural framing exercise. Without them, the revision rearranges documentation without changing what ships for the user, and the roadmap grows without a corresponding outcome gain. Recommendation: request changes; do not merge.

### R2's unblocking conditions (quoted verbatim)

> **Unblocking condition 1 (M1 — entity spec currency):**
>
> `docs/specs/v0.5.1_tier3_entity_system_spec.md` must be updated to remove or supersede the non-goal statement that classifies `folio entities merge` as "a future UX pass" (lines 96 and 519). The update must either: (a) add a revision note acknowledging that `folio entities merge` and `folio entities suggest-merges` shipped as part of the Tier 4 graph-ops foundation on 2026-04-15, or (b) create a dedicated supplementary spec section covering the shipped merge behavior. The governing spec must not contradict the shipped command's existence.
>
> **Unblocking condition 2 (M2 — enrich diagnose spec coverage):**
>
> `docs/specs/folio_enrich_spec.md` must be updated to include a spec section for the `folio enrich diagnose` subcommand introduced by FR-810. At minimum, the spec must define: the eligibility predicate (which notes are evaluated), the minimum finding classes (consistent with FR-810: managed sections unidentified, protected by curation level, protected by review status), the output schema for `--json` mode, and the failure behavior. Alternatively, a standalone spec file for the quality-layer commands (FR-810/811/812) may be created with an explicit dependency declaration linking back to `folio_enrich_spec.md`.

### Merge policy

Per §13, when product and technical reviewers reach the same verdict label from divergent findings, **the union of their blocking sets applies**. Do not merge PR #43 until both sets are addressed:

- R2's two corpus-completion updates (J-1 entity spec, J-2 enrich spec) are mechanically straightforward and can land as part of this PR or as a same-day follow-up PR.
- R1's blockers are structural and will likely require a second proposal revision before Pre-Phase A can close. The minimum bar is R1's items **1, 3, 5, 6, and 8** by R1's own guidance; the remainder are strong-should-fix.

Until both reviewer blocker sets are addressed, the Pre-Phase A verdict remains **Request Changes**. The two-Minor agreement set (N-1, N-2) confirms real drift between the PRD and the proposal spec and should be folded into the revision regardless of which blocker track is prioritized.

No GitHub comment, no merge, no push was performed by this review round. Only the three review files on disk were written.
