# PR #36 (`folio enrich` Core Spec) — Multi-Agent Review Consolidation

**Target:** `docs/specs/folio_enrich_spec.md` (Revision 1)
**Reviewers:** Peer, Alignment, Adversarial (Simulated)
**Lead Synthesizer:** Antigravity (powered by Gemini) (Review Lead)

---

## 1. Executive Summary & Verdict

**Verdict: REQUEST CHANGES (BLOCKING)**

The spec is highly structured and conservative, excelling in idempotency design (`input_fingerprint` / `managed_body_fingerprint`) and avoiding broad rewrite hazards. However, the review team identified **4 Critical/Blocking issues** related to pipeline sequencing conflicts, ontology deviations, and race conditions during body mutation. 

There is an active disagreement between the Alignment and Adversarial reviewers regarding the risk of `folio refresh` destroying enriched metadata. As Lead, I am surfacing both views for the architect to adjudicate.

---

## 2. Consolidated Findings by Priority

### 🔴 CRITICAL / BLOCKING

1. **Undefined Pipeline Sequencing (Peer & Adversarial):** 
   Section 10 states the three axes (tags, entities, relationships) are analysed but does not define the execution order or context sharing. 
   *Adversarial note:* If entity extraction runs before tag enrichment, the LLM has less semantic context. If they run in parallel, 3 separate LLM calls are made without cross-pollinated insights, wasting context window and multiplying token cost. The spec must define strict serialization or explicit parallel isolation.

2. **Ontology Deviation on Relationship Eligibility (Alignment):** 
   The spec claims `supersedes` applies to evidence notes and `impacts` applies to interaction notes (Sections 5.3, D6, 13.2). 
   *Alignment note:* `Folio_Ontology_Architecture.md` defines `supersedes` primarily for deliverable and analysis documents, not raw captured evidence. Evidence doesn't *supersede* evidence; it contradicts or contextualizes it. This represents an unapproved deviation from the ontology.

3. **Body Mutation Boundary Precision Risks (Peer & Adversarial):**
   Sections 10 (D10) and 14 restrict mutation to `### Analysis` blocks. 
   *Adversarial note:* The spec assumes homogeneous `### Analysis` blocks. Older evidence notes (or overridden notes) may lack this exact heading. What happens if the regex matches globally and overwrites human-authored sections below it? The mutation logic must use AST or strict hierarchical parsing, not naive regex, to prevent leaking into `## Raw Transcript` or protected headers.

4. **Refresh vs. Enrich State Destruction (Alignment & Adversarial Conflict):**
   *Alignment Reviewer:* `folio refresh` is documented as dropping manually added relationships. Running `refresh` after `enrich` will silently destroy enriched relationships that a human validated. This contradicts the roadmap's requirement that "Human override safety: Never silently overwrite human corrections."
   *Adversarial Reviewer:* This is worse than mere data loss. A fingerprint mismatch triggered by an upstream source change will clear the `_llm_metadata.enrich` proposal state entirely, leaving orphaned `## Related` blocks in the body that point to non-existent proposals.
   *Lead Synthesis:* The interaction between `enrich` and `refresh` must be explicitly designed. Either `refresh` honors the enrich fingerprint, or a new `folio sync` mechanism is required.

### 🟡 MAJOR / NEEDS REVISION

1. **Test Plan vs. Acceptance Criteria Gap (Peer):** 
   The test plan (Section 16) lacks specific tests for the `## Related` rendering edge cases. Specifically: what does the body look like when *all* canonical relationships have unresolvable targets? A test must explicitly assert that empty sections are either pruned or stubbed correctly without leaving dangling raw links.

2. **Registry Contract Bleed (Alignment):** 
   Adding `last_enriched` to `RegistryEntry` (D14) risks complicating the single-source-of-truth model. If a note is enriched but the registry update fails, the note metadata and registry are out of sync. Relying on frontmatter (`_llm_metadata.enrich`) is sufficient and maintains the "frontmatter as TRUTH" ontology rule.

3. **Entity Resolution Policy Coupling (Alignment):**
   Reusing the shipped resolver contract (D5) from interaction notes is aspirational. The existing resolver logic relies heavily on `InteractionAnalysisResult`. Using it for general evidence notes will require significant refactoring of `folio.pipeline.entity_resolution`, which the spec underestimates.

### 🔵 MINOR / OBSERVATIONS

- **Read Scope for Relationship Candidates (Peer):** The read scope for relationship peer inference (Section 8.3) is well-bounded but could explode if entire peer document bodies are loaded into context. The spec should clarify that only peer frontmatter/summaries are read.
- **Dry-Run Costs (Adversarial):** The spec implies `160 notes × 3 LLM calls`. A full library run is 480 LLM calls. A strict `--dry-run` that skips the LLM API is needed to test pipeline mechanics without incurring massive Anthropic API bills.

---

## 3. Disagreements to Adjudicate

**The `refresh` vs `enrich` lifecycle:**
- *Alignment* argues that running `refresh` is a user error if they expect enriched data to survive, based on current documentation.
- *Adversarial* argues the system MUST defend against this because dropping human-confirmed relationships violates NFR-200 ("Never silently overwrite human corrections").
- **Action Required:** The architect must decide if `enrich` state is explicitly protected during `refresh` (via `.overrides.json` equivalent) or if `enrich` operates strictly as an ephemeral pipeline.

---

## 4. Next Steps for Author

1. Specify the exact execution sequencing for the 3 enrichment axes (parallel vs sequential).
2. Clarify how AST or regex bounds the `### Analysis` and `## Entities Mentioned` mutation boundaries to prevent bleeding.
3. Align relationship type semantics (`supersedes`) with `Folio_Ontology_Architecture.md`, or formally propose an ontology amendment.
4. Add an explicit section defining the interaction between `folio refresh` and `folio enrich` state persistence.
5. Provide a test case for empty/dangling `## Related` blocks.

**Status:** Awaiting revision.
