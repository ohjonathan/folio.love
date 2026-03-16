# Implementation Prompt: PR #21 Minor Fixes (M-NEW-1, M-NEW-3, M1, M5)

## Context

PR #21 (`codex/diagram-pr3-schema-cache`) has been approved after 3 review rounds. Four minor issues were identified as fixable now. Apply all four in a single commit on the current branch.

**Branch:** `codex/diagram-pr3-schema-cache`
**Base commit:** `dc2ba9b`
**File:** `folio/pipeline/analysis.py` (all 4 fixes), `tests/test_diagram_analysis.py` (test updates)

---

## Fix 1: M-NEW-1 — Remove dead `isinstance` check in node bbox NaN guard

**File:** `folio/pipeline/analysis.py`, lines 216–221

**Current code:**
```python
# S4: Guard against NaN/Inf values in bbox
if bbox is not None and any(
    not isinstance(v, (int, float)) or v != v or abs(v) == float('inf')
    for v in bbox
):
    bbox = None
```

**Problem:** After `tuple(float(v) for v in bbox_raw)` on line 213, all values are guaranteed `float`. The `not isinstance(v, (int, float))` predicate is unreachable dead code.

**Fix:** Remove the dead predicate, matching the cleaner pattern already used in the `DiagramEdge.evidence_bbox` guard (lines 279–284):
```python
# S4: Guard against NaN/Inf values in bbox
if bbox is not None and any(
    v != v or abs(v) == float('inf')
    for v in bbox
):
    bbox = None
```

**Tests:** No test changes needed — existing `TestNanBboxGuard` covers NaN, Inf, and valid cases; behavior is identical.

---

## Fix 2: M-NEW-3 — Change `from_slide_analysis` from warn to raise

**File:** `folio/pipeline/analysis.py`, lines 405–430

**Current code:**
```python
@classmethod
def from_slide_analysis(
    cls,
    sa: "SlideAnalysis",
    *,
    diagram_type: str = "unknown",
    review_required: bool = False,
    abstained: bool = False,
) -> "DiagramAnalysis":
    """Promote a SlideAnalysis to DiagramAnalysis, copying inherited fields.

    Warning: if called on a DiagramAnalysis, diagram-specific fields
    (graph, mermaid, description, uncertainties) are NOT copied.
    """
    if isinstance(sa, DiagramAnalysis):
        logger.warning(
            "from_slide_analysis() called on DiagramAnalysis — "
            "diagram-specific fields will be lost"
        )
    return cls(
        slide_type=sa.slide_type,
        ...
    )
```

**Problem:** Warning-only means diagram data (graph, mermaid, description, uncertainties, etc.) is silently destroyed. The sole current caller (`converter.py:275`) guards with `not isinstance(existing, analysis.DiagramAnalysis)`, but future callers won't be protected. A `TypeError` is the correct signal — this is a caller bug, not a recoverable situation.

**Fix:** Replace `logger.warning(...)` with `raise TypeError(...)`:
```python
    """Promote a SlideAnalysis to DiagramAnalysis, copying inherited fields.

    Raises:
        TypeError: If sa is already a DiagramAnalysis (diagram-specific
            fields would be silently lost).
    """
    if isinstance(sa, DiagramAnalysis):
        raise TypeError(
            "from_slide_analysis() called on DiagramAnalysis — "
            "use the instance directly or copy diagram-specific fields manually"
        )
```

**Tests:** Add one test to `TestDiagramAnalysis` in `tests/test_diagram_analysis.py`:
```python
def test_from_slide_analysis_rejects_diagram_analysis(self):
    """M-NEW-3: Passing a DiagramAnalysis should raise TypeError."""
    da = DiagramAnalysis(diagram_type="architecture", mermaid="graph LR")
    with pytest.raises(TypeError, match="from_slide_analysis.*DiagramAnalysis"):
        DiagramAnalysis.from_slide_analysis(da, diagram_type="mixed")
```

---

## Fix 3: M1 — Remove dead `_cache_signature` writes

**File:** `folio/pipeline/analysis.py`

**Current code in `_save_cache` (lines 2045–2052):**
```python
cache["_cache_signature"] = _stable_signature(
    _prompt_version(ANALYSIS_PROMPT),
    _DIAGRAM_SCHEMA_VERSION,
    _DIAGRAM_PIPELINE_VERSION,
    _IMAGE_STRATEGY_VERSION,
    provider or "",
    model or "",
)
```

**Same pattern in `_save_cache_deep` (lines 1949–1956).**

**Problem:** `_cache_signature` is written to cache but never validated on load by `_load_cache` or `_load_cache_deep`. The individual version checks already provide full invalidation coverage. The dead write wastes bytes in cache files and misleads readers into thinking the signature serves a validation purpose.

**Fix:**
1. Remove the `cache["_cache_signature"] = _stable_signature(...)` block (6 lines) from both `_save_cache` and `_save_cache_deep`.
2. `_stable_signature` itself is still used by tests and may be needed in PR 4, so **keep the function definition** at line 52.

**Tests:** No test changes needed. Existing cache round-trip tests don't assert on `_cache_signature`. The `TestStableSignature` tests validate the function itself (keep those).

---

## Fix 4: M5 — Use null-byte delimiter in `_stable_signature`

**File:** `folio/pipeline/analysis.py`, line 54

**Current code:**
```python
def _stable_signature(*parts: str) -> str:
    """Compute a stable SHA-256 signature from ordered string parts."""
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

**Problem:** `"|"` can appear in part values (e.g., LLM-generated `key_data` like `"Revenue | $10M"`), causing `_stable_signature("a|b", "c")` to collide with `_stable_signature("a", "b|c")`. Same issue exists in `_pass1_context_hash` at line 737.

**Fix:** Use `"\x00"` (null byte) as delimiter in both functions. Null bytes cannot appear in the string values (model names, version strings, slide analysis text fields):

```python
def _stable_signature(*parts: str) -> str:
    """Compute a stable SHA-256 signature from ordered string parts."""
    combined = "\x00".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

```python
def _pass1_context_hash(analysis: SlideAnalysis) -> str:
    """Hash pass-1 fields that feed into the depth prompt (B2).

    Only hashes fields interpolated into DEPTH_PROMPT: slide_type,
    framework, key_data, main_insight. Evidence is excluded because
    it is not an input to the depth prompt.
    """
    content = "\x00".join([
        analysis.slide_type, analysis.framework,
        analysis.key_data, analysis.main_insight,
    ])
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Tests:** Update `TestStableSignature` — existing tests (determinism, different inputs, length) still pass since the hash output changes but the properties don't. Add one new test:

```python
def test_delimiter_not_ambiguous(self):
    """M5: Parts containing the old '|' delimiter must not collide."""
    s1 = _stable_signature("a|b", "c")
    s2 = _stable_signature("a", "b|c")
    assert s1 != s2
```

**Cache invalidation note:** Changing `_stable_signature` output does NOT break existing caches because `_cache_signature` is never validated on load (and is being removed in Fix 3). Changing `_pass1_context_hash` output will cause one-time deep cache misses (slides re-analyzed in Pass 2), which is the correct behavior since the hash function changed.

---

## Commit Message

```
fix(pr3): address 4 minor review findings (M-NEW-1, M-NEW-3, M1, M5)

- Remove dead isinstance check in node bbox NaN guard (M-NEW-1)
- Raise TypeError in from_slide_analysis() on DiagramAnalysis input (M-NEW-3)
- Remove dead _cache_signature writes from _save_cache/_save_cache_deep (M1)
- Use null-byte delimiter in _stable_signature and _pass1_context_hash (M5)
```

## Validation

Run `python3 -m pytest tests/test_diagram_analysis.py tests/test_analysis_cache.py -q` — all tests must pass (existing + 2 new).
