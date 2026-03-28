# Review Team: `folio enrich` Code Review (PR #37)

## Verdict Summary

| Reviewer | Role | Verdict | Blocking Issues |
|----------|------|---------|-----------------|
| 1 | Peer | Request Changes | C1, C2, C3 |
| 2 | Alignment | Request Changes | R2-5 (DEV-4) |
| 3 | Adversarial | Block | C1, C2, C3, M1 |

## Blocking Issues

| # | Issue | Flagged By | Category | Action Required |
|---|-------|------------|----------|-----------------|
| B1 | `_update_related_section` bypasses body protection rules for protected/conflicted notes. | R3 | Body Safety / Spec Violation | Gate the execution of `_update_related_section` behind `body_safe` check, ensuring protected notes' bodies remain untouched. |
| B2 | `_replace_frontmatter` fragile delimiter `str.index("\n---", 4)` causes crash or silent corruption on multiline YAML values. | R1 (C1), R3 (M1) | Data Integrity | Replace with robust boundary detection (e.g., reuse `_parse_frontmatter_from_content` logic) that ignores interior YAML multi-line block `---`. |
| B3 | Entity resolution fingerprint excludes resolution status and created entities. | R3 (C2) | Idempotency Logic | Update fingerprint logic to use the documented `confirmed/unconfirmed/proposed_match/unresolved` prefixes and include `created_entities`, so status updates trigger re-enrichment. |
| B4 | Promoted-proposal cleanup (spec rule 9.2.7) is not implemented. | R3 (C3) | Data Lifecycle | Add logic before `enrich_block` assembly to remove pending proposals that match existing canonical `supersedes`/`impacts` targets. |
| B5 | `## Related` is lost from body on `folio refresh` but spec D12 requires regeneration. | R2 (R2-5) | Spec/Code Mismatch | EITHER amend D12 to clarify `refresh` only preserves frontmatter, OR add `## Related` regeneration to the refresh code path. |
| B6 | `## Impact on Hypotheses` marked as managed but never mutated; creates false conflict positives. | R1 (C2), R3 (M5) | Precision/Safety | Remove it from the interaction managed-section list if unmutated, OR implement the expected mutations. |
| B7 | Missing warning for unresolvable canonical targets. | R1 (C3) | UX / Spec Violation | Add logging/warning when `_update_related_section` finds unresolved canonical target IDs. |

## Should-Fix Issues

- **S1. Unnecessary LLM API Costs on Protected Notes (R3-M2):** Short-circuit protected/conflicted notes before LLM calls to avoid burning API budget.
- **S2. Roadmap Relationship Type Deviation (R2-1):** Spec activates `supersedes` + `impacts` instead of roadmap's `depends_on` + `draws_from`. Roadmap should be updated to reflect this delivered scope.
- **S3. Singular `supersedes` Non-deterministic Filter (R3-M3):** Sort LLM supersedes proposals by confidence descending before enforcing singular cardinality.
- **S4. O(N²) Peer Frontmatter Disk Reads (R1-M1):** `_build_peer_context` reads full frontmatter from disk for every peer note, violating D3. Implement a lightweight cache or acknowledge performance hit.

## Minor Issues

- **m1. Generic Resolver Delegation (R2-4):** `resolve_entities()` delegates to `resolve_interaction_entities()`. Add a comment or rename to clarify its generic nature.
- **m2. Minor Documentation Gaps (R2-3, R2-6, R1-m3):** Update PRD FR-604 routing table list, correct the PRD amendment count to 9, and add an inline comment for `routing.enrich` in example YAML.
- **m3. Code Duplication (R1-m1, R3-m3):** `_build_peer_context` and `_build_peer_descriptors` perform duplicate registry traversals.

## Agreement Analysis

**Strong agreement (2+ reviewers):**
- **Body safety boundary precision vs reality:** All 3 reviewers highlighted gaps between what the spec *says* is protected/managed and what the code *actually* does. R1 focused on `## Impact` falsely triggering conflicts; R3 found the critical failure that `_update_related_section` entirely bypassed the protection gate. Both show a critical execution flaw in the body safety implementation.
- **Fragile Frontmatter Parsing:** R1 and R3 independently found the `content.index("\n---", 4)` bug. R1 approached it from an atomicity/crash angle, while R3 identified the YAML multi-line string corruption vector. They strongly agree the implementation is unsafe.

**Disagreement:**
- *No significant factual disagreements.* Reviewer 2 focused heavily on architectural mapping and backward compatibility, while Reviewers 1 and 3 focused on execution logic and edge cases. Their findings perfectly complement each other.

## Required Actions for Developer

| Priority | Action | Addresses | Effort |
|----------|--------|-----------|--------|
| 1 | **Fix Body Safety Gate Bypass:** Ensure `_update_related_section` is never called when `body_safe == False` (or disposition is conflict/protect). | B1 | Low |
| 2 | **Harden Frontmatter Parsing:** Replace `str.index("\n---", 4)` with robust YAML boundary logic. | B2 | Low |
| 3 | **Fix Entity Fingerprints:** Include status prefixes and `created_entities` in the fingerprint. | B3 | Medium |
| 4 | **Implement Proposal Cleanup:** Filter `_llm_metadata.enrich.axes.relationships.proposals` against canonical targets before saving. | B4 | Low |
| 5 | **Resolve Refresh `## Related` Mismatch:** Update spec text OR modify converter to regenerate the section. | B5 | Medium |
| 6 | **Resolve `## Impact` Managed State:** Stop tracking as managed if no mutations occur. | B6 | Low |
| 7 | **Add Unresolvable Target Warning:** Emit a warning when a canonical relationship target cannot be resolved. | B7 | Low |
| 8 | **Cost Optimization & Quality:** Short-circuit LLM calls (S1) and sort `supersedes` proposals by confidence (S3). | S1, S3 | Low |

## Test Verification Requirements

- **B1 (Safety Gate Bypass):** Provide a test showing an L1 evidence note with a canonical `supersedes` field. Enrich it. Assert the note body remains 100% identical.
- **B2 (YAML Parsing):** Provide a unit test with a `description: |` multi-line YAML frontmatter containing an internal `---`. Assert `_replace_frontmatter` preserves the full frontmatter.
- **B3 (Entity Fingerprints):** Provide an integration test: Run enrich -> confirm an entity -> run enrich without `--force`. Assert the note DID re-enrich successfully.
- **B4 (Proposal Cleanup):** Provide a unit test showing that a pending proposal matching a target in `canonical_fields` is proactively removed from the `proposals` block.
- **B5 (Refresh Related):** Update the refresh integration test to verify the chosen path (either `## Related` body survives, or spec is updated and metadata survival is tested).

## Decision Summary

Overall status: **Needs Fixes**
