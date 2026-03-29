---
id: folio_provenance_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-03-29
revision: 6
revision_note: |
  Rev 6: Lands the governance edits in the live corpus and redesigns
    provenance repair around immutable `**Evidence:**` entries instead of
    enrich-managed `### Analysis` blocks.
  Governance: roadmap, ontology, enrich refresh contract, kickoff tracker,
    baseline memo, and PRD are updated directly in this revision. The live
    docs are now authoritative; this spec no longer embeds normative appendix
    patch text.
  Anchor model: target provenance now points to structured target evidence
    entries (`target_slide` + `target_claim_index`) with exact stored source
    and target snapshots for verification.
  Repair model: `re-evaluate` never auto-confirms. It creates replacement
    proposals that still require human confirmation, uses `re_evaluate_pending`
    as the canonical repair state, and surfaces blocked-repair reasons when a
    pair cannot be reprocessed.
  CLI: `folio provenance review` is now read-only. Mutations are explicit CLI
    subcommands (`confirm`, `reject`, `stale refresh-hashes`, etc.).
  Runtime: hard shard ceiling remains, and over-ceiling repairs now surface a
    documented blocked state rather than silently looping.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - folio_ontology_architecture
  - folio_enrich_spec
  - v0.5.1_tier3_entity_system_spec
  - tier2_real_vault_validation_report
  - tier3_kickoff_checklist
---

# Retroactive Provenance Linking Spec (PR D)

## 1. Overview

This spec defines **PR D: retroactive provenance linking**, the next Tier 3
slice after the shipped `folio enrich` core (PR C).

PR C established document-level relationships: "this evidence note supersedes
that older version." PR D goes one level deeper: it connects **specific
grounded claims** in one evidence note to **specific structured evidence
entries** in a related evidence note, creating a claim-to-source trail within
the library.

**PR D is a provenance infrastructure slice with an evidence version-lineage
pilot.** The approved roadmap describes the full vision as "match deliverable
claims against library evidence," but the current registry-managed corpus
contains only evidence and interaction notes — no deliverable or analysis notes
exist yet, and the only ontology-legal provenance-relevant relationship on
evidence notes is `supersedes`. v1 ships the provenance pipeline, confirmation
UX, stale-link lifecycle, and data model on the relationship type and document
types that exist today. Deliverable-to-evidence provenance is deferred to v2
when deliverable notes enter the registry.

**Governance:** Rev 6 lands the matching roadmap, ontology, refresh,
kickoff-tracker, baseline-memo, and PRD edits directly in the live corpus.
Those live docs, not embedded appendix patch text, are authoritative.

This is **not** the implementation prompt.

**Output path:** `docs/specs/folio_provenance_spec.md`

---

## 2. Why This Slice Comes Next

PR C shipped two things that make provenance linking possible:

1. **Document-level `supersedes` relationships.** Evidence notes carry
   `supersedes` proposals. When humans confirm these into canonical
   frontmatter, the library has version-lineage edges.

2. **Structured evidence blocks.** Every evidence note carries per-slide
   grounded claims with verbatim quoted spans, element types, and confidence
   levels.

What is still missing is the **cross-document claim-to-evidence trail**. PR D
closes that gap for `supersedes`-linked evidence pairs. The infrastructure is
designed to extend to `draws_from`, `depends_on`, and deliverable/analysis
sources in v2 without redesign.

---

## 3. Goals

1. Add `folio provenance [scope] [--dry-run] [--llm-profile <profile>] [--limit N] [--force] [--clear-rejections]`.
2. Extract matchable claims from evidence notes (structured evidence blocks).
3. Extract matchable evidence entries from target evidence notes linked via
   canonical `supersedes` frontmatter.
4. Use LLM-assisted semantic matching to propose claim-to-evidence provenance
   links, handling paraphrase, summarization, and synthesis.
5. Surface all proposed links for human confirmation with stable IDs,
   filtering, pagination, and batch actions.
6. Store confirmed provenance links as frontmatter queryable via CLI and
   optionally via Obsidian Dataview, with content hashes for stale detection.
7. Provide a complete stale/orphan link lifecycle: detection, surfacing,
   semantic re-evaluation, and first-class repair actions.
8. Make reruns safe: pair-level fingerprints, stale-aware confirmed-link
   deduplication, proposal reconciliation, rejection suppression, and
   human-edit protection.
9. Keep runtime practical: context-budget preflight with deterministic
   overflow sharding (target evidence entries and claims), `--limit` batching, and
   atomic-lock concurrency protection.

---

## 4. Non-Goals

| Item | Why deferred |
|------|--------------|
| Deliverable-source provenance | No deliverable notes in registry. `draws_from`/`depends_on` not applicable to evidence. v2. |
| Analysis-source provenance | No analysis notes in registry. v2. |
| Interaction-source/target provenance | Different format, 0 in production vault. v2. |
| `draws_from`/`depends_on` as seeds | Ontology §12.3: `analysis, deliverable` only. v2. |
| `impacts`/`relates_to`/`instantiates` as seeds | Wrong semantics for evidence support. |
| Reverse-direction `supersedes` | v1 is one-way: newer→older. |
| Cross-engagement provenance | Different trust model. |
| External source matching | Library-internal only. |
| Auto-confirmation | Human-in-the-loop required (FR-706). |
| Citation graph UI | CLI primary. Dataview optional. |
| N-way synthesis | Pairwise only. |
| `.overrides.json` implementation | Separate PR. See §7. |
| Context document generation | PR E. |
| Diagram-note provenance | Not registry-managed. |
| Embedding-based retrieval | LLM matching directly. |
| `--max-calls` | `--limit` provides control. |

---

## 5. Current Shipped Baseline

### 5.1 What exists

1. `folio enrich` proposes `supersedes` for evidence notes, `impacts` for
   interaction notes.
2. Confirmed relationships live in canonical frontmatter.
3. Evidence notes carry structured per-slide evidence blocks.
4. `grounding_summary` aggregates per-note claim statistics.
5. `_llm_metadata.enrich` carries idempotency fingerprints.
6. Frontmatter passthrough in `folio refresh` preserves canonical fields
   and `_llm_metadata.enrich`.

### 5.2 Production library metrics

- 115 registry decks, 160 evidence notes (1,003-393,335 chars; 1-137 slides)
- 1,524 diagram notes, 1,684 total markdown files
- 0 interaction notes in active use
- `anthropic_sonnet4` + 12 blind-validated `haiku45` merges

### 5.3 What does NOT exist

1. No claim-level cross-document linking.
2. No shipped `provenance_links` frontmatter field yet. Rev 6 lands the
   ontology amendment, but implementation still needs to write it.
3. `draws_from`/`depends_on` not legal on evidence notes per ontology §12.3.
4. `supersedes` is the only ontology-legal, provenance-relevant relationship
   on evidence notes. PR C has 6 pending proposals.

### 5.4 v1 yield estimate

- **0 canonical `supersedes` populated** (6 proposals pending)
- PR D v1 yields zero output until humans confirm at least one `supersedes`
- After review of 6 proposals: up to 6 version-lineage pairs
- PR D is an **infrastructure slice**: ships pipeline, UX, lifecycle, and
  data model. Yield scales with confirmed `supersedes` density.

---

## 6. Key Decisions

### D1: Standalone CLI with dedicated `_llm_metadata.provenance` namespace

Separate command, separate namespace, separate lifecycle.

### D2: `supersedes`-only one-way seed (corpus-driven priority reordering)

v1 evaluates only canonical `supersedes`-linked pairs. One-way: newer→older.
`supersedes` is singular per the ontology, so at most one pair per source.

| Relationship | Evidence-legal? | v1 status |
|-------------|----------------|-----------|
| `supersedes` | Yes (`all`) | **Included** (one-way) |
| `draws_from` | No (`analysis, deliverable`) | Deferred v2 |
| `depends_on` | No (`analysis, deliverable`) | Deferred v2 |
| `impacts` | No (`interaction`) | Excluded |
| `relates_to` | Yes (`all`) | Excluded (too broad) |
| `instantiates` | Yes (`all except ref`) | Excluded (wrong semantics) |

This follows PR C's pattern of corpus-driven priority reordering against the
ontology's v1 recommendation (§6.4).

### D3: Batch matching with preflight and deterministic sharding

One LLM call per pair if within budget. Target-evidence sharding and claims
sharding as fallbacks (§12.6).

### D4: Target-side structured `**Evidence:**` entry as evidence granularity

Target matching uses the same structured evidence-entry extraction contract as
source-claim extraction: `target_slide` + `target_claim_index` with exact
claim text and supporting quote snapshots. v1 does **not** fall back to
enrich-managed `### Analysis` prose.

### D5: Three-tier confidence (`high`/`medium`/`low`; default review `medium+`)

### D6: Human confirmation with stable IDs and explicit repair commands

Pending proposals: stable IDs, filtering, pagination, batch actions.
Stale links: `refresh-hashes`, `re-evaluate`, `remove`, `acknowledge`.
`re-evaluate` triggers LLM semantic re-matching — not just a hash refresh.

### D7: Canonical/proposed separation in dedicated namespace

Proposals in `_llm_metadata.provenance`. Confirmed links in
`provenance_links`.

### D8: `.overrides.json` as separate prerequisite PR

### D9: Evidence-note-only claim extraction in v1

### D10: Pair-level fingerprinting

### D11: `--limit` with pair-level continuation

### D12: Rejection suppression with `--clear-rejections` explicit retry

### D13: Stale-aware proposal reconciliation with confirmed-link deduplication

Re-evaluation **replaces** pending proposals. **Stale-aware dedupe:** new
proposals are only suppressed against **fresh** confirmed links. Stale and
`re_evaluate_pending` confirmed links do **not** suppress reproposals.

### D14: Non-destructive stale repair with exact immutable snapshots

Confirmed links store the exact hashed source and target evidence surfaces.
`re-evaluate` is non-destructive, but it never auto-confirms after drift:
replacement matches return as normal pending proposals and still require human
confirmation. `refresh-hashes` is the only "this is still the same link"
action.

### D15: Atomic-lock concurrency protection

Advisory lock via atomic exclusive file creation (`O_CREAT|O_EXCL`). Error
exit on contention. Stale-lock cleanup for dead PIDs.

---

## 7. `.overrides.json` Interaction

Separate prerequisite PR. Provenance extracts from overridden sections
(more authoritative). Confirmed links survive refresh. FR-705 not stretched.

---

## 8. CLI Contract

### 8.1 Command shape

```bash
folio provenance [scope] [--dry-run] [--llm-profile <profile>] [--limit N] [--force] [--clear-rejections]
```

### 8.2 Subcommands

```bash
folio provenance review [scope] [--include-low] [--stale] [--doc <doc_id>] [--target <doc_id>] [--page N]
folio provenance status [scope]
folio provenance confirm <proposal_id>
folio provenance reject <proposal_id>
folio provenance confirm-range <start>..<end> [scope] [--doc <doc_id>] [--target <doc_id>]
folio provenance confirm-doc <doc_id> [scope] [--target <doc_id>]
folio provenance reject-doc <doc_id> [scope] [--target <doc_id>]
folio provenance stale refresh-hashes <link_id>
folio provenance stale re-evaluate <link_id>
folio provenance stale remove <link_id>
folio provenance stale acknowledge <link_id>
folio provenance stale remove-doc <doc_id> [scope]
folio provenance stale acknowledge-doc <doc_id> [scope]
```

### 8.3 Scope

Same as `folio enrich`. Scope = source documents. Targets discovered from
canonical `supersedes`.

### 8.4 Routing

`routing.provenance.primary` → `routing.default.primary`. `--llm-profile`
overrides. `--force` bypasses pair fingerprint; respects rejection bases
unless `--clear-rejections`.

### 8.5 `--dry-run`

No writes, no LLM calls. Reports: scope, pairs, disposition, estimated calls
with shard counts, context-budget status per pair, queued repair work,
and blocked-repair reasons already present in metadata.

### 8.6 `--limit N`

At most N source-target pair evaluations that would invoke the LLM. Skips,
stale checks, and pair-marker self-heal do not count. Pairs queued by
`re_evaluate_pending` **do** count because they consume LLM work.
Deterministic order.

### 8.7 `--clear-rejections`

Requires `--force`.

### 8.8 Progress output

```text
Scope: 6 source document(s), 6 candidate pair(s) [supersedes: 6]
Estimated calls: 6 (1 pair requires sharding → 7 total calls)

+ market-sizing-v2 → market-sizing-v1 (supersedes)    7 claims, 3 proposed links
~ org-review-v2 → org-review-v1 (supersedes)          unchanged
! strategy-v2                                          protected [L1, metadata-only]
! diligence-v2 → diligence-v1 (supersedes)            repair blocked [shard_ceiling_exceeded: 12 > 8]
x failover-v2 → failover-v1 (supersedes)              <error: LLM timeout>

Provenance complete: 4 evaluated, 8 proposed, 1 unchanged, 1 protected, 1 blocked, 1 failed
```

### 8.9 Review output (read-only pending listing)

```text
folio provenance review ClientA --doc market-sizing-v2 --page 1

Pending (3 pending, 2 confirmed [2 fresh], 0 stale):
Page 1/1 (3 items, page size 20, ordered: source doc → confidence desc → proposal_id)

[prov-a1b2] slide 7, claim 0 → market-sizing-v1 slide 3, claim 1
   Claim: "TAM of $2.3B in the Asia-Pacific automotive sector"
   Evidence: "total addressable market estimated at $2.3 billion..."
   Confidence: high | Rationale: Same TAM figure.
   Replaces: plink-g7h8

[prov-c3d4] slide 12, claim 2 → market-sizing-v1 slide 8, claim 0  (medium)
[prov-e5f6] slide 15, claim 1 → market-sizing-v1 slide 10, claim 2 (medium)
```

No confirm/reject prompts appear in-session. `folio provenance review` is
inspection only. All mutations use explicit CLI commands from §13.

**Ordering:** source doc (registry order) → confidence descending →
`proposal_id` lexicographic (stable tie-break). This ordering is deterministic
and stable across runs, making `confirm range` safe.

**Pagination:** page size 20. `--page N`.

### 8.10 Status output

```text
folio provenance status ClientA

| Source Document    | Pairs | Claims | Pending | Fresh | Stale | Ack'd | Re-eval Pending | Blocked | Orphaned | Rejected |
|--------------------|-------|--------|---------|-------|-------|-------|------------------|---------|----------|----------|
| market-sizing-v2   | 1     | 21     | 3       | 8     | 1     | 1     | 1                | 0       | 0        | 2        |
| comp-analysis-v3   | 1     | 12     | 2       | 5     | 0     | 0     | 1                | 1       | 1        | 0        |

Total: 2 pairs, 33 claims, 5 pending, 13 confirmed
       (8 fresh, 1 stale, 1 acknowledged, 2 re-evaluate pending, 1 blocked, 1 orphaned), 2 rejected
Coverage: 8/33 claims have fresh confirmed provenance (24.2%)
```

**Coverage:** distinct source claims with ≥1 **fresh** (non-stale,
non-acknowledged) confirmed link / total extractable claims. A claim with
multiple confirmed links counts once. Stale and acknowledged-stale links
are excluded from coverage.

**Visible surfaced states:**
- **Fresh:** `link_status == confirmed` AND hashes match current content
- **Stale:** `link_status == confirmed` AND hashes don't match
- **Acknowledged:** `link_status == acknowledged_stale` and hashes still match
  the acknowledgment-time hashes
- **Re-evaluate pending:** `link_status == re_evaluate_pending` and no
  current repair error on the pair
- **Repair blocked:** `link_status == re_evaluate_pending` and the pair has a
  current `repair_error`

`Orphaned` is an additional label shown when the original source or target
position no longer exists. It is not a separate canonical `link_status`.

### 8.11 Exit behavior

Exit `0` on success/skip. Non-zero on failures. Non-zero on lock contention.

---

## 9. Data Model Changes

### 9.1 New frontmatter field: `provenance_links`

**Ontology amendment required** (landed in the live ontology doc; see §19).

```yaml
provenance_links:
  - link_id: plink-g7h8
    source_slide: 7
    source_claim_index: 0
    source_claim_hash: "sha256:a1b2..."
    source_claim_text_snapshot: "TAM of $2.3B in the Asia-Pacific automotive sector"
    source_supporting_quote_snapshot: "Total addressable market estimated at $2.3 billion..."
    target_doc: clienta_ddq126_evidence_20260301_market-sizing
    target_slide: 3
    target_claim_index: 1
    target_claim_hash: "sha256:c3d4..."
    target_claim_text_snapshot: "Total addressable market estimated at $2.3 billion..."
    target_supporting_quote_snapshot: "The Asia-Pacific automotive sector TAM is estimated at $2.3B."
    confidence: high
    confirmed_at: "2026-03-29T15:00:00Z"
    link_status: confirmed
```

Rules:

1. Human-owned. Only confirmation/review actions write to it.
2. `link_id`: stable hash of (source_doc, source_slide, source_claim_index,
   target_doc, target_slide, target_claim_index).
3. `source_claim_hash` / `target_claim_hash`: SHA-256 for stale detection.
4. Snapshot fields store the **exact structured evidence surfaces used for
   hashing**: source claim text + quote, target claim text + quote. They are
   persisted verbatim for stale review and `refresh-hashes`; no summary or
   200-character truncation is used in v1.
5. `link_status`:
   - `confirmed` — fresh when hashes match current content.
   - `acknowledged_stale` — human chose to keep despite staleness. Auto-reverts
     to effective `stale` if content changes again after acknowledgment.
   - `re_evaluate_pending` — human requested LLM re-matching. Link persists
     across reruns until a human confirms a replacement, refreshes hashes, or
     removes/acknowledges the link.
6. `acknowledged_at_claim_hash` / `acknowledged_at_target_hash`: stored when
   `acknowledge` is set. Used to detect further content drift after
   acknowledgment (§14.3). Only present on `acknowledged_stale` links.
7. Must be in frontmatter passthrough (landed in the live enrich spec; see
   §19).

### 9.2 `_llm_metadata.provenance`

```yaml
_llm_metadata:
  provenance:
    requested_profile: provenance_default
    profile: provenance_default
    provider: anthropic
    model: claude-sonnet-4-20250514
    provenance_spec_version: 1
    pairs:
      clienta_ddq126_evidence_20260301_market-sizing:
        pair_fingerprint: sha256:...
        repair_error: null
        repair_error_detail: null
        status: proposed
        re_evaluate_requested: false
        timestamp: "2026-03-29T14:30:00Z"
        proposals:
          - proposal_id: prov-a1b2
            replaces_link_id: plink-g7h8
            source_claim:
              slide_number: 7
              claim_index: 0
              claim_text: "TAM of $2.3B"
              claim_hash: "sha256:..."
            target_evidence:
              slide_number: 3
              claim_index: 1
              claim_text: "total addressable market..."
              supporting_quote: "Asia-Pacific automotive sector TAM is estimated at $2.3B."
              claim_hash: "sha256:..."
            confidence: high
            rationale: "Same TAM figure"
            basis_fingerprint: sha256:...
            model: anthropic/claude-sonnet-4-20250514
            timestamp_proposed: "2026-03-29T14:30:00Z"
            status: pending_human_confirmation
```

`proposal_id` is a deterministic stable hash of (source_doc, source_slide,
source_claim_index, target_doc, target_slide, target_claim_index). It does
not depend on shard order, rationale text, or timestamp.

### 9.3 Allowed statuses

Proposal `status`: `pending_human_confirmation` | `rejected` | `stale_pending`

Per-pair `status`: `proposed` | `no_change` | `skipped` | `error`

Per-pair `repair_error`: `null` | `shard_ceiling_exceeded` |
`frontmatter_unreadable` | `target_missing` | `target_ineligible` |
`llm_error`

### 9.4 Pair fingerprint

Hash of: source claims (sorted) + target evidence entries (sorted) + profile +
`provenance_spec_version`.

### 9.5 Content hashes

`claim_hash`: SHA-256 of `claim_text + "|" + supporting_quote`. Including
the quote captures grounding changes even when the claim text is stable.

`target_claim_hash`: SHA-256 of `claim_text + "|" + supporting_quote` for the
target evidence entry. Source and target use the same normalized surface.

### 9.6 Basis fingerprint

Hash of: `claim_hash` + `target_claim_hash` + profile.

### 9.7 Frontmatter passthrough

Both extraction (`cli.py`) and injection (`frontmatter.py`) must be updated.
The live enrich spec now carries the refresh/passthrough contract (§19).

### 9.8 Refresh stale behavior

On source change: preserve `provenance_links` and `_llm_metadata.provenance`
structure. Clear pair fingerprints and cached pair-level repair metadata
(`re_evaluate_requested`, `repair_error`, `repair_error_detail`). Set pending
proposals to `stale_pending`. Preserve rejected proposals. Do not modify
confirmed links (stale detection via hashes). Any `re_evaluate_pending` link
remains canonical repair state and will self-heal back into the next run even
if the pair marker was cleared here.

### 9.9 Registry unchanged

---

## 10. Provenance Pipeline

For each source document in scope:

1. **Read frontmatter and body.**

2. **Check disposition** (§14.1):
   - `_frontmatter_unreadable` → skip entirely
   - `curation_level != L0` or `review_status in {reviewed, overridden}` →
     protected (metadata-only; skip LLM unless re-evaluate queued, §14.1)

3. **Extract claims** (§11).

4. **Discover target.** Read canonical `supersedes`. Resolve via registry.
   Skip if absent, not evidence, or not in registry. Direction: source
   (newer) → target (older). Singular cardinality: at most one pair.

5. **Load target. Extract target evidence entries** (§11).

6. **For the (source, target) pair:**

   a. Compute `pair_fingerprint`.

   b. Build repair queue state:
      - `repair_links` = all `provenance_links` on this pair with
        `link_status: re_evaluate_pending`
      - If `repair_links` exist and pair metadata lacks
        `re_evaluate_requested`, treat the pair as queued anyway (self-heal).
      - If pair metadata has `re_evaluate_requested: true` but `repair_links`
        is empty, clear the marker as stale cache.

   c. Check idempotency. Skip if fingerprint matches, no `--force`, and no
      `repair_links` require LLM reprocessing.

   d. Check `--limit`. Stop if reached. Queued repair pairs count because they
      invoke the LLM.

   e. Estimate context budget. Shard if needed (§12.6).

   f. Build prompt(s) (§12). Call LLM. Parse response.

   g. Score and filter.

   h. **Reconcile.** Replace `pending_human_confirmation` for this pair.
      Preserve `rejected`. If a proposal matches a queued repair target,
      attach `replaces_link_id` to that proposal.

   i. **Stale-aware dedupe.** For each new proposal, check
      `provenance_links` for a confirmed link at (source_slide,
      source_claim_index, target_doc, target_slide, target_claim_index):
      - If confirmed link is **fresh** (hashes match) → suppress proposal.
      - If confirmed link is **stale** (hashes don't match) → **allow**
        proposal. The stale link needs semantic re-validation.
      - If confirmed link has `link_status: acknowledged_stale` **and** still
        matches the acknowledgment-time hashes → suppress (human explicitly
        chose to keep it).
      - If confirmed link has `link_status: re_evaluate_pending` → **allow**
        proposal. Repair requires explicit human reconfirmation.

   j. Check rejection suppression (`basis_fingerprint`).

   k. Write pair state: update `pair_fingerprint`, clear `repair_error`,
      clear `repair_error_detail`, clear `re_evaluate_requested`, and record
      timestamp/status.

7. **Check confirmed-link staleness.** Recompute source and target hashes.
   Flag mismatches. Read-only on `provenance_links` (does not modify
   `link_status`).

8. **Surface blocked repair.** If a queued repair pair cannot be processed
   (`frontmatter_unreadable`, `target_missing`, `target_ineligible`,
   `shard_ceiling_exceeded`, `llm_error`), leave the link(s)
   `re_evaluate_pending`, set `repair_error` + `repair_error_detail` on the
   pair, and surface the link(s) as `repair_blocked`. If a repair run
   succeeds but finds no replacement proposal, leave the link
   `re_evaluate_pending` with no `repair_error`; the human must explicitly
   remove, acknowledge, or confirm a later replacement proposal.

9. **Atomic write.**

10. **Report and continue.**

### 10.1 Atomicity

Atomic per-file. Failures don't abort scope.

### 10.2 Dry-run

Steps 1-6e (disposition, extraction, candidate discovery, fingerprint,
repair self-heal, limit, context-budget estimation) **plus** steps 7-8 in
read-only mode (stale-check preview, queued repair preview, and blocked-repair
preview). No LLM calls, no writes.

Reports: disposition, shard counts, context-budget status, stale link counts,
pending re-evaluate links, and blocked-repair reasons (flagged as
"would trigger LLM on protected note" where applicable). This ensures
dry-run reflects all LLM-triggering paths.

### 10.3 Pair ordering

Sources in **registry order** (`deck_id` lexicographic sort — deterministic
and stable across runs). `supersedes` is singular: at most one target per
source.

---

## 11. Claim and Evidence Extraction

### 11.1 Evidence note claims

From per-slide `**Evidence:**` blocks:

| Source field | Maps to |
|-------------|---------|
| `claim` | `claim_text` |
| `quote` | `supporting_quote` |
| `confidence` | `original_confidence` |
| `element_type` | `element_type` |
| `## Slide N` | `slide_number` |
| position | `claim_index` |

`claim_hash`: SHA-256 of `claim_text + "|" + supporting_quote`.

### 11.2 Target evidence entries

From per-slide `**Evidence:**` blocks in the target note, using the **same
structured extraction contract** as §11.1. v1 does **not** use `### Analysis`
as a fallback surface.

If the target note or targeted slide has no structured evidence entries, the
pair is ineligible. Normal evaluation skips it. Queued repair on such a pair
sets `repair_error: target_ineligible`.

### 11.3 Common representation

```
ExtractedEvidenceItem:
  claim_text, supporting_quote, original_confidence, element_type,
  slide_number, claim_index, claim_hash
```

---

## 12. Matching Contract

### 12.1 Prompt

System: provenance analyst. Newer→older version comparison. JSON response.

User: `CLAIMS:` numbered + `TARGET_EVIDENCE:` lettered + response format spec.

### 12.2 Response: `[{claim_ref, target_ref, confidence, rationale}]`

### 12.3 Confidence: high (exact), medium (paraphrase), low (thematic)

### 12.4 False positive filtering

LLM-primary. Post-LLM: discard unparseable, missing-field, invalid-index.

### 12.5 Semantic matching

Handles paraphrase, summarization, unit variation, rounding, scope narrowing.

### 12.6 Context-budget preflight and deterministic sharding

```
estimated_tokens = ceil(chars / 3.5)
context_budget = model_context_window * 0.80
```

**Normal case:** claims + target evidence entries fit → single call.

**Target-evidence overflow:** target evidence entries exceed remaining budget
after claims. Sort target entries by slide number then `claim_index`. Fill
chunks sequentially, no overlap.

**Single oversized target evidence entry:** If one target evidence entry alone
exceeds available budget, truncate the **supporting quote** to fit and log:
`target evidence quote truncated: slide {N}, claim {I} ({actual}→{budget} tokens)`.
The target claim text is never truncated.

**Claims overflow (fallback):** If claims alone exceed the budget, **shard
claims** symmetrically: sort by slide/index, fill chunks sequentially. Each
chunk gets all target evidence entries. Merge results across shards. This is
the fallback for extremely dense source notes.

**Both claims and target evidence overflow:** Shard claims first, then shard
target evidence within each claim chunk. This produces a matrix of calls.

**Oversized single claim:** If one claim (text + quote) exceeds the available
budget, truncate the quote to fit and log a warning. The claim text is never
truncated (it is the match key).

**Hard ceiling:** `max_shards_per_pair` (default: **8**, configurable via
`FolioConfig`). If a pair would require more shards than the ceiling, **abort
the pair** with `error: pair exceeds shard ceiling ({N} shards needed,
max {max})`. This bounds worst-case cost to 8 LLM calls per pair regardless
of note density. `--limit 1` on a dense pair costs at most 8 calls. If the
pair was queued for repair, write `repair_error: shard_ceiling_exceeded` and
surface `repair_blocked` until a human resolves it.

**Merge:** If same (claim_ref, target_ref) appears in multiple shards, keep
higher confidence.

**Determinism:** Sorting is by slide number (claims: then claim_index).
Sequential fill. No overlap. Stable across identical reruns.

### 12.7 Prompt safety

Role separation. Author-controlled consulting content. Same trust model as
enrich analysis prompts.

---

## 13. Confirmation Contract

### 13.1 Pending proposal review

Grouped by source doc. Stable `prov-XXXX` IDs generated from stable logical
coordinates (source doc/slide/claim index + target doc/slide/claim index).
Pagination: page size 20. Order: source doc (registry) → confidence desc →
`proposal_id` lexicographic (deterministic tie-break). `--page N`.

### 13.2 Pending actions

| Action | Syntax | Effect |
|--------|--------|--------|
| Confirm one | `folio provenance confirm prov-XXXX` | Promote to `provenance_links` |
| Reject one | `folio provenance reject prov-XXXX` | `status: rejected` |
| Confirm range | `folio provenance confirm-range prov-XXXX..prov-YYYY [scope] [--doc <doc_id>] [--target <doc_id>]` | Contiguous range in the current deterministic ordering |
| Confirm doc | `folio provenance confirm-doc <doc_id> [scope] [--target <doc_id>]` | All pending for one source |
| Reject doc | `folio provenance reject-doc <doc_id> [scope] [--target <doc_id>]` | All pending for one source |

No `confirm all` / `reject all`.

### 13.3 Promotion

1. Compute current hashes.
2. Generate `link_id`.
3. Persist **exact current snapshots** for both source and target evidence
   items (`*_text_snapshot`, `*_supporting_quote_snapshot`).
4. If `proposal.replaces_link_id` is present:
   - If `proposal.replaces_link_id == link_id`, update that existing
     `re_evaluate_pending` entry in place to `confirmed`.
   - If `proposal.replaces_link_id != link_id`, append/update the new link,
     then remove the replaced `re_evaluate_pending` entry.
5. If `proposal.replaces_link_id` is absent and `link_id` already exists in
   `provenance_links`, update hashes/snapshots, `confirmed_at`, clear
   acknowledgment fields, and reset `link_status` to `confirmed`
   (re-confirmation).
6. If neither condition applies, append new entry with `link_status:
   confirmed`.
7. Remove proposal from metadata. If no queued repairs remain on the pair,
   clear `repair_error` and `repair_error_detail`.
8. Atomic write.

### 13.4 Rejection

Set `status: rejected`. Preserve for suppression. `--clear-rejections`
removes all in scope.

### 13.5 Stale/orphan link review and repair

Invoked via `folio provenance review --stale`.

**Same pagination contract as pending review:** page size 20, ordered by
source doc → surfaced state (`repair_blocked`, `re_evaluate_pending`, stale,
acknowledged) → orphaned label → `link_id` lexicographic. `--page N`.

| Action | Syntax | Effect |
|--------|--------|--------|
| Refresh hashes | `folio provenance stale refresh-hashes plink-XXXX` | Shows exact persisted source/target snapshots vs current source/target evidence entries. If human confirms, updates hashes and snapshots. Sets `link_status: confirmed`. |
| Re-evaluate | `folio provenance stale re-evaluate plink-XXXX` | **Non-destructive.** Sets `link_status: re_evaluate_pending` and `re_evaluate_requested: true` on the pair. Next `folio provenance` run attempts semantic re-matching. Any match returns as a normal pending proposal with `replaces_link_id`; nothing auto-confirms. |
| Remove | `folio provenance stale remove plink-XXXX` | Delete from `provenance_links`. |
| Acknowledge | `folio provenance stale acknowledge plink-XXXX` | Set `link_status: acknowledged_stale`. Visible as "Ack'd". Excluded from coverage. Auto-reverts to stale on further content drift. |
| Remove doc | `folio provenance stale remove-doc <doc_id> [scope]` | Remove all stale/orphaned links for one source. |
| Acknowledge doc | `folio provenance stale acknowledge-doc <doc_id> [scope]` | Acknowledge all stale links for one source. |

**`re-evaluate` is the semantic repair path.** Unlike `refresh-hashes` (which
shows exact snapshots for visual comparison), `re-evaluate` marks the link for
LLM re-matching on the next run. The link is **not deleted** and is never
auto-confirmed by rerun output. If the next run finds a candidate, it creates
a normal pending proposal with `replaces_link_id`. If no candidate is found,
the old link remains `re_evaluate_pending` until a human removes or
acknowledges it. If the pair cannot be processed, the link surfaces as
`repair_blocked` with the pair-level `repair_error`.

**`refresh-hashes` shows exact snapshots.** The review output displays the
persisted source and target evidence snapshots alongside the current source
and target evidence entries so the human can visually compare before deciding.

**Re-evaluate on protected notes.** The explicit command is itself the opt-in.
The CLI warns that the next provenance run will bypass protection for that
pair only.

**Orphaned links:** `re-evaluate` is **allowed** for orphaned links (pair-level
re-matching does not require the old coordinates). `refresh-hashes` is not
available when positions are gone (no content to verify).

---

## 14. Human Edit Safety and Lifecycle

### 14.1 Protection rules

| Condition | Behavior |
|-----------|---------|
| `_frontmatter_unreadable` | Skip entirely |
| `curation_level != L0` or `review_status in {reviewed, overridden}` | Protected: skip LLM evaluation, still check stale links. **Exception:** if a confirmed link was marked `re-evaluate` (§13.5), the pair evaluation bypasses protection for that pair only. |
| Normal | Full evaluation |

Protected notes receive metadata-only work (stale checks, status reporting)
consistent with enrich's pattern. The `re-evaluate` exception ensures curated
notes with stale provenance can get replacement proposals without lowering
their curation level.

### 14.2 Confirmed provenance persistence

Confirmed links survive re-enrichment, re-conversion, and provenance runs.
Only human actions modify them.

### 14.3 Stale detection (dynamic)

On each run, for each confirmed link:

1. Recompute `source_claim_hash` from current content at (slide, claim_index).
2. Recompute `target_claim_hash` from target at
   (target_doc, target_slide, target_claim_index).
3. Compare against stored hashes.

**Five surfaced states:**

| State | Condition | Coverage | Dedupe behavior | Shown in |
|-------|-----------|----------|----------------|----------|
| **Fresh** | `link_status == confirmed` AND hashes match | Yes | Suppresses reproposals | `status` |
| **Stale** | `link_status == confirmed` AND hashes don't match | No | Does NOT suppress (allows reproposal) | `status`, `review --stale` |
| **Acknowledged** | `link_status == acknowledged_stale` AND hashes match stored ack hashes | No | Suppresses | `status` (Ack'd column), `review --stale` |
| **Re-evaluate pending** | `link_status == re_evaluate_pending` AND pair has no `repair_error` | No | Does NOT suppress | `status`, `review --stale` |
| **Repair blocked** | `link_status == re_evaluate_pending` AND pair has `repair_error` | No | Does NOT suppress | `status`, `review --stale` |

**`acknowledged_stale` auto-revert:** When content changes again after
acknowledgment (hashes drift from the values stored at acknowledgment time),
the link effectively re-enters `stale` state: it stops suppressing
reproposals and reappears in stale review. Implementation: store
`acknowledged_at_claim_hash` and `acknowledged_at_target_hash` when
`acknowledge` is set; compare on each run.

**`provenance_link_stale` review flag:** Added when stale or re-evaluate-
pending links exist. `repair_blocked` is included in this signal. This is an
**additive** flag in the `review_flags` list. It does NOT auto-set
`review_status: flagged` (to avoid worsening the already 94%-flagged corpus).
It is a separate signal visible in `folio provenance status` and queryable
independently.

### 14.4 Orphaned link detection

Orphan = source position gone OR target doc/slide/claim gone. Subset label
on stale, `re_evaluate_pending`, or `repair_blocked`. Label: `ORPHANED` in
review/status. `refresh-hashes` is unavailable for orphaned links. `re-evaluate`,
`remove`, and `acknowledge` remain allowed.

### 14.5 Body mutation

PR D does not mutate body content.

---

## 15. Idempotency

### 15.1 Pair fingerprint under `_llm_metadata.provenance.pairs[target_id]`

### 15.2 Skip: fingerprint match + no `--force` + no queued repair → skip

### 15.3 Rejection suppression: unchanged basis → suppressed

### 15.4 Stale-aware reconciliation

When a pair is re-evaluated:

1. New proposals **replace** `pending_human_confirmation` for that pair.
2. `rejected` proposals **preserved**.
3. Changed-basis rejections: old removed, new stored.
4. **Repair self-heal rules:**
   - Pending link exists but pair marker absent → queue the pair anyway.
   - Pair marker exists but no pending link remains → clear the marker.
5. **Replacement proposals:** proposals generated while a link is
   `re_evaluate_pending` carry `replaces_link_id`. Human confirmation of that
   proposal performs the actual replacement (§13.3). Reruns never auto-confirm.
6. **Confirmed-link check per state:**
   - `confirmed` + fresh (hashes match) → suppress proposal.
   - `confirmed` + stale (hashes don't match) → **allow** proposal.
   - `acknowledged_stale` + hashes still match ack-time hashes → suppress.
   - `acknowledged_stale` + hashes drifted since ack → **allow** proposal.
   - `re_evaluate_pending` / `repair_blocked` → **allow** proposal.
7. Successful pair evaluation clears `repair_error`. Failed or skipped queued
   repair writes/retains `repair_error` so status can surface `repair_blocked`.

### 15.5 Stale-pending after refresh

Pending proposals set to `stale_pending`. Next run reconciles. Canonical
repair state stays on the link (`re_evaluate_pending`), not the pair marker.

---

## 16. Scale Considerations

### 16.1 Estimates

Current: 6 pending proposals → up to 6 pairs after confirmation. Typical
engagement: 10-30 version-lineage pairs.

### 16.2 `--limit`, cost estimation, interruption recovery

Standard pair-level mechanics. Pre-run call/shard estimation.

### 16.3 Advisory-lock concurrency protection

`folio provenance`, `folio enrich`, `folio refresh` must not run concurrently
on overlapping scope.

**Acquisition:** Create `{library_root}/.folio.lock` using atomic exclusive
file creation (`O_CREAT | O_EXCL`). This is race-safe on local filesystems —
only one process can create the file.

**Lock content:** PID + command name + timestamp.

**On startup:**
1. Attempt exclusive create of `.folio.lock`.
2. If file exists: read PID. If process is alive → **error exit**. If dead →
   remove stale lock, retry create.
3. On success: proceed.

**On exit:** Remove lock file. On crash: stale lock cleaned by next caller.

**Scope:** Library-wide lock. Does not protect against non-folio writers or
processes on different machines (e.g., NFS). The operational constraint
("don't run concurrently") remains primary; the lock prevents the most common
accident (two terminal tabs).

---

## 17. Test Plan

### 17.1 Unit: source claim extraction

1. Multiple slides, evidence blocks, pass 1/2
2. Empty slides skipped
3. `claim_hash` includes quote text, deterministic

### 17.2 Unit: target evidence extraction

1. Target note uses the same `**Evidence:**` extraction contract as source
2. Missing/empty target evidence blocks skipped
3. Pair with no target evidence entries → ineligible
4. No fallback to `### Analysis`

### 17.3 Unit: candidate pairs

1. `supersedes` → one-way pair
2. Excluded: all other relationship types
3. Non-evidence targets skipped, absent targets skipped
4. Singular cardinality: at most 1 pair per source

### 17.4 Unit: matching

1. JSON parsing, malformed handling, invalid indices
2. Confidence filtering
3. Basis fingerprint, rejection suppression/expiry
4. `--clear-rejections`

### 17.5 Unit: pair idempotency and continuation

1. Deterministic fingerprint, skip on match
2. Changed source/target → re-evaluate, `--force` bypasses
3. `--limit` counts only LLM-evaluated pairs
4. Queued `re_evaluate_pending` pair counts toward `--limit`
5. Skips, stale checks, and pair-marker self-heal do not count

### 17.6 Unit: stale-aware reconciliation and repair

1. Replace pending, preserve rejected
2. Fresh confirmed link → suppress proposal
3. **Stale confirmed link → allow proposal** (semantic re-validation)
4. `acknowledged_stale` → suppress while ack hashes still match
5. `re_evaluate_pending` / `repair_blocked` → allow replacement proposal
6. Replacement proposals carry `replaces_link_id`
7. Confirming replacement clears or updates the old pending link correctly
8. No auto-confirm on rerun, even when logical coordinates match

### 17.7 Unit: context budget and deterministic sharding

1. Normal pair → single call
2. Target-evidence overflow → deterministic shards (sorted, sequential, no overlap)
3. Single oversized target evidence entry → target quote truncation only
4. **Claims overflow → claims sharding** (symmetric fallback)
5. Both overflow → matrix sharding
6. Merge across shards
7. Stable shard assignment across identical reruns
8. Over-ceiling pair writes `repair_error: shard_ceiling_exceeded`

### 17.8 Integration: full pipeline

Convert two related evidence decks, enrich, confirm `supersedes`, run
provenance, verify proposals, fingerprints, and frontmatter writes.

### 17.9 Stale repair lifecycle

1. Confirm → `provenance_links` with exact source/target hashes and snapshots
2. Proposal removed
3. Persists across refresh
4. Source change → stale detected, shown in status/review
5. Target deletion → orphaned
6. `refresh-hashes` → shows exact old/new source and target evidence entries,
   updates hashes/snapshots, `link_status: confirmed`
7. `re-evaluate` → sets `link_status: re_evaluate_pending`, marks pair for
   re-matching, next run can emit replacement proposal(s) but never auto-confirms
8. No replacement found → old link remains `re_evaluate_pending`
9. Blocked repair (`target_missing`, `target_ineligible`, `frontmatter_unreadable`,
   `llm_error`, `shard_ceiling_exceeded`) surfaces as `repair_blocked`
10. `remove` → deletes
11. `acknowledge` → `link_status: acknowledged_stale`, visible in status
12. `acknowledged_stale` excluded from coverage but visible in Ack'd column
13. Content changes again on acknowledged link → returns to surfaced stale state

### 17.10 Self-heal invariants

1. Pending link with missing pair marker still reprocesses on next run
2. Pair marker with no pending link self-clears
3. Refresh clears cached pair repair metadata but canonical link repair state survives

### 17.11 CLI contract

1. `folio provenance review` is read-only
2. Explicit mutation commands exist for confirm/reject/stale actions
3. Pending pagination: 20/page, ordering stable, `confirm-range` safe
4. Stale pagination: 20/page, ordering by surfaced state then `link_id`
5. `proposal_id` tie-break: lexicographic, deterministic, shard-independent

### 17.12 Status and reporting

1. Status includes `Re-eval Pending` and `Blocked` counts
2. Coverage counts fresh links only
3. `repair_blocked` is surfaced from pending link + pair `repair_error`
4. Dry-run reports stale link counts, queued repairs, blocked repairs, and
   "would trigger LLM on protected note" warnings

### 17.13 Protection and concurrency

1. `L1` → skip LLM, still report stale status
2. `re-evaluate` on protected note → pair bypasses protection on next run
3. Lock: atomic exclusive create, second invocation errors
4. Stale lock cleanup
5. `folio enrich` blocked by existing `folio provenance` lock (cross-command)

### 17.14 Governance/corpus consistency

1. No authoritative live doc still describes PR D v1 as deliverable-to-evidence
2. Roadmap, ontology, PRD, enrich spec, kickoff tracker, baseline memo, and
   provenance spec all name the same CLI family
3. All authoritative docs agree that v1 seeds from confirmed `supersedes`
4. Refresh passthrough for `provenance_links` and `_llm_metadata.provenance`
   is documented consistently

### 17.15 Seeded real-library validation

1. One seeded normal pair exercising proposal generation, confirmation,
   stale detection, `refresh-hashes`, and `re-evaluate`
2. One seeded dense pair that actually exercises sharding
3. One seeded pair or synthetic-real note that exceeds the shard ceiling and
   proves blocked-repair surfacing
4. Validation records exact commands, model/profile used, shard counts, and
   observed status transitions

---

## 18. Acceptance Criteria

**Governance / corpus alignment:**

- No authoritative live doc still describes PR D v1 as deliverable-to-evidence
- Roadmap, PRD, ontology, enrich spec, kickoff tracker, baseline memo, and
  this spec all describe the same v1 scope, seed model, CLI family, and
  refresh durability story

**Infrastructure:**

- All CLI commands exist with defined flags and subcommands
- `folio provenance review` is read-only; all mutations are explicit commands
- `_llm_metadata.provenance` namespace with pair-level state
- `provenance_links` field with content hashes, `link_id`, exact snapshots,
  and `link_status`
- Frontmatter passthrough for both fields
- Atomic-lock concurrency protection
- Context-budget preflight with target-evidence and claims sharding

**Correctness:**

- `supersedes`-only, one-way, evidence-to-evidence pairs
- Target anchoring uses structured `**Evidence:**` entries only
- Confirmed-link deduplication is stale-aware
- Surfaced states are complete: fresh, stale, acknowledged,
  `re_evaluate_pending`, `repair_blocked`
- `re-evaluate` provides semantic repair via LLM re-matching without
  auto-confirmation
- Proposal reconciliation: replace pending, preserve rejected
- Replacement proposals use `replaces_link_id`
- Rejection suppression via basis fingerprint
- Pair-level fingerprints with correct `--limit` continuation
- Blocked repair is operator-visible via status/review

**Yield (infrastructure-first):**

- Correct proposals on fixture data with confirmed `supersedes`
- Zero candidate pairs when no `supersedes` → clean no-op
- Manual relationship seeding is a documented prerequisite for output
- Acceptance does not require non-trivial yield on the current production
  baseline; it requires the pipeline to produce correct results when pairs
  exist

**Seeded real-library validation:**

- One seeded normal pair exercising proposal generation, confirmation, stale
  detection, `refresh-hashes`, and `re-evaluate`
- One seeded dense pair that actually exercises sharding
- One seeded pair or synthetic-real note that exceeds the shard ceiling and
  proves blocked-repair surfacing
- Validation records enough detail to prove the real-library repair lifecycle
  is trustworthy, not just the fixture behavior

---

## 19. Live Alignment Summary

Rev 6 lands the governing-doc alignment directly in the live corpus. The
authoritative edits are now in:

- `docs/product/04_Implementation_Roadmap.md`
- `docs/product/02_Product_Requirements_Document.md`
- `docs/architecture/Folio_Ontology_Architecture.md`
- `docs/specs/folio_enrich_spec.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/product/tier3_baseline_decision_memo.md`

Those docs now agree on the v1 scope:

- PR D is an infrastructure + evidence version-lineage pilot, not
  deliverable-to-evidence v1
- confirmed `supersedes` is the only active provenance seed in the current
  corpus
- `folio provenance` / `review` / `status` and the explicit mutation commands
  are part of the CLI family
- `provenance_links` and `_llm_metadata.provenance` are preserved through
  refresh
- the baseline memo is historical for sequencing; roadmap + kickoff tracker
  are the active sequencing surfaces

---

## 20. Open Questions

### Q1: Confidence threshold

`medium+` default. No reviewer challenged. Keep.

### Q2: v2 seed expansion priority

When deliverable or analysis notes enter the registry, revisit whether v2
should add `draws_from`, `depends_on`, or both first. Rev 6 does not decide
that ordering.

---

## 21. Sequencing / Preconditions

1. PR C merged. ✓
2. PR #38 merged. ✓
3. Live roadmap / PRD / ontology / enrich spec / kickoff tracker / baseline
   memo aligned to Rev 6 scope. ✓
4. `.overrides.json` sidecar either shipped or explicitly deferred. ✓
5. Production baseline unchanged. ✓
6. At least one human-confirmed `supersedes` pair is required for non-zero
   provenance yield.
7. Follow-on work remains: implementation prompt, seeded real-library
   validation, and v2 scope decision when non-evidence note types enter the
   registry.

---

## 22. Rev 6 Review Closure

- Governance blockers are addressed by live-doc edits, not appendix-only text.
- Repair-trust blockers are addressed by immutable evidence-entry anchoring,
  exact persisted snapshots, non-destructive `re-evaluate`, and surfaced
  blocked-repair reasons.
- UX blockers are addressed by a read-only `review` command plus explicit
  mutation commands with deterministic IDs and batchable scope.
