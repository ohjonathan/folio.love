---
id: pr37_spec_review_consolidated
type: review
status: complete
ontos_schema: 2.2
created: 2026-03-28
depends_on:
  - folio_enrich_spec
---

# Consolidated Spec Review: `folio enrich` Core (PR #37, Rev 2)

**Review date:** 2026-03-28
**Artifact:** `docs/specs/folio_enrich_spec.md` (Rev 2, v1.0)
**Phase:** B.1 Spec Review
**Review lead:** Claude (Team Lead)

---

## Verdict Summary

| Reviewer | Role | Verdict | Blocking Issues |
|----------|------|---------|-----------------|
| 1 | Peer | Request Changes | 3 Critical |
| 2 | Alignment | Request Changes | 1 Blocking |
| 3 | Adversarial | Block | 3 Critical |

**Overall status: Needs Revision**

---

## Blocking Issues

Combined and deduplicated across all three reviewers. Where multiple reviewers
flagged the same issue, attribution shows all.

| # | Issue | Flagged By | Category | Action Required |
|---|-------|------------|----------|-----------------|
| B1 | `folio refresh` destroys all enrich state; mechanism to preserve it is unspecified | R2 (B-1), R3 (C1) | Safety / Architecture | Specify the refresh preservation mechanism (which fields, how `generate_frontmatter()` changes). See details below. |
| B2 | `input_fingerprint` uses file-level `entities.json.updated_at`, causing O(N) mass re-enrichment on any entity mutation | R3 (C2) | Idempotency | Replace with a granular entity change marker scoped to the note's client/engagement. |
| B3 | No relationship proposal rejection mechanism; stale wrong proposals persist indefinitely | R3 (C3) | UX / Data integrity | Add `rejected` status to proposal lifecycle. Rejected (relation, target_id) pairs must not be re-proposed unless signals materially change. |
| B4 | Interaction note body mutation contradicts ontology immutability rule ("content sections are append-only after L0") | R1 (C1), R3 (M2) | Ontology compliance | Either restrict interaction body mutation to stub sections only (`## Entities Mentioned`, `## Impact on Hypotheses`) or explicitly amend the ontology immutability rule for enrich-time entity link insertion. |
| B5 | Ontology wikilink-promotion feature deferred without acknowledging it is an ontology-specified responsibility for `folio enrich` | R1 (C2), R2 (L-1) | Ontology compliance | Acknowledge in the spec that this is a known deferral of an ontology-specified feature (Ontology Section 2.6, 6.3). Two sentences in the non-goals table suffice. |
| B6 | `## Key Findings` subsection structure (`### Claims`, `### Data Points`, `### Decisions`, `### Open Questions`) invisible to the spec | R1 (C3) | Implementability | Specify whether these subsections are individually managed or collectively managed as part of the `## Key Findings` tree. State that user edits to any subsection trigger the managed-body fingerprint conflict. |

---

## Should-Fix Issues

Non-blocking but strongly recommended before implementation.

| # | Issue | Flagged By | Category | Recommendation |
|---|-------|------------|----------|----------------|
| S1 | Scope fingerprint invalidates all peers when any peer changes (new note added to engagement forces re-enrichment of all siblings) | R3 (M3) | Idempotency | Narrow the scope fingerprint (e.g., count of peers, or hash of peer IDs only) rather than full registry entry identity. |
| S2 | Ontology v1 recommendation deviation mischaracterized — spec activates `supersedes` (ontology says "add later") and defers `depends_on`/`draws_from` (ontology says "start with") | R1 (M1), R2 (D-1, M-2) | Ontology compliance | Acknowledge as a deliberate priority reordering justified by corpus scope, not as strict ontology compliance. Note the deviation in Section 18 PRD patch. |
| S3 | Entity wikilink insertion location for evidence notes is unspecified (interaction notes have `## Entities Mentioned`, evidence notes have no equivalent) | R1 (M3), R2 (A3-1) | Implementability | Specify whether entity wikilinks are inserted inline in `### Analysis` prose or in a new subsection. Define the rendering rule. |
| S4 | No `--force` or re-enrichment override mechanism | R1 (M4) | UX | Add `--force` flag or document manual override procedure (clear `input_fingerprint`). |
| S5 | Cost estimation and guardrails absent (160+ notes × multiple LLM calls, no budget warning, no cost tracking) | R3 (M1) | Operational | Add at minimum a pre-run note count and estimated API call count. Consider `--max-calls` safety valve. |
| S6 | Heading parser fallback behavior undefined for malformed or absent heading trees | R3 (M4) | Safety | Specify: treat malformed notes as fully protected? Skip with error? Log and continue? |
| S7 | Section 9.1 "may update directly" wording on canonical relationship fields is ambiguous — could be misread as allowing machine writes to canonical fields, contradicting D7 | R2 (M-1) | Clarity | Reword to clarify enrich *reads* canonical fields to derive `## Related` but does not *write* proposals into them. |
| S8 | FR-505 (Refresh Command) not included in PRD amendment proposals despite refresh being a PR C prerequisite | R2 (L-2) | PRD alignment | Elevate Section 18.7 from a "note" to a formal FR-505 amendment proposal. |
| S9 | Stale source-path repair deferral contradicts vault validation report's explicit recommendation that PR C fix the 148 legacy-root references | R1 (M2) | Scope | Cite and respond to the vault validation recommendation rather than ignoring it. Deferral may be appropriate but should be justified against the recommendation. |

---

## Minor Issues

Consider but not required for approval.

| # | Issue | Flagged By | Note |
|---|-------|------------|------|
| m1 | `supersedes` is type `id` (singular) in ontology, not `list[id]`. Spec and proposal schema should enforce singular cardinality. | R1 (m1), R3 (m4) | |
| m2 | `## Related` section placement unspecified (before/after Version History? after last slide?) | R1 (m2), R3 (m1) | |
| m3 | Diagram note skip lacks progress indicator symbol | R1 (m3) | |
| m4 | `spec_version: 1` lacks versioning policy (when to increment, what it means for the library) | R1 (m4) | |
| m5 | `scope_fingerprint` derivation underspecified (what data from peer entries, what happens when a new note is added) | R1 (m5) | Overlaps with S1. |
| m6 | Dry-run does not separate "protected" vs "conflicted" in output | R3 (m2) | |
| m7 | Behavior for notes with `_llm_metadata.enrich.status: stale` not explicitly handled in Section 10 pipeline | R3 (m3) | |
| m8 | No mechanism to exclude individual notes from enrichment without promoting to L1 | R3 (blind spot 5.5) | |
| m9 | Body safety contract (Section 14) not anchored to a PRD FR | R2 (Gap 1) | |
| m10 | `folio status` integration for enrichment state not addressed | R1 (completeness) | |
| m11 | No LLM prompt strategy guidance (implementation detail, but affects implementability) | R1 (completeness) | |
| m12 | "Lightweight summaries already available in frontmatter" for peer reads — no `summary` field exists in frontmatter today | R1 (Investigation 3) | |

---

## Agreement Analysis

### Strong Agreement (2+ reviewers)

**Refresh compatibility is the highest-risk item in the spec.** All three
reviewers independently verified against the codebase that the current
`generate_frontmatter()` function destroys enrich state. All three agree the
spec correctly identifies this as a prerequisite but underspecifies the
mechanism.

**Ontology wikilink-promotion deferral needs acknowledgment.** R1 and R2
both flagged that the ontology (Sections 2.6, 6.3) explicitly describes
wikilink promotion as a `folio enrich` responsibility, and the spec defers it
without noting the deviation.

**Ontology v1 recommendation ordering is mischaracterized.** R1 and R2 both
found that the spec presents activating `supersedes` while deferring
`depends_on`/`draws_from` as pure ontology compliance, when the ontology's
Section 6.4 recommendation says the opposite ordering. Both agree the spec's
actual choice is defensible but should be acknowledged as a priority reordering.

**Interaction note body mutation tension.** R1 (C1) and R3 (M2, blind spot
5.4) both flagged the ontology's "append-only after L0" rule for interaction
content sections. The spec rewrites four content sections without addressing
this tension.

**Entity wikilink insertion for evidence notes is underspecified.** R1 (M3)
and R2 (A3-1) both flagged that evidence notes have no `## Entities Mentioned`
section equivalent and the spec does not define where entity wikilinks land.

**`## Related` edge cases are well-handled in Rev 2.** R1 (Investigation 5)
confirmed this was fixed. R3's attack on `## Related` with no canonical
relationships confirmed the spec handles the empty case correctly (omit section
entirely).

### Disagreement

| Topic | R1 says | R3 says | Recommendation |
|-------|---------|---------|----------------|
| **Interaction body mutation severity** | Critical (C1): must be reconciled with ontology immutability rule before implementation | Major (M2): should be addressed but not blocking | **Treat as blocking (B4).** The ontology's immutability rule is a design principle, not a suggestion. Silent contradiction creates architectural debt. R1's analysis is more thorough on this point — the ontology explicitly says "content sections are append-only after L0" and R1 correctly identifies that `## Summary` and `## Key Findings` contain records of what happened, while `## Entities Mentioned` and `## Impact on Hypotheses` are stubs/placeholders. |
| **`input_fingerprint` granularity** | Minor concern (m5: scope fingerprint underspecified) | Critical (C2: file-level `updated_at` causes mass re-enrichment) | **Treat as blocking (B2).** R3's reproduction scenario is concrete and convincing: one entity confirmation triggers 160+ unnecessary LLM calls. R1 noted the same underlying issue (m5) but classified it lower. The cost and UX implications at production scale make this blocking. |
| **Proposal rejection mechanism** | Not flagged | Critical (C3: infinite re-proposal loop) | **Treat as blocking (B3).** Single-reviewer finding but the reproduction scenario is clear and the UX impact (stale wrong proposals appearing indefinitely) erodes system trust. The lack of a rejection mechanism is a genuine lifecycle gap. |
| **Cost estimation** | Noted as gap (completeness check) | Major (M1) | **Treat as should-fix (S5).** Both agree it's missing; R3 argues more forcefully. Not blocking because the library is small enough to run at reasonable cost, but should be addressed for operational safety. |
| **94% flagged rate makes body protection "nearly meaningless"** | Not flagged | Blind spot (5.3) | **Note but do not elevate.** R3's observation is accurate but the body protection rule protects against *future* promotion/review states. The spec is correct that L0 notes should receive body enrichment. |

---

## Required Actions for CA

Prioritized by blocking status, then by estimated effort.

### Blocking (must resolve before implementation)

| # | Action | Effort | Maps to |
|---|--------|--------|---------|
| 1 | **Specify refresh preservation mechanism.** Add a design sketch: which fields does `generate_frontmatter()` preserve? Frontmatter merge after conversion, or metadata passthrough, or sidecar? Minimum: state the approach and acceptance criteria for the refresh sub-deliverable. | Medium | B1 |
| 2 | **Replace `entities.json.updated_at` with granular entity marker in `input_fingerprint`.** Propose: hash of confirmed entity canonical names within the note's client/engagement scope, or a per-type version counter, or a scoped entity fingerprint. | Small | B2 |
| 3 | **Add `rejected` proposal status.** Add to allowed status values. Specify: rejected proposals not re-proposed unless signals materially change. Define what "materially change" means (new source content, new entity, new peer). | Small | B3 |
| 4 | **Reconcile interaction body mutation with ontology immutability.** Recommended path: restrict body mutation for interaction notes to `## Entities Mentioned` and `## Impact on Hypotheses` (stubs), treat `## Summary` and `## Key Findings` as protected content. Or amend the ontology rule explicitly. | Small | B4 |
| 5 | **Acknowledge wikilink-promotion deferral as ontology deviation.** Two sentences in Section 4 non-goals table referencing Ontology Sections 2.6 and 6.3. | Small | B5 |
| 6 | **Specify `## Key Findings` subsection handling.** State whether `### Claims`, `### Data Points`, `### Decisions`, `### Open Questions` are part of the managed surface. If B4 restricts `## Key Findings` to protected, this is moot. | Small | B6 |

### Should-Fix (address before or during implementation)

| # | Action | Effort | Maps to |
|---|--------|--------|---------|
| 7 | Narrow scope fingerprint to avoid peer-change cascade | Small | S1 |
| 8 | Acknowledge ontology v1 recommendation reordering; note in Section 18 PRD patch | Small | S2 |
| 9 | Specify evidence-note entity wikilink rendering location | Small | S3 |
| 10 | Add `--force` flag or document manual fingerprint clearing | Small | S4 |
| 11 | Add pre-run cost estimation (note count + estimated API calls) | Small | S5 |
| 12 | Define heading parser fallback for malformed notes | Small | S6 |
| 13 | Clarify Section 9.1 "may update directly" wording | Small | S7 |
| 14 | Elevate Section 18.7 to formal FR-505 amendment | Small | S8 |
| 15 | Cite vault validation recommendation on stale paths; justify deferral | Small | S9 |

---

## Decision Summary

**Overall status: Needs Revision**

The spec is well-constructed and shows strong iteration from Rev 1. The
three-axis enrichment model is sound, the safety contract is well-designed, and
the fingerprint-based idempotency approach is architecturally correct. The
refresh compatibility contract, the registry-contract-unchanged decision, and
the PRD implications section are particularly strong.

However, six blocking issues must be resolved before implementation can begin.
The highest-risk item is **B1 (refresh preservation mechanism)** — all three
reviewers independently verified against the codebase that the current refresh
path destroys all enrich state, and the spec mandates a fix without specifying
the approach. This is the single hardest engineering task in PR C and is treated
as a bullet point.

The second cluster of blocking issues (**B2, B3**) targets the idempotency
system's practical behavior at production scale. The fingerprint design is
architecturally sound but uses inputs that are too coarse (file-level entity
timestamp) and lacks a lifecycle mechanism for rejected proposals.

The third cluster (**B4, B5, B6**) addresses ontology compliance gaps that are
straightforward to fix but represent genuine contradictions or
mischaracterizations that should not ship to implementation unresolved.

**Estimated revision effort: 1–2 hours.** Most blocking actions are small
(clarifications, status additions, acknowledgments). B1 is the only medium-
effort item and requires a design sketch, not full implementation specification.

---

## Positive Observations (Cross-Reviewer Consensus)

All three reviewers independently praised:

1. **D7 (proposals in metadata, not canonical fields)** — the right
   architectural call that avoids machine overwriting human judgment.
2. **D12 / Section 15.2 (refresh compatibility contract)** — correctly
   identifying the refresh lifecycle risk before implementation, even though the
   mechanism is underspecified.
3. **The non-goals table (Section 4)** — thorough, well-reasoned deferrals with
   justification.
4. **The Review Resolution Map (Section 22)** — excellent documentation
   practice making Rev 1 → Rev 2 changes auditable.
5. **D5 (entity resolver policy reuse)** — honest framing as policy-level
   reuse, not identical function signatures.
6. **The PRD implications section (Section 18)** — rare and valuable upstream
   impact documentation.
7. **Dry-run as strict no-write, no-LLM (Rev 2 fix)** — appropriate cost
   control for production-scale libraries.

---

*Generated by three-reviewer agent team. Each reviewer operated independently
with full spec and reference document access.*
