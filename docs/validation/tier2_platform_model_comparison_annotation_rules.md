---
id: tier2_platform_model_comparison_annotation_rules
label: tier2_platform_model_comparison
created: 2026-03-22
locked: true
---

# Annotation Rules — Tier 2 Platform Model Comparison

## Schema Version

v1.0 — locked before scored execution. Do not modify mid-run.

## General Rules

1. Every scored slide gets one adjudicated final label set
2. Labels are normalized to lowercase before comparison
3. Minor whitespace and punctuation variation is equivalent
4. When multiple acceptable labels exist, list all in the gold set

## Pass 1 Annotation Schema

For every corpus slide, annotate:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `gold_slide_type` | string | yes | One of: title, narrative, framework, data, process-flow, executive-summary, next-steps, appendix |
| `gold_framework` | string or null | yes | One of: process-flow, mece, timeline, org-chart, waterfall, swot, or null |
| `gold_key_facts` | list of strings | yes | Atomic facts, max 5. Normalize numbers (e.g., "4.2B" = "$4.2 billion") |
| `gold_main_insight` | string | yes | One sentence capturing the slide's primary message |
| `gold_quotes` | list of strings | yes | 1-5 acceptable grounding quotes from the slide text |
| `acceptable_alt_types` | list of strings | no | Alternative acceptable slide_type values |
| `acceptable_alt_frameworks` | list of strings | no | Alternative acceptable framework values |

### Scoring Rules

- `slide_type`: exact match against gold or acceptable alternates. Score: 1.0 (match) or 0.0
- `framework`: exact match against gold or acceptable alternates. Score: 1.0 (match) or 0.0. Null matches null.
- `key_facts`: atomic-fact precision and recall against gold set. Normalize numbers before comparison.
- `main_insight`: factual faithfulness to gold sentence (primary), coverage (secondary). Score: 0.0-1.0
- `evidence_quotes`: precision and recall against acceptable quote set. Minor whitespace/punctuation variation is equivalent.

## Diagram Annotation Schema

For diagram/mixed corpus slides, annotate:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `expected_classification` | string | yes | diagram, mixed, or non-diagram |
| `expected_diagram_type` | string | yes | architecture, data-flow, or unsupported type name |
| `expected_supported` | boolean | yes | true for architecture/data-flow, false otherwise |
| `expected_abstain` | boolean | yes | true if extraction should abstain |
| `expected_review_required` | boolean | yes | true if review flag should be set |
| `gold_nodes` | list of {label, kind} | yes | All expected nodes with labels and kinds |
| `gold_edges` | list of {source, target, label?, direction} | yes | All expected edges |
| `gold_groups` | list of {name, contains} | no | Containment/grouping structure |
| `acceptable_alt_labels` | dict of {node_id: [alt_labels]} | no | Alternative acceptable node labels |

### Scoring Rules

- Node precision/recall: match by normalized label (case-insensitive, whitespace-collapsed)
- Edge precision/recall: match by (source_label, target_label) after normalization
- Edge direction: exact match (forward, reverse, bidirectional, none)
- Abstention correctness: binary — did the model correctly abstain on unsupported types?
- Review-flag correctness: binary — is review_required set appropriately?
- Mermaid validity: binary per page when Mermaid is emitted

### Unsupported Diagram Scoring

Unsupported diagram types (org-chart, matrix, etc.) are scored ONLY on:
- Correct abstention behavior (did it abstain?)
- Correct review_required flag
- NOT on graph accuracy (no gold nodes/edges needed)

### Pass-1-Gated Control Scoring

Title, data, and appendix pages that happen to contain diagram-like visuals are scored on:
- Correct Pass 1 classification (should remain plain SlideAnalysis)
- NOT treated as diagram extraction misses

## Pass 2 Annotation Schema

For Pass-2-eligible slides, annotate:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `gold_incremental_facts` | list of strings | yes | New facts that should appear in Pass 2 but not Pass 1 |
| `gold_reassessment_type` | string | yes | "unchanged" or a corrected slide_type |
| `gold_reassessment_framework` | string | yes | "unchanged" or a corrected framework |

### Scoring Rules

- Incremental evidence: only score facts NEW in Pass 2 (not already in Pass 1)
- Reassessment: "unchanged" is a valid target label; score exact match
- Net lift: compare final Pass-2 output quality against Pass-1 baseline

## Calibration Protocol

1. Select 10-slide calibration subset (marked `[S]` in corpus manifest)
2. Annotate all 10 slides with gold labels
3. Verify schema stability — if any rule is ambiguous, resolve before full annotation
4. Lock rules (this document) before scored execution begins

## Adjudication Rules

When annotator disagreement occurs:
1. If both labels are defensible, include both as acceptable alternates
2. If one label is clearly better grounded, use it as primary
3. Record adjudication rationale in the calibration notes
4. Never change the schema to accommodate a model's output
