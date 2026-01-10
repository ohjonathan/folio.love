# Folio: Implementation Roadmap

**Version 1.0 | January 2026**  
**folio.love**

---

## Executive Summary

This roadmap prioritizes **conversion quality above all else**. Fancy features don't matter if the basic conversion is unreliable. The phases are structured to nail the fundamentals first, then layer on organization and discovery features.

### The Hierarchy (Never Forget)

```
1. CONVERSION QUALITY    ← Phase 1 focus
2. VERSION INTEGRITY     ← Phase 1 focus  
3. ORGANIZATION          ← Phase 2 focus
4. KNOWLEDGE GRAPH       ← Phase 3 focus
```

### Timeline Overview

| Phase | Duration | Focus | Exit Criteria |
|-------|----------|-------|---------------|
| 0 | Complete | POC validation | Pipeline works ✓ |
| 1 | Weeks 1-3 | Conversion quality | Every output is trustworthy |
| 2 | Weeks 4-6 | Library organization | Multi-project structure works |
| 3 | Weeks 7-10 | Obsidian integration | Graph view is useful |

---

## Phase 0: Proof of Concept ✓

**Status: COMPLETE**

### What We Proved

- PPTX → PDF → PNG pipeline works
- MarkItDown extracts text with slide boundaries
- LLM analysis correctly identifies frameworks
- Version tracking detects changes accurately
- Dual-layer output (image + text + analysis) is valuable

### Artifacts

- `converter_v2.py`: Working POC script
- Sample conversions validating approach
- Architecture decisions documented

---

## Phase 1: Conversion Quality (Weeks 1-3)

**Goal:** Make every conversion trustworthy. No missing images, no mangled text, no broken source links.

### Week 1: Core Pipeline Hardening

**Objective:** Bulletproof the conversion pipeline.

#### Tasks

- [ ] **Image extraction reliability**
  - Handle PDFs with unusual page sizes
  - Verify every page produces an image
  - Add blank page detection (warning, not failure)
  - Test with 20+ real consulting decks
  
- [ ] **Text extraction accuracy**
  - Compare extracted text to source (automated diffing)
  - Handle special characters, bullets, numbering
  - Preserve table structure
  - Flag extraction failures visibly

- [ ] **Source tracking implementation**
  - Relative path computation
  - Hash computation and storage
  - Path resolution (markdown → source)
  - Validation that source exists

#### Deliverables

- Conversion pipeline that doesn't silently fail
- Source path appears in every output
- 99%+ text extraction accuracy on test corpus

#### Acceptance Tests

```bash
# Every slide has an image
ls slides/ | wc -l  # Should equal slide count

# Source path is valid
head -20 deck.md | grep "source:"  # Path exists
cat deck.md | grep source: | xargs test -f  # File exists

# Text matches source (spot check)
diff <(pptx-text-dump source.pptx) <(grep -A999 "Verbatim" deck.md)
```

---

### Week 2: LLM Analysis Quality

**Objective:** Analysis that actually helps, not placeholder text.

#### Tasks

- [ ] **Prompt engineering for consulting frameworks**
  - Test detection of: 2x2, SCR, MECE, waterfall, Gantt, org chart
  - Improve visual description quality
  - Ensure "main insight" is actually insightful
  
- [ ] **Analysis validation**
  - Compare LLM output to human judgment on 50 slides
  - Identify failure patterns
  - Iterate on prompts

- [ ] **Error handling**
  - Graceful degradation when API fails
  - Retry logic with backoff
  - Clear marking of "analysis pending" slides

- [ ] **Caching**
  - Cache by image hash
  - Skip analysis for unchanged slides
  - Estimate cost before batch operations

#### Deliverables

- Analysis prompt tuned for consulting content
- 90%+ framework detection accuracy
- Cached analysis persists across runs

---

### Week 3: Version Tracking Reliability

**Objective:** Trust the change detection completely.

#### Tasks

- [ ] **Change detection accuracy**
  - Test with single-word changes
  - Test with slide reordering
  - Test with added/removed slides
  - Verify no false positives

- [ ] **Staleness detection**
  - Detect when source file modified
  - Clear status output
  - Integration with `status` command

- [ ] **Version history persistence**
  - JSON schema validation
  - Atomic writes (no corruption)
  - History survives re-conversion

- [ ] **Integration testing**
  - Full workflow: convert → edit source → re-convert → verify changes
  - Test with real revision cycle (5 versions of same deck)

#### Deliverables

- Change detection you can trust
- `folio status` shows accurate staleness
- Version history is complete and correct

#### Exit Criteria for Phase 1

- [ ] Convert 50 real decks with zero silent failures
- [ ] Every slide has image, text, and analysis
- [ ] Source tracking works (can open original from any conversion)
- [ ] Change detection correctly identifies modifications
- [ ] Staleness detection flags outdated conversions

---

## Phase 2: Library Organization (Weeks 4-6)

**Goal:** Support multi-client, multi-project organization with Obsidian compatibility.

### Week 4: Package Structure & CLI

**Objective:** Proper Python package with usable CLI.

#### Tasks

- [ ] **Package structure**
  - `folio/` package layout
  - `pyproject.toml` configuration
  - Entry points for CLI
  
- [ ] **CLI implementation**
  - `folio convert <file>` - single file conversion
  - `folio batch <dir>` - batch conversion
  - `folio status [scope]` - check status
  - `folio scan` - find new/changed sources
  - `folio refresh` - re-convert stale decks

- [ ] **Configuration**
  - `folio.yaml` configuration file
  - Source directory mapping
  - LLM settings (model, API key location)

#### Deliverables

- Installable package: `pip install folio`
- Working CLI with all core commands
- Configuration file support

---

### Week 5: Multi-Project Organization

**Objective:** Library structure that scales across clients and projects.

#### Tasks

- [ ] **Directory structure**
  - Client/Project/Deck hierarchy
  - Internal and Research top-level folders
  - Consistent naming conventions

- [ ] **Source mapping**
  - Configure source roots in `folio.yaml`
  - Map sources to library locations
  - Handle sources from different locations

- [ ] **Registry implementation**
  - Global `registry.json` tracking all decks
  - Status aggregation by client/project
  - Fast staleness checking

#### Deliverables

- Library with 100+ decks across 5+ clients
- Registry accurately reflects library state
- `folio status` works at library, client, and project level

---

### Week 6: Obsidian Compatibility

**Objective:** Library opens as Obsidian vault and works properly.

#### Tasks

- [ ] **Frontmatter completeness**
  - All required fields populated
  - Tags extracted from content
  - Frameworks and slide types indexed

- [ ] **Obsidian testing**
  - Open library as vault
  - Search by frontmatter fields
  - Verify images render
  - Test with Dataview queries

- [ ] **Link compatibility**
  - Standard markdown links work
  - File links to source work (if supported)
  - No broken references

#### Deliverables

- Library opens in Obsidian with no errors
- Search by tag, framework, client works
- Dataview queries return correct results

#### Exit Criteria for Phase 2

- [ ] CLI is usable for daily workflow
- [ ] Multi-client library is organized and navigable
- [ ] Obsidian opens library as vault
- [ ] Configuration supports multiple source roots

---

## Phase 3: Knowledge Graph (Weeks 7-10)

**Goal:** Make the library's connections visible and useful.

### Week 7-8: Cross-References

#### Tasks

- [ ] **Automatic linking**
  - Link decks in same project
  - Link decks using same framework
  - Detect explicit cross-references in content

- [ ] **Maps of Content (MOCs)**
  - Auto-generate client index pages
  - Auto-generate framework index pages
  - Keep MOCs updated on conversion

### Week 9-10: Graph Optimization

#### Tasks

- [ ] **Graph view tuning**
  - Meaningful clusters (by client, by framework)
  - Useful hover previews
  - Reasonable node sizing

- [ ] **Discovery features**
  - "Related decks" based on content similarity
  - Framework reuse suggestions
  - Cross-client pattern detection

#### Exit Criteria for Phase 3

- [ ] Graph view shows meaningful structure
- [ ] MOCs help navigation
- [ ] Cross-references work in Obsidian

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Text extraction accuracy issues | Medium | **Critical** | Extensive testing, fallback to image-only |
| LLM analysis inconsistent | Medium | Medium | Prompt iteration, manual override option |
| Source path breaks on sync | Medium | High | Thorough testing with OneDrive/Dropbox |
| Obsidian compatibility issues | Low | Medium | Test early and often |
| Time constraints | High | High | Strict Phase 1 focus, defer nice-to-haves |

---

## Quality Gates

### Phase 1 Gate (Must Pass to Proceed)

- [ ] Zero silent conversion failures in 50-deck test
- [ ] Text extraction accuracy >99%
- [ ] Image present for every slide
- [ ] Source path valid for every conversion
- [ ] Change detection accuracy >95%

### Phase 2 Gate

- [ ] CLI works for daily workflow (self-use test)
- [ ] 100+ deck library organized correctly
- [ ] Obsidian opens without errors
- [ ] Configuration is documented

### Phase 3 Gate

- [ ] Graph view provides value (subjective)
- [ ] MOCs are useful for navigation
- [ ] Would recommend to colleague

---

## Resource Requirements

### Development Time

| Phase | Weekly Hours | Total |
|-------|--------------|-------|
| Phase 1 | 12-15 | 36-45 |
| Phase 2 | 10-12 | 30-36 |
| Phase 3 | 8-10 | 32-40 |
| **Total** | | **~100 hours** |

### External Costs

| Item | Estimate |
|------|----------|
| Anthropic API (development) | $20-50 |
| Anthropic API (ongoing) | $10-30/month |
| Domain (folio.love) | ~$30/year |
| Infrastructure | $0 (local) |

---

## Success Metrics

### Phase 1 Success

> "I trust the conversion output completely."

- Open any conversion, text matches source
- Every slide has visible image
- Source file is one click away
- Changes are detected correctly

### Phase 2 Success

> "I use this every day without friction."

- Convert new materials in seconds
- Find past work quickly
- Obsidian provides useful views

### Phase 3 Success

> "I discover connections I wouldn't have found otherwise."

- Graph reveals patterns
- MOCs help navigation
- Would share with colleagues

---

## Next Actions

### This Week

1. [ ] Create `folio/` package structure
2. [ ] Port POC code to package format
3. [ ] Implement source path tracking
4. [ ] Build test corpus (20 real decks)

### Next Week

1. [ ] Hardened image extraction
2. [ ] Text extraction validation
3. [ ] CLI skeleton (`convert` command)

### Week 3

1. [ ] LLM prompt tuning
2. [ ] Version tracking implementation
3. [ ] Phase 1 quality gate testing
