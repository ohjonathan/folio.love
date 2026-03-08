# Change Summary for CA

This note summarizes the targeted changes made to [renderer_and_cache_fix_proposal.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/renderer_and_cache_fix_proposal.md) after review so the CA can quickly assess what changed and why.

| Change | Why changed | Which review concern it addresses |
|---|---|---|
| Reframed the proposal as mitigation-first rather than self-contained Tier 1 closure | The prior draft implied the proposal itself closed Tier 1 even though manual PDF counting still required policy approval | Tier 1 closure was being redefined rather than explicitly bounded |
| Recorded the project decision that operator-exported PDFs do not count toward Tier 1 | Tier 1 has now been explicitly defined as fully automated conversion, so Phase 1 must remain mitigation-only | Tier 1 counting policy is now explicit rather than pending |
| Renamed and softened the counting table into a decision surface | The previous table read like the proposal was authorizing counting rules on its own | Scope honesty and policy-boundary concerns |
| Added a structured normalization outcome requirement for the eventual spec | Batch restart/reporting logic cannot safely depend on parsing human-readable exception strings | Phase 0 observability/runtime-surface gap |
| Tightened Phase 0 instrumentation to observable outcomes only | The previous draft implied a direct sandbox bucket even though sandbox dialogs are unobservable programmatically | Misleading failure taxonomy / unmeasurable claims |
| Promoted the dedicated-session restart model from open assumption to approved operating constraint | PowerPoint app ownership/restart is now an accepted batch invariant rather than an unresolved governance question | Unsafe global PowerPoint lifecycle control is now bounded by an explicit operating model |
| Removed `_conversion_quality` from the proposal | The prior draft introduced hidden frontmatter/schema work while claiming none | Frontmatter inconsistency / schema drift |
| Downgraded portrait-PDF handling from reject-by-default to warn + exclude-from-counting | Rejecting portrait PDFs by default would have changed the current global PDF acceptance behavior | PDF compatibility regression concern |
| Reframed scanned/portrait/handout PDF handling as warnings, guidance, and counting exclusions | The proposal needed to distinguish operational mitigation from global pipeline enforcement | Blast-radius and operator-workflow clarity |
| Made the PDF-canonical fallback tradeoff explicitly non-neutral | The prior draft understated the semantic cost of switching a deck from PPTX source to PDF source | Provenance/version semantics concern |
| Increased the effort estimate and Phase 0 scope description | Phase 0 now explicitly includes structured outcome design and safer restart/reporting assumptions, not just a small `normalize.py` tweak | Scope/effort honesty |
| Kept Approach J deferred as a v0.5.1 follow-on and stated the automated-PPTX cache gap explicitly | The review agreed cache-key redesign should stay out of scope, but the unresolved automated-PPTX cache gap had to remain visible | Deferred automated-cache persistence concern |
