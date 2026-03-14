---
id: claude_code_prompt_grounding_multipass
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-14
---

# Implementation Prompt: Grounding, Multi-Pass, and Reviewability Integration

**For:** Developer Agent Team (CA lead + spawned developers)  
**PRD:** `docs/product/02_Product_Requirements_Document.md`  
**Roadmap:** `docs/product/04_Implementation_Roadmap.md`  
**Ontology:** `docs/architecture/Folio_Ontology_Architecture.md`  
**Strategic memo:** `docs/product/strategic_direction_memo.md`  
**Historical prompt reviewed:** `docs/prompts/CLAUDE_CODE_PROMPT_grounding_multipass.md` from commit `69abd9f3e9aa6c45020aea857d3f385565a6970b`  
**Branch:** `codex/grounding-reviewability` from `main`  
**Test command:** `python3 -m pytest tests/ -v`  
**Commit format:** `feat(reviewability): description`  
**PR title:** `feat: reviewability fields for grounded multi-pass analysis`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, writes the implementation plan, decomposes the work, spawns developers, and owns final verification.
2. Developers implement in the order defined below. Do not parallelize dependent refactors blindly; this change crosses analysis, frontmatter, converter wiring, registry, CLI, and tests.
3. The CA lead verifies the output against this prompt, runs the targeted test slices after each major step, then runs the full suite before opening the PR.

---

## Task Context

### What to Build

Bring the old grounding and multi-pass prompt up to the current repo reality.
This is not a greenfield grounding project anymore. `main` already ships:

- multi-provider LLM routing, named profiles, and transient fallback chains
- managed-mac PowerPoint automation and current converter orchestration
- `SlideText`, grounded JSON evidence flow, evidence validation, density scoring, Pass 2, and CLI `--passes`
- Tier 2 registry/status/scan/refresh/promote workflow
- `_llm_metadata` provenance in frontmatter

The remaining gap is FR-700 reviewability integration on top of that shipped baseline:

- add document-level `review_status`, `review_flags`, and `extraction_confidence`
- flow review metadata and `grounding_summary` into `registry.json`
- surface flagged counts in `folio status`
- block `folio promote` when a document is still flagged
- preserve current grounding, caching, provider routing, and Pass 2 behavior

### Scope Boundaries

This work is limited to the current deck conversion path and the Tier 2 daily-driver surfaces that already exist.

- Extend the current `convert` and `batch` analysis flow. Do not replace it.
- Treat `text.py`, `analysis.py`, `converter.py`, `frontmatter.py`, `markdown.py`, `registry.py`, `cli.py`, and the existing tests as the primary change surface.
- Keep the current `SlideText` contract and the current Pass 1 / Pass 2 contract intact.
- Keep the current provider abstraction, route resolution, fallback policy, and cache invalidation logic intact.
- If `.overrides.json` support already exists somewhere in runtime code, respect it. If it does not exist, do not invent it here. Note it as an explicit dependency boundary and leave `refresh` behavior otherwise unchanged.

### What Not to Build

- No character-level offset indexing.
- No Pass 3 or cross-slide synthesis pass.
- No embedding-based or semantic deduplication.
- No async or parallel API orchestration.
- No new dependencies.
- No normalize or images pipeline changes.
- No rework of current provider adapters, routing semantics, or `_llm_metadata` shape unless required for reviewability correctness.
- No `.overrides.json` implementation in this task.
- No re-introduction of `default_passes` or `density_threshold`; they already exist and must remain as-is.

### Rollout Constraint

Do not start by rewriting `analysis.py` from scratch. The shipped grounding and multi-pass path is directionally correct and already covered by tests. This work is an additive FR-700 integration pass over current `main`, not a replay of the March 2 grounding implementation.

---

## Read Before Writing

Read these in order before touching code:

1. `docs/product/02_Product_Requirements_Document.md`
   - Focus on FR-103, FR-607, FR-700 through FR-706, and NFR-100.
2. `docs/architecture/Folio_Ontology_Architecture.md`
   - Focus on Section 2.7, Section 12.1, and Section 12.7.
3. `docs/product/strategic_direction_memo.md`
4. `docs/product/04_Implementation_Roadmap.md`
5. `folio/pipeline/text.py`
6. `folio/pipeline/analysis.py`
7. `folio/output/frontmatter.py`
8. `folio/output/markdown.py`
9. `folio/converter.py`
10. `folio/config.py`
11. `folio/tracking/registry.py`
12. `folio/cli.py`
13. `tests/test_grounding.py`
14. `tests/test_analysis_cache.py`
15. `tests/test_pipeline_integration.py`
16. `tests/test_converter_integration.py`
17. `tests/test_frontmatter.py`
18. `tests/test_config.py`
19. `tests/test_registry.py`
20. `tests/test_cli_tier2.py`

Read the historical prompt only as intent input. Do not trust its repo assumptions.

---

## Codebase Context

### Current Baseline

Current `main` is not the repo described by the deleted prompt:

- `folio/pipeline/text.py` already defines `SlideText` and keeps `extract()` backward-compatible by returning `dict[int, str]`.
- `folio/pipeline/analysis.py` already uses provider adapters, JSON-only pass contracts, `_validate_evidence()`, `_compute_density_score()`, `_deduplicate_evidence()`, and `analyze_slides_deep()`.
- `folio/converter.py` already resolves named LLM profiles, threads fallback chains, runs optional Pass 2, and emits `_llm_metadata`.
- `folio/config.py` already supports `default_passes` and `density_threshold`, but it does not yet load or validate `review_confidence_threshold`.
- `folio/output/frontmatter.py` already emits `grounding_summary`, but not FR-700 review fields.
- `folio/output/markdown.py` already renders evidence blocks, pass labels, and `[unverified]` markers.
- `folio/tracking/registry.py` and `folio/cli.py` already implement Tier 2 registry/status/scan/refresh/promote, but they do not carry or surface review metadata.

### Already Shipped

Treat these as existing behavior to preserve:

- `SlideText`
- `extract()` as a backward-compatible wrapper
- grounded JSON evidence flow
- `_validate_evidence()`
- `_compute_density_score()`
- `_deduplicate_evidence()`
- `analyze_slides_deep()`
- converter `passes`
- CLI `--passes` on `convert` and `batch`
- provider-aware cache invalidation
- current registry plus `status`, `scan`, `refresh`, and `promote`

### Missing or Partial

These are the gaps this PR must close:

- `review_status`, `review_flags`, and `extraction_confidence` in frontmatter
- `review_confidence_threshold` in config
- registry storage and reconciliation of review fields and `grounding_summary`
- flagged counts in `folio status`
- promotion gating on `review_status == flagged`
- explicit review auto-flagging derived from evidence validation, low confidence, and analysis unavailability
- any real `.overrides.json` mechanism

### Existing Test Surface

Use the current test patterns instead of inventing new harnesses:

- `tests/llm_mocks.py` already provides provider-native JSON response factories.
- `tests/test_grounding.py` already covers JSON extraction, normalization, evidence validation, density scoring, and deduplication.
- `tests/test_analysis_cache.py` already covers prompt-version, provider/model, extraction-version, force-miss, and Pass 2 cache behavior.
- `tests/test_pipeline_integration.py` already covers grounding summaries, Pass 2 evidence addition, and prompt content.
- `tests/test_cli_tier2.py` already covers registry bootstrap, status, scan, refresh, promote, and reconciliation.

Do not replace these suites with new ones. Extend them surgically.

---

## Target Behavior and Interfaces

### Reviewability Contract

Every converted document must carry these frontmatter fields:

```yaml
review_status: clean
review_flags: []
extraction_confidence: 0.78
grounding_summary:
  total_claims: 12
  high_confidence: 8
  medium_confidence: 3
  low_confidence: 1
  validated: 10
  unvalidated: 2
  pass_1_claims: 9
  pass_2_claims: 3
  pass_2_slides: 2
```

`review_status` values are:

- `clean`
- `flagged`
- `reviewed`
- `overridden`

`review_flags` must use stable, machine-generated strings. Implement these exact flags in this PR:

- `analysis_unavailable`
- `partial_analysis_slide_<N>` — slide N is pending while others succeeded (only for slides with text content; blank/divider slides are intentionally pending and not flagged)
- `low_confidence_slide_<N>`
- `unvalidated_claim_slide_<N>`
- `high_density_unanalyzed`
- `confidence_below_threshold`

`reviewed` and `overridden` are human states. The pipeline must not auto-set either of them. It may preserve them when the current run is otherwise clean.

### Non-Breaking Evidence Helper

You may add an internal helper type, but do not force a broad runtime rewrite if `list[dict]` remains the lowest-risk storage shape.

Acceptable sketch:

```python
@dataclass(frozen=True)
class EvidenceItem:
    claim: str
    quote: str
    element_type: str
    confidence: str
    validated: bool = False
    pass_number: int = 1

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "quote": self.quote,
            "element_type": self.element_type,
            "confidence": self.confidence,
            "validated": self.validated,
            "pass": self.pass_number,
        }
```

If this causes unnecessary churn, keep plain dicts and implement helper functions instead.

### Evidence Validation

Keep the current validation approach and expose it as the canonical basis for review flags:

```python
def _validate_evidence(evidence: list[dict], slide_text: SlideText) -> None:
    full_text_normalized = _normalize_for_matching(slide_text.full_text)
    for item in evidence:
        quote = item.get("quote", "")
        if not quote:
            item["validated"] = False
            continue
        quote_normalized = _normalize_for_matching(quote)
        if quote_normalized in full_text_normalized:
            item["validated"] = True
            continue
        quote_words = set(quote_normalized.split())
        text_words = set(full_text_normalized.split())
        item["validated"] = bool(
            quote_words and len(quote_words & text_words) / len(quote_words) >= 0.8
        )
```

Do not replace this with a new fuzzy-matching dependency.

### Density Scoring

Do not change the current scoring semantics. Reuse the existing function as the basis for `high_density_unanalyzed`:

```python
def _compute_density_score(analysis: SlideAnalysis, text: SlideText) -> float:
    score = 0.0
    score += len(analysis.evidence) * 0.3
    word_count = len(text.full_text.split()) if text.full_text else 0
    if word_count > 150:
        score += 1.0
    elif word_count > 75:
        score += 0.5
    if analysis.framework not in ("none", "pending", ""):
        score += 1.0
    if analysis.slide_type in {"data", "framework"}:
        score += 0.5
    comma_count = analysis.key_data.count(",") if analysis.key_data else 0
    score += min(comma_count * 0.2, 1.0)
    return score
```

Strict `>` against `density_threshold` remains the contract.

### Extraction Confidence

Implement a simple, deterministic document-level score in `analysis.py` and use it everywhere else. Use this exact formula:

```python
_CONFIDENCE_BASE = {"high": 0.90, "medium": 0.65, "low": 0.40}

def _compute_extraction_confidence(analyses: dict[int, SlideAnalysis]) -> float | None:
    evidence = [
        ev
        for analysis in analyses.values()
        for ev in getattr(analysis, "evidence", [])
        if isinstance(ev, dict)
    ]
    if not evidence:
        return None

    score = sum(_CONFIDENCE_BASE.get(ev.get("confidence", "medium"), 0.65) for ev in evidence)
    score = score / len(evidence)

    if any(ev.get("confidence") == "low" for ev in evidence):
        score = min(score, 0.59)
    if any(not ev.get("validated", False) for ev in evidence):
        score = min(score, 0.59)

    return round(score, 2)
```

This gives:

- all validated high-confidence evidence: around `0.90`
- mixed high and medium evidence: roughly `0.65` to `0.80`
- any low-confidence or unvalidated evidence: below `0.60`
- no evidence: `None`

### Review Auto-Flagging

Add a pure helper in `analysis.py` to derive document-level review state after Pass 1 / Pass 2 complete:

```python
@dataclass(frozen=True)
class ReviewAssessment:
    review_status: str
    review_flags: list[str]
    extraction_confidence: float | None


def assess_review_state(
    analyses: dict[int, SlideAnalysis],
    slide_texts: dict[int, SlideText],
    *,
    effective_passes: int,
    density_threshold: float,
    review_confidence_threshold: float,
    existing_review_status: str | None = None,
) -> ReviewAssessment:
    flags: list[str] = []

    all_pending = bool(analyses) and all(a.slide_type == "pending" for a in analyses.values())
    if all_pending:
        flags.append("analysis_unavailable")

    for slide_num, analysis in analyses.items():
        evidence = getattr(analysis, "evidence", [])
        if any(ev.get("confidence") == "low" for ev in evidence):
            flags.append(f"low_confidence_slide_{slide_num}")
        if any(not ev.get("validated", False) for ev in evidence):
            flags.append(f"unvalidated_claim_slide_{slide_num}")

    if effective_passes < 2:
        dense_slides = [
            slide_num
            for slide_num, analysis in analyses.items()
            if slide_num in slide_texts
            and _compute_density_score(analysis, slide_texts[slide_num]) > density_threshold
        ]
        if dense_slides:
            flags.append("high_density_unanalyzed")

    extraction_confidence = _compute_extraction_confidence(analyses)
    if extraction_confidence is not None and extraction_confidence < review_confidence_threshold:
        flags.append("confidence_below_threshold")

    flags = sorted(set(flags))

    if flags:
        review_status = "flagged"
    elif existing_review_status in {"reviewed", "overridden"}:
        review_status = existing_review_status
    else:
        review_status = "clean"

    if all_pending:
        extraction_confidence = None

    return ReviewAssessment(review_status, flags, extraction_confidence)
```

This helper is the source of truth for:

- frontmatter review fields
- registry review fields
- `folio status` flagged counts
- `folio promote` blocking behavior

### Config Addition

Add exactly one new config field:

```python
@dataclass
class ConversionConfig:
    image_dpi: int = 150
    image_format: str = "png"
    libreoffice_timeout: int = 60
    default_passes: int = 1
    density_threshold: float = 2.0
    pptx_renderer: str = "auto"
    review_confidence_threshold: float = 0.6
```

Load and validate it from `folio.yaml`. It must be a numeric value in the inclusive range `0.0` to `1.0`.

### Registry and CLI Contract

`RegistryEntry` must gain these fields:

- `review_status`
- `review_flags`
- `extraction_confidence`
- `grounding_summary`

`folio status` must report flagged counts from the registry using this summary shape:

```text
Library: 12 decks
  ! Flagged: 3
  OK Current: 8
  WARN Stale: 1
```

If flagged entries exist in scope, print:

```text
Flagged:
  ClientA/project_x/deck.md [low_confidence_slide_4, unvalidated_claim_slide_7]
```

`folio promote` must block any promotion attempt when the frontmatter `review_status` is exactly `flagged`. It must not auto-set `reviewed` or clear `review_flags`.

---

## File-by-File Instructions

### MODIFY `folio/pipeline/text.py`

Do not change the public shape of `SlideText` or the `extract()` wrapper unless a tiny additive fix is required.

- Preserve `extract()` returning `dict[int, str]`.
- Preserve `extract_structured()` returning `dict[int, SlideText]`.
- Preserve current heuristics unless you need a minimal additive tweak for evidence `element_type` correctness.
- Do not turn this into a breaking return-type migration. That work is already done.

If no runtime change is required here after inspection, leave the file untouched.

### MODIFY `folio/pipeline/analysis.py`

This is the main implementation file.

- Keep current provider orchestration, fallback behavior, prompt contracts, and cache behavior.
- Add `ReviewAssessment`, `_compute_extraction_confidence()`, and `assess_review_state()`.
- Reuse current `_validate_evidence()` and `_compute_density_score()` for flag derivation rather than duplicating logic elsewhere.
- Keep `SlideAnalysis` storage shape backward-compatible.
- Do not change `analyze_slides()` or `analyze_slides_deep()` return shapes unless there is no smaller way to thread reviewability. Prefer pure post-pass helpers over return-shape churn.
- Keep current `Pass 2` conflict handling, `validated` markers, and pass-number tagging.

Important behavior:

- `analysis_unavailable` only when every slide result is `pending`.
- `high_density_unanalyzed` only when `effective_passes < 2` and at least one slide exceeds the existing density threshold.
- `confidence_below_threshold` only when aggregate confidence is non-null and below the configured threshold.
- `reviewed` or `overridden` may be preserved only when the current run produces no machine flags.

### MODIFY `folio/output/frontmatter.py`

Add FR-700 fields without disturbing current ontology output.

- Extend `generate()` with keyword-only args for `review_status`, `review_flags`, and `extraction_confidence`.
- Insert those fields in the lifecycle/trust block immediately after `curation_level`.
- Preserve current `grounding_summary` logic and current `_llm_metadata` behavior.
- Preserve `authority` and `curation_level` from existing frontmatter exactly as today.
- Preserve human-set `review_status` only when the incoming computed status is `clean` and the existing value is `reviewed` or `overridden`.
- Never auto-set `reviewed` or `overridden`.
- Emit `review_flags: []` explicitly when clean.

Required field order in frontmatter:

1. `id`, `title`, `type`, `subtype`
2. `status`, `authority`, `curation_level`, `review_status`, `review_flags`, `extraction_confidence`
3. source fields
4. temporal fields
5. engagement/content fields
6. reconciliation metadata
7. `grounding_summary`
8. `_llm_metadata`

### MODIFY `folio/output/markdown.py`

Do not churn the body format.

- Keep the current evidence block format, pass labels, and `[unverified]` indicator.
- Do not move evidence into frontmatter or sidecar files.
- Only make a markdown change if a tiny formatting tweak is required to keep review/provenance output coherent.
- If no markdown change is necessary after implementing the frontmatter and registry work, leave this file untouched.

### MODIFY `folio/converter.py`

Thread reviewability into the current conversion flow.

- After Pass 1 / optional Pass 2 complete, call `analysis.assess_review_state(...)`.
- Use `self.config.conversion.review_confidence_threshold` as the threshold input.
- Pass the resulting `review_status`, `review_flags`, and `extraction_confidence` into `frontmatter.generate()`.
- Reuse `frontmatter._compute_grounding_summary()` or extract a small shared helper so the same `grounding_summary` object can be written into the registry. Do not parse the generated YAML string just to recover it.
- Upsert registry entries with the computed review fields plus `grounding_summary`.
- Preserve current routing, fallback, blank-slide override, Pass 2 execution, and `_llm_metadata` logic.

Do not change `convert()` signature beyond what already exists on `main`.

### MODIFY `folio/config.py`

Add only `review_confidence_threshold`.

- Add the dataclass field.
- Validate it in `_validate()`.
- Load it from `conversion.review_confidence_threshold`.
- Update tests for defaults, explicit load, and invalid values.

Do not alter `default_passes`, `density_threshold`, or route resolution semantics.

### MODIFY `folio/tracking/registry.py`

Extend the registry schema forward-compatibly.

- Add `review_status`, `review_flags`, `extraction_confidence`, and `grounding_summary` to `RegistryEntry`.
- Ensure `to_dict()` preserves empty `review_flags` and present `grounding_summary`.
- Update `rebuild_registry()` to read the new frontmatter fields when they exist.
- Update `reconcile_from_frontmatter()` so these new fields are frontmatter-authoritative.
- Keep backward compatibility with old registry entries that lack the new fields.

Do not redesign the registry format beyond these additive fields.

### MODIFY `folio/cli.py`

Extend existing Tier 2 commands. Do not introduce new commands.

#### `status`

- Count flagged documents from registry entries where `review_status == "flagged"`.
- Print the flagged summary line before current/stale/missing lines.
- Print a `Flagged:` section with `markdown_path` and `review_flags`.
- When `--refresh` is used, reconcile frontmatter-authoritative fields before final tally output so the printed counts reflect current frontmatter.

#### `promote`

- Read `review_status` from frontmatter before existing curation-level validation.
- If `review_status == "flagged"`, exit non-zero with a message telling the user to review or resolve the flags first.
- Do not auto-set `review_status` to `reviewed`.
- Do not clear `review_flags`.

#### `refresh`

- Inspect for a real override mechanism first.
- If no `.overrides.json` runtime support exists, leave behavior unchanged and document FR-705 as out of scope for this PR in the implementation summary.
- Do not invent override preservation here.

### MODIFY `tests/test_grounding.py`

Add or update tests for:

- `_compute_extraction_confidence()` values and `None` behavior
- `assess_review_state()` clean vs flagged cases
- `analysis_unavailable`
- `low_confidence_slide_<N>`
- `unvalidated_claim_slide_<N>`
- `high_density_unanalyzed`
- `confidence_below_threshold`
- preservation of current density-score and dedup behavior

Keep the existing JSON-normalization and evidence-validation tests.

### MODIFY `tests/test_frontmatter.py`

Add or update tests for:

- new review fields present and correctly ordered
- `review_flags: []` emitted when clean
- `extraction_confidence` emitted when provided and absent or null only when appropriate
- preservation of human `review_status` values when computed status is clean
- escalation back to `flagged` when machine flags exist

Do not regress existing ordering, tags, or source-type tests.

### MODIFY `tests/test_pipeline_integration.py`

Add end-to-end coverage for:

- clean frontmatter when evidence is validated and confidence is above threshold
- flagged frontmatter when any claim is unvalidated
- flagged frontmatter when any claim is low confidence
- `analysis_unavailable` behavior with null extraction confidence
- existing evidence rendering and Pass 2 evidence growth still working

Reuse current JSON mocks and current converter wiring patterns.

### MODIFY `tests/test_cli_tier2.py`

Add CLI coverage for:

- `folio status` flagged count and flagged listing
- `folio status --refresh` reconciling review fields from frontmatter
- `folio promote` blocking flagged documents
- `folio promote` allowing `clean` or `reviewed` documents
- registry bootstrap and reconciliation still working with new fields

Do not remove the existing stale/missing/promote coverage.

### MODIFY `tests/test_config.py`

Add config coverage for:

- default `review_confidence_threshold == 0.6`
- explicit YAML load
- invalid values below `0.0`, above `1.0`, non-numeric

Keep all current LLM profile and route tests intact.

### MODIFY `tests/test_registry.py`

Add registry round-trip coverage for:

- new review fields in `RegistryEntry`
- rebuild from frontmatter including `grounding_summary`
- reconciliation updating review fields from frontmatter

Keep old-entry compatibility coverage.

### MODIFY `tests/test_converter_integration.py`

Add converter coverage for:

- review fields threaded into frontmatter
- registry upsert includes review fields and `grounding_summary`
- no regression to blank-slide override
- no regression to existing `passes` behavior

Do not revert these tests to prose-format or Anthropic-only assumptions.

### MODIFY `tests/test_analysis_cache.py`

The cache contract should remain unchanged. Only add a regression if you need one to prove the new review helpers do not alter Pass 1 / Pass 2 cache semantics.

At minimum, ensure the existing cache suite still passes unchanged.

---

## Implementation Order

### 1. Config and Pure Analysis Helpers

- Add `review_confidence_threshold` to config and tests.
- Add `ReviewAssessment`, `_compute_extraction_confidence()`, and `assess_review_state()` to `analysis.py`.
- Extend `tests/test_grounding.py` first so the reviewability rules are pinned down before converter/frontmatter wiring.

Run:

```bash
python3 -m pytest tests/test_grounding.py -v
python3 -m pytest tests/test_config.py -v
```

### 2. Frontmatter and Converter Wiring

- Thread computed review metadata through `converter.py`.
- Extend `frontmatter.generate()`.
- Add or update converter and frontmatter tests.

Run:

```bash
python3 -m pytest tests/test_frontmatter.py -v
python3 -m pytest tests/test_converter_integration.py -v
python3 -m pytest tests/test_pipeline_integration.py -v
```

### 3. Registry and CLI Integration

- Extend `RegistryEntry`, `rebuild_registry()`, and `reconcile_from_frontmatter()`.
- Update `status` flagged counts and `promote` gating.
- Add CLI and registry tests.

Run:

```bash
python3 -m pytest tests/test_registry.py -v
python3 -m pytest tests/test_cli_tier2.py -v
```

### 4. Final Regression Pass

- Re-run any touched cache tests if helper placement required it.
- Run the full suite.

Run:

```bash
python3 -m pytest tests/test_analysis_cache.py -v
python3 -m pytest tests/ -v
```

---

## Test Requirements

The final PR is not acceptable unless it demonstrates all of the following:

- clean frontmatter path
- flagged frontmatter path
- low-confidence auto-flagging
- unvalidated-claim auto-flagging
- `analysis_unavailable` path with `extraction_confidence: null`
- `confidence_below_threshold` path
- `high_density_unanalyzed` path when Pass 2 is disabled
- registry round-trip of review fields and `grounding_summary`
- `folio status` flagged counts
- `folio promote` rejection on flagged documents
- no regression to routing, fallback, cache invalidation, blank-slide override, Pass 2 selection, or evidence rendering

Use existing fixtures and mock styles whenever possible.

---

## Constraints

- No new dependencies.
- No normalize or images pipeline changes.
- No provider-architecture rewrite.
- No route-selection rewrite.
- No Pass 3.
- No async or parallel calls.
- No semantic dedup.
- No `.overrides.json` implementation.
- No YAML round-trip in `promote`.
- No frontmatter parsing of generated markdown just to populate the registry.

---

## Verification Checklist

- [ ] `review_status`, `review_flags`, and `extraction_confidence` appear in frontmatter with correct ordering
- [ ] `grounding_summary` remains present and internally consistent
- [ ] `review_flags: []` is emitted for clean documents
- [ ] flagged documents carry specific, slide-addressable flags
- [ ] `analysis_unavailable` produces `review_status: flagged`
- [ ] `analysis_unavailable` produces `extraction_confidence: null`
- [ ] `folio status` prints flagged counts from registry data
- [ ] `folio status --refresh` reconciles review fields from frontmatter
- [ ] `folio promote` blocks when `review_status == flagged`
- [ ] `folio promote` does not clear flags or auto-set `reviewed`
- [ ] registry rebuild and reconciliation handle older entries without crashing
- [ ] current Pass 1 / Pass 2 cache tests still pass
- [ ] current provider routing and `_llm_metadata` behavior still pass
- [ ] blank-slide override and existing `passes` behavior still pass

---

## Deliverable Standard

Ship this as a focused implementation PR over current `main`.

- Keep the diff bounded to the runtime files and tests above.
- In the PR summary, explicitly call out that `.overrides.json` / FR-705 was inspected and left out of scope if no runtime mechanism exists.
- In the PR summary, explicitly call out that grounding and multi-pass already existed and that this PR adds FR-700 reviewability integration on top of that baseline.

Do not describe this as "implement grounding and multi-pass from scratch." That is no longer true for this repo.
