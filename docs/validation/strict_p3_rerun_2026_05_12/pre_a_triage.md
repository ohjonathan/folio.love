# Pre-A Triage: Strict-P3 GitHub Issues Closeout Rerun

Date: 2026-05-12

Framework: `llm-dev-framework@df39e6e3de47b2b5a970b99aa1580c1463dd97e0`

Repository baseline: `origin/main` at `8fbddf7369684ad5609ec3ac450ce986932f21d9`

Evidence rule: prior `folio_*_v1_*` artifacts and the preserved dirty attempt are implementation history only; they are not lifecycle evidence for this rerun.

## Scope Authority

This artifact was regenerated from live GitHub issue bodies and PR #50 metadata after reopening issues #56, #61, #62, #63, #64, #69, #70, and #71 for strict-P3 verification.

## PR #50 Merge-Readiness Scope

- PR: #50 chore(log): ontos session archive — slices 2 merge, 3, 4

- URL: https://github.com/ohjonathan/folio.love/pull/50

- State: MERGED

- Merged at: 2026-05-12T01:35:07Z

- Merge commit: 8fbddf7369684ad5609ec3ac450ce986932f21d9

- Files: docs/logs/2026-04-15_merge-pull-request-45-from-ohjonathan-feat-propos.md, docs/logs/2026-04-15_v0-6-3-emission-time-rejection-memory-queue-cap.md, docs/logs/2026-04-15_v0-6-4-code-adversarial-codex.md

- Closeout requirement: verify the merged change remains docs-only and the archive logs are present on `main`; no re-merge action is needed because PR #50 is already merged.

## Issue-to-Slice Mapping

| Slice | Issues / PR | Scope |
|---|---|---|

| `folio-github-closeout-v1-0-0` | PR #50, #69 | Verify PR #50 merged/docs-only; verify VTT/SRT support from PR #73; reclose #69 with strict-P3 evidence. |

| `folio-ingest-signals-v1-1-0` | #70, #71 | First-class `action_items`; subtype rendering; deterministic speaker analytics in frontmatter, markdown, and registry. |

| `folio-document-format-coverage-v1-1-1` | #56 | `.docx` conversion through document-oriented MarkItDown path; no slide image extraction; document evidence note and compatibility metadata. |

| `folio-config-defaults-v1-2-0` | #63 | `defaults`/`derive` in `folio.yaml`; metadata resolution order CLI flag -> derivation -> defaults -> error. |

| `folio-correspondence-ingest-v1-3-0` | #61, #64 | Native EML ingest and Message-ID overlap continuation/versioning with `--as-new-entry`. |

| `folio-watch-v1-4-0` | #62 | Watch/drop-zone ingestion routing, stable size waits, success archive, failure quarantine. |

## Live GitHub Issue Records

### Issue #56: folio convert rejects .docx files — normalization gate too narrow

- URL: https://github.com/ohjonathan/folio.love/issues/56

- State at triage: OPEN

- Created: 2026-04-16T16:30:52Z

- Updated: 2026-05-12T19:23:15Z

- Labels: none

#### Body

## Summary

`folio convert` rejects `.docx` files with `Unsupported format: .docx` at the normalization stage, even though `markitdown` (used internally for text extraction) supports DOCX natively.

## Reproduction

```bash
folio convert "./path/to/sow.docx" --client Acme --engagement "Build"
```

```
Converting: sow.docx
  Normalizing to PDF...
✗ Conversion failed: Unsupported format: .docx
```

## Context

Real consulting corpora frequently contain `.docx` artifacts (SOWs, contracts, terms sheets, design documents). Today the workaround is to manually export to PDF via Word, then convert the PDF. This adds an operator step that breaks automation and `folio batch` workflows.

## Suggested behavior

Accept `.docx` at the normalization gate. Since DOCX is not slide-oriented:
- Skip slide image extraction (or render page images via a document renderer)
- Use `markitdown` for full-document text extraction (already works)
- Produce a single evidence note with the full document body rather than per-slide sections

Alternatively, expose a `folio convert --format document` flag that opts into a document-oriented pipeline rather than the slide-oriented one.

## Environment

- folio-love 0.6.4
- macOS 25.4.0
- Python 3.12


### Issue #61: folio ingest: native .eml / email thread support

- URL: https://github.com/ohjonathan/folio.love/issues/61

- State at triage: OPEN

- Created: 2026-04-17T04:29:35Z

- Updated: 2026-05-12T19:23:17Z

- Labels: none

#### Body

## Summary

`folio` does not natively handle `.eml` files. Email threads — a critical class of consulting engagement evidence — currently require a custom parsing step (extract headers, reconstruct quoted thread, strip Outlook noise, render markdown) before they can be fed into `folio ingest --type internal_sync`. A first-class email pipeline would close a significant gap in the format coverage story alongside #56.

## Today's workaround

On a live engagement we wrote a ~370-line `scripts/parse_emails.py` to:
- Parse `.eml` via Python's `email` stdlib
- Extract envelope headers (From, To, CC, Date, Subject)
- Reconstruct the quoted thread by splitting on Outlook's `From: ...` / `Date: ...` blocks
- Sort messages chronologically (oldest-first), with the outermost message dated from the EML envelope
- Strip noise: `<tel:>` / `<mailto:>` / `<https://disclaimer-link>` wrappers, Zoom dial-in tables, SIP/H.323 lines, `____________` separators, repeated signatures, external-sender warnings, scotiabank/firm-wide disclaimers
- Collapse Outlook's split bullets (`*` on one line, content on the next) into proper markdown bullets
- Catalog attachments by filename + MIME type (no binary extraction)

The resulting markdown then ingests cleanly via:

```bash
folio ingest <thread.md> \
  --type internal_sync \
  --date <YYYY-MM-DD> \
  --client <Client> \
  --engagement <Engagement> \
  --participants \"<comma-separated-names>\"
```

For a 3-thread, 11-attachment Scotiabank corpus this produced 3 `review_status: clean` interaction notes with 28 total claims extracted via the Anthropic fallback (Sonnet 4 took over after the OpenAI route 403'd at the AI Gateway).

## Suggested behavior

### 1. New document type: `correspondence`

Email threads aren't really meetings. Add a sibling to `interaction` and `evidence`:

```yaml
type: correspondence
subtype: email_thread  # or email_single
```

This avoids overloading `internal_sync` and gives consumers (e.g., the Folio Library cursor rule) a cleaner lookup vocabulary.

### 2. New CLI: `folio ingest-email <path.eml>`

Or extend `folio ingest` with `--type email_thread` and accept `.eml` directly. Required behavior:

- Parse all `text/plain` parts; fall back to `html` -> markdown via `markitdown`
- Reconstruct the thread (oldest-first); preserve per-message From/To/CC/Date in frontmatter
- Strip Outlook/Zoom/disclaimer noise (a curated rules list will get most of it)
- Resolve participants from To/CC/From across the thread (deduplicated, normalized)
- Catalog attachments in frontmatter:
  ```yaml
  attachments:
    - filename: SOW_v9.docx
      content_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
      size_bytes: 2140160
      sha256: <hash>
  ```
- Optionally extract attachment bodies into the registry (gated by `--extract-attachments`) so that PDFs and images on the thread become first-class documents and can be `impacts:`-linked back to the email

### 3. Registry / frontmatter additions

```yaml
sender: Mishal Desai <Mishal_Desai@mckinsey.com>
recipients_to: [Jake Itzkowitz, Tim Vogeler, ...]
recipients_cc: [Pankaj Kumar, ...]
thread_message_count: 11
attachment_count: 3
external_thread: false   # true if any party is non-McKinsey
```

### 4. Enrichment hints

The `enrich` step would benefit from email-aware heuristics:
- Quoted blocks (markdown `>`) should be lower-weight than primary author content
- Signatures should be detected and excluded from claim extraction
- Decisions that show up in the most recent message should be boosted

## Why this matters

For a typical engagement, the email thread is where decisions are actually made and where vendor positions are first surfaced. The Scotia corpus we just ingested includes a Microsoft solutions-engineer pitch on Azure vs GCP that doesn't appear in any deck or meeting note, but is essential context for the architecture decision. Without first-class email support, this evidence either gets dropped or gets shoehorned into `internal_sync` with awkward titles like \"Re: [External] AI Platform Vendor Decision Points\".

## Related

- #56 (DOCX normalization gate) — same theme: format coverage gaps push real consulting evidence outside Folio's pipeline.

## Environment

- folio-love 0.6.4
- macOS 25.4.0
- Python 3.12
- QuantumBlack AI Gateway (enterprise proxy)


### Issue #62: folio watch <dir>: folder-based auto-ingestion (drop-zone UX)

- URL: https://github.com/ohjonathan/folio.love/issues/62

- State at triage: OPEN

- Created: 2026-04-17T05:03:55Z

- Updated: 2026-05-12T19:23:19Z

- Labels: none

#### Body

## Summary

Add `folio watch <dir>` — a long-running daemon (or `--once` mode for cron / launchd) that monitors a directory for new files and routes each to the appropriate Folio pipeline based on file extension. Closes the "manual CLI invocation per file" gap that today makes Folio feel like a tool you reach for rather than a system that just runs.

## User pain (current state)

To save an email, transcript, deck, or PDF into Folio today, every artifact has the same 4-7 ceremony steps:

1. Get the file into the right subdirectory (`library/<client>/<engagement>/<doctype>/`)
2. Open terminal, `cd` to workspace, `source .env`
3. Remember which Folio verb (`ingest` vs `convert`)
4. Type the right flags (`--type`, `--client`, `--engagement`, `--date`, `--participants`, `--target`)
5. Wait for processing
6. Verify the registry entry was written

Steps 2-6 are 100% mechanical given the file. The user always has the same intent ("this is engagement evidence, file it") but has to translate that into Folio's verb-and-flag vocabulary every single time.

For a solo consultant on a live engagement, this friction is the dominant reason artifacts *don't* end up in Folio — the ceremony cost beats the marginal value of any single file.

## Concrete example from a live engagement

Today, ingesting one email thread on the Scotiabank AI Platform engagement looks like this (from our actual workflow):

```bash
folio ingest \"library/scotiabank/aiplatform/correspondence/2026-04-17_scotia_ai_platform_azure_gcp.md\" \\
  --type internal_sync \\
  --date 2026-04-16 \\
  --client Scotiabank \\
  --engagement \"AI Platform\" \\
  --participants \"Chi Wai Cheung, Jonathan Oh, Bishal Dasgupta, Will Lau\" \\
  --target library/scotiabank/aiplatform/correspondence/ \\
  -n \"Initial ingest from email thread (Azure/GCP agentic stack discussion)\"
```

Seven flags. Six of them have the same value across every email on this engagement, or could be derived from the email's headers. Only `-n` is genuinely per-invocation.

Multiply by a dozen artifacts a day and the reason Folio adoption stalls becomes obvious.

## Proposed feature

### CLI

```bash
folio watch <dir> [--config folio.yaml] [--once] [--dry-run] [--quiet]
```

| Flag | Behavior |
|---|---|
| (default) | Long-running daemon. Watches `<dir>` via `watchdog` (cross-platform: kqueue on macOS, inotify on Linux, ReadDirectoryChangesW on Windows) |
| `--once` | Single pass: process anything currently in `<dir>` that hasn't been seen, then exit. Suitable for cron / launchd. |
| `--dry-run` | Log what would be processed but don't call the underlying pipeline. |
| `--quiet` | Suppress per-file stdout; only log errors. |

### Routing rules

By file extension, with overrides via `folio.yaml`:

| Extension | Default pipeline | CLI equivalent |
|---|---|---|
| `.eml` | EML thread ingest (#61) | `folio ingest --type email_thread` |
| `.pptx`, `.ppt` | Deck conversion | `folio convert` |
| `.pdf` | Document conversion | `folio convert` |
| `.docx` | Document conversion (#56) | `folio convert` |
| `.md`, `.txt` | Interaction ingest | `folio ingest` |
| Other | Skip with warning |

### Configuration

```yaml
# folio.yaml
watch:
  - path: ~/Folio-Inbox
    defaults:
      client: Scotiabank
      engagement: AI Platform
    routing:
      - match: \"*.eml\"
        action: ingest
        type: email_thread
      - match: \"*.pptx\"
        action: convert
      - match: \"*.md\"
        action: ingest
        type: internal_sync   # or auto-derive (see related FR for defaults)
    after_process:
      action: archive          # or \"delete\", \"leave\"
      to: ~/Folio-Inbox/_archive/
    notify:
      backend: macos_notification  # or \"stdout\", \"slack\", \"none\"
```

### Behavior

1. New file appears in watched directory
2. Folio matches extension against routing rules
3. Folio waits until file size is stable for N seconds (configurable; default 3) — guards against partial drops while drag is in progress
4. Folio runs the appropriate pipeline (calls the existing `folio convert` or `folio ingest` internally), with engagement defaults applied
5. On success: archive (or delete, or leave) the original; post a notification
6. On failure: write `<filename>.error.log` to `<dir>/_failed/`; post a notification with the error

### Edge cases

- **Partial files / drag in progress**: wait for file size to be stable for N seconds before processing. Configurable via `watch.stability_seconds`.
- **Duplicates** (same file dropped twice): hash content; if already in registry, log \"already ingested as <id>\" and skip (or archive directly without re-processing).
- **Concurrent files dropped together**: process serially to avoid LLM rate limits and to make registry writes atomic.
- **Daemon hygiene**: log rotation under `~/.folio/logs/`, restart on `folio.yaml` change (config watcher), `folio watch --healthcheck` command for monitoring.
- **Missing target subdirectory**: if `library/scotiabank/aiplatform/correspondence/` doesn't exist, create it (parent dir derived from `defaults.client` + `defaults.engagement` + routed `type`).

### Composition with other features

This feature depends on or composes with:

- **#56** — `.docx` normalization gate. Without this, the watcher can't route `.docx` properly.
- **#61** — Native `.eml` support. Without this, the watcher needs an intermediate parser for emails (which we've written as a workaround in this engagement — temporary scaffolding to be deleted when #61 ships).
- **[FR-defaults]** — Engagement defaults in `folio.yaml`. Without this, the watcher would still need to know `--client`, `--engagement`, `--type` etc. for each file. This is the feature that makes `folio watch` truly zero-ceremony. To be filed as a sibling issue.
- **[FR-thread-dedup]** — Message-ID-based thread dedup. Without this, dragging a thread continuation creates a duplicate registry entry. With it, thread continuations bump the existing entry's version. To be filed as a sibling issue.

### Why not just a shell wrapper around `fswatch` / `inotifywait`?

We considered this. We declined because:

1. **Routing rules need to evolve with Folio's own format support** (today PPTX/PDF; tomorrow DOCX/EML/CSV/etc.). A shell wrapper has to be re-edited every time Folio adds a format.
2. **Defaults need to compose with Folio's existing config** (`folio.yaml`). A shell wrapper invents its own config or hardcodes values.
3. **Dedup needs registry-aware logic**, which a shell wrapper would have to reimplement against `library/registry.json`.
4. **Notification format / failure handling should match Folio's existing UX**, not diverge across N user-built wrappers.
5. **The Folio user community would build N divergent shell scripts**; one Folio feature replaces them all.

The same argument holds for asking users to write a Hazel rule, Dropzone action, or macOS Folder Action. They all work, but they all reinvent Folio-aware logic outside of Folio.

### Why this matters

Folio today is a CLI-of-verbs (`convert`, `ingest`, `enrich`). For solo consultants doing live engagements, the cognitive overhead of \"which verb, which flags, where does it go\" is the dominant friction — and it's the reason artifacts don't get filed.

A drop-zone collapses that friction to \"save this thing\" — same gesture for any artifact, no taxonomy decisions at the moment of saving. The taxonomy work happens in `folio.yaml` once and is reused forever.

This pattern is well-established in adjacent tools (Hazel, Dropzone, DropBox folder upload, OneDrive auto-sort). What's missing is something that knows the Folio pipeline.

### Environment

- folio-love 0.6.4
- macOS 25.4.0 (target: also Linux via `inotify`, Windows via `watchdog`)
- Python 3.12

### Related issues

- #56 — DOCX support (needed for full extension routing coverage)
- #61 — Native EML support (needed for `.eml` routing)
- [FR-defaults] — Engagement defaults in `folio.yaml` (sibling)
- [FR-thread-dedup] — Message-ID-based email thread dedup (sibling)


### Issue #63: Engagement defaults & auto-derived ingest metadata in folio.yaml

- URL: https://github.com/ohjonathan/folio.love/issues/63

- State at triage: OPEN

- Created: 2026-04-17T05:04:45Z

- Updated: 2026-05-12T19:23:21Z

- Labels: none

#### Body

## Summary

Add a `defaults:` block to `folio.yaml` so `folio ingest` and `folio convert` don't require repeating `--client`, `--engagement`, `--type`, `--date`, `--participants`, `--target` on every CLI invocation. Layer on a `derive:` block with rules for pulling `--date` from EML envelope headers, `--participants` from From/To/CC, `--type` from sender domain matching, etc. CLI flag still wins; config is the floor.

## User pain (current state)

For a solo consultant on one engagement, every `folio ingest` invocation today looks like this (real example from the Scotiabank AI Platform engagement):

```bash
folio ingest \"thread.md\" \\
  --type internal_sync \\
  --date 2026-04-16 \\
  --client Scotiabank \\
  --engagement \"AI Platform\" \\
  --participants \"Chi Wai Cheung, Jonathan Oh, Bishal Dasgupta, Will Lau\" \\
  --target library/scotiabank/aiplatform/correspondence/ \\
  -n \"Initial ingest from email thread\"
```

Of those 7 flags:

| Flag | Source of truth | Repeated value? |
|---|---|---|
| `--client` | Engagement-level constant | Same for every invocation on this engagement |
| `--engagement` | Engagement-level constant | Same for every invocation on this engagement |
| `--target` | Deterministic from client + engagement + type | Same for every invocation |
| `--type` | Derivable from participants | All `@mckinsey.com` → `internal_sync`; mixed → `client_meeting` |
| `--date` | Derivable from EML `Date:` header / markdown frontmatter / filename | Per-file but available in the file itself |
| `--participants` | Derivable from EML From/To/CC | Per-file but available in the file itself |
| `-n` | Genuinely per-invocation | The only flag that's truly user input |

Six of seven flags either:
(a) repeat constant values, or
(b) restate values already present in the source file.

The user is doing manual data entry against information that already exists.

## Concrete example

Across a single workday on this engagement, we filed 3 emails. That's 3 × 7 = 21 flag inputs, of which 18 were either constant or derivable. Three were genuinely per-invocation. **86% of flag-typing was redundant.**

This compounds: as adoption grows or the corpus expands, the redundant typing scales linearly while the value of each marginal artifact stays constant. At some threshold, users stop filing.

## Proposed feature

### Config schema additions

```yaml
# folio.yaml
defaults:
  client: Scotiabank
  engagement: AI Platform
  target_root: ./library

  # Per-source-type derivation rules
  derive:
    date:
      - from: eml.date                    # for .eml inputs
      - from: markdown.frontmatter.date   # for .md inputs with YAML frontmatter
      - from: filename.regex
        pattern: '^(\\d{4}-\\d{2}-\\d{2})_'  # date prefix in filename
      - from: file.mtime                  # last resort

    participants:
      - from: eml.headers
        fields: [from, to, cc]
        normalize: name_only              # strip \"<email@domain>\"; dedup
      - from: markdown.frontmatter.participants

    type:
      - rule: all_participants_match_domain
        domain: \"@mckinsey.com\"
        type: internal_sync
      - rule: any_participant_matches_domain
        domain: \"@scotiabank.com\"
        type: client_meeting
      - rule: filename_contains
        substring: \"_workshop_\"
        type: workshop
      - default: internal_sync

    target:
      - rule: type_is
        type: email_thread
        target: \"{target_root}/{client_slug}/{engagement_slug}/correspondence/\"
      - rule: type_is
        type: client_meeting
        target: \"{target_root}/{client_slug}/{engagement_slug}/interactions/\"
```

### CLI behavior

When a flag is omitted, Folio resolves in this precedence order:

1. **Explicit CLI flag** (highest precedence)
2. **Derivation rule** matching the source file
3. **`defaults:` block** in `folio.yaml`
4. **Interactive prompt** (only if `--strict` is set; default behavior is to use defaults silently)
5. **Error** (if still unresolved and `--strict` is set, OR if the field is required and unresolvable)

Folio always logs the derived value so the user can see what was used:

```bash
$ folio ingest thread.eml
[derive] client: Scotiabank (defaults.client)
[derive] engagement: AI Platform (defaults.engagement)
[derive] type: internal_sync (rule: all_participants_match_domain @mckinsey.com)
[derive] date: 2026-04-16 (eml.date)
[derive] participants: [Chi Wai Cheung, Jonathan Oh, Bishal Dasgupta, Will Lau] (eml.headers)
[derive] target: ./library/scotiabank/aiplatform/correspondence/ (rule: type_is email_thread)
✓ Ingested as scotiabank_aiplatform_sync_20260416_re_scotia_azure_gcp
```

### CLI overrides still work

```bash
# Override just the type — everything else is derived
folio ingest thread.eml --type workshop

# Strict mode: prompt if anything's unresolvable
folio ingest thread.eml --strict
```

### Why this matters

Without this, **`folio watch` (related FR) is impossible** without per-file metadata sidecar files or some other awkward UX. With this, the watcher just calls `folio ingest <file>` and the right thing happens.

This also reduces error: today, a typo like `--client \"Scotabank\"` creates a phantom client in the registry that's hard to clean up afterward. With config-defined defaults, the value is right once and right forever.

### Composition

- **#62 (folio watch)** depends on this. The watcher cannot apply per-file flags via shell — it needs config-driven defaults.
- **#61 (EML support)** is the highest-value beneficiary of derivation: date, participants, and type all come \"for free\" from RFC 5322 headers.
- **#56 (DOCX support)** benefits from this. DOCX ingest could derive type and date from the document itself.

### Edge cases

- **Multiple defaults per workspace** (e.g., user works on multiple engagements simultaneously): support `defaults` per directory tree. `folio.yaml` in a subdirectory overrides the parent. Or: `--profile <name>` flag to select among named default profiles.
- **Missing required field** (e.g., file has no extractable date): error with a clear message naming the field, the source file, and the rules that were tried.
- **Conflicting derivations** (e.g., filename says 2026-04-16 but EML header says 2026-04-15): use first-match-wins per the order in `derive:`. Log both.
- **Backward compatibility**: when `defaults` is absent, behavior is unchanged. Existing scripts continue to work.

### Why not \"just write a shell alias\"?

A user could `alias fingest='folio ingest --client Scotiabank --engagement \"AI Platform\"'`. We considered this and declined because:

1. Aliases don't compose with `folio watch` — daemons don't read shell aliases.
2. Aliases can't do file-content derivation (date, participants, type from headers).
3. Aliases are per-user; Folio config is per-workspace and survives onboarding new team members.
4. Aliases proliferate (`fingest`, `fingest_internal`, `fingest_client`, ...) where one config block would do.

### Environment

- folio-love 0.6.4
- macOS 25.4.0
- Python 3.12

### Related issues

- #56 — DOCX support
- #61 — Native EML support (highest-value beneficiary of `derive:` rules)
- #62 — `folio watch <dir>` (depends on this feature)
- [FR-thread-dedup] — Message-ID-based dedup (sibling, to be filed)


### Issue #64: Email thread continuation / Message-ID-based dedup for EML ingest

- URL: https://github.com/ohjonathan/folio.love/issues/64

- State at triage: OPEN

- Created: 2026-04-17T05:05:33Z

- Updated: 2026-05-12T19:23:23Z

- Labels: none

#### Body

## Summary

When ingesting an `.eml` (post-#61) or an EML-derived markdown file, use the email's RFC 5322 `Message-ID`, `In-Reply-To`, and `References` headers to detect when the new file is a **continuation** of a previously-ingested thread. Treat continuations as new versions of the same registry entry rather than as independent entries.

## User pain (anticipated; we'll hit this within a week of using #61)

A typical engagement email thread grows over time:

| Day | What happened | Action |
|---|---|---|
| Mon | \"Re: Vendor Decision\" — 3 messages so far | Drag .eml to Folio → ingested as `entry_v1` |
| Tue | Same thread, now 5 messages (2 new replies) | Drag updated .eml to Folio |
| Wed | Same thread, now 8 messages | Drag updated .eml to Folio again |

Today, Folio (and our parser as a temporary workaround) hashes the full body for each ingest. Different bodies = different `source_hash` = different registry entry IDs.

Result:

```
scotiabank_aiplatform_sync_20260415_re_vendor_decision (3 msgs, v1)
scotiabank_aiplatform_sync_20260416_re_vendor_decision (5 msgs, v1)
scotiabank_aiplatform_sync_20260417_re_vendor_decision (8 msgs, v1)
```

All three look like distinct interactions. None are marked stale. Claims are extracted three times — once for each version — and surfaced redundantly in any consumer that filters by `review_status: clean`. Search returns three hits for what the user mentally models as one conversation.

This violates the Folio promise of \"one document, versioned correctly.\"

## Why this is solvable

Email already carries the relationship metadata. Every reply chain has:

- **`Message-ID:`** — unique identifier for this specific message
- **`In-Reply-To:`** — Message-ID of the parent
- **`References:`** — full ancestry of Message-IDs in the thread

So a thread is **definitively identified** by the set of Message-IDs in its body. If two ingested files share any Message-ID, they're the same thread. RFC 5322 has guaranteed this since 1982.

## Proposed feature

### Detection

For email-sourced documents, Folio extracts the **set of Message-IDs** in the thread:

- The outermost `Message-ID:` header (most recent message in this ingest)
- All Message-IDs in `References:` (the full ancestry)
- Optionally: parse quoted-message blocks for embedded `Message-ID:` lines (Outlook sometimes preserves them)

Store this set in the registry entry:

```yaml
id: scotiabank_aiplatform_sync_20260415_re_vendor_decision
message_ids:
  - \"<CAJ8z...mck@mail.gmail.com>\"
  - \"<MX2P234...scotia@scotiabank.com>\"
  - \"<DM6PR07...mck@mckinsey.com>\"
```

### Behavior on ingest

When ingesting a new EML:

1. Extract the new file's Message-ID set
2. Query the registry for any existing entry whose `message_ids` set intersects
3. **If intersection is non-empty:**
   - This is a thread continuation
   - Compute the union of old + new Message-IDs
   - Bump the existing entry's `version` from N → N+1
   - Mark prior version as `staleness_status: stale`
   - Update `message_ids` to the union
   - Re-run enrichment on the new (larger) body
4. **If intersection is empty:**
   - This is a new thread; create a new entry as today

### CLI output

```bash
$ folio ingest 2026-04-17_re_vendor_decision.eml
[detect] Message-ID set: {<msg-1@>, <msg-2@>, <msg-3@>, <msg-4@>, <msg-5@>}
[detect] Continuation of: scotiabank_aiplatform_sync_20260415_re_vendor_decision (v1, 3 msgs)
[action] Bumping to v2 (5 msgs); marking v1 as stale
✓ Updated scotiabank_aiplatform_sync_20260415_re_vendor_decision (v2)
```

### Behavior on subsequent ingests of the same content

If the same file is dropped again with no new messages (identical Message-ID set + identical body hash):

```bash
$ folio ingest same_thread.eml
[detect] Message-ID set: {<msg-1@>, <msg-2@>, <msg-3@>}
[detect] Identical to: scotiabank_aiplatform_sync_20260415_re_vendor_decision (v1)
[action] No-op (no new content)
✓ Skipped (already current)
```

### Edge cases

- **Branch in thread**: someone replies-all and creates a fork (different recipient list, but shares early Message-IDs). Folio detects divergence (the new branch has Message-IDs the existing thread doesn't, AND the existing thread has Message-IDs the new branch doesn't). Configurable behavior:
  - `branch_strategy: new_entry` (default) — create a separate registry entry, link via `branched_from:`
  - `branch_strategy: merge` — merge into existing entry as a v2 with both branches in the body
- **Forward-as-new-thread**: someone forwards the thread to a new audience, generating a new outer Message-ID but preserving old ones in References. Configurable:
  - `forwarded_as_continuation: true` — continuation of the original thread
  - `forwarded_as_continuation: false` (default) — new entry, link via `forwarded_from:`
- **Lost Message-IDs**: Outlook sometimes strips or mangles Message-IDs in deeply quoted thread blocks. Fall back to body-hash similarity (e.g., longest common substring of body content) as a secondary signal. Threshold configurable.
- **Manual override**: `folio ingest --as-new-entry` to force creation of a new entry even when continuation would be detected.

### Composition

- **#61** — depends on this. EML ingest without dedup creates the duplication problem; EML ingest with dedup is the polished feature. Worth landing #61 first without this, then layering dedup on; but it should be in the same release.
- **#62 (folio watch)** — critical for usability. Without dedup, a watched folder polluted with re-dragged thread updates becomes useless after a week.
- **#63 (defaults)** — pairs naturally; once defaults remove flag friction, dedup removes registry friction.
- **Existing version semantics** — this generalizes the existing `version: N` field to be aware of inherent document identity (Message-ID for emails) rather than just `source_hash`. Other document types (PPTX with version-suffixed filenames, e.g., `proposal_v6.pptx` → `proposal_v7.pptx`) could similarly benefit from filename-based identity rules in a future generalization.

### Why this matters

Email threads are **inherently cumulative**: every reply is a superset of the previous body. Treating each version as a fresh document violates the user's mental model and pollutes the registry. Other Folio document types (PPTX, PDF) have explicit version tracking (via filename or `--version`). EML needs the same, but derived automatically from headers that already exist in every email since 1982.

Without this, `folio watch` becomes a registry-pollution machine.

### Environment

- folio-love 0.6.4
- macOS 25.4.0
- Python 3.12

### Related issues

- #61 — Native EML support (this feature is meaningless without it)
- #62 — `folio watch <dir>` (this feature is critical to make watching usable)
- #63 — Engagement defaults


### Issue #69: Support transcript-native ingest formats like .vtt and .srt

- URL: https://github.com/ohjonathan/folio.love/issues/69

- State at triage: OPEN

- Created: 2026-04-22T23:14:08Z

- Updated: 2026-05-12T19:23:25Z

- Labels: none

#### Body

## Problem

`folio ingest` currently only accepts `.txt` and `.md` sources.

That is too restrictive for the actual transcript artifacts people get from meeting tools. In practice, raw exports often come as:

- `.vtt` / `WEBVTT`
- `.srt`
- plain UTF-8 transcript files that may not have a `.txt` extension

In a real workflow today, I had a meeting transcript that Folio should absolutely be able to ingest directly, but instead I had to:

1. move the raw transcript out of the workspace root
2. rename/re-home it
3. create a separate intermediate `.md` note
4. run `folio ingest` on that surrogate file instead of the actual source transcript

That is a lot of avoidable friction for a transcript-ingestion command.

## Current behavior

`folio ingest` rejects the raw transcript source based on extension.

Example failure:

```text
Unsupported source extension ''. v0.5.0 supports .txt and .md only.
```

And `.vtt` is likewise not supported even though it is a very common transcript format.

## Requested behavior

`folio ingest` should support transcript-native input formats directly, at minimum:

- `.vtt`
- `.srt`
- `.txt`
- `.md`

Nice-to-have:

- accept extensionless plaintext files when the content is clearly transcript-like / UTF-8 text
- or provide an explicit override flag such as `--format vtt|srt|plain|markdown`

## Why this matters

These formats are not edge cases. They are standard outputs from common meeting / transcription systems. If Folio is going to be the interaction-ingestion layer, it should ingest the raw artifacts users actually have, not force a manual conversion to markdown first.

## Suggested implementation

For `.vtt` / `.srt` inputs:

- parse the transcript structure instead of rejecting by suffix
- strip / normalize transport markup (cue numbers, timestamps, `WEBVTT` header, etc.)
- preserve speaker attribution and timestamps where possible
- feed the normalized transcript into the existing interaction-analysis path
- keep the original source path in provenance/frontmatter

For extensionless plaintext:

- either content-sniff UTF-8 text and allow ingest
- or require an explicit `--format plain` / `--format transcript` override

## Acceptance criteria

- `folio ingest meeting.vtt --type internal_sync ...` succeeds
- `folio ingest meeting.srt --type internal_sync ...` succeeds
- extracted interaction notes still preserve grounded findings, quotes, participants, and raw transcript sections
- provenance/frontmatter still points back to the original raw source file
- docs/help text for `folio ingest` mention the supported transcript formats explicitly

## Extra note

The current docs describe interaction ingestion as taking a transcript/note file, which is exactly why the current extension restriction is surprising. Supporting raw transcript formats would make the CLI match the real user workflow much better.


### Issue #70: Interaction analysis: add action_items as a first-class finding type (rendered as Next Steps / Action Items)

- URL: https://github.com/ohjonathan/folio.love/issues/70

- State at triage: OPEN

- Created: 2026-04-24T15:30:27Z

- Updated: 2026-05-12T19:23:26Z

- Labels: enhancement

#### Body

## Problem

`folio ingest` extracts interaction findings into four buckets — `claims`, `data_points`, `decisions`, `open_questions`. The subtype prompt hints in [`folio/pipeline/interaction_analysis.py`](https://github.com/ohjonathan/folio.love/blob/main/folio/pipeline/interaction_analysis.py) explicitly tell the LLM to surface **next steps**, **actions**, **owners**, **commitments**, and **asks**:

```python
_SUBTYPE_PROMPT_HINTS = {
    "client_meeting":    "Emphasize decisions, asks, owners, and next steps.",
    "expert_interview":  "Emphasize interview insights, expert observations, and cited datapoints.",
    "internal_sync":     "Emphasize updates, blockers, dependencies, and internal decisions.",
    "partner_check_in":  "Emphasize partner asks, commitments, risks, and coordination topics.",
    "workshop":          "Emphasize workshop outputs, open questions, decisions, and actions.",
}
```

But the JSON schema in `_ANALYSIS_SYSTEM_PROMPT_TEMPLATE` has no slot for them:

```json
"findings": {
  "claims": [...],
  "data_points": [],
  "decisions": [],
  "open_questions": []
}
```

Result: the LLM either drops next-step content entirely or squashes it into `decisions` with the wrong framing and timestamp.

## Concrete evidence (real ingest from today)

I just ingested an `expert_interview` transcript that closed with three distinct forward-looking commitments:

| Time | Speaker | Commitment |
|---|---|---|
| 00:23:30 | Jed | "Let me digest the conversation and come back to you with some next steps." |
| 00:23:35 | Jed | "Get some more information and hopefully be in a position to come back to you with some thinking on an offer soon, like in the next couple of days, at least maybe the next couple of business days." |
| 00:24:05 | Jonathan | "Let me know if you have any other questions. I'll do vice versa if I have any more questions." |

What Folio extracted into `decisions`:

```yaml
- Jed will follow up with offer details within next couple of business days
  - quote: "hopefully be in a position to come back to you with some thinking on an offer soon..."
  - timestamp: 00:23:56     # wrong — actual sentence starts at 00:23:35
```

Problems:

1. Only **1 of 3** commitments was captured.
2. The captured one's timestamp is wrong (00:23:56 is "and we go from there", not where the commitment starts).
3. No `owner`, no `due`, no signal that this is an action vs. a decision.
4. The first Jed commitment ("digest and come back with next steps") was missed entirely — there was no schema bucket to hold it.

I had to hand-add a `### Next Steps` subsection to the L0 markdown post-hoc, with `owner` and `due` fields invented locally, to make the doc actionable.

## Current behavior

- The four-bucket schema forces every action-shaped finding into `decisions` (or drops it).
- No `owner` / `due` / `status` metadata on findings, even though `_SUBTYPE_PROMPT_HINTS` references "owners".
- `InteractionFinding.element_type` enum allows `<statement|response|data_point|decision|question>` — no `action`.
- Markdown renderer emits `### Claims / ### Data Points / ### Decisions / ### Open Questions` under `## Key Findings` — no `### Next Steps` or `### Action Items` section.

## Requested behavior

Add a fifth finding bucket to the schema and surface it in the rendered markdown.

### Schema additions

```python
# folio/pipeline/interaction_analysis.py — _ANALYSIS_SYSTEM_PROMPT_TEMPLATE
"findings": {
  "claims":         [...],
  "data_points":    [],
  "decisions":      [],
  "open_questions": [],
  "action_items":   [                                     # NEW
    {
      "statement":    "<who will do what>",
      "quote":        "<supporting quote>",
      "element_type": "action",                           # NEW enum value
      "confidence":   "<high|medium|low>",
      "speaker":      "<speaker if known>",
      "timestamp":    "<timestamp if available>",
      "attribution":  "<attribution if available>",
      "owner":        "<owner if identifiable>",          # NEW field
      "due":          "<ISO date or natural-language window>"  # NEW field
    }
  ]
}
```

### Dataclass additions

```python
# folio/pipeline/interaction_analysis.py
@dataclass
class InteractionFinding:
    statement: str
    quote: str
    element_type: str = "statement"   # extend enum to include "action"
    confidence: str = "medium"
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    attribution: Optional[str] = None
    validated: bool = False
    owner: Optional[str] = None        # NEW — only meaningful for actions
    due: Optional[str] = None          # NEW — only meaningful for actions

@dataclass
class InteractionAnalysisResult:
    ...
    claims: list[InteractionFinding] = field(default_factory=list)
    data_points: list[InteractionFinding] = field(default_factory=list)
    decisions: list[InteractionFinding] = field(default_factory=list)
    open_questions: list[InteractionFinding] = field(default_factory=list)
    action_items: list[InteractionFinding] = field(default_factory=list)   # NEW
```

### Render label per subtype (Next Steps vs. Action Items)

Same bucket, different markdown header depending on subtype convention:

| Subtype | Header |
|---|---|
| `client_meeting`, `expert_interview`, `partner_check_in` | `### Next Steps` |
| `internal_sync`, `workshop` | `### Action Items` |

(Both terms exist for a reason — "Next Steps" reads better in narrative client conversations; "Action Items" reads better in tracked internal/workshop contexts. Using one canonical field with two render labels keeps the schema simple and the prose natural.)

## Why this matters

- **Closing exchanges are the highest-signal part of any client/partner conversation.** Missing them defeats the point of an interaction note.
- The prompt already promises this content per `_SUBTYPE_PROMPT_HINTS` — it's a schema/prompt mismatch bug, not a new feature ask.
- Downstream consumers (synthesize, enrich, MCP server FRs) need a clean place to ask "what was committed in this conversation?" without having to re-parse `decisions` for action-shaped content.
- For `client_meeting` and `partner_check_in` subtypes, this is arguably the single most important section of the doc.

## Suggested implementation

Files that need to change (probably all in `folio/pipeline/interaction_analysis.py` plus rendering downstream):

1. **`_ANALYSIS_SYSTEM_PROMPT_TEMPLATE`** — add `action_items` bucket + `owner` / `due` fields + `action` to `element_type` enum.
2. **`_REDUCE_SYSTEM_PROMPT`** — already says "same schema as before"; verify reducer dedupes action_items by `(owner, statement)` not just `(quote)`.
3. **`InteractionFinding`** — add `owner` / `due` optional fields.
4. **`InteractionAnalysisResult`** — add `action_items` list; update `all_findings()` to include it.
5. **Provenance / grounding** (`folio/pipeline/provenance_analysis.py`) — extend the validation walk to cover `action_items`.
6. **Markdown rendering** (likely in `folio/analysis_docs.py` or `folio/output/`) — emit `### Next Steps` or `### Action Items` subsection under `## Key Findings`, with `owner:` and `due:` shown when present.
7. **Registry `grounding_summary`** — count action_items in totals (or expose them as a separate count if maintainers prefer).

## Backward compatibility

- Older interaction notes have no `action_items` field → renders as empty section (or omitted entirely if list is empty, matching how `Open Questions` is handled).
- Older `registry.json` entries unaffected — `grounding_summary` schema unchanged.
- Re-ingest with `--no-cache` would populate the new section for existing docs.

## Acceptance criteria

- [ ] `folio ingest <client-meeting transcript>` produces a populated `### Next Steps` subsection when the transcript contains forward-looking commitments.
- [ ] `folio ingest <workshop transcript>` produces a populated `### Action Items` subsection.
- [ ] Each action item shows `owner:` and `due:` when extractable from the source.
- [ ] `element_type: action` is accepted by the validator and counted in `grounding_summary`.
- [ ] Re-ingesting an existing transcript with the new schema fills the new section without breaking existing fields.
- [ ] An interaction with no actionable content emits no `### Next Steps` / `### Action Items` subsection (no empty stub).

## Related

- Triggering case: Altitude workspace, `library/altitude/spinoff/interactions/2026-04-24_20260424_jed_cairo_*` — Jed Cairo offer-thinking conversation; close-out commitments at 00:23:30 / 00:23:35 / 00:24:05 missed or squashed.
- Related FR ideas: `due` field begs for a `folio actions ls --pending --due-before <date>` CLI down the road, but out of scope for this issue.

## Environment

- folio-love 0.6.4
- Python 3.12
- macOS 25.4.0


### Issue #71: Interaction analysis: speaker analytics (talk time, word share, turn balance)

- URL: https://github.com/ohjonathan/folio.love/issues/71

- State at triage: OPEN

- Created: 2026-04-24T17:34:54Z

- Updated: 2026-05-12T19:23:28Z

- Labels: enhancement

#### Body

## Problem

Every transcript Folio ingests already contains the raw signal needed to answer *who talked, how much, and for how long* — speaker labels and second-resolution timestamps on every turn. Today we throw that signal away during ingest. The analysis pipeline only feeds the text into the LLM and never computes the deterministic per-speaker stats that fall out of the structure for free.

This is a missed opportunity because:

1. **It's almost free to compute** — a regex over the timestamp/speaker prefix lines, no LLM call needed.
2. **It enables a class of self-coaching questions Folio is uniquely positioned to answer**, e.g. *"in my last 5 client meetings, what % of words did I speak?"* — useful for consultants, salespeople, interviewers, facilitators.
3. **It surfaces conversation imbalance instantly** — for an `expert_interview`, the SME should be doing >70% of the talking; if I'm doing 60%, that's a quality flag I'd want to see in the registry.

## Concrete evidence

Today I ingested an `expert_interview` (Altitude workspace, `library/altitude/spinoff/interactions/2026-04-24_20260424_jed_cairo_*`) — a ~24-minute Jed Cairo / Jonathan Oh conversation. Every turn in the source transcript looks like:

```
00:00:04 Jed Cairo
Yeah, you know, today is beautiful.
00:00:09 Jed Cairo
I like warm but not hot, and I feel like we only have a couple of weeks every year of that...
00:00:19 Jonathan Oh
That's true, but that four weeks is the nicest place on earth, right?
```

Speaker labels and timestamps on every turn. After ingest, the rendered note has:

- `## Summary` (LLM paragraph)
- `## Key Findings` (claims / data_points / decisions / open_questions)
- `## Entities Mentioned`
- `## Quotes / Evidence`
- raw transcript callout

Nowhere does it say:

- *"Jed spoke 38% of the words / Jonathan spoke 62%"*
- *"Jed had 47 turns averaging 22 words; Jonathan had 51 turns averaging 38 words"*
- *"Jed's longest contiguous monologue: 142 words at 00:18:30"*
- *"Total duration: 24m 14s; Jed talk time: ~9m; Jonathan talk time: ~15m"*

For an `expert_interview` where the goal was to absorb Jed's perspective on AGTI, that 62/38 split would be a useful red flag I could act on next time.

## Current behavior

- `folio/pipeline/interaction_analysis.py` parses the transcript only as text input to the LLM.
- No deterministic speaker-stats pass exists.
- `InteractionAnalysisResult` has no speaker-stats fields.
- The rendered markdown has no speaker-analytics section.
- `registry.json` entries carry no speaker-balance data, so corpus queries like *"interactions where I spoke <30%"* are impossible without re-parsing every raw transcript.

## Requested behavior

Add a deterministic speaker-stats pass at ingest time. Render in the markdown, lift summary metrics into frontmatter, and surface a compact subset in `registry.json` for corpus queries.

### Per-speaker metrics (computed deterministically)

| Metric | Notes |
|---|---|
| `word_count` | `len(text.split())` summed across the speaker's turns |
| `word_share` | `word_count / total_words`, as a float 0-1 |
| `turn_count` | number of contiguous speaking blocks |
| `avg_words_per_turn` | mean turn length |
| `longest_turn_words` | longest single contiguous monologue (words) |
| `longest_turn_timestamp` | when the longest turn started |
| `talk_time_seconds` | sum of turn durations (next_turn.start − this_turn.start; last turn estimated from words / WPM) |
| `talk_share` | `talk_time_seconds / total_duration` |
| `first_turn_timestamp` / `last_turn_timestamp` | engagement window |

### Aggregate metrics

| Metric | Notes |
|---|---|
| `total_words` | all words across all speakers |
| `total_duration_seconds` | last_turn.start − first_turn.start (+ trailing turn estimate) |
| `speaker_count` | number of distinct speakers detected |
| `balance_score` | normalized 0-1 metric of how balanced the conversation was; e.g. `1 - gini(word_shares)` so 1.0 = perfectly even, 0.0 = monologue |
| `dominant_speaker` | speaker with highest `word_share` |

### Frontmatter (proposed)

```yaml
speakers:
  jed_cairo:
    word_count: 1842
    word_share: 0.38
    turn_count: 47
    avg_words_per_turn: 39
    longest_turn_words: 142
    longest_turn_timestamp: "00:18:30"
    talk_time_seconds: 542
    talk_share: 0.37
  jonathan_oh:
    word_count: 3009
    word_share: 0.62
    turn_count: 51
    avg_words_per_turn: 59
    longest_turn_words: 198
    longest_turn_timestamp: "00:11:46"
    talk_time_seconds: 912
    talk_share: 0.63
total_words: 4851
total_duration_seconds: 1454
speaker_count: 2
balance_score: 0.76
dominant_speaker: "Jonathan Oh"
```

### Markdown section (proposed)

Place after `## Summary`, before `## Key Findings`:

```markdown
## Speaker Analytics

| Speaker | Words | % | Turns | Avg/turn | Talk time | Talk % |
|---|---:|---:|---:|---:|---:|---:|
| Jonathan Oh | 3,009 | 62% | 51 | 59 | 15m 12s | 63% |
| Jed Cairo   | 1,842 | 38% | 47 | 39 | 9m 02s  | 37% |
| **Total**   | **4,851** | 100% | **98** | **49** | **24m 14s** | 100% |

Conversation balance: **0.76** (1.0 = even split, 0 = monologue) — dominant speaker: Jonathan Oh.
Longest monologue: Jonathan Oh, 198 words at 00:11:46.
```

### Registry surface (minimal — keep entries small)

Add to each interaction entry in `registry.json`:

```json
{
  "speaker_summary": {
    "total_words": 4851,
    "duration_seconds": 1454,
    "speaker_count": 2,
    "balance_score": 0.76,
    "dominant_speaker": "Jonathan Oh",
    "shares": { "Jonathan Oh": 0.62, "Jed Cairo": 0.38 }
  }
}
```

This unlocks corpus queries without re-reading the markdown.

## Why this matters

- **Self-coaching loop for the user.** *"In my last 5 client meetings, my average word_share was 47% — too high; aim for <35% next month."* Folio becomes a feedback mechanism, not just a record.
- **Quality flag on expert interviews.** If `dominant_speaker` is the interviewer (not the SME), the doc is suspect for that purpose. Could even auto-emit a `review_flag: interview_balance_inverted` when an `expert_interview` has interviewer word_share > 50%.
- **Engagement health signal.** Across a portfolio of meetings with one stakeholder, a sudden drop in their `talk_share` over time is a leading indicator of disengagement.
- **Workshop facilitation diagnostics.** For workshops, `balance_score` directly answers *"did everyone participate?"* without re-listening.
- **Free of charge.** Pure regex + arithmetic. No incremental LLM tokens.

## Suggested implementation

New deterministic pass in the ingest pipeline, runs **before** the LLM analysis call so its output is available regardless of LLM status (analysis_unavailable runs still get speaker stats):

1. **New module `folio/pipeline/speaker_analytics.py`** — pure-function parser + analyzer.
   - `parse_turns(source_text: str) -> list[Turn]` — regex over the standard `HH:MM:SS Speaker Name` line pattern; supports the existing transcript convention (one timestamp + speaker per turn block).
   - `compute_stats(turns: list[Turn]) -> SpeakerStats` — emits the per-speaker + aggregate metrics above.
   - `last-turn duration estimate`: words / 150 WPM (configurable).

2. **Hook into `folio/pipeline/interaction_analysis.py`** — call `speaker_analytics.compute_stats()` early in the ingest path; attach result to `InteractionAnalysisResult.speaker_stats`.

3. **Dataclass additions:**
   ```python
   @dataclass
   class TurnStats:
       speaker: str
       word_count: int
       word_share: float
       turn_count: int
       avg_words_per_turn: float
       longest_turn_words: int
       longest_turn_timestamp: str
       talk_time_seconds: int
       talk_share: float
       first_turn_timestamp: str
       last_turn_timestamp: str

   @dataclass
   class SpeakerStats:
       per_speaker: dict[str, TurnStats]
       total_words: int
       total_duration_seconds: int
       speaker_count: int
       balance_score: float
       dominant_speaker: str
   ```

4. **Render** in the existing markdown writer (probably `folio/analysis_docs.py` or `folio/output/`) — emit `## Speaker Analytics` section + `speakers:` frontmatter block.

5. **Registry surface** — extend interaction entries with the compact `speaker_summary` block in `folio/tracking/registry.py`.

6. **Speaker-name normalization** — defer to existing entity resolution where possible; canonical name takes precedence over transcript label, but `aliases` are accepted as same-speaker (so "Jonathan" and "Jonathan Oh" don't show up as two speakers).

7. **Graceful degradation** — if the transcript has no parseable timestamps/speakers (e.g. a free-form interview note), skip the pass silently and emit `review_flag: speaker_analytics_unavailable`.

## Backward compatibility

- Empty / malformed transcripts → no `## Speaker Analytics` section emitted; new flag in `review_flags` (`speaker_analytics_unavailable`) so it's discoverable.
- Existing markdown notes without speaker stats remain valid — section is additive.
- `registry.json` entries without `speaker_summary` remain valid — consumers should treat the field as optional.
- Re-ingest with `--no-cache` populates speaker stats for existing interaction docs.

## Acceptance criteria

- [ ] `folio ingest <transcript with timestamps + speaker labels>` produces a populated `## Speaker Analytics` section + `speakers:` frontmatter block.
- [ ] `folio ingest <free-form note without speaker labels>` ingests cleanly, no analytics section, `review_flag: speaker_analytics_unavailable` set.
- [ ] `registry.json` entry contains `speaker_summary` with `total_words`, `duration_seconds`, `balance_score`, `dominant_speaker`, `shares`.
- [ ] Speaker-name aliases are merged via the existing entity registry (no double-counting "Jonathan" vs "Jonathan Oh").
- [ ] Stats are computed when LLM analysis is unavailable (e.g. missing API key) — speaker analytics does not depend on the LLM.
- [ ] Re-ingesting an existing transcript with `--no-cache` populates the new fields without breaking existing fields.

## Future / out of scope

- `folio interactions stats --speaker "Jonathan Oh" --since 2026-01-01` CLI for cross-doc trend analysis (depends on this issue + a query layer).
- Auto-flag `expert_interview` entries where interviewer `word_share` > 50% (single-line heuristic; could ride on the `review_flags` mechanism).
- Per-topic speaker-share breakdown (depends on intent / topic segmentation, much more complex).

## Related

- Triggering case: Altitude workspace, Jed Cairo expert interview (2026-04-24); the question *"did I talk too much in that 24 minutes?"* could not be answered without re-parsing the raw transcript by hand.
- Sibling: #70 (action_items as first-class finding type) — different schema gap, same theme of *"the signal is in the transcript, surface it explicitly."*

## Environment

- folio-love 0.6.4
- Python 3.12
- macOS 25.4.0


## Strict-P3 Lifecycle Requirements

- Each implementation slice uses `manifest_version: "1.6.0"` and `lifecycle_receipt_inventory_path`.

- Author family is `claude-opus`; B.1/D.2 roles are `claude-sonnet: peer`, `codex: alignment`, `gemini: adversarial`; D.5 roles are all three as verifiers.

- B.1, D.2, and D.5 are dispatched through `dispatch-family-review.sh --append-receipt`; Claude Sonnet receipts use `--family-as claude-sonnet --model sonnet`.

- One negative lifecycle control must fail with `review_pending` before receipts exist; after receipts exist, D.6 must include `Strict-P3 lifecycle receipts verified` and pass `verify-d6-gate.sh --strict-p3`.

