# Folio: User Stories & Use Cases

**Version 1.0 | January 2026**  
**folio.love**

---

## Priority Framework

Stories are prioritized by the hierarchy of value:

| Priority | Category | Meaning |
|----------|----------|---------|
| **P0-Critical** | Conversion Quality | If this fails, nothing else matters |
| **P0-Critical** | Version Integrity | Must work correctly |
| **P1** | Organization | Makes it usable at scale |
| **P2** | Knowledge Graph | Amplifies value |

---

## Epic 1: Conversion Quality (P0-Critical)

*The foundation. Every story here must be rock-solid before moving to other epics.*

---

### US-101: Slide Image Extraction

> **As a** consultant  
> **I want** every slide captured as an image  
> **So that** I can see the visual layout, frameworks, and spatial relationships

**Acceptance Criteria:**
- [ ] Every slide in source has corresponding PNG in output
- [ ] Images are 150 DPI (readable text, clear diagrams)
- [ ] Images render correctly in markdown preview
- [ ] Images render correctly in Obsidian

**Priority:** P0-Critical

**Test Cases:**
- 50-slide deck produces 50 images
- Complex diagrams are legible
- Charts and graphs are clear
- Tables are readable

---

### US-102: Verbatim Text Extraction

> **As a** consultant  
> **I want** exact text extracted from each slide  
> **So that** I can review wording, check grammar, and maintain editorial precision

**Acceptance Criteria:**
- [ ] Text matches source exactly (diffable)
- [ ] Bullet points appear as bullets
- [ ] Numbering is preserved
- [ ] Tables render as markdown tables
- [ ] Special characters handled correctly

**Priority:** P0-Critical

**Test Cases:**
- Single quote/apostrophe preservation
- Em-dash vs. hyphen
- Trademark symbols
- Foreign characters
- Bullet/number formatting

---

### US-103: LLM Analysis Generation

> **As a** consultant  
> **I want** AI analysis explaining visual content  
> **So that** I can search for frameworks and understand slides without opening images

**Acceptance Criteria:**
- [ ] Every slide has slide type classification
- [ ] Frameworks are correctly identified (2x2, SCR, MECE, etc.)
- [ ] Visual descriptions capture spatial relationships
- [ ] Key data points are extracted
- [ ] Main insight summarizes the "so what"

**Priority:** P0-Critical

**Test Cases:**
- 2x2 matrix: axes and quadrants described
- SCR: situation/complication/resolution identified
- Data slide: key metrics extracted
- Process flow: sequence described

---

### US-104: Source File Tracking

> **As a** consultant  
> **I want** to always know where the original file is  
> **So that** I can open, edit, or share the source when needed

**Acceptance Criteria:**
- [ ] Source path stored in markdown header and frontmatter
- [ ] Path is relative (works across machines)
- [ ] Path resolves correctly (file exists)
- [ ] Can open source file within 2 clicks
- [ ] Path works when synced via OneDrive/Dropbox

**Priority:** P0-Critical

**Test Cases:**
- Path valid after moving library to new machine
- Path valid after OneDrive sync
- Path handles spaces and special characters
- Missing source file is clearly flagged

---

### US-105: Source Hash Verification

> **As a** consultant  
> **I want** to know if the source file has changed  
> **So that** I can reconvert when the deck is updated

**Acceptance Criteria:**
- [ ] SHA256 hash stored at conversion time
- [ ] Hash comparison detects any file change
- [ ] Staleness clearly flagged in status output
- [ ] Staleness visible in frontmatter

**Priority:** P0-Critical

**Test Cases:**
- Single character change detected
- Saved without changes = no staleness
- Different file with same name detected

---

## Epic 2: Version Tracking (P0-Critical)

*Changes happen constantly in consulting. Tracking them is essential.*

---

### US-201: Automatic Change Detection

> **As a** consultant  
> **I want** automatic detection of what changed between versions  
> **So that** I don't have to manually compare slides

**Acceptance Criteria:**
- [ ] Modified slides identified by text comparison
- [ ] Added slides detected
- [ ] Removed slides detected
- [ ] Change summary at top of markdown
- [ ] Per-slide *(modified)* markers

**Priority:** P0-Critical

**Test Cases:**
- Single word change detected
- Slide reorder detected
- Slide added in middle detected
- Slide removed detected
- No false positives on unchanged slides

---

### US-202: Version Notes

> **As a** consultant  
> **I want** to add context about why a version changed  
> **So that** I can remember the context months later

**Acceptance Criteria:**
- [ ] `--note` parameter on convert command
- [ ] Note stored in version history
- [ ] Note visible in markdown output
- [ ] Note searchable

**Priority:** P0-Critical

**Example Notes:**
- "Updated per client feedback on risk figures"
- "Added slides 5-8 from appendix to main deck"
- "Revised positioning based on SteerCo discussion"

---

### US-203: Version History

> **As a** consultant  
> **I want** complete history of a deck's revisions  
> **So that** I can understand how it evolved

**Acceptance Criteria:**
- [ ] All versions tracked in version_history.json
- [ ] Each version has: number, date, hash, note, changes
- [ ] History table rendered in markdown footer
- [ ] `folio status <deck>` shows full history

**Priority:** P0-Critical

---

### US-204: Staleness Warning

> **As a** consultant  
> **I want** to know when my conversions are out of date  
> **So that** I can trust the information I'm reading

**Acceptance Criteria:**
- [ ] `folio status` shows stale conversions
- [ ] Stale status visible in frontmatter
- [ ] Missing source files flagged separately
- [ ] Easy to refresh stale decks

**Priority:** P0-Critical

---

## Epic 3: CLI & Workflow (P1)

*The daily driver interface.*

---

### US-301: Convert Single File

> **As a** consultant  
> **I want** to convert a deck with one command  
> **So that** I can quickly add new materials

**Acceptance Criteria:**
- [ ] `folio convert <file>` works
- [ ] `--note` parameter for version note
- [ ] `--target` to specify location
- [ ] Progress indication for long operations
- [ ] Clear error messages on failure

**Priority:** P1

**Example:**
```bash
folio convert ./materials/market_sizing.pptx --note "Initial conversion"
```

---

### US-302: Batch Convert Directory

> **As a** consultant  
> **I want** to convert all decks in a folder at once  
> **So that** I can quickly onboard project materials

**Acceptance Criteria:**
- [ ] `folio batch <directory>` converts all files
- [ ] `--pattern` to filter files (default: *.pptx)
- [ ] Progress shows current file
- [ ] Errors on one file don't stop batch
- [ ] Summary at end

**Priority:** P1

**Example:**
```bash
folio batch ./client_materials --pattern "*.pptx"
# Converting 12 files...
# ✓ market_sizing.pptx (12 slides)
# ✓ competitive_analysis.pptx (8 slides)
# ✗ corrupted_file.pptx (failed: invalid format)
# ...
# Complete: 11 succeeded, 1 failed
```

---

### US-303: Check Status

> **As a** consultant  
> **I want** to see the status of my library at a glance  
> **So that** I know what needs attention

**Acceptance Criteria:**
- [ ] `folio status` shows library summary
- [ ] `folio status ClientA` scopes to client
- [ ] Shows current/stale/missing counts
- [ ] Lists specific decks needing attention

**Priority:** P1

**Example:**
```bash
folio status

Library: 47 decks
  ✓ Current: 42
  ⚠ Stale: 4
  ✗ Missing source: 1

Stale:
  ClientA/Project1/market_sizing (source modified 2 days ago)
  ClientA/Project1/competitive (source modified 5 hours ago)
  ...

Missing:
  ClientB/OldProject/legacy_deck (source not found)
```

---

### US-304: Scan for New Files

> **As a** consultant  
> **I want** to find new source files not yet converted  
> **So that** I keep my library complete

**Acceptance Criteria:**
- [ ] `folio scan` finds unconverted files in source directories
- [ ] Also finds files changed since conversion
- [ ] Outputs actionable list
- [ ] Respects source configuration

**Priority:** P1

**Example:**
```bash
folio scan

Found 3 new files:
  sources/ClientA/Project2/new_deck.pptx
  sources/ClientB/kickoff_materials.pptx
  sources/Internal/updated_template.pptx

Found 2 changed files:
  sources/ClientA/Project1/market_sizing.pptx (stale)
  sources/ClientA/Project1/competitive.pptx (stale)

Run 'folio refresh' to update stale conversions
```

---

### US-305: Refresh Stale Conversions

> **As a** consultant  
> **I want** to update all outdated conversions at once  
> **So that** my library stays current

**Acceptance Criteria:**
- [ ] `folio refresh` reconverts all stale decks
- [ ] `--scope ClientA` limits to specific area
- [ ] Shows what will be updated before proceeding
- [ ] Preserves version history

**Priority:** P1

---

## Epic 4: Library Organization (P1)

*Structure for career-spanning knowledge.*

---

### US-401: Multi-Client Structure

> **As a** consultant  
> **I want** my library organized by client and project  
> **So that** I can navigate my career's worth of materials

**Acceptance Criteria:**
- [ ] Top-level folders for each client
- [ ] Project subfolders within clients
- [ ] Internal and Research as top-level peers
- [ ] Consistent structure enforced by tool

**Priority:** P1

---

### US-402: Source Directory Configuration

> **As a** consultant  
> **I want** to configure where source files live  
> **So that** I don't have to move files around

**Acceptance Criteria:**
- [ ] `folio.yaml` configuration file
- [ ] Map multiple source roots
- [ ] Source → library path mapping
- [ ] Supports absolute and relative paths

**Priority:** P1

**Example:**
```yaml
sources:
  - name: client-materials
    path: ../client_materials
    
  - name: internal
    path: C:/OneDrive/Internal
    target_prefix: Internal/
```

---

### US-403: Obsidian Frontmatter

> **As a** consultant  
> **I want** proper Obsidian metadata in every file  
> **So that** I can search and filter in Obsidian

**Acceptance Criteria:**
- [ ] YAML frontmatter in every markdown
- [ ] Tags from content
- [ ] Frameworks indexed
- [ ] Slide types indexed
- [ ] Searchable in Obsidian

**Priority:** P1

---

### US-404: Registry Index

> **As a** consultant  
> **I want** a central index of all my decks  
> **So that** status checks are fast and I can query programmatically

**Acceptance Criteria:**
- [ ] `registry.json` at library root
- [ ] All decks indexed with metadata
- [ ] Updated on every conversion
- [ ] Queryable for reporting

**Priority:** P1

---

## Epic 5: Obsidian Integration (P2)

*Making the graph useful.*

---

### US-501: Wiki Links

> **As a** consultant  
> **I want** decks to link to related decks  
> **So that** I can navigate connections in Obsidian

**Acceptance Criteria:**
- [ ] Same-project decks linked
- [ ] Same-framework decks linked
- [ ] Links use `[[wiki syntax]]`
- [ ] Graph shows meaningful connections

**Priority:** P2

---

### US-502: Framework Index Pages

> **As a** consultant  
> **I want** index pages for each framework type  
> **So that** I can find all my 2x2 matrices in one place

**Acceptance Criteria:**
- [ ] Auto-generated MOC for each framework
- [ ] Lists all decks using that framework
- [ ] Updated when library changes
- [ ] Useful in graph view

**Priority:** P2

---

### US-503: Client Index Pages

> **As a** consultant  
> **I want** an index page for each client  
> **So that** I can see all work for a client at once

**Acceptance Criteria:**
- [ ] Auto-generated MOC for each client
- [ ] Lists all projects and decks
- [ ] Summary statistics
- [ ] Useful for project handoffs

**Priority:** P2

---

## Usage Scenarios

### Scenario 1: New Project Onboarding

```
Day 1: Receive materials from predecessor (15 PPTX files)

1. Copy files to sources/ClientC/Transformation/
2. Run: folio batch sources/ClientC/Transformation/
3. All files converted with images, text, analysis
4. Open Obsidian, browse ClientC folder
5. Ask Claude (with library as context): "Summarize the key findings"
```

### Scenario 2: Daily Revision Cycle

```
Afternoon: Partner gives feedback on executive summary

1. Edit the PPTX in PowerPoint
2. Save to same location
3. Run: folio status
   → Shows market_sizing is stale
4. Run: folio convert sources/.../market_sizing.pptx --note "Partner feedback"
5. Folio detects slides 2, 5, 8 modified
6. Markdown updated with changes highlighted
7. Ask Claude: "What changed in the latest version?"
```

### Scenario 3: Cross-Project Research

```
Need to find past market sizing work for new proposal

1. Open Obsidian
2. Search: tag:#market-sizing
3. Find 6 decks across 3 clients
4. Review images to find most relevant approach
5. Use past work as template for new project
```

### Scenario 4: Source File Access

```
Client asks for "that competitive analysis deck"

1. Open library in Obsidian
2. Navigate to ClientB/Project2/competitive_analysis
3. See source path in frontmatter
4. Click/follow path to open original PPTX
5. Email to client
```

---

## Prioritization Summary

### P0-Critical (Conversion Quality + Version Integrity)

| ID | Story | Must Work Perfectly |
|----|-------|---------------------|
| US-101 | Slide Image Extraction | Every slide captured |
| US-102 | Verbatim Text Extraction | Exact wording |
| US-103 | LLM Analysis Generation | Frameworks identified |
| US-104 | Source File Tracking | Path always valid |
| US-105 | Source Hash Verification | Staleness detected |
| US-201 | Automatic Change Detection | Changes found |
| US-202 | Version Notes | Context preserved |
| US-203 | Version History | Complete record |
| US-204 | Staleness Warning | Out-of-date flagged |

### P1 (Organization)

| ID | Story | Makes It Usable |
|----|-------|-----------------|
| US-301 | Convert Single File | Daily workflow |
| US-302 | Batch Convert | Onboarding |
| US-303 | Check Status | Maintenance |
| US-304 | Scan for New Files | Completeness |
| US-305 | Refresh Stale | Maintenance |
| US-401 | Multi-Client Structure | Scale |
| US-402 | Source Configuration | Flexibility |
| US-403 | Obsidian Frontmatter | Search |
| US-404 | Registry Index | Performance |

### P2 (Knowledge Graph)

| ID | Story | Amplifies Value |
|----|-------|-----------------|
| US-501 | Wiki Links | Navigation |
| US-502 | Framework Index | Discovery |
| US-503 | Client Index | Overview |
