---
id: pr_1_review_comment_source_grounding_multi_pass
type: reference
status: active
created: 2026-03-02
source: codex
---

# PR #1 Review: Request Changes

Directionally, this is a meaningful improvement, but it is not ready to merge in its current form.

## Summary

- Peer reviewer: Request Changes
- Alignment reviewer: Request Changes
- Adversarial reviewer: Block

All three reviewers agreed that the branch should not merge as-is. The highest-risk issues are concentrated in prompt safety, grounding correctness, and backward compatibility.

## Blocking Issues

1. **Pass 2 prompt injection**
   Pass 1 model output is interpolated directly into the depth-pass prompt without escaping or delimiting. That makes Pass 2 steerable by malformed or adversarial pass-1 content and turns model output into prompt control input.

2. **Grounding is weaker than advertised**
   The new grounding flow validates quotes against `SlideText` after the call, but neither Pass 1 nor Pass 2 actually gives the model the extracted text it is supposed to quote. The model receives only the slide image plus the prompt, so exact quote fidelity and `title/body/note` attribution are unreliable on OCR-hostile or dense slides.

3. **`text.extract()` breaks backward compatibility**
   The public extractor return type changed from `dict[int, str]` to `dict[int, SlideText]` with no compatibility layer for external callers. Internal consumers were updated, but older integrations expecting strings will break.

4. **Cache compatibility is not actually preserved**
   Old analysis caches are invalidated before `SlideAnalysis.from_dict()` can apply the new `evidence=[]` default. Separately, cache loaders accept any JSON shape and can later fail on save if the cache body is not a dict.

## Should-Fix Before Merge

- The current "integration" tests do not exercise `FolioConverter.convert()` or the CLI `--passes` path, so the main wiring is still unverified.
- Density scoring drifts from the implementation contract:
  - counts commas from full slide text instead of `key_data`
  - treats `executive-summary` as data-heavy
  - triggers at `>= 2.0` instead of `> 2.0`
- Pass 2 conflict handling is still a stub; `pass2_slide_type` / `pass2_framework` are not captured.
- Truncated `max_tokens` responses are still parsed as successful analyses instead of being downgraded to a safe failure state.
- `pyproject.toml` adds `pdfplumber`, which conflicts with the follow-up implementation constraint of "no new dependencies" unless that rule is intentionally waived.

## Minor Issues

- `created` is rewritten on every conversion instead of staying fixed after first generation.
- Frontmatter emits `status: current`, which does not match the ontology v2 status enum.
- Evidence dedup uses raw token overlap and `>= 0.85`, which does not match the documented `>85%` normalized-overlap rule.
- Config loading still fails on `llm: null` or `conversion: null`.

## Required Actions

1. Remove the pass-2 prompt injection path by escaping or structurally isolating pass-1 fields before reuse.
2. Rework grounding so the LLM sees extracted slide text and element structure in both passes, or stop promoting unvalidated inferences into queryable metadata.
3. Restore backward compatibility for `text.extract()` and legacy cache files; harden cache loading against invalid JSON shapes.
4. Add real end-to-end tests that call `FolioConverter.convert(passes=1)` and `FolioConverter.convert(passes=2)` and cover the CLI path.
5. Align density scoring, dedup logic, and pass-2 conflict handling with the documented feature contract.

## Verdict

Request changes before merge.
