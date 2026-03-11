---
id: obsidian_queries
type: reference
status: active
---

# Obsidian Dataview Queries for Folio

> Practical examples using [Dataview](https://blacksmithgu.github.io/obsidian-dataview/)
> with Folio's ontology-v2 frontmatter fields.

## Prerequisites

Install the **Dataview** community plugin in Obsidian and ensure your Folio
library folder is inside your Obsidian vault (or symlinked into it).

---

## 1. Tracked Decks by Oldest Conversion

Show all converted documents sorted by oldest conversion first — a useful
proxy for spotting decks that may need a refresh.

```dataview
TABLE source AS "Source", version AS "Version", converted AS "Last Converted"
FROM ""
WHERE source AND source_hash
SORT converted ASC
```

> **Note:** Dataview reads frontmatter only and cannot query live
> staleness (which requires comparing source hashes). For real-time
> stale detection, use `folio status --refresh` or `folio scan`
> from the CLI.

---

## 2. All Evidence for an Engagement

```dataview
TABLE title AS "Title", subtype AS "Subtype", slide_count AS "Slides", curation_level AS "Level"
FROM ""
WHERE engagement = "DD Q1 2026" AND type = "evidence"
SORT title ASC
```

Replace `"DD Q1 2026"` with your engagement name.

---

## 3. Documents by Authority Tier

```dataview
TABLE title AS "Title", type AS "Type", curation_level AS "Curation"
FROM ""
WHERE authority
GROUP BY authority
SORT authority ASC
```

Authority values: `captured` (machine-generated), `analyzed` (LLM-processed),
`aligned` (human-verified), `decided` (human-curated).

---

## 4. Decks Tagged with a Framework or Industry Term

```dataview
TABLE title AS "Title", client AS "Client", frameworks AS "Frameworks"
FROM ""
WHERE contains(tags, "market-sizing") OR contains(tags, "competitive-analysis")
SORT client ASC
```

Swap the tag values for any framework or industry term from your library.

---

## 5. Curation Dashboard

```dataview
TABLE length(rows) AS "Count"
FROM ""
WHERE curation_level
GROUP BY curation_level
SORT curation_level ASC
```

Shows how many documents are at each curation level (L0, L1, L2, L3).
