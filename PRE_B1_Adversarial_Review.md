# PR E Spec Review: Reviewer 3 — Adversarial Review

**Spec:** `docs/specs/folio_context_docs_tier3_closeout_spec.md` (Rev 1, draft)
**Review date:** 2026-03-30
**Focus:** Assumptions, failure modes, what the architect isn't seeing.
**Default stance:** Skeptical.

---

## Assumption Attack Table

| # | Assumption | Why It Might Be Wrong | Impact If Wrong | Code Evidence |
|---|------------|----------------------|-----------------|---------------|
| AA-1 | "Registry generalization is safe" — D9 presents making source-backed fields optional as simple. | `RegistryEntry` at `registry.py:21-43` declares `source_relative_path: str` and `source_hash: str` as **required, non-optional, non-defaulted** positional fields. Making them optional requires changing the dataclass signature, which changes field ordering and breaks every existing `RegistryEntry(...)` call. Six crash points: (1) `refresh_entry_status()` → `check_staleness()` → `resolve_source_path()` does `(markdown_dir / None)` = `TypeError`. (2) `resolve_entry_source()` does `(md_dir / entry.source_relative_path).resolve()` = `TypeError`. (3) `folio scan` calls `resolve_entry_source()` on every entry. (4) `folio status --refresh` calls `refresh_entry_status()` on every entry. (5) `rebuild_registry()` skips docs without `source_hash`. (6) `to_dict()` strips `None` values, but `entry_from_dict()` then fails to reconstruct without defaults. | A context doc in `registry.json` would crash `folio status --refresh`, `folio scan`, and `folio refresh` with `TypeError`. Not "simple generalization" — this is a dataclass contract break touching 6+ call sites across 4 commands. |
| AA-2 | "Implicit linkage is sufficient for v1" — D8 chooses shared `client`/`engagement` over explicit `context` field. | No code path exists that resolves "find documents with matching client and engagement" for context purposes. Enrich filters by client+engagement for relationship proposals, but nothing says "find the context doc for this engagement." The implicit linkage is not consumed by any programmatic path. The context doc sits in the registry and shows up in counts, but nothing connects it to its engagement notes. | Low immediate impact — context doc has value as human-readable Obsidian anchor. But "implicit linkage" is marketing language for "no linkage." The closeout will evaluate "context documents provide engagement scaffolding" and pass it even though zero programmatic evidence connects the scaffolding to anything. |
| AA-3 | "The lifecycle integration test proves Tier 3 works" — §8.3 uses synthetic seeded evidence notes. | Converter integration tests exist (`test_pipeline_integration.py`, `test_converter_integration.py`) but do NOT test converter-output-to-enrich/provenance interaction. The synthetic notes will have perfect `**Evidence:**` block structure. The provenance spec depends on precise regex extraction from real converter output. If converter output drifts in formatting, provenance extraction silently misses claims. The synthetic test deliberately avoids this surface. Production test report found only 6/115 notes (5%) produced relationship proposals — synthetic test will have 100% hit rate. | Test could pass perfectly while real-world converter-to-provenance integration is broken. Proves pipeline works on perfect input only. |
| AA-4 | "The closeout package will be honest" — Gate semantics (§9.6) allow partial closeout with waivers. | No FAIL condition is defined. No threshold for when a criterion must fail vs get PARTIAL with waiver. If all 6 `supersedes` proposals remain unconfirmed (production test report shows 0 canonical `supersedes` populated), provenance has zero confirmed links. Can you declare "provenance works" with zero confirmed links? Under these gate semantics: yes, with a waiver. | Every criterion can receive PARTIAL, every PARTIAL gets a waiver, Tier 3 is "complete enough." Closeout becomes unfalsifiable. |
| AA-5 | "PR #39 is accepted as merged baseline" — §5.1 treats provenance as shipped. | Kickoff tracker line 298 still has `[ ] PR D merged: retroactive provenance` unchecked. Roadmap still says "PR D is next active Tier 3 slice." Baseline memo says current sequencing authority lives in roadmap and kickoff tracker — but those contradict the spec. §11.2 says sync is required "after approval," creating a window where the approved spec contradicts its own governance docs. | Document-reality gap. If PR #39 has subtle issues discovered post-merge, the closeout evaluates provenance as "shipped" while governance docs still say "pending." No safety net. |
| AA-6 | "No blocking open questions remain" — §12 lists four deferred questions. | Question 2 ("should future enrichment read context docs?") hides a design implication: if "yes," enrichment needs `_llm_metadata` and `review_status` on context docs, but the v1 contract explicitly excludes them. The v1 decision is not wrong but presenting it as non-blocking hides the v2 migration obligation. | Medium — not a v1 blocker, but "no blocking open questions" framing is overconfident. V1 frontmatter contract constrains v2 design space. |
| AA-7 | "The spec is three clean parts" — Context docs, lifecycle test, closeout are independent deliverables. | The closeout (§9) evaluates "context documents provide engagement scaffolding" delivered by part 1. The lifecycle test (§8) exercises context doc flow from part 1. If part 1 has a design flaw, parts 2 and 3 validate a flawed design against itself. No external anchor exists. Provenance spec had 15 test plan subsections. PR E has 11 assertions and no unit test plan. | Self-referential validation. Closeout grades its own homework. A subtle context-doc design flaw (e.g., `folio status --refresh` crash) would pass both the lifecycle test and closeout until exercised on a real mixed library. |

---

## Failure Mode Analysis

| # | Failure | How It Happens | Would We Notice? | Spec Coverage |
|---|---------|----------------|------------------|---------------|
| FM-1 | `folio status --refresh` crashes with `TypeError` on context entry. | `refresh_entry_status()` passes `entry.source_relative_path` to `check_staleness()` → `resolve_source_path()` does `(markdown_dir / None)` = `TypeError`. | Only if someone runs `folio status --refresh` on a library with context docs. Lifecycle test assertion 4 tests `folio status` but doesn't specify `--refresh`. | Spec D10 does NOT describe what happens when `folio status --refresh` encounters a context entry. The `--refresh` path calls `refresh_entry_status()` on EVERY entry without type filtering. |
| FM-2 | `folio scan` crashes when resolving context doc source path. | `scan` calls `resolve_entry_source()` on every registry entry (cli.py:858). For context docs with null `source_relative_path`: `TypeError`. | Only when `folio scan` is run on a library with context docs. | D10 says "scan unchanged" — but scan cannot be unchanged if context docs are in the registry. No type filter exists. |
| FM-3 | `folio refresh` passes context docs to `refresh_entry_status()` before type check. | The type check at cli.py:992 only blocks `interaction`. Context entries fall through to `refresh_entry_status()` → crash. | Only when `folio refresh` is run with context docs. | D10 says refresh skips context, but current code only has an interaction skip. |
| FM-4 | `rebuild_registry()` silently drops context docs. | Lines 136-137 require `source`/`source_transcript` + `source_hash`. Context docs have neither → skipped. Any registry corruption or rebuild loses all context entries. | Only after corruption or manual rebuild. User sees 0 context docs in status. | Section 7.4 correctly requires change but doesn't scope how invasive the rebuild rewrite is — rebuild is called from `upsert_entry()`, `status`, `scan`, and `refresh` recovery paths. |
| FM-5 | Context doc ID collision on same-day re-init after deletion. | User deletes context doc, re-runs `folio context init` same day. File doesn't exist (CLI passes), but registry entry with `staleness_status: missing` still exists. Spec says "upsert" but doesn't define upsert semantics for file-deleted-but-registry-present case. | Probably works (upsert overwrites), but behavior is unspecified. | Not covered. |
| FM-6 | `folio enrich` accidentally processes a context doc with missing type field. | Production test report documented all 115 entries were missing `type` field. `_infer_missing_entry_type()` defaults to `"evidence"`, not `"context"`. An orphaned context entry without `type` would be inferred as evidence and pass the enrich eligibility filter. | Only if type field is lost — unlikely but matches a previously observed production bug pattern. | Not covered. |

---

## Blind Spot Identification

1. **No unit test plan.** Provenance spec had 15 test plan subsections. PR E has one integration test with 11 assertions and zero unit test requirements for: context ID generation, path sanitization edge cases, frontmatter template generation, registry upsert for source-less entries, `rebuild_registry()` rewrite, `check_staleness` bypass, validation tooling changes.

2. **No migration/compatibility section.** The `RegistryEntry` dataclass change is a schema-level breaking change. No discussion of: existing tool dependencies on non-null fields, `entry_from_dict()` default paths, or whether `_SCHEMA_VERSION` (currently 1, line 17) should increment.

3. **No risk assessment section.** The enrich spec has a dedicated baseline with known-caveats. The provenance spec has disposition and protection rules. PR E has no risk register, no fallback plan.

4. **`validate_frontmatter.py` will reject context docs.** The validation script's `BASE_REQUIRED_FIELDS` (line 17-21) includes `source_hash`, `version`, `created`, `modified`, `converted`. Context docs will fail as "Missing required field: source_hash." `ALLOWED_TYPES` includes `"context"` (line 25) but there is no context-specific validation branch — code falls through to evidence validation.

5. **What happens during `folio convert --rebuild-registry`?** The converter's registry management calls `rebuild_registry()` on corruption. After context docs exist, they vanish from the rebuilt registry.

6. **Test density regression.** Existing suite has 1,569 test functions across 39 files. PR E proposes ONE integration test. Enrich delivered `test_enrich_integration.py` and `test_enrich_scale.py`. Provenance delivered 15+ test plan subsections.

7. **No `to_dict()`/`entry_from_dict()` round-trip analysis.** `to_dict()` strips `None` values. If source fields are `None`, they won't appear in JSON. `entry_from_dict()` then fails to reconstruct without dataclass defaults.

8. **`folio status` per-type summary is new functionality.** The spec (D10, §7.5) requires per-type counts like "By type: evidence 2, interaction 1, context 1." But the current implementation has no type-counting logic — only staleness buckets. This is a new feature buried in a "behavior" section.

---

## Issues by Severity

**Critical:**

1. **`RegistryEntry` dataclass contract break.** `source_relative_path: str` and `source_hash: str` are required. Making them optional ripples through 6+ crash points across 4 commands. The spec presents this as "source-backed fields become optional at the row level" (D9) without acknowledging any crash points.

2. **`rebuild_registry()` silently drops context docs.** Hard gate on `source_hash`. Any registry corruption loses all context entries. The spec identifies the requirement (§7.4) but doesn't scope the change.

**Major:**

3. **No unit test plan.** Prior specs defined 10-15 test subsections. PR E defines one integration test. Testing density regression.

4. **Self-referential validation structure.** Closeout evaluates its own deliverables using its own test. No external anchor.

5. **Unfalsifiable gate semantics.** No FAIL threshold. Every criterion can get PARTIAL with a waiver. Closeout is unfalsifiable.

6. **`validate_frontmatter.py` will reject context docs.** `BASE_REQUIRED_FIELDS` includes `source_hash`. D12 correctly identifies the need for a context branch but doesn't enumerate exemptions.

**Minor:**

7. Stale governance sync has no enforcement mechanism.
8. "Implicit linkage" is marketing language for "no linkage."
9. Context doc ID date collision is an underspecified edge case.

---

## Risk Assessment Override

The CA rated this as the "final Tier 3 slice" with no blocking open questions. **I disagree on both characterization and risk level.**

**Risk is not low.** The registry generalization is a schema-level contract break that touches at minimum 6 code paths across 4 commands. The spec does not audit these call sites, does not propose a migration strategy, does not increment the schema version, and does not define a unit test plan for the registry changes.

**Blocking open questions exist:**
1. How does `check_staleness()` compute staleness for a source-less entry without throwing?
2. How does `rebuild_registry()` discover context docs that lack `source_hash`?
3. What is the `entry_from_dict()` behavior when `source_relative_path` is absent from JSON?
4. Does the registry schema version need to increment?

**The synthetic test provides weak integration coverage.** By seeding perfect fixtures, the test avoids the converter-to-provenance integration surface most likely to harbor interaction effects.

---

## Verdict

**Request Changes.**

The product design for context docs is sound. But the engineering risk of the registry generalization is significantly underspecified. Before approval:

1. Add a section auditing every call site that accesses `source_relative_path`, `source_hash`, or `source_type` on a `RegistryEntry`.
2. Add a unit test plan comparable to prior Tier 3 specs.
3. Strengthen gate semantics with at least one hard-fail condition.
4. Acknowledge the self-referential validation structure and mitigate with at least one assertion exercising pre-existing code.
