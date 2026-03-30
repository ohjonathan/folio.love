---
id: folio_context_docs_tier3_closeout_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-03-29
revision: 1
revision_note: |
  Initial approval spec for PR E: context documents, Tier 3 lifecycle
  integration coverage, and the Tier 3 closeout validation package.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - folio_ontology_architecture
  - tier3_baseline_decision_memo_20260327
  - folio_enrich_production_test_report
  - tier3_kickoff_checklist
  - folio_provenance_spec
---

# Context Docs + Tier 3 Closeout Spec (PR E)

## 1. Overview

This spec defines **PR E**, the final Tier 3 slice:

1. engagement context documents
2. a synthetic end-to-end Tier 3 lifecycle integration test
3. the Tier 3 closeout validation package

This is the **approval spec**, not the implementation prompt.

PR E lands the last missing Tier 3 capability named in the roadmap:

- engagement scaffolding through a first-class `context` note
- proof that the shipped Tier 3 surfaces work together in one library
- a closeout package that evaluates the Tier 3 exit criteria against evidence

The deliverable is a new spec document at:

- `docs/specs/folio_context_docs_tier3_closeout_spec.md`

---

## 2. Why This Slice Comes Last

PR E is intentionally the integration and closeout slice, not a foundational
pipeline slice.

By the time PR E starts, the Tier 3 baseline is:

- `folio ingest` shipped
- entity registry and ingest-time entity resolution shipped
- `folio enrich` shipped and production-tested
- retroactive provenance shipped on `main` via PR #39

What remains is the missing engagement anchor and the proof package:

- there is still no single note that defines what an engagement is
- there is still no Tier 3 integration test that exercises the shipped
  registry, entity, enrich, provenance, and status flows together
- there is still no Tier 3 closeout package that evaluates the roadmap exit
  criteria against the real production baseline plus the final context-doc
  addition

PR E closes those gaps without widening scope into Tier 4 behavior.

---

## 3. Goals

### 3.1 Product goals

PR E must:

1. add an engagement-scaffolding note type that is human-authored and
   ontology-native
2. provide a lightweight CLI entry point for creating that scaffolding note
3. make context docs first-class managed library documents, visible to
   registry-backed status flows
4. prove that the shipped Tier 3 capabilities work together in one synthetic
   library
5. define the exact closeout artifacts and evidence required to declare Tier 3
   complete or partially complete

### 3.2 Technical goals

PR E must:

1. keep context docs source-less and non-LLM
2. generalize `registry.json` to handle source-less managed docs
3. keep `folio scan`, `folio enrich`, and `folio provenance` narrowly scoped
   rather than turning context docs into new consumers
4. extend validation tooling so context docs are real schema citizens rather
   than evidence-note exceptions
5. reuse the current test style: `tmp_path`, real file I/O, mocked external
   LLM or rendering boundaries, and `CliRunner` where appropriate

---

## 4. Non-Goals

The following are explicitly out of scope for PR E:

| Item | Why deferred |
|------|--------------|
| `client_profile` or `workstream` creation CLI | The ontology allows these subtypes, but PR E CLI v1 is engagement-only. |
| LLM-generated context docs | Context is human-authored scaffolding, not generated output. |
| Auto-populating team, stakeholder, or hypothesis sections from the registry | The command creates a template only. Humans fill the content. |
| A new top-level `context` frontmatter field on all other notes | v1 uses implicit linkage through shared `client` and `engagement`. |
| Context-aware enrich proposals | Tier 4 sophistication. PR E keeps `folio enrich` context-blind. |
| Context-aware provenance seeding | Provenance remains evidence-only in v1. |
| Converting a PPTX or PDF as part of the new Tier 3 lifecycle integration test | Converter integration already has broad coverage elsewhere; PR E's lifecycle test focuses on Tier 3 surfaces. |
| Dataview-specific closeout validation requirements | Closeout targets core mixed-library behavior in Obsidian, not plugin-specific queries. |
| A registry.json top-level key rename away from `decks` | Backward compatibility wins. Row semantics are generalized; container naming is not changed in PR E. |

---

## 5. Current Baseline And Governance

### 5.1 Authoritative baseline

For PR E planning and implementation, treat **PR #39 provenance as merged
baseline**.

Evidence:

- `main` includes merge commit `faf499a`
- the provenance spec is already present
- the local codebase already contains the `folio provenance` CLI and tests

### 5.2 Stale status surfaces

Some live docs still speak as if PR D is pending. PR E must treat those lines
as stale status language, not authoritative sequencing:

- `docs/validation/tier3_kickoff_checklist.md`
  - still says PR D is the next feature slice
  - still leaves the PR D checklist item unchecked
- `docs/product/04_Implementation_Roadmap.md`
  - still marks provenance as the next feature slice in the status table

The historical baseline memo is still useful context, but it is not the
sequencing authority for PR E. The roadmap, kickoff tracker, and merged code
state are the operational source of truth.

### 5.3 Production baseline relevant to PR E

Existing production evidence already available before PR E:

- retained `anthropic_sonnet4` production library plus 12 blind-validated
  `haiku45` merges
- `folio enrich` production run on 115 eligible notes with 0 failures
- confirmed `supersedes` links and generated `## Related` sections
- large entity stub layer added after the production enrich run
- real vault validation already passed on the production library

What is still missing from that production baseline:

- no context docs
- no interaction-heavy production validation package
- no Tier 3 closeout package

---

## 6. Key Decisions

### D1: Context docs are first-class managed docs, but CLI v1 is `subtype: engagement` only

The ontology defines three context subtypes:

- `engagement`
- `client_profile`
- `workstream`

PR E CLI scope is deliberately narrower:

- `folio context init` creates only `type: context`, `subtype: engagement`

`client_profile` and `workstream` remain valid ontology concepts, but they are
manual/future paths, not CLI-generated artifacts in v1.

### D2: Add a new CLI surface: `folio context init`

PR E adds:

```bash
folio context init --client <name> --engagement <name> [--target <path>]
```

Behavior:

- creates a markdown template only
- does not run an LLM
- does not inspect or mutate slide, transcript, or provenance data
- does not open an editor
- fails if the resolved target file already exists
- writes the new note into the library and immediately registers it

### D3: Default path is canonical and local to the engagement

Default output path:

```text
<library_root>/<client-token>/<engagement-short>/_context.md
```

This keeps the context doc beside the engagement corpus rather than in a
central `_context/` directory.

Path rules:

- `<client-token>` uses the same path sanitization rules already used in the
  codebase
- `<engagement-short>` uses the existing engagement-short derivation helper
- the filename is always `_context.md`

`--target` rules:

- if `--target` ends in `.md`, write exactly to that file path
- otherwise treat `--target` as a directory and write `_context.md` inside it
- all target modes still fail if the final markdown path already exists

### D4: Context IDs are deterministic and date-based

Context IDs use a deterministic date-based pattern:

```text
<client-token>_<engagement-short>_context_<YYYYMMDD>_engagement
```

The date is the local command date when `folio context init` is run.

Example:

```text
us_bank_techresiliencedd_context_20260329_engagement
```

This makes the ID pattern explicit and resolves the current roadmap/ontology
ambiguity around whether context docs are date-bearing or date-free.

### D5: Context frontmatter is ontology-aligned and source-less

Required frontmatter for PR E context docs:

- `id`
- `title`
- `type: context`
- `subtype: engagement`
- `status: active`
- `authority: aligned`
- `curation_level: L1`
- `review_status: clean`
- `review_flags: []`
- `extraction_confidence: null`
- `client`
- `engagement`
- `tags`
- `created`
- `modified`

Optional frontmatter:

- `industry`
- `service_line`

Explicitly excluded:

- `source`
- `source_hash`
- `source_type`
- `slide_count`
- `version`
- `converted`
- `grounding_summary`
- `_llm_metadata`
- any new top-level `context` field

Rationale:

- context docs are human-authored and source-less
- they are not extracted or analyzed content
- `review_status: clean` and `review_flags: []` satisfy the universal review
  surface without inventing warnings for a manual scaffold
- `extraction_confidence: null` records that no LLM extraction occurred

### D6: Rich engagement content belongs in the body, not new canonical metadata fields

PR E does **not** introduce new canonical top-level frontmatter fields for:

- client background narrative
- SOW summary text
- timeline bullets
- team roster details
- stakeholder roster details
- starting hypotheses
- risks and open questions

Those belong in the markdown body so humans can maintain them directly without
expanding the canonical schema.

### D7: The template must be complete and human-editable on first write

`folio context init` writes a fully structured template with the required body
sections already present.

Required body sections:

1. Client Background
2. Engagement Snapshot
3. Objectives / SOW
4. Timeline
5. Team
6. Stakeholders
7. Starting Hypotheses
8. Risks / Open Questions

Team and stakeholder entries are written as list items intended to hold entity
wikilinks, for example `[[Jane Smith]]`.

### D8: Linkage is implicit in v1

PR E chooses **implicit context linkage** in v1:

- no new `context` field on evidence, interaction, analysis, or deliverable
  docs
- no automatic `depends_on` insertion into evidence or interaction docs
- other docs are considered in the same engagement context when they share
  `client` and `engagement`

Human-authored relationship fields remain allowed where the ontology already
permits them. PR E simply does not make them mandatory or machine-managed.

### D9: `registry.json` becomes a generic managed-document index

PR E generalizes the registry model:

- keep the top-level container shape unchanged for compatibility
- bump the registry schema version because row shape changes to support
  source-less managed docs
- context docs live in `registry.json` alongside evidence and interaction
  docs
- source-backed fields become optional at the row level
- add `subtype` to the stored row shape so context rows round-trip cleanly

For `type: context` rows:

- `id`, `title`, `markdown_path`, `deck_dir`, `type`, `subtype`, `client`,
  `engagement`, `authority`, `curation_level`, `modified`,
  `review_status`, `review_flags`, `extraction_confidence`, and
  `staleness_status` are stored
- `source_relative_path`, `source_hash`, `source_type`, `version`, and
  `converted` are absent or null
- `staleness_status` is `current` while the note exists and `missing` if the
  note file is gone

### D9A: Required registry schema and compatibility changes

PR E is not implementable without explicit registry-contract changes. These
are part of the approved scope, not implementation discretion.

Required registry model changes:

- increment `registry._SCHEMA_VERSION` from `1` to `2`
- add `subtype: Optional[str] = None` to `RegistryEntry`
- make `source_relative_path`, `source_hash`, `version`, and `converted`
  `Optional[...]` fields with defaults so source-less context rows can be
  constructed without positional crashes
- keep `source_type` optional; context rows leave it unset
- context rows must persist explicit `type: context` and `subtype`;
  `_infer_missing_entry_type()` is not the recovery mechanism for them
- `to_dict()` may continue omitting `None` values, but `entry_from_dict()`
  must reconstruct context rows successfully when those source-backed keys are
  absent
- `entry_from_dict()` must continue loading schema-v1 evidence and
  interaction rows without a one-shot migration
- `reconcile_from_frontmatter()` must reconcile `subtype`, `review_status`,
  and `review_flags` for context rows and only reconcile
  `source_relative_path` when a real source field exists in frontmatter

Required rebuild behavior:

- `rebuild_registry()` must recognize `type: context` notes even when they
  have no `source`, `source_transcript`, or `source_hash`
- corruption-recovery rebuilds reached via `upsert_entry()`, `folio status`,
  `folio scan`, and `folio refresh` must preserve context rows instead of
  silently dropping them
- standalone diagrams remain excluded; PR E is not broadening rebuild to
  every source-less markdown type

Required call-site guards:

- `refresh_entry_status()` must treat source-less rows as file-presence-only:
  `current` if the markdown note exists, `missing` if it does not
- `refresh_entry_status()` must never call `check_staleness()` for a
  source-less row
- `resolve_entry_source()` remains source-backed only; callers must guard
  before invoking it
- `folio status --refresh` must bypass source hashing for context rows
- `folio scan` must exclude source-less rows from source lookup,
  stale-source comparison, and missing-source reporting
- `folio refresh` must skip context rows before staleness refresh and before
  source resolution
- `status` and `scan` missing-source sections must never print
  `source: None`

Compatibility posture:

- a one-shot migration script is not required if schema-v1 rows keep loading
  and schema-v2 is written lazily on the next save or rebuild
- the implementation prompt must audit every direct `RegistryEntry(...)`
  constructor and every `entry.source_*` access touched by this contract

### D10: `status` shows context docs; `scan` ignores them safely; `refresh` skips them safely

PR E command behavior:

- `folio status`
  - counts context docs in total library counts
  - continues to print current/stale/missing summaries
  - adds a per-type summary line when more than one managed document type is
    present in scope
  - `folio status --refresh` refreshes source-backed rows only and treats
    context rows as file-presence-only entries rather than hashing sources
- `folio scan`
  - remains a source-root discovery tool only
  - does not attempt to discover context docs from source roots
  - ignores context rows already present in `registry.json` when building
    source lookups and missing-source lists
  - must complete without crashing or printing `_context.md` as a bogus
    source-backed entry
- `folio refresh`
  - explicitly skips `type: context`
  - prints guidance similar to the current interaction skip behavior
  - skips context before any staleness refresh or source-path resolution call
  - does not try to synthesize source-backed staleness for context docs

### D11: `folio enrich` and `folio provenance` do not consume context docs in v1

PR E keeps these boundaries explicit:

- `folio enrich` remains eligible for `evidence` and `interaction` only
- `folio provenance` remains evidence-only and `supersedes`-driven
- context docs are registry-visible but not enrichment or provenance inputs

This keeps the slice narrow and avoids turning PR E into context-aware graph
reasoning.

### D12: Validation tooling must treat context as a real first-class type

The current validation script at `tests/validation/validate_frontmatter.py`
nominally allows `type: context`, but it still routes every non-interaction,
non-diagram note through evidence validation.

PR E must fix that.

Validator changes required:

- add a dedicated context validation branch before the evidence fallback
- allow `subtype: engagement` in the new branch
- require the source-less context frontmatter contract defined here,
  including `review_status: clean`, `review_flags: []`, and
  `extraction_confidence: null`
- ensure the required body sections are present
- stop requiring evidence-only or interaction-only fields on context docs:
  `source`, `source_hash`, `source_type`, `slide_count`, `version`,
  `converted`, `source_transcript`, `date`, and `impacts`
- stop requiring evidence-only generated-content fields on context docs:
  `grounding_summary` and `_llm_metadata`

---

## 7. Context Document Design

### 7.1 CLI contract

```bash
folio context init --client <name> --engagement <name> [--target <path>]
```

Required options:

- `--client`
- `--engagement`

Optional:

- `--target`

Behavior:

- resolve target path
- derive context ID
- write the template markdown file
- upsert the new context row into `registry.json`
- print the final path and ID

Failure cases:

- target file already exists
- resolved target path escapes the library root when default routing is used
- registry update fails

### 7.2 Frontmatter example

```yaml
---
id: us_bank_techresiliencedd_context_20260329_engagement
title: "US Bank Tech Resilience DD - Engagement Context"
type: context
subtype: engagement
status: active
authority: aligned
curation_level: L1
review_status: clean
review_flags: []
extraction_confidence: null
client: US Bank
engagement: Tech Resilience DD
industry: []
service_line: ""
tags:
  - engagement-context
created: 2026-03-29
modified: 2026-03-29
---
```

Rules:

- `tags` must always be present as a list
- `industry` may be an empty list
- `service_line` may be omitted if blank in the final human-edited note
- `review_status` and `review_flags` use fixed clean defaults in v1
- `extraction_confidence` is explicit `null` because no LLM extraction occurs
- `created` and `modified` use local date format `YYYY-MM-DD`

### 7.3 Full template example

```md
---
id: us_bank_techresiliencedd_context_20260329_engagement
title: "US Bank Tech Resilience DD - Engagement Context"
type: context
subtype: engagement
status: active
authority: aligned
curation_level: L1
review_status: clean
review_flags: []
extraction_confidence: null
client: US Bank
engagement: Tech Resilience DD
industry: []
service_line: ""
tags:
  - engagement-context
created: 2026-03-29
modified: 2026-03-29
---

# US Bank Tech Resilience DD - Engagement Context

## Client Background

TBD.

## Engagement Snapshot

- Engagement name: Tech Resilience DD
- Engagement type: TBD
- Current phase: TBD

## Objectives / SOW

- TBD

## Timeline

- Kickoff: TBD
- Key milestones: TBD
- Decision date: TBD

## Team

- Engagement lead: [[TBD]]
- Team members:
  - [[TBD]]

## Stakeholders

- Client sponsor: [[TBD]]
- Key stakeholders:
  - [[TBD]]

## Starting Hypotheses

- TBD

## Risks / Open Questions

- TBD
```

Template rules:

- body headings are fixed
- placeholder content is explicit rather than omitted
- `Engagement type` should be replaced with a firm-local taxonomy value such
  as `diligence`, `strategy`, `transformation`, `PMO`, or `other`
- no `## Related` section is generated
- no `_llm_metadata` block is generated

### 7.4 Registry behavior

Creating a context doc must:

- write the markdown file
- bootstrap or load `registry.json`
- add or update the context entry immediately
- overwrite an existing `missing` context row with the same ID if the note is
  recreated

Rebuilding the registry must:

- recognize context notes without source fields
- include them in the registry during normal bootstraps and
  corruption-recovery rebuilds
- preserve `subtype` and the fixed review defaults
- avoid forcing fake source hashes or fake source paths
- continue excluding standalone diagram notes

Registry compatibility requirements:

- schema-v2 is the first registry version that may contain source-less
  managed rows
- schema-v1 evidence and interaction rows remain readable
- context rows must round-trip through `to_dict()` and `entry_from_dict()`
  even when source-backed keys are omitted entirely

### 7.5 Status and refresh behavior

`folio status` must display context docs as managed documents, and
`folio status --refresh` must not crash when a context row is present.

Expected shape in a mixed library:

```text
Library: 5 documents
  By type: evidence 2, interaction 1, context 1, analysis 1
  ✓ Current: 5
```

Exact spacing is implementation-defined, but the per-type summary behavior is
not.

`folio scan` must complete without listing context docs as new, stale, or
missing sources.

`folio refresh` on a context row must produce an explicit skip message rather
than silently ignoring it.

---

## 8. Tier 3 Lifecycle Integration Test

### 8.1 Purpose

PR E adds a new dedicated integration test that proves the shipped Tier 3
surfaces can coexist in one synthetic library.

This is **not** a converter integration test and does not replace converter
coverage. It is a Tier 3 system-integration test.

### 8.2 Scenario

The primary scenario is:

1. create synthetic source files for two evidence notes and one transcript
   under configured source roots
2. `folio context init`
3. seed two synthetic evidence notes whose newer note carries canonical
   `supersedes: <older_note_id>` and deterministic evidence blocks
4. `folio entities import <csv>`
5. confirm any entities needed for resolution
6. `folio ingest` on a transcript fixture that mentions those entities
7. `folio entities generate-stubs`
8. `folio enrich`
9. `folio provenance`
10. `folio provenance confirm-doc <newer_note_id> --target <older_note_id>`
11. `folio status --refresh`
12. `folio scan`
13. `folio refresh`
14. final `folio status`

### 8.3 Why the test seeds evidence notes instead of calling `folio convert`

PR E chooses synthetic seeded evidence notes rather than invoking
`folio convert` inside the new Tier 3 lifecycle test because:

- converter integration already has extensive dedicated coverage
- Tier 3 closeout risk is in the registry/entity/enrich/provenance layering,
  not slide rendering
- the seeded notes can encode the exact `supersedes` and evidence-block shapes
  required for deterministic provenance assertions

This keeps the test stable and focused on the PR E problem.

### 8.4 Fixtures

Reuse existing fixtures where possible:

- `tests/fixtures/test_org_chart.csv`
- an existing transcript fixture pattern with entity mentions

Add only the minimal new synthetic fixture content needed for:

- two evidence-source files so `scan` and `refresh` can exercise source-backed
  behavior without real client data
- a context note created by CLI
- two evidence notes in one `supersedes` lineage
- one transcript source whose named entities match confirmed org-chart entries

The new evidence fixtures may live inline in the test file if that keeps the
fixture surface smaller and clearer.

### 8.5 Test mechanics

The test should follow the current integration style:

- `tmp_path` library root
- real markdown and JSON writes
- real registry and entity registry behavior
- mocked external LLM boundaries where needed
- `CliRunner` for command surfaces

### 8.6 Required assertions

The test must assert all of the following:

1. `folio context init` creates `_context.md` at the canonical path
2. the context file has the required frontmatter fields, fixed review
   defaults, and body headings
3. the context file is present in `registry.json` as `type: context`, and the
   stored row round-trips through `entry_from_dict()` without source fields
4. `folio status --refresh` includes the context doc in library counts and
   type summary and completes without crashing
5. `folio scan` ignores context rows, does not emit `_context.md` as a
   bogus source-backed entry, and completes without crashing
6. `folio refresh` skips the context doc explicitly before source resolution
7. interaction ingest resolves confirmed entities into canonical wikilinks
8. entity stubs are created under `_entities/`
9. org hierarchy fields are present on the relevant person stubs
10. `folio enrich` updates the eligible evidence/interaction notes and
    ignores the context doc
11. `folio provenance` creates pair metadata for the canonical
    `supersedes` pair, and `confirm-doc` yields at least one confirmed
    `provenance_links` entry
12. the final library contains the expected mix of context, evidence,
    interaction, and entity-stub files, with the context row still present in
    registry-backed status output

### 8.7 Required supporting unit coverage

PR E also needs targeted unit coverage alongside the lifecycle test.

Minimum unit categories:

- context ID and default-path generation, including path-sanitization and
  target-escape rejection
- `RegistryEntry` round-trip for a source-less context row
- `rebuild_registry()` discovery of context notes and preservation of context
  rows during corrupt-registry recovery
- `refresh_entry_status()` file-presence behavior for source-less rows,
  including `current` and `missing`
- mixed-registry guard behavior in `status --refresh`, `scan`, and `refresh`
- context branch coverage in `tests/validation/validate_frontmatter.py`,
  including evidence-field exemptions
- type-summary counting in `folio status` when context rows coexist with
  source-backed docs

### 8.8 Explicit exclusions

The PR E lifecycle integration test does **not** need to assert:

- a real Obsidian application launch
- Dataview query output
- PPTX/PDF rendering behavior
- promotion flows

Those concerns already have other coverage or belong to the manual closeout
package.

---

## 9. Tier 3 Closeout Validation Package

### 9.1 Required artifacts

PR E defines the required Tier 3 closeout artifacts under `docs/validation/`:

1. `tier3_closeout_report.md`
2. `tier3_closeout_session_log.md`
3. `tier3_closeout_chat_log.md`
4. `tier3_closeout_prompt.md`

If the platform cannot export a literal raw chat log, the chat-log artifact may
be a decision-and-rationale summary that explicitly states where the raw
transcript is preserved and why direct export was not possible.

`tier3_closeout_prompt.md` should preserve the exact validation brief used for
the run: target engagement/library, required commands, required outputs, and
the pass/partial/fail reporting contract.

### 9.2 Report structure

`tier3_closeout_report.md` must include:

1. Run context
2. Executive summary
3. Tier 3 exit-criteria table with `PASS / PARTIAL / FAIL`
4. Evidence for each exit criterion
5. Library-state summary
6. What worked
7. What was awkward
8. Blockers or carried-forward limitations
9. Tier 4 readiness recommendation
10. Artifacts produced

### 9.3 Evidence expectations

The closeout report must use concrete evidence, not high-level narration only.

Expected evidence types:

- command lines actually run
- timings for the real ingest validation
- registry and entity counts
- sample markdown or frontmatter checks
- library-state counts by type
- screenshots or visual observations where appropriate
- links to the earlier production validation artifacts already accepted by the
  repo

Historical artifacts are valid support, but a criterion may only be marked
`PASS` when the closeout also includes at least one closeout-time
corroborating observation from the current production library.

### 9.4 Exit criteria mapping

PR E closeout must evaluate these Tier 3 criteria:

| Criterion | Required evidence |
|-----------|-------------------|
| `folio ingest` converts transcript to structured interaction in <60 seconds | Real timed ingest on the McKinsey machine |
| Entity registry tracks people, departments, systems | `folio entities` output and library entity counts |
| Name resolution works for common cases | Existing shipped behavior plus a closeout-time spot check from the ingest/entity flow on the current library |
| `folio enrich` adds tags and links to existing assets | `folio_enrich_production_test_report.md` plus any follow-on spot checks |
| Retroactive provenance infrastructure works on confirmed `supersedes`-linked evidence pairs | PR #39 baseline plus at least one current closeout-time provenance check on a confirmed `supersedes` pair; without that current pair the criterion cannot be `PASS` |
| Context documents provide engagement scaffolding | A real populated context doc for the target engagement |
| Full engagement lifecycle tested end-to-end | The new synthetic integration test plus the production closeout narrative |

### 9.5 Library-state summary requirements

The closeout report must summarize at least:

- total managed docs
- counts by document type
- entity counts by type
- stub count
- enriched-note count
- confirmed `supersedes` count
- confirmed provenance-link count
- context-doc count

### 9.6 Gate semantics

The closeout report is an assessment artifact, not an automatic stop gate.

It may recommend:

- full Tier 3 closeout
- closeout with explicit carried-forward limitations
- partial closeout with a written waiver into Tier 4

That matches the established Tier 1 and Tier 2 pattern, but PR E still needs
hard-fail rules to keep the closeout falsifiable.

Hard-fail conditions:

- the Tier 3 lifecycle integration test must pass in CI
- `folio status --refresh`, `folio scan`, and `folio refresh` must complete
  without crashing on a mixed library that contains a context row
- production validation must show that a real context doc can be created and
  is registry-visible in `folio status`

If a hard-fail condition is not met, the closeout cannot recommend full Tier 3
closeout. It must be `FAIL` or `PARTIAL` with the blocking condition called
out explicitly.

### 9.7 Anti-rubber-stamp rules

To avoid ceremonial closeout:

- a criterion cannot be `PASS` based only on historical reports
- the provenance criterion cannot be `PASS` when the closeout has zero
  current confirmed `supersedes` pairs available for inspection
- the lifecycle criterion cannot be waived; if the new CI test fails, the
  criterion is `FAIL`

---

## 10. Risks And Compatibility

### 10.1 Registry-contract risk

The highest implementation risk in PR E is the registry contract change.
Source-less context rows touch the shared `RegistryEntry` dataclass and the
command paths that assume every row has `source_relative_path` and
`source_hash`. D9A is therefore a mandatory implementation contract, not an
optimization.

### 10.2 Synthetic lifecycle-test limitation

The lifecycle test intentionally seeds deterministic evidence notes instead of
running `folio convert`. This keeps PR E focused and stable, but it does not
replace converter-to-provenance realism. The mitigation is to keep the
existing converter integration suite intact and require current production
closeout evidence in addition to the synthetic CI test.

### 10.3 Closeout honesty risk

The closeout package can become ceremony if it relies only on earlier reports
or if every miss becomes a waiver. Sections 9.3, 9.4, and 9.6 therefore
require current corroborating evidence and define hard-fail conditions for the
new PR E surfaces.

### 10.4 Compatibility posture

PR E should preserve compatibility with existing source-backed registry rows.
The schema version should advance because the row contract changes, but the
upgrade path is lazy: existing registries may be read in place and rewritten
as schema-v2 on the next save or rebuild.

---

## 11. Design Question Answers

1. **Creation flow**
   - Use `folio context init`.
   - It creates a template only.
   - No LLMs, no editor launch, no auto-filled body content beyond placeholders.

2. **Template content**
   - Fixed frontmatter contract defined in this spec.
   - Fixed body headings defined in this spec.
   - Full example included above.

3. **Location**
   - Place the note beside the engagement corpus:
     `library/<client-token>/<engagement-short>/_context.md`.

4. **Registry integration**
   - Yes.
   - Context docs are first-class managed docs in `registry.json`.

5. **Relationship to other docs**
   - v1 uses implicit linkage via shared `client` and `engagement`.
   - No new `context` field.
   - No auto-written `depends_on`.

6. **Enrichment interaction**
   - `folio enrich` does not consume or reason over context docs in PR E.
   - That is future work.

---

## 12. PRD And Roadmap Implications

PR E requires explicit doc updates after approval.

### 12.1 PRD additions

Add a new FR-400-family block:

- **FR-405: Context Documents**
  - defines the context note type
  - defines the source-less frontmatter contract
  - defines the fixed review defaults for human-authored context docs
  - defines the body template and registry integration

Add a new FR-500-family block:

- **FR-510: Context Init Command**
  - defines `folio context init`
  - defines path, ID, failure, and registration behavior

Amend:

- **FR-403: Registry**
  - registry now tracks source-less context docs
  - registry schema/version guidance must cover source-less rows and rebuild
    compatibility
- **Tier 3 exit criteria status table**
  - provenance should be treated as shipped baseline
  - context docs and lifecycle closeout remain the final open slice until PR E

### 12.2 Roadmap and tracker sync required

After approval, the live corpus must be synced so it no longer says PR D is
pending.

At minimum:

- `docs/product/04_Implementation_Roadmap.md`
- `docs/validation/tier3_kickoff_checklist.md`
- `docs/architecture/Folio_Ontology_Architecture.md` if its context-ID example
  still shows the older date-free pattern

The historical baseline memo does not need to be rewritten as sequencing
authority, but any misleading "next slice" language should be clearly treated
as historical if it remains in place.

---

## 13. Open Questions

No unresolved product-shape questions remain for PR E approval.

Implementation is still blocked, however, unless the schema, validator,
testing, and hard-fail commitments above are accepted as part of scope.

Non-blocking deferred questions:

1. Should a future CLI also create `client_profile` or `workstream` context
   notes?
2. Should a future enrichment pass read context docs as peer context?
3. Should a future PR introduce an explicit `context` field on analysis or
   deliverable notes?
4. Should closeout later add Dataview-specific validation once plugin
   dependency is acceptable?

---

## 14. What Must Be True Before Implementation Starts

1. PR #39 is accepted as merged baseline for PR E.
2. The team accepts source-less, registry-managed context docs as the model.
3. The team accepts implicit context linkage in v1 instead of a new `context`
   field.
4. The team accepts the synthetic evidence-note approach for the new Tier 3
   lifecycle integration test.
5. Validation-tooling updates for `type: context` are included in PR E scope,
   not deferred.
6. The implementation prompt for PR E must include the roadmap/tracker sync
   surfaces that still describe PR D as pending.
7. The registry schema-v2 contract and call-site guards in D9A are accepted
   as required implementation work.
8. The supporting unit coverage in Section 8.7 is included alongside the new
   lifecycle integration test.
9. The closeout hard-fail rules in Section 9.6 are accepted; they are not
   optional report polish.

---

## 15. Output Summary

PR E should deliver three things:

1. `folio context init`, the source-less context-note model, and the
   registry/validator changes that make source-less context rows safe
2. one dedicated Tier 3 lifecycle integration test plus the targeted unit
   coverage needed for registry generalization
3. the Tier 3 closeout package contract and artifact set

That is the complete intended scope for the final Tier 3 PR.
