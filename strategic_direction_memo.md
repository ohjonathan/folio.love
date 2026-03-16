# Folio.love: Strategic Direction Update

**Date:** 2026-03-14
**Context:** This memo captures shifts in project philosophy, quality bar, and design principles that should inform all current and future PRD work. These changes emerged from a diagram extraction research effort but apply to the entire folio.love system.

---

## The Shift

Folio.love was designed as a personal knowledge management tool for a consultant's career library. That's still true, but the use case has expanded. The system now needs to produce output that is directly usable in active McKinsey engagements serving Fortune 100 clients. The audience for folio's output is no longer just me browsing my vault — it includes engagement teams, in-house architects doing review, and ultimately deliverables that inform C-suite decisions.

This changes what "good enough" means at every level of the system.

---

## Design Principle Changes

### 1. Quality is the only constraint

Previously, the system balanced quality against cost and processing time. That balance is gone. Every pipeline step should perform the most thorough processing available. If a page needs additional LLM passes, more tiles, extra validation rounds, or a different model, the system does it without checking a budget counter.

Cost and processing time are tracked for transparency and auditability, but they never gate or throttle quality. Expected costs may be $0.50-2.00+ per diagram page and processing may take 30-120 seconds per page. These are acceptable. The system should never make a quality/cost tradeoff.

This isn't about being wasteful. It's about removing the engineering pressure to cut corners. When cost is a constraint, every design decision implicitly asks "is this worth the extra API call?" That question no longer applies.

### 2. Output must be trustworthy, not just useful

Previously, the bar was "searchable and retrievable." Now the bar is "a senior McKinsey consultant can include this in a client deliverable without manually verifying every detail." That means:

- **Extraction accuracy matters at the individual label level.** A component name that's wrong or paraphrased ("Data Store" instead of "PostgreSQL") isn't a minor quality issue — it undermines trust in the entire extraction.
- **The system must know what it doesn't know.** Confidence scoring, uncertainty flagging, and explicit "I'm not sure about this" signals are not nice-to-haves. They're required. A wrong answer presented with false confidence is worse than a gap flagged for human review.
- **Provenance is non-negotiable.** Every extracted fact should trace back to its source: which page, which extraction method (PDF text layer vs vision LLM vs OCR), which model, which pass. When someone questions a data point, the answer should be findable in seconds.

### 3. Human review is part of the system, not an afterthought

The system should assume that high-stakes output will be reviewed by human experts before use. This means designing for reviewability:

- **Flag what needs attention.** Low-confidence extractions, uncertain elements, and repair-needed outputs should surface automatically, not require someone to manually inspect every page.
- **Support human override.** When a reviewer corrects an extraction, that correction should persist across re-processing. The system should never silently overwrite human judgment.
- **Make review efficient.** Reviewers are expensive (in-house architects, senior consultants). The system should minimize their time by pointing them at specific issues, not asking them to re-verify everything.

### 4. Diagrams are first-class knowledge objects

Previously, diagrams were just pages within a deck — processed the same as any slide, rendered as a section in a deck note. That undersells their value. An architecture diagram is a standalone piece of knowledge that gets referenced across engagements, linked to other artifacts, and queried independently.

This means:
- Diagrams deserve their own notes in the vault, with their own frontmatter, their own queryability, and their own position in Obsidian's graph view.
- Diagram extraction deserves its own pipeline path with specialized prompts, validation, and output structure — not just a different template on the same generic slide analysis.
- The structured data extracted from diagrams (components, connections, technologies, hierarchy) should be as queryable and linkable as any other knowledge in the vault.

### 5. Production-grade means incrementally shipped, not incrementally compromised

The old approach was "build an MVP, then iterate." The new approach is "ship in increments, but every increment is production-grade." The difference:

- **MVP mindset:** "What's the minimum that works?" → tends toward cutting scope to ship faster, with quality debt accumulating.
- **Incremental production mindset:** "What's the next complete, high-quality capability we can ship?" → each increment is fully tested, fully documented, and meets the quality bar on its own.

Concretely: if a feature can't be built to the quality bar within a PR, it gets scoped differently or sequenced later — not shipped at lower quality. The system never contains a "good enough for now, fix later" component that's exposed to engagement use.

### 6. The system should get smarter over time

As the corpus grows and more diagrams are processed, the system should accumulate knowledge that improves future extractions:

- **Human corrections are training signal.** When an architect overrides an extraction, that's information about where the system fails. Even if we don't use it for automated retraining now, it should be captured in a way that's usable later.
- **Model evaluation is ongoing.** New models drop frequently (GPT-5.4, Gemini 3.1, Claude Sonnet 4.6 — all recent). The system should make it easy to re-run extraction with a new model and compare results. The provider abstraction already supports this; the evaluation workflow should be formalized.
- **Confidence calibration improves with data.** As we accumulate ground-truth annotations from human review, we can calibrate whether "confidence 0.85" actually means "85% of the time this is correct." Initially these are estimates; over time they should become empirically grounded.

---

## Scope Implications

These principle changes may affect existing PRD scope in several ways:

**Conversion quality standards may need revisiting.** If the existing slide deck pipeline was designed to the old "searchable and retrievable" bar, does it meet the new "trustworthy for client deliverables" bar? Evidence validation, source grounding, and confidence scoring may need to be strengthened across the board, not just for diagrams.

**The curation system (L0-L3) may need a "review required" state.** Currently curation levels represent completeness of human curation. The new quality bar suggests a "flagged for review" state that's distinct from curation level — a document can be L0 (uncurated) but also specifically flagged because the system detected quality issues.

**Frontmatter and ontology may need new fields.** Extraction confidence, review status, human overrides, provenance metadata — these weren't part of the original ontology design. The frontmatter schema should be evaluated for whether it supports the trust and reviewability requirements.

**Testing strategy may need to evolve.** The current 506-test suite validates functional correctness. The new quality bar may require evaluation-style testing: ground-truth annotated fixtures where the test measures extraction accuracy, not just "did it run without errors."

---

## What This Memo Is Not

This is not a feature spec, a technical proposal, or an implementation plan. It's a statement of direction. The specific technical decisions that follow from these principles will be developed separately, grounded in the codebase and informed by research. The purpose of sharing this now is to ensure that all PRD work from this point forward reflects these principles, even for features that aren't directly related to diagram extraction.
