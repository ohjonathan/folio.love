---
id: doc_02_product_requirements_document
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Product Requirements Document

**Version 1.4 | March 2026**
**folio.love**

**v1.4 changes:** Added context document support after PR E (PR #40).
Updated FR-403 for registry schema v2 and source-less managed documents.
Added FR-510 for the `folio context` command family. Updated scope to
include context documents alongside evidence and interaction notes.
See the closeout at `docs/validation/tier3_closeout_report.md`.

**v1.3 changes:** Added the shipped entity-system baseline after PR #32,
PR #34, and PR #35. Expanded the FR-400 and FR-500 families to cover
`entities.json`, the `folio entities` command family, and ingest-time entity
resolution. Clarified the current late-March pre-PR-C baseline and linked the
detailed status delta in
`docs/product/tier3_baseline_decision_memo.md`. See
`docs/product/strategic_direction_memo.md` for governing principles.

---

## 1. Product Overview

### 1.1 Purpose

This document defines the requirements for Folio, a knowledge management system that converts consulting materials into an AI-native, searchable library. Requirements are prioritized by the hierarchy of value: conversion quality first, then version integrity, then organization features.

Folio's output must be trustworthy enough for direct use in active McKinsey engagements serving Fortune 100 clients. The quality bar is not "searchable and retrievable" but "a senior consultant can include this in a client deliverable without manually verifying every detail."

### 1.2 Scope

Folio v1.0 encompasses:
- Document conversion pipeline (PPTX/PDF to Markdown)
- Interaction ingestion pipeline (txt/md transcripts and notes to interaction markdown)
- Context document management (engagement scaffolding notes)
- Entity registry and CSV import for known people, departments, systems, and processes
- Ingest-time entity resolution against confirmed registry entries
- Source file tracking with relative paths
- Version tracking and change detection
- Optional LLM analysis with bring-your-own provider credentials
- Knowledge library organization (multi-client, multi-engagement)
- Mixed-library registry/status/scan behavior across evidence, interaction, and context documents
- Obsidian-compatible output format
- CLI for all operations
- Source grounding and extraction confidence scoring
- Review status tracking and human override persistence

### 1.3 Definitions

| Term | Definition |
|------|------------|
| Deck | A PowerPoint presentation (.pptx) or PDF document |
| Interaction | A meeting, interview, workshop, or sync note created by `folio ingest` from transcript or notes text |
| Document | Any managed Folio markdown asset in the library (for example evidence or interaction) |
| Library | The organized collection of all converted materials (an Obsidian vault) |
| Source Path | Relative path from the markdown file to the original source file |
| Source Transcript | Relative path from an interaction note to the transcript or notes file used to create it |
| Source Hash | SHA256 hash of the source file for staleness detection |
| Verbatim Text | Exact text extracted from slides, preserving wording |
| Analysis | LLM-generated description of visual content and frameworks |
| Frontmatter | YAML metadata block at the top of markdown files (Obsidian standard) |
| Source Grounding | Mapping from an extracted claim to the specific text that supports it |
| Extraction Confidence | Aggregate score (0.0-1.0) reflecting reliability of LLM analysis for a document |
| Review Status | Machine-tracked state indicating whether a document needs human attention |
| Human Override | A correction made by a human reviewer that persists across re-conversion |
| Entity Registry | Library-local `entities.json` store of canonical people, departments, systems, and processes |
| Confirmed Entity | Registry entry eligible for exact/alias resolution during ingest |
| Unconfirmed Entity | Auto-created or imported-for-review entity that is visible to humans but excluded from future resolution until confirmed |
| Proposed Match | LLM-suggested link from an unresolved extracted entity to an existing confirmed registry entry, surfaced for human confirmation |

---

## 2. Functional Requirements

### 2.1 Core Conversion (FR-100) — P0 CRITICAL

These requirements are non-negotiable. If any of these fail, the entire system fails.

#### FR-101: Slide Image Extraction

The system SHALL extract a PNG image for every slide/page:
- Resolution: 150 DPI minimum
- Format: PNG (lossless)
- Naming: `slide-NNN.png` (zero-padded to 3 digits)
- Storage: `slides/` subdirectory within deck folder

**Acceptance Criteria:**
- [ ] Every slide in source has corresponding image in output
- [ ] Images are legible (text readable, diagrams clear)
- [ ] Images render correctly in Obsidian preview

#### FR-102: Verbatim Text Extraction

The system SHALL extract text exactly as it appears in the source:
- Preserve exact wording (no paraphrasing)
- Maintain bullet points and numbering
- Preserve table structure where detectable
- Display in blockquote format for visual distinction

**Acceptance Criteria:**
- [ ] Text diff between source and extraction shows <1% character difference
- [ ] Bullet points appear as bullets, not mangled
- [ ] Tables render as markdown tables

#### FR-103: LLM Analysis Generation

The system SHALL generate grounded analysis for each slide using the configured LLM provider when valid credentials are available:
- **Slide Type:** title, executive-summary, framework, data, narrative, next-steps, appendix
- **Framework Detection:** 2x2-matrix, scr, mece, waterfall, gantt, timeline, process-flow, org-chart
- **Visual Description:** Axes labels, quadrant contents, chart types, spatial relationships
- **Key Data Points:** Numbers, percentages, metrics mentioned
- **Main Insight:** One-sentence summary of the "so what"
- **Source Grounding:** Every claim must cite the specific slide text that supports it (see FR-701)
- **Per-Claim Confidence:** Each grounded claim must include a confidence level (high/medium/low)

Supported providers in v1.0:
- Anthropic
- OpenAI
- Google Gemini

**Acceptance Criteria:**
- [ ] Every slide has all five analysis fields populated
- [ ] Framework detection correctly identifies common consulting frameworks
- [ ] Visual description captures information lost in text-only extraction
- [ ] Every claim includes a quoted text span and confidence level
- [ ] Quoted spans are validated against extracted text; unvalidated quotes are flagged
- [ ] If analysis cannot run, conversion succeeds with `review_status: flagged` and flag `analysis_unavailable`

#### FR-104: Source File Tracking

The system SHALL maintain a link back to the original source file:
- **Relative Path:** Path from markdown file to source (portable across machines)
- **Source Hash:** SHA256 hash of source file at conversion time
- **Display:** Source path shown in markdown header AND frontmatter

**Acceptance Criteria:**
- [ ] Source path is valid and file exists at that location
- [ ] User can open original file within 2 clicks from markdown
- [ ] Path works when library is synced via OneDrive/Dropbox to another machine

#### FR-105: Markdown Assembly

The system SHALL produce a single markdown file per deck with:
- Obsidian-compatible YAML frontmatter
- Source tracking (path and hash)
- Version information
- Per-slide sections with image, verbatim text, and grounded analysis
- Evidence block per slide showing claims with quoted sources and confidence
- Version history table at end

---

### 2.2 Source Management (FR-200) — P0 CRITICAL

#### FR-201: Relative Path Storage

Source paths SHALL be stored as relative paths:
- Relative to the markdown file location
- Use forward slashes (cross-platform compatible)
- Handle spaces and special characters correctly

Example:
```
Markdown: library/ClientA/Project1/market_sizing.md
Source:   sources/ClientA/Project1/market_sizing.pptx
Path:     ../../../sources/ClientA/Project1/market_sizing.pptx
```

#### FR-202: Source Configuration

The system SHALL support configuring source directories:
- Map source roots to library locations
- Store configuration in `folio.yaml` at library root
- Support multiple source roots

```yaml
# folio.yaml
library_root: ./library
sources:
  - name: client-materials
    path: ../client_materials
  - name: internal
    path: ../internal_templates
  - name: research
    path: C:/Users/Johnny/Research  # absolute paths allowed for external sources
```

#### FR-203: Source Hash Verification

The system SHALL track source file hashes:
- Compute SHA256 hash at conversion time
- Store hash in frontmatter and version_history.json
- Compare hashes to detect source file changes

---

### 2.3 Version Tracking (FR-300) — P0 CRITICAL

#### FR-301: Change Detection

When re-converting a previously converted deck, the system SHALL:
- Compare current text to cached previous text
- Identify added slides (new slide numbers)
- Identify removed slides (missing slide numbers)
- Identify modified slides (text content differs)
- Mark unchanged slides

**Acceptance Criteria:**
- [ ] Modified slides correctly detected when single word changes
- [ ] Added/removed slides correctly detected
- [ ] Change summary appears at top of markdown

#### FR-302: Version History

The system SHALL maintain version history in `version_history.json`:
```json
{
  "versions": [
    {
      "version": 1,
      "timestamp": "2026-01-10T14:30:00Z",
      "source_hash": "abc123def456",
      "source_path": "../../../sources/ClientA/market_sizing.pptx",
      "note": "Initial conversion",
      "changes": {
        "added": [1, 2, 3, 4, 5],
        "removed": [],
        "modified": [],
        "unchanged": []
      }
    }
  ]
}
```

#### FR-303: Staleness Detection

The system SHALL detect when source files have changed:
- Compare stored hash to current file hash
- Flag stale conversions in `status` output
- Include staleness warning in markdown frontmatter if detected during read

---

### 2.4 Library Organization (FR-400) — P1

#### FR-401: Directory Structure

The knowledge library SHALL follow this structure:
```
folio_library/
├── folio.yaml               # Configuration
├── registry.json            # Index of all managed documents
│
├── ClientA/
│   └── Project1/
│       └── market_sizing/
│           ├── market_sizing.md
│           ├── slides/
│           │   ├── slide-001.png
│           │   └── ...
│           ├── version_history.json
│           ├── .texts_cache.json
│           └── .overrides.json  # Human corrections (if any)
│
├── ClientA/
│   └── DD_Q1_2026/
│       └── interactions/
│           └── clienta_ddq126_interview_20260321_expert-interview/
│               ├── clienta_ddq126_interview_20260321_expert-interview.md
│               └── version_history.json
│
├── Internal/
│   └── Templates/
│       └── ...
│
└── Research/
    └── Industry/
        └── ...
```

#### FR-402: Obsidian Frontmatter

Every markdown file SHALL include Obsidian-compatible YAML frontmatter aligned
to the Folio Ontology v2 baseline:
```yaml
---
id: clienta_ddq126_evidence_20260210_market-sizing
title: Market Sizing Analysis
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
source_type: deck
version: 2
converted: 2026-01-10T14:30:00Z
client: ClientA
engagement: Due Diligence Q1 2026
type: evidence
subtype: research
status: current  # or "stale" if source changed
authority: captured
curation_level: L0
frameworks:
  - 2x2-matrix
  - scr
slide_types:
  - executive-summary
  - framework
  - data
tags:
  - market-sizing
  - competitive-analysis
review_status: clean         # clean | flagged | reviewed | overridden
review_flags: []
extraction_confidence: 0.87
provenance_links:
  - link_id: plink-a1b2c3d4e5f6
    source_slide: 7
    source_claim_index: 0
    target_doc: clienta_ddq126_evidence_20260210_market-sizing-v1
    target_slide: 3
    target_claim_index: 1
    confidence: high
    confirmed_at: 2026-03-29T15:00:00Z
    link_status: confirmed
_llm_metadata:
  provenance:
    pairs: {}
---
```

Here, `engagement` replaces `project` as the metadata field. Example source
paths and directory structures may still use project-style folder names without
changing the frontmatter contract.

#### FR-403: Registry

The system SHALL maintain a `registry.json` with:
- All managed documents (including evidence decks, interaction notes, and context documents)
- Document type (`evidence`, `interaction`, `context`), with optional `subtype` for context docs
- Source paths/transcripts and source hashes (where applicable; context docs are source-less)
- Last processing timestamp
- Current staleness status
- Review status and extraction confidence (for library-wide review queries)
- Canonical relationship context sufficient to resolve provenance targets
  (including confirmed `supersedes` predecessor IDs for evidence notes)
- Registry schema version tracking (`_schema_version: 2` as of PR E)

#### FR-404: Entity Registry

The system SHALL maintain a separate `entities.json` at the library root with:
- Canonical entities for `person`, `department`, `system`, and `process`
- Canonical names plus aliases
- Confirmation state (`confirmed` or `unconfirmed`)
- Optional proposed-match metadata for human review
- Type-specific metadata such as title, department, owner, or reports-to

The entity registry is distinct from `registry.json`: entities are graph nodes,
not managed markdown documents.

The system SHALL also support derived entity stub notes under `_entities/`
within the library root. These stub notes are generated artifacts organized by
entity type for Obsidian graph connectivity. They are distinct from both
`entities.json` and `registry.json`, and they are not managed documents.

For the current shipped Tier 3 baseline, the registry contract is broader than
the most heavily exercised ingest-time extraction path: registry storage,
import, and review support all four entity types, while the first production
ingest-resolution pass has been exercised most heavily on people and
departments. Broader production-scale entity backfill remains later Tier 3
work.

**Acceptance Criteria:**
- [ ] `entities.json` persists the four shipped entity types
- [ ] Confirmed and unconfirmed entities are distinguishable
- [ ] Aliases participate in lookup for confirmed entities
- [ ] Proposed matches are retained for human review instead of silently applied

#### FR-405: Context Documents

The system SHALL support context documents as first-class managed documents in
`registry.json`. Context documents provide engagement-level scaffolding
(client background, SOW, team, timeline, hypotheses) without a backing source
file.

Context document requirements:
- `type: context` with `subtype: engagement` for the v1 template
- Source-less frontmatter: no `source`, `source_hash`, `source_type`, or
  `source_transcript` fields
- Fixed review defaults: `review_status: clean`, `review_flags: []`,
  `extraction_confidence: null`
- Deterministic date-based ID: `{client}_{engagement}_{context}_{date}_{subtype}`
- Registry schema v2 required for source-less row compatibility
- Body template with required sections: Client Background, Engagement Snapshot,
  Objectives / SOW, Timeline, Team, Stakeholders, Starting Hypotheses,
  Risks / Open Questions

Context documents are first-class registry citizens but do not participate in:
- `folio scan` (no source file to track)
- `folio refresh` (no conversion to redo)
- `folio enrich` (not an analysis target in v1)
- `folio provenance` (not an evidence document)

**Acceptance Criteria:**
- [ ] Context docs are registered with `type: context` in `registry.json`
- [ ] Context frontmatter is source-less and uses fixed review defaults
- [ ] Context body template includes all required sections
- [ ] `folio status` displays context docs in per-type summary
- [ ] `folio scan`, `folio refresh`, `folio enrich`, and `folio provenance`
      safely skip context rows

### 2.5 CLI Commands (FR-500) — P1

#### FR-501: Convert Command
```bash
folio convert <source_file> [--note "version note"] [--target <library_path>] [--llm-profile <profile>]
```
- Convert single file to markdown
- Auto-detect target location from config or create new
- Generate LLM analysis using the configured route or explicit LLM profile
- Preserve deterministic single-profile behavior when `--llm-profile` is used

#### FR-502: Batch Command
```bash
folio batch <source_directory> [--pattern "*.pptx"] [--llm-profile <profile>]
```
- Convert all matching files
- Progress indicator
- Error handling per file (continue on failure)
- Summary output
- When duplicate-content or empty files are encountered, skip them without
  aborting the batch and report the skipped counts in summary output

#### FR-503: Status Command
```bash
folio status [<scope>]
```
- Show all managed documents and their status
- Flag stale documents
- Flag missing source files
- Flag documents with `review_status: flagged`
- When `entities.json` exists, include an entity summary with total and
  unconfirmed counts
- Scope to client/engagement or any library-relative path (any path relative to
  `library_root`) if specified

#### FR-504: Scan Command
```bash
folio scan
```
- Find new files in source directories not yet converted or ingested
- Find source files that have changed since last conversion or ingest
- Include transcript and notes sources (`.txt`, `.md`) alongside deck inputs
- Output actionable list

#### FR-505: Refresh Command
```bash
folio refresh [--scope <path>] [--all]
```
- Re-convert all stale decks
- Optionally scope to a specific client/engagement or library-relative path
  (any path relative to `library_root`)
- Update registry
- Respect human overrides: do not overwrite sections recorded in `.overrides.json`
- Skip interaction entries with explicit rerun guidance to use `folio ingest`

#### FR-506: Ingest Command
```bash
folio ingest <source_file> --type <subtype> --date YYYY-MM-DD [--client <name>] [--engagement <name>] [--participants "A, B"] [--duration-minutes N] [--source-recording <path>] [--title <title>] [--target <path>] [--llm-profile <profile>] [--note "version note"]
```
- Accept transcript or notes sources in `.txt` or `.md` format
- Generate a single structured interaction note with ontology-native frontmatter
- Support interaction subtypes: `client_meeting`, `expert_interview`,
  `internal_sync`, `partner_check_in`, `workshop`
- Preserve note identity on re-ingest by matching explicit target,
  `source_transcript`, or `source_hash`
- Resolve extracted entities against confirmed registry entries using exact
  canonical-name or alias matching
- When exact/alias matching fails and same-type candidates exist, record a
  bounded LLM-proposed soft match for human review
- Auto-create unresolved extracted entities as unconfirmed registry entries
- Render resolved mentions as canonical wikilinks in the output interaction note
- If analysis cannot run, still write a degraded interaction note that is
  visibly flagged for review

**Acceptance Criteria:**
- [ ] `folio ingest` writes a markdown note with `type: interaction`
- [ ] Interaction frontmatter uses `source_transcript` and `source_hash`, not
  evidence-only source fields
- [ ] Interaction notes include Summary, Key Findings, Entities Mentioned,
  Quotes / Evidence, Impact on Hypotheses, and Raw Transcript sections
- [ ] Re-ingesting the same source reuses the existing note path and increments
  versioning instead of creating duplicates
- [ ] Exact canonical-name and alias matches resolve to confirmed registry entities
- [ ] Unresolved extracted entities are preserved as visible unconfirmed follow-up work
- [ ] LLM soft-match proposals are reviewable rather than silently canonicalized

#### FR-507: Entities Command Family

```bash
folio entities [--type <entity_type>] [--unconfirmed]
folio entities show <name> [--type <entity_type>]
folio entities import <csv>
folio entities generate-stubs [--output-dir <path>] [--force]
folio entities confirm <name>
folio entities reject <name>
```

- List entities grouped by type with confirmation status
- Filter to a specific type or only unconfirmed entities
- Show a single entity with aliases, type-specific metadata, and proposed match
- Import org-chart style CSV data into the registry, auto-detecting hierarchy
  columns such as `reports_to` or `level`
- When org-chart hierarchy data is present, merge `title`, `org_level`,
  `department`, and `reports_to` into existing person entities and auto-create
  missing manager-chain entries as confirmed people
- Generate lightweight stub notes for registry entities without tracking those
  stubs in `registry.json`
- Confirm an unconfirmed entity for future resolution
- Reject an unconfirmed entity from the registry

**Acceptance Criteria:**
- [ ] `folio entities` shows grouped entity totals and unconfirmed counts
- [ ] `folio entities import <csv>` creates or upgrades registry entries
- [ ] Org-chart imports merge hierarchy fields into matching people and
  complete missing `reports_to` chains
- [ ] `folio entities confirm <name>` clears pending review state and keeps the entity
- [ ] `folio entities reject <name>` removes only unconfirmed entities

#### FR-508: Entity Stub Generation

```bash
folio entities generate-stubs [--output-dir <path>] [--force]
```

- Generate lightweight markdown stub files for all confirmed and unconfirmed
  entities so existing canonical wikilinks resolve in Obsidian
- Organize stubs under `_entities/<entity_type>/` by default, with an optional
  output-directory override
- Skip existing stubs during normal runs and refresh auto-generated stubs only
  when `--force` is requested
- Preserve manually enriched stubs instead of overwriting them

**Acceptance Criteria:**
- [ ] Every registry entity can have a corresponding generated stub note
- [ ] Generated stubs resolve canonical entity wikilinks in Obsidian
- [ ] `generate-stubs` is additive and idempotent by default
- [ ] Manually enriched stubs survive subsequent generation runs

#### FR-509: Provenance Command
```bash
folio provenance [scope] [--dry-run] [--llm-profile <profile>] [--limit N] [--force] [--clear-rejections]
folio provenance review [scope] [--include-low] [--stale] [--doc <doc_id>] [--target <doc_id>] [--page N]
folio provenance status [scope]
folio provenance confirm <proposal_id>
folio provenance reject <proposal_id>
folio provenance confirm-range <start_id>..<end_id> [scope] [--doc <doc_id>] [--target <doc_id>]
folio provenance confirm-doc <doc_id> [scope] [--target <doc_id>]
folio provenance reject-doc <doc_id> [scope] [--target <doc_id>]
folio provenance stale refresh-hashes <link_id>
folio provenance stale re-evaluate <link_id>
folio provenance stale remove <link_id>
folio provenance stale acknowledge <link_id>
folio provenance stale remove-doc <doc_id> [scope]
folio provenance stale acknowledge-doc <doc_id> [scope]
```

- Extract grounded source claims and target evidence entries from confirmed
  `supersedes`-linked evidence-note pairs
- Use LLM-assisted semantic matching to propose claim-to-evidence links
- Keep proposed links in `_llm_metadata.provenance` and confirmed links in
  `provenance_links`
- Support stale-link review with visual verification, semantic re-evaluation,
  acknowledgment, and removal
- Semantic re-evaluation MUST never auto-confirm; replacement matches return
  as reviewable proposals and blocked repairs surface via status/review
- Keep review listing read-only; all mutations happen through explicit CLI
  commands

**Acceptance Criteria:**
- [ ] `folio provenance` generates reviewable proposals on confirmed
  `supersedes` pairs
- [ ] `folio provenance review` is a read-only listing surface with stable IDs
- [ ] Mutation actions are available through explicit CLI subcommands
- [ ] Confirmed links persist through refresh and support stale detection /
  repair
- [ ] Blocked repairs surface explicitly; they do not silently disappear

#### FR-510: Context Command
```bash
folio context init --client <name> --engagement <name> [--target <path>]
```

- Create an engagement context document at the canonical library path
- Populate ontology-aligned frontmatter (`type: context`, `subtype: engagement`)
- Generate a complete human-editable template with required body sections
- Register the context document in `registry.json` as a source-less managed row
- Reject duplicate creation (error if context doc already exists at that path)
- Context documents are first-class registry citizens but do not participate in
  `folio scan` (no source to track) or `folio refresh` (no conversion to redo)
- `folio enrich` and `folio provenance` skip context docs in v1

**Acceptance Criteria:**
- [ ] `folio context init` creates a valid context document at the canonical path
- [ ] Context doc appears in `registry.json` with `type: context` and `subtype: engagement`
- [ ] Context doc is visible in `folio status` output with per-type summary
- [ ] Duplicate `folio context init` for the same client/engagement is rejected
- [ ] `folio scan`, `folio refresh` do not crash on libraries containing context rows
- [ ] Frontmatter validator accepts valid context docs and rejects malformed ones

---

### 2.6 LLM Provider Configuration (FR-600) — P1

#### FR-601: Multi-Provider Support

Folio SHALL support Anthropic, OpenAI, and Google Gemini for slide analysis.

#### FR-602: Bring Your Own Credentials

Folio SHALL accept provider credentials through environment variables referenced by configuration, and SHALL NOT require raw secrets in `folio.yaml`.

#### FR-603: Named LLM Profiles

Folio SHALL support named LLM profiles containing:
- Provider
- Model
- Environment variable reference for credentials

#### FR-604: Task Routing

Folio SHALL support route-based selection of LLM profiles by task:
- `routing.default` defines the fallback route for unspecified tasks
- `routing.convert` controls the `folio convert` analysis path in v1.0
- `routing.ingest` controls the `folio ingest` analysis path in v1.0
- `routing.enrich` controls the `folio enrich` analysis path in v1.0
- `routing.provenance` controls the `folio provenance` analysis path
- `--llm-profile` overrides route-based selection for a single command invocation

#### FR-605: Optional Transient Fallback

Folio SHALL support configured fallback chains for transient provider failures only.

#### FR-606: Execution Transparency

Folio SHALL record internal LLM execution metadata in output frontmatter, including the requested profile, actual provider/model used, fallback activation, Pass 2 status, and provenance-matching metadata in `_llm_metadata.provenance` when `folio provenance` runs.

#### FR-607: Graceful Degradation with Explicit Flagging

Folio SHALL degrade to pending analysis without failing document processing
when analysis cannot run because of missing credentials, missing SDKs,
provider rejection, or exhausted transient fallbacks.

When degradation occurs, the system SHALL:
- Set `review_status: flagged` in frontmatter
- Add `analysis_unavailable` to `review_flags`
- Set `extraction_confidence: null`
- Display a visible warning in the markdown body (not just a placeholder)

The command still succeeds, but the output is explicitly marked as incomplete.
A document with pending analysis must never appear identical to a fully
analyzed document when browsing in Obsidian or querying via Dataview.

---

### 2.7 Trust & Reviewability (FR-700) — P0 CRITICAL

These requirements ensure that Folio's output meets the quality bar for
professional engagement use. They apply to all LLM-generated content across all
pipeline paths (conversion, ingestion, enrichment).

#### FR-701: Source Grounding

Every LLM-extracted claim SHALL include source grounding:
- A verbatim quoted text span (10-100 characters) from the source material
- The element type the quote came from (title, body, note, chart label, or
  interaction utterance)
- A per-claim confidence level (high, medium, low)

Quoted spans SHALL be validated against extracted text. If the quoted span does
not appear in the source material (case-insensitive, whitespace-normalized
fuzzy match), the claim SHALL be flagged as `unvalidated`.

**Acceptance Criteria:**
- [ ] Every LLM claim includes a quoted source span
- [ ] Validation correctly identifies matching and non-matching quotes
- [ ] Unvalidated claims are flagged, not silently discarded

When confirmed `supersedes`-linked evidence pairs exist, `folio provenance`
extends this grounding model across documents by linking a source claim to a
specific target evidence entry with confidence and rationale.

#### FR-702: Extraction Confidence Scoring

Every document SHALL carry an aggregate `extraction_confidence` score (0.0-1.0)
computed from per-claim confidence levels:
- All claims high-confidence and validated: confidence approaches 1.0
- Mix of high and medium: confidence in 0.6-0.8 range
- Any low-confidence or unvalidated claims: confidence below 0.6
- No LLM analysis: `null`
- Whole-document source-text validation unavailable (for example, scanned PDFs
  with zero extracted text): confidence remains non-null and directionally
  meaningful when analysis succeeded; unavailable validation is not treated as
  failed validation

The exact scoring formula is an implementation detail and may be calibrated over
time. The requirement is that the score exists, is queryable, and is
directionally meaningful.

**Acceptance Criteria:**
- [ ] Every analyzed document has a non-null `extraction_confidence`
- [ ] Confidence is queryable via Dataview (`WHERE extraction_confidence < 0.7`)
- [ ] Confidence correlates with actual extraction quality on ground-truth fixtures
- [ ] Documents with unavailable source-text validation still receive a
  meaningful non-null confidence score when analysis succeeded

#### FR-703: Review Status Tracking

Every document SHALL carry a `review_status` field orthogonal to both
`curation_level` and `authority`:

| Status | Meaning |
|--------|---------|
| `clean` | No issues detected by the system |
| `flagged` | System detected issues requiring human attention |
| `reviewed` | Human has reviewed and confirmed the content |
| `overridden` | Human has corrected system output |

The system SHALL automatically set `review_status: flagged` when:
- Any extraction claim is unvalidated (quoted span not found in source)
- Any extraction claim has low confidence
- Analysis was unavailable (degraded conversion)
- Source-text validation was unavailable for the whole document (for example,
  scanned PDFs with zero extracted text)
- Extraction confidence is below a configurable threshold (default: 0.6)

Humans update `review_status` to `reviewed` or `overridden` manually or via
`folio promote` (promotion to L1+ may require `review_status != flagged`).

**Acceptance Criteria:**
- [ ] `review_status` is populated on every document
- [ ] Auto-flagging triggers on the defined conditions
- [ ] `folio status` reports flagged document count

#### FR-704: Review Flags

Every document SHALL carry a `review_flags` list that enumerates specific
issues detected by the system:

Example flags:
- `analysis_unavailable` — LLM analysis could not run
- `low_confidence_slide_N` — slide N has low-confidence extractions
- `unvalidated_claim_slide_N` — slide N has a quoted span that doesn't match source
- `low_confidence_claim_N` — interaction claim N has low-confidence extraction
- `unvalidated_claim_N` — interaction claim N has a quoted span that doesn't match source
- `text_validation_unavailable_slide_N` — slide N had no extracted text to
  validate against
- `text_validation_unavailable` — document-level text validation was
  unavailable
- `zero_text_extraction` — every reviewable slide lacked extractable text, so
  the document is flagged for review even if claim confidence remains high
- `high_density_unanalyzed` — dense slide only received single-pass analysis

Review flags are machine-generated. Humans clear them by resolving the
underlying issue or by setting `review_status: reviewed`.

**Acceptance Criteria:**
- [ ] Flags are specific and actionable (include slide numbers where applicable)
- [ ] Flags are queryable via Dataview
- [ ] Clearing `review_status` to `reviewed` does not delete the flags (they remain as historical record)

#### FR-705: Human Override Persistence

When a human corrects an extraction in the markdown body, that correction SHALL
persist across re-conversion (`folio refresh`).

Implementation: the system SHALL maintain a `.overrides.json` sidecar file per
deck that records which sections have been manually edited. During re-conversion,
the pipeline SHALL preserve overridden sections rather than regenerating them.

When an override is active:
- `review_status` SHALL be set to `overridden`
- The overridden sections SHALL be clearly marked in the markdown body
- Re-conversion SHALL warn (not error) that overrides were preserved

**Acceptance Criteria:**
- [ ] Manual edits to analysis sections survive `folio refresh`
- [ ] Overrides are recorded in `.overrides.json`
- [ ] `review_status: overridden` is set when overrides exist
- [ ] User can clear overrides to allow regeneration

#### FR-706: Extraction Provenance

Every LLM extraction SHALL record provenance metadata sufficient to answer
"which model produced this claim, when, and how":
- Model identifier (provider + model name)
- Extraction method (vision analysis, text extraction, OCR)
- Pass number (1 = breadth, 2 = depth)
- Timestamp

This metadata extends the existing `_llm_metadata` block in frontmatter.
Per-slide provenance is recorded in the markdown body alongside evidence blocks.
Document-level provenance remains in `_llm_metadata`.

`folio provenance` extends extraction provenance to cross-document
claim-to-evidence lineage:
- confirmed links live in `provenance_links`
- machine proposals and repair metadata live in `_llm_metadata.provenance`
- refresh preserves both structures while clearing stale pair fingerprints

**Acceptance Criteria:**
- [ ] Every extraction is traceable to a specific model and pass
- [ ] Provenance is recorded, not reconstructed
- [ ] Re-conversion with a different model produces updated provenance

---

## 3. Non-Functional Requirements

### 3.1 Performance & Quality (NFR-100)

Quality is a hard floor. Speed and cost are soft targets tracked for
transparency but never used to gate or throttle quality.

| Requirement | Type | Target |
|-------------|------|--------|
| Extraction accuracy | Hard floor | 99%+ character accuracy for text; directionally accurate for LLM claims |
| Image extraction | Hard floor | 100% of slides captured |
| Source path validity | Hard floor | 100% of paths resolvable |
| Conversion speed (no LLM) | Soft target | <30 seconds for 20-slide deck |
| Conversion speed (with LLM) | Soft target | Tracked, not capped. Multi-pass and validation may increase time. |
| Batch processing | Soft target | Tracked, not capped. |
| Status command | Soft target | <5 seconds for 500-deck library |
| LLM cost per deck | Tracked | Logged in `_llm_metadata` for auditability. Never gates quality decisions. |

### 3.2 Reliability (NFR-200)

| Requirement | Target |
|-------------|--------|
| Text extraction accuracy | 99%+ character accuracy |
| Image extraction | 100% of slides captured |
| Source path validity | 100% of paths resolvable |
| Crash recovery | Never corrupt existing conversions |
| Human override safety | Never silently overwrite human corrections |

### 3.3 Portability (NFR-300)

| Requirement | Target |
|-------------|--------|
| Path compatibility | Works on macOS, Linux, Windows |
| Sync compatibility | Works with OneDrive, Dropbox, iCloud |
| Obsidian compatibility | Opens as vault with no errors |

### 3.4 Usability (NFR-400)

| Requirement | Target |
|-------------|--------|
| Zero config start | Basic conversion works without config file |
| Error messages | Actionable (what failed, how to fix) |
| Progress feedback | Long operations show progress |
| Review surfacing | Flagged documents visible in `folio status` and Dataview queries |

---

## 4. Data Schemas

### 4.1 Markdown Output Format

```markdown
---
id: clienta_ddq126_evidence_20260210_market-sizing
title: Market Sizing Analysis
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
source_type: deck
version: 2
converted: 2026-01-10T14:30:00Z
client: ClientA
engagement: Due Diligence Q1 2026
type: evidence
subtype: research
status: current
authority: captured
curation_level: L0
frameworks:
  - 2x2-matrix
slide_types:
  - executive-summary
  - framework
tags:
  - market-sizing
review_status: clean
review_flags: []
extraction_confidence: 0.91
grounding_summary:
  total_claims: 8
  high_confidence: 6
  medium_confidence: 2
  low_confidence: 0
  validated: 8
  unvalidated: 0
_llm_metadata:
  convert:
    requested_profile: high_quality_anthropic
    profile: high_quality_anthropic
    provider: anthropic
    model: claude-sonnet-4-20250514
    fallback_used: false
    status: executed
    pass2:
      status: skipped
      reason: pass_disabled
---

# Market Sizing Analysis

**Source:** `../../../sources/ClientA/Project1/market_sizing.pptx`  
**Version:** 2 | **Converted:** 2026-01-10  
**Status:** ✓ Current

## Recent Changes

| Slides Modified | Slides Added | Slides Removed |
|-----------------|--------------|----------------|
| 2, 5 | — | — |

**Note:** Updated market size figures per client feedback

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Executive Summary
> 
> The total addressable market is $2.3B, growing at 12% CAGR
> - North America represents 45% of market
> - APAC is fastest growing region (18% CAGR)

### Analysis

**Slide Type:** executive-summary  
**Framework:** None  
**Key Data:** $2.3B TAM, 12% CAGR, 45% North America, 18% APAC growth  
**Main Insight:** Large and growing market with APAC as key growth driver

**Evidence:**
- **TAM identification (high):** "total addressable market is $2.3B" *(body)*
- **Growth rate (high):** "growing at 12% CAGR" *(body)*
- **Regional split (high):** "North America represents 45% of market" *(body)*
- **Growth driver (medium):** "APAC is fastest growing region (18% CAGR)" *(body)*

---

## Slide 2 *(modified)*

![Slide 2](slides/slide-002.png)

### Text (Verbatim)

> Market Segmentation
> 
> [2x2 matrix content...]

### Analysis

**Slide Type:** framework  
**Framework:** 2x2-matrix  
**Visual Description:** X-axis: Market Size (Small → Large), Y-axis: Growth Rate (Low → High). Four quadrants: TL=Niche, TR=Stars, BL=Dogs, BR=Cash Cows. Company positioned in "Stars" quadrant.  
**Key Data:** Market size ranges $100M-$5B, growth rates 2%-25%  
**Main Insight:** Company is well-positioned in high-growth, large-market segment

**Evidence:**
- **Framework identification (high):** "Market Segmentation" *(title)*
- **Positioning claim (medium):** "Company positioned in Stars quadrant" *(body, inferred from visual)*

---

## Version History

| Version | Date | Changes | Note |
|---------|------|---------|------|
| v2 | 2026-01-10 | 2 modified | Updated market size figures |
| v1 | 2026-01-05 | Initial (5 slides) | First conversion |
```

Interaction notes are a second shipped output family. They use ontology-native
interaction frontmatter rather than evidence shims:
- `type: interaction`
- `source_transcript` and `source_hash`
- optional `participants`, `duration_minutes`, and `source_recording`
- `impacts: []` at L0
- interaction-specific body sections: `## Summary`, `## Key Findings`,
  `## Entities Mentioned`, `## Quotes / Evidence`, `## Impact on Hypotheses`,
  and a collapsed raw-transcript callout

### 4.2 Configuration Schema (folio.yaml)

```yaml
# Folio Configuration
version: 1

library_root: ./library

sources:
  - name: client-materials
    path: ../client_materials
    target_prefix: ""  # Maps to library root
    
  - name: internal
    path: ../internal
    target_prefix: Internal/
    
  - name: research
    path: /absolute/path/to/research
    target_prefix: Research/

llm:
  profiles:
    high_quality_anthropic:
      provider: anthropic
      model: claude-sonnet-4-20250514
      api_key_env: ANTHROPIC_API_KEY

    fast_openai:
      provider: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

    backup_google:
      provider: google
      model: gemini-2.5-pro
      api_key_env: GEMINI_API_KEY

  routing:
    default:
      primary: high_quality_anthropic
      fallbacks: []
    convert:
      primary: high_quality_anthropic
      fallbacks: [backup_google]
    ingest:
      primary: high_quality_anthropic
      fallbacks: [backup_google]

conversion:
  image_dpi: 150
  image_format: png
  libreoffice_timeout: 60
  default_passes: 1
  density_threshold: 2.0
  pptx_renderer: auto
  review_confidence_threshold: 0.6  # Below this, auto-flag for review
```

Legacy shorthand remains valid for Anthropic-only setups:

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
```

---

## 5. Constraints and Assumptions

### 5.1 Technical Constraints

- PPTX→PDF conversion uses LibreOffice (Linux, unmanaged macOS) or Microsoft
  PowerPoint (managed macOS with `pptx_renderer: powerpoint`)
- Poppler required for PDF→image conversion
- Python 3.10+
- Credential and SDK for the selected LLM provider/profile when AI analysis is enabled
- Supported providers: Anthropic, OpenAI, Google Gemini

### 5.2 Assumptions

- Users have Obsidian installed (or compatible markdown viewer)
- Source files are not password-protected
- Sufficient disk space (~100KB per slide for images)
- Network access for LLM API calls
- Provider credentials are managed through environment variables, not committed config
- Quality and accuracy take precedence over cost and processing time in all design decisions

### 5.3 Platform Support

| Platform | Support Level |
|----------|---------------|
| macOS | Full |
| Linux | Full |
| Windows | Best effort (path handling may need testing) |
