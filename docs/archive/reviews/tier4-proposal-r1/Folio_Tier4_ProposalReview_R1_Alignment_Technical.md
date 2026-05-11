# Folio Tier 4 Proposal Review — R1 · Alignment · Technical

Reviewer identity: Claude Code + claude-sonnet-4-6
Review round: 1
Artifact: folio.love PR #43 (branch `codex/tier4-latent-discovery-proposal-layer` @ `5063279`)
Primary target: `docs/specs/tier4_discovery_proposal_layer_spec.md`

---

## 1. Architecture Compliance

The proposal layer spec (`docs/specs/tier4_discovery_proposal_layer_spec.md`) is structurally compliant with the ontology architecture (`docs/architecture/Folio_Ontology_Architecture.md`). PR #43 adds §2.8 to the ontology document, which defines the three-layer separation — latent discovery / proposal / canonical graph state — using identical terminology and design rules to what the spec introduces. The table in ontology §2.8 and the canonical boundary table in proposal spec §4 are congruent: both mark discovery and proposal layers as non-canonical and list frontmatter + registries as the only canonical source of truth.

The latent → proposal → canonical progression respects the evidence-vs-canonical-link distinction that has been established since Tier 3. Specifically:

- The proposal spec §5 contract uses `evidence_bundle`, `reason_bundle`, `trust_bundle`, and `schema_gate_result` fields, echoing the machine-proposal / human-confirmation separation already established by the provenance spec's `_llm_metadata.provenance` / `provenance_links` pattern (`docs/specs/folio_provenance_spec.md`, §9.1 and §9.2).
- Proposal spec §4 rule 2 ("proposal objects are non-canonical until explicitly reviewed and promoted") is consistent with the provenance spec's handling of `provenance_links` as human-owned canonical metadata and `_llm_metadata.provenance` as machine-owned proposals (`folio_provenance_spec.md` line 867: "`provenance_links` is human-owned canonical metadata").
- The human-confirmation posture of Tier 3 (`folio provenance confirm`, `folio entities confirm`, `folio enrich` relationship proposals requiring human promotion) is preserved: proposal spec §3 non-goals explicitly bar automatic confirmation and unsupervised schema minting.

The ontology §2.7 Trust & Reviewability section establishes `review_status: flagged` as a universal ontology field. Proposal spec §8 correctly applies this gate to the new layer (rule 1: flagged inputs excluded by default from graph-oriented surfaces) and correctly treats `extraction_confidence` as surfaced metadata rather than a second hard gate (rule 3), consistent with the ontology's design principle that the system must surface uncertainty without hiding it.

No architectural violations detected.

---

## 2. Roadmap Alignment

The roadmap changes in `docs/product/04_Implementation_Roadmap.md` are internally consistent and align with what the proposal spec actually specifies.

**Tier 4 implementation order** is updated from 5 items to 8 items. The new steps 3–5 (graph quality layer, discovery/proposal foundation, proposal lifecycle governance) correctly map to the weeks allocated:

| Roadmap step | Weeks | Content | FR coverage |
|---|---|---|---|
| Step 3 | 26-27 | Graph quality layer | FR-810, FR-811, FR-812 |
| Step 4 | 28-29 | Discovery/proposal foundation | FR-813 |
| Step 5 | 30-31 | Proposal lifecycle governance | FR-814 |

The roadmap week narratives for 28-29 ("Formalize the latent discovery layer…standardize proposal objects…Keep storage technology unspecified") match proposal spec §2 goals and §3 non-goals. The Week 30-31 narrative ("Add durable rejection memory…Define stale invalidation…Apply trust-aware surfacing") maps cleanly to proposal spec §7.1, §7.2, and §8.

The "Tier 4 Foundation (Shipped)" section added to the roadmap names `folio links`, `folio graph`, `folio entities suggest-merges/merge`, and `folio analysis init` as shipped commands. These are corroborated by the 2026-04-15 implementation log (`docs/logs/2026-04-15_tier-4-graph-ops-layer.md`) and the 196-test pass result recorded there.

The CLI command map addition in the roadmap (lines 692–701 of `04_Implementation_Roadmap.md`) lists all graph-ops commands with consistent syntax. `folio enrich diagnose [scope] [--json] [--limit N]` appears identically in the roadmap command map (line 701), in the roadmap Week 26-27 narrative (line 561), and in PRD FR-810 (line 1107). No CLI syntax inconsistency detected within the roadmap.

**One internal inconsistency in the roadmap**: The Tier 4 timeline table (near line 651) says duration is "12+ weeks" and weeks are "23-34+", consistent with the updated step count. The previous text said "10+ weeks, 23-32+", so the update is self-consistent. No residual stale week-range language detected.

**One discrepancy between Exit Criteria and Quality Gate**: The Tier 4 Exit Criteria section (10 items) and the Tier 4 Gate section in Quality Gates (9 items) are not identical. The Exit Criteria includes two items ("Latent discovery views and proposal objects are documented as non-canonical and rebuildable" and "Rejection memory and stale invalidation rules are defined for proposal review") that the Quality Gate consolidates into a single item ("Proposal review rules cover rejection memory and stale invalidation before proposal volume scales up"). The Quality Gate also omits the "documented as non-canonical and rebuildable" criterion explicitly. This is a Minor inconsistency — see Section 8.

---

## 3. PRD / Requirements Consistency

**FR mapping completeness**: The crosswalk tables in both `docs/product/02_Product_Requirements_Document.md` (lines 864-876) and `docs/product/06_Prioritization_Matrix.md` (lines 102-114) are identical for F-401 through F-415 mapping to FR-801 through FR-814. The new entries (F-411 → FR-810, F-412 → FR-811, F-413 → FR-812, F-414 → FR-813, F-415 → FR-814) are synchronized across both documents. No crosswalk divergence.

**FR body completeness**: Every FR cited in the new crosswalk entries has a defined body in the PRD:

- FR-810 (`docs/product/02_Product_Requirements_Document.md`, line 1104): defined with CLI syntax, minimum finding classes, and acceptance criteria.
- FR-811 (line 1127): defined with scope list, trust gate rule, and acceptance criteria.
- FR-812 (line 1151): defined with validation checks, v1 governed relations, deferred relations, and acceptance criteria.
- FR-813 (line 1179): defined with discovery surface types, rebuildability rule, and acceptance criteria.
- FR-814 (line 1204): defined with minimum field list, lifecycle states, rejection/stale rules, and acceptance criteria.

**New FR roadmap/matrix coverage**: All five new FRs have corresponding roadmap entries (Weeks 26-27, 28-29, 30-31) and matrix entries (F-411 through F-415 in the Tier 4 table). The matrix includes rationale, effort, risk, and dependency graph entries for all five new features (lines 120-124 and 209-213 of `06_Prioritization_Matrix.md`).

**One lifecycle state count discrepancy**: FR-814 lists minimum lifecycle states as `suggested`, `queued`, `accepted`, `rejected`, `suppressed`, `stale`, and then "`expired` or `superseded`" (treating them as alternatives in one bullet). The proposal spec §6 lists them as eight distinct states: `suggested`, `queued`, `accepted`, `rejected`, `suppressed`, `stale`, `expired`, and `superseded` separately. This is a Minor inconsistency in cardinality framing — the PRD implies 7 minimum states, the spec specifies 8 distinct states. This is documented in Section 8.

**FR-811 scope gap**: FR-811 names these surfaces: `folio graph`, `folio digest`, `folio synthesize`, org traversal, semantic search. It does not name `folio links` or `folio entities`. Proposal spec §8 rules state that flagged inputs are excluded by default from "graph-oriented Tier 4 discovery and output surfaces" and that proposals from flagged inputs must surface as trust-degraded in the review queue. The spec's §8 rule 2 effectively applies a modified form of the trust gate to folio links (proposals appear as trust-degraded, not suppressed entirely), which is a different behavior from the hard exclusion FR-811 mandates. FR-811 is silent on how folio links should handle trust-degraded proposals. This is a Minor inconsistency in scope specification — see Section 8.

---

## 4. Ontology & Data Model Alignment

The proposal layer spec correctly preserves the separation between machine proposals and canonical graph state:

**Machine proposals remain non-canonical**: Proposal spec §4 rules 1-5 prohibit probabilistic writes to canonical graph state. The proposal object contract in §5 stores evidence, reason, trust, and lifecycle state in named bundles rather than in frontmatter relationship fields. This mirrors the established `_llm_metadata` pattern from the enrich and provenance specs.

**Canonical state remains frontmatter + registries**: Proposal spec §4 rule 3 and §4 rule 4 (sidecar index must be derived and rebuildable) are consistent with the ontology's frontmatter-as-source-of-truth principle (ontology §2.6). The spec does not introduce any new canonical field, registry mutation, or permanent side-table.

**Human confirmation boundary maintained**: Proposal lifecycle §6 state 3 defines `accepted` as the result of explicit human review and promotion. The spec explicitly prohibits automatic promotion (§3 non-goals: "Automatic confirmation of machine suggestions"). This preserves the governance posture established in the entity spec (entity system spec, §11.3 confirmation lifecycle) and the provenance spec (`folio provenance confirm` as the promotion mechanism).

**Trust fields**: The `trust_bundle` field in the proposal object contract (§5) and the `extraction_confidence` surfacing rule in §8 rule 3 are consistent with the ontology's definition of `extraction_confidence` as a universal field that is surfaced metadata rather than a hard gate (`Folio_Ontology_Architecture.md`, §12.1, line 815).

**No new ontology fields introduced**: PR #43 does not add new frontmatter fields or registry schema changes. The existing `review_status`, `extraction_confidence`, `provenance_links`, and `_llm_metadata` fields are referenced but not mutated.

One structural observation: the proposal spec's `depends_on` front-matter list (lines 11-17 of `tier4_discovery_proposal_layer_spec.md`) does not include `folio_provenance_spec` or `folio_enrich_spec`, even though the proposal contract pattern (evidence bundle, reason bundle, machine vs. canonical separation) is architecturally descended from those specs. This is not a correctness defect — the spec does not contradict either — but the missing lineage citations reduce traceability. This is classified Minor in Section 8.

---

## 5. CLI / Interface Contract Consistency

The commands mentioned across the PR's modified documents are checked for name, scope, and syntax consistency:

**`folio enrich diagnose [scope] [--json] [--limit N]`**

Appears in: PRD FR-810 (line 1107), Roadmap Week 26-27 (line 561), Roadmap CLI map (line 701), Roadmap v1.6 changelog header (line 17). Syntax is identical across all four locations. Consistent.

**`folio links review / status / confirm / reject`**

Listed in Roadmap CLI map (lines 692-695) and described in PRD §2.8 graph-ops foundation paragraph (line 892). The proposal spec §9 names `folio links` as a consumer without specifying CLI syntax (consistent with §3 non-goal of no new CLI commits from the proposal spec). The digest spec §13 deferred item 2 correctly says "digest-generated relationship suggestions routed through `folio links`" is deferred. Consistent across documents.

**`folio graph status / doctor`**

Listed in Roadmap CLI map (lines 696-697). PRD §2.8 refers to "`folio graph` is the default graph health and backlog surface" (line 894) without specifying subcommand syntax. The proposal spec §9 names `folio graph` as a consumer. The ontology architecture does not name subcommands. No syntax conflict.

**`folio analysis init`**

Listed in Roadmap CLI map (line 700) and Roadmap Tier 4 Foundation section (line 522). Not mentioned in any spec file. No spec file has been created or updated for this command beyond the implementation log. This is consistent with the proposal spec's non-goal ("no additional user-facing CLI is required in this revision"), but there is no governing spec for `folio analysis init` beyond the log. This is noted but within scope of the graph-ops foundation, not the proposal layer spec.

**`folio entities suggest-merges / merge`**

Listed in Roadmap CLI map (lines 698-699) and Roadmap Tier 4 Foundation section (line 520). Tests in `tests/test_cli_entities.py` (lines 768, 798) confirm both commands are shipped. However, `docs/specs/v0.5.1_tier3_entity_system_spec.md` (lines 96 and 519) explicitly says `folio entities merge` is "a future UX pass" and is not part of v1. This spec has NOT been updated by PR #43 to reflect that merge is now shipped. The governing Tier 3 spec contradicts the shipped state. This is classified Major in Section 8.

**`folio digest` CLI syntax**

`folio digest <scope> [--date YYYY-MM-DD] [--week] [--llm-profile <profile>]` appears in: PRD FR-801 (line 912), digest spec §4 (line 69), Roadmap CLI map (line 702), Feature Handoff Brief (line 68). Consistent across all four locations.

---

## 6. Tier 3 Backward Compatibility

The PR makes no changes to Tier 3 spec files (`folio_provenance_spec.md`, `folio_enrich_spec.md`, `v0.5.0_tier3_ingest_spec.md`, `v0.5.1_tier3_entity_system_spec.md`). The Tier 3 contracts are not directly modified.

**Contracts preserved:**

- The enrich spec's eligibility rules (evidence and interaction notes only; analysis, context, and diagram notes excluded) are preserved and explicitly reaffirmed in the digest spec §8 rule 5 ("enrich continues to skip `analysis` rows in the first digest slice") and in digest spec §3 non-goals ("Digest-specific enrich pass: Current `folio enrich` continues to skip `analysis` docs").
- The provenance spec's `_llm_metadata.provenance` / `provenance_links` machine-proposal / canonical-link separation is preserved as the pattern for the new proposal layer contract.
- The entity system spec's ingest-time resolution model is unmodified.
- The registry schema v2 source-less document support (introduced for context docs in PR E) is reused for digest notes without modification.

**One Tier 3 spec that is now stale** (not broken, but contradicted by shipped code):

`docs/specs/v0.5.1_tier3_entity_system_spec.md` lines 96 and 519 explicitly classify `folio entities merge` as "a future UX pass." PR #43 does not update this spec, but the roadmap (line 520) and tests (`test_cli_entities.py` lines 717, 755, 842) confirm the command is shipped. The entity system spec's non-goals table now contains a statement that is factually incorrect relative to the shipped state. This does not break any existing canonical contract, but it does mean the governing Tier 3 spec for the entity system is stale on a shipped CLI surface. This is classified Major in Section 8.

**FR-810 (`folio enrich diagnose`) and `folio_enrich_spec.md`**: The enrich spec defines the enrich command family but contains no reference to a `diagnose` subcommand. FR-810 introduces this new subcommand at the PRD level without updating the governing enrich spec. This is not a backward compatibility break (adding a new subcommand does not break existing behavior), but it creates a spec coverage gap: the implementation will have no governing spec beyond the PRD FR body. This is classified Minor in Section 8.

---

## 7. Digest Spec Alignment

`docs/specs/tier4_digest_design_spec.md` (revised from revision 1 to revision 3 by PR #43) aligns correctly with the revised proposal layer spec in all material respects:

**Inputs/outputs**: The digest spec §5 daily input predicate (type evidence or interaction, not flagged, activity date matching) is consistent with FR-811's trust gate and with proposal spec §8 rule 1 (flagged inputs excluded by default). The digest spec §8 registry contract preserves the source-less managed doc pattern and the `enrich`-skip-analysis rule.

**Flagged-evidence handling**: Digest spec §5 rule 4 ("review_status is not flagged") applies the trust gate at input selection time. Digest spec §12 item 4 ("daily digest input selection excludes flagged source-backed notes by default") reaffirms this. The `## Trust Notes` section requirement (§9, item 6 for daily, item 7 for weekly) makes the exclusion visible to the human reader. This is consistent with proposal spec §8 and FR-811.

**Routing of relationship suggestions to `folio links`**: Digest spec §3 non-goals correctly defers "Digest-specific proposal lifecycle or relationship confirmation UX" to the shared proposal layer and `folio links`. Digest spec §13 item 2 lists "digest-generated relationship suggestions routed through `folio links`" as deferred work. The proposal spec §9 lists `folio digest` as a "planned" consumer (the language is "existing and planned Tier 4 surfaces"). This is internally consistent: the digest is a planned consumer once it generates relationship suggestions, not a current consumer for the first slice.

**`extraction_confidence` handling**: Digest spec §5 last paragraph ("extraction_confidence remains surfaced trust metadata, not a second hard exclusion rule in the first digest slice") is consistent with proposal spec §8 rule 3 and FR-811's `extraction_confidence` language.

**Revision numbering gap**: The digest spec's `revision` field jumps from 1 (as it stood in commit `aaf02e1` / PR #41) to 3 in PR #43. There is no revision 2 and no `revision_note` entry for a revision 2. This is a metadata gap in the spec's own revision history. This is classified Minor in Section 8.

**`depends_on` field addition**: The digest spec correctly adds `tier4_discovery_proposal_layer_spec` to its `depends_on` list (line 18 of revised digest spec). This bidirectional dependency reference (proposal spec also lists `doc_02` etc.) is appropriate.

---

## 8. Cross-Document Consistency & Deviation Report

### Critical

No critical deviations identified. Every FR cited in the roadmap and matrix is defined in the PRD body. The proposal object contract, lifecycle states, and canonical boundary rules are self-consistent across the primary documents.

---

### Major

| # | Location | Deviation |
|---|---|---|
| M1 | `docs/specs/v0.5.1_tier3_entity_system_spec.md` lines 96, 519 vs. `docs/product/04_Implementation_Roadmap.md` line 520 and `tests/test_cli_entities.py` lines 717, 755, 798, 842 | The entity system spec explicitly classifies `folio entities merge` as "a future UX pass" and excludes it from v1. The roadmap names `folio entities suggest-merges` / `merge` as shipped Tier 4 foundation, and the shipped test suite confirms the command exists and passes. The governing Tier 3 spec is factually incorrect relative to the shipped state. PR #43 does not update the entity spec to reflect this. Any future reviewer consulting the entity spec for the merge command's contract will find a non-goal statement that conflicts with reality. |
| M2 | `docs/specs/folio_enrich_spec.md` (entire document) vs. PRD `FR-810` (`02_Product_Requirements_Document.md` lines 1104-1125) | FR-810 introduces `folio enrich diagnose [scope] [--json] [--limit N]` as a new subcommand of `folio enrich`. The governing spec for the enrich command family (`folio_enrich_spec.md`) contains no mention of a `diagnose` subcommand — neither its eligibility predicate, output schema, nor failure behavior. The PRD FR body provides a brief description and acceptance criteria, but there is no spec-level contract for this new subcommand's implementation. FR-810 is named in the roadmap (Weeks 26-27, line 561) and in the CLI map (line 701) but the enrich spec is the governing document for the enrich command surface and it is not updated. |

---

### Minor

| # | Location | Deviation |
|---|---|---|
| m1 | `docs/product/02_Product_Requirements_Document.md` FR-814, lifecycle states bullet vs. `docs/specs/tier4_discovery_proposal_layer_spec.md` §6 lifecycle states | PRD FR-814 lists "`expired` or `superseded`" as a single bullet (implying they are alternatives or a single combined state), making a minimum of 7 states. The proposal spec §6 lists `expired` and `superseded` as two distinct separate bullets, making a minimum of 8 states. The spec's §6 state expectations (items 6-7) further clarify both as distinct states with their own semantics. The PRD's formulation is ambiguous on whether both must be supported or only one suffices. |
| m2 | `docs/product/04_Implementation_Roadmap.md` Tier 4 Exit Criteria (10 items) vs. Tier 4 Gate in Quality Gates section (9 items) | The Exit Criteria section explicitly lists "Latent discovery views and proposal objects are documented as non-canonical and rebuildable" and "Rejection memory and stale invalidation rules are defined for proposal review" as two separate gate items. The Quality Gates section consolidates these into one item: "Proposal review rules cover rejection memory and stale invalidation before proposal volume scales up" and omits the "documented as non-canonical and rebuildable" criterion. An exit criterion with no matching quality gate entry creates an ambiguity about whether the documentation requirement is actually gated. |
| m3 | `docs/specs/tier4_digest_design_spec.md` front-matter, `revision: 3` | The digest spec's revision field jumps from 1 (PR #41 / commit `aaf02e1`) to 3 in PR #43. There is no revision 2, no `revision_note` entry covering what a revision 2 would have changed, and no prior commit introducing a revision 2. The `revision_note` in PR #43's version covers the PR #43 changes correctly but the version integer skips a number with no explanation. This weakens the spec's own revision audit trail. |
| m4 | `docs/specs/tier4_discovery_proposal_layer_spec.md` front-matter `depends_on` list vs. `docs/specs/folio_provenance_spec.md` and `docs/specs/folio_enrich_spec.md` | The proposal spec introduces a proposal object contract and a machine-proposal / canonical-link separation that is architecturally descended from the provenance spec's `_llm_metadata.provenance` / `provenance_links` pattern and the enrich spec's relationship proposal contract. Neither `folio_provenance_spec` nor `folio_enrich_spec` appear in the proposal spec's `depends_on` list. The missing lineage citations reduce cross-document traceability. This does not create a contradiction, but it means the spec does not declare its own architectural predecessors. |
| m5 | `docs/product/02_Product_Requirements_Document.md` FR-814 consumer list vs. `docs/specs/tier4_discovery_proposal_layer_spec.md` §9 consumer list | PRD FR-814 uses abbreviated names in the consumer list: "`folio links`, `folio entities`, `folio graph`, `digest`, `synthesize`, `search`" — dropping the `folio` prefix from the last three. The proposal spec §9 uses the fully-qualified names: `folio links`, `folio entities`, `folio graph`, `folio digest`, `folio synthesize`, `folio search`. The referents are the same six surfaces and the content is equivalent, but the formatting inconsistency weakens cross-document precision. |

---

## 9. Verdict & Unblocking Conditions

**Verdict: Request Changes**

The proposal spec itself (`docs/specs/tier4_discovery_proposal_layer_spec.md`) is architecturally sound. The canonical boundary, proposal object contract, lifecycle states, rejection memory, trust-gate rules, and consumer model are internally consistent and align with the ontology, PRD, roadmap, matrix, and digest spec. No inconsistency in the proposal spec's own content rises to a blocking level.

However, two Major deviations in the broader governing corpus must be resolved before the PR passes alignment review:

**Unblocking condition 1 (M1 — entity spec currency):**

`docs/specs/v0.5.1_tier3_entity_system_spec.md` must be updated to remove or supersede the non-goal statement that classifies `folio entities merge` as "a future UX pass" (lines 96 and 519). The update must either: (a) add a revision note acknowledging that `folio entities merge` and `folio entities suggest-merges` shipped as part of the Tier 4 graph-ops foundation on 2026-04-15, or (b) create a dedicated supplementary spec section covering the shipped merge behavior. The governing spec must not contradict the shipped command's existence.

**Unblocking condition 2 (M2 — enrich diagnose spec coverage):**

`docs/specs/folio_enrich_spec.md` must be updated to include a spec section for the `folio enrich diagnose` subcommand introduced by FR-810. At minimum, the spec must define: the eligibility predicate (which notes are evaluated), the minimum finding classes (consistent with FR-810: managed sections unidentified, protected by curation level, protected by review status), the output schema for `--json` mode, and the failure behavior. Alternatively, a standalone spec file for the quality-layer commands (FR-810/811/812) may be created with an explicit dependency declaration linking back to `folio_enrich_spec.md`.

The three Minor deviations (m1 lifecycle state ambiguity, m2 exit-criteria / gate mismatch, m3 revision number skip) are recommended for correction but are not blocking. The reviewer recommends resolving them in the same pass to maintain spec discipline.

---

*Review prepared by Claude Code + claude-sonnet-4-6 on 2026-04-15.*
