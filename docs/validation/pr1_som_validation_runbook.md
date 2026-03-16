---
id: pr1_som_validation_runbook
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-14
---

# PR 1 Set-of-Mark Validation Runbook

This runbook closes the missing PR 1 decision gate for diagram extraction:

- `SoM viable` -> PR 2 implements Set-of-Mark annotation as the primary image strategy
- `SoM not viable` -> PR 2 implements tiles (`global + quadrant crops`) as the image strategy

PR 1 merged without a recorded real-corpus SoM verdict, so this run must happen
before PR 2 is specified.

## Goal

Run `inspect_pages()` on 5-10 real diagram PDFs, measure page-level
`som_viable` results, and produce a single PR 2 gate decision.

## Important Constraint

Current `som_viable` is **lexical-only**. It checks text overlap between
`pypdfium2` and `pdfplumber`; it does **not** validate spatial box alignment on
rendered images. Be conservative in the final decision.

## 1. Prep the Repo

From the repo root:

```bash
cd /path/to/folio.love
git checkout main
git pull
```

If `.venv` already exists and works, keep it. If not:

```bash
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

Sanity check:

```bash
.venv/bin/python -m pytest tests/test_inspect.py -q
```

## 2. Build a Small Real Corpus

Create one folder with 5-10 representative real PDFs.

Use PDFs only. If your source files are PPTX, export them to PDF first.

Include a spread:

- 2 simple diagrams
- 2 medium diagrams
- 2 dense or small-label diagrams
- 1 mixed text + diagram page if available
- 1 rasterized or scan-like export if that exists in your real workflow

Do not cherry-pick only easy examples.

Example:

```bash
mkdir -p ~/tmp/diagram_som_corpus
# copy your PDFs into that folder
```

## 3. Run the Validation

Replace `CORPUS_DIR` with your folder path.

```bash
cd /path/to/folio.love
CORPUS_DIR=~/tmp/diagram_som_corpus
REPORT=tmp/som_validation_$(date +%Y%m%d_%H%M%S).json
mkdir -p tmp

.venv/bin/python - "$CORPUS_DIR" <<'PY' > "$REPORT"
from pathlib import Path
from folio.pipeline.inspect import inspect_pages
import json
import sys

corpus = Path(sys.argv[1]).expanduser().resolve()
pdfs = sorted(corpus.glob("*.pdf"))
if not pdfs:
    raise SystemExit(f"No PDFs found in {corpus}")

all_diag = []
all_medium_dense = []
per_pdf = []

for pdf in pdfs:
    profiles = inspect_pages(pdf)
    class_counts = {}
    diagram_like = []
    medium_dense = []

    for page_num, p in profiles.items():
        class_counts[p.classification] = class_counts.get(p.classification, 0) + 1

        page_row = {
            "page": page_num,
            "classification": p.classification,
            "escalation_level": p.escalation_level,
            "word_count": p.word_count,
            "bounded_text_count": len(p.bounded_texts),
            "vector_count": p.vector_count,
            "has_images": p.has_images,
            "som_viable": p.som_viable,
        }

        if p.classification in {"diagram", "mixed", "unsupported_diagram"}:
            diagram_like.append(page_row)
            all_diag.append(page_row)
            if p.escalation_level in {"medium", "dense"}:
                medium_dense.append(page_row)
                all_medium_dense.append(page_row)

    per_pdf.append({
        "pdf": str(pdf),
        "total_pages": len(profiles),
        "class_counts": class_counts,
        "diagram_like_pages": len(diagram_like),
        "diagram_like_som_true": sum(1 for x in diagram_like if x["som_viable"]),
        "diagram_like_som_rate": round(
            sum(1 for x in diagram_like if x["som_viable"]) / len(diagram_like), 3
        ) if diagram_like else None,
        "medium_dense_pages": len(medium_dense),
        "medium_dense_som_true": sum(1 for x in medium_dense if x["som_viable"]),
        "medium_dense_som_rate": round(
            sum(1 for x in medium_dense if x["som_viable"]) / len(medium_dense), 3
        ) if medium_dense else None,
        "failing_pages": [x for x in diagram_like if not x["som_viable"]],
    })

overall = {
    "pdf_count": len(pdfs),
    "diagram_like_pages": len(all_diag),
    "diagram_like_som_true": sum(1 for x in all_diag if x["som_viable"]),
    "diagram_like_som_rate": round(
        sum(1 for x in all_diag if x["som_viable"]) / len(all_diag), 3
    ) if all_diag else None,
    "medium_dense_pages": len(all_medium_dense),
    "medium_dense_som_true": sum(1 for x in all_medium_dense if x["som_viable"]),
    "medium_dense_som_rate": round(
        sum(1 for x in all_medium_dense if x["som_viable"]) / len(all_medium_dense), 3
    ) if all_medium_dense else None,
}

print(json.dumps({
    "corpus_dir": str(corpus),
    "pdfs": per_pdf,
    "overall": overall,
}, indent=2))
PY

cat "$REPORT"
```

## 4. Paste the JSON Back

Paste the full JSON report into the orchestrator thread.

The orchestrator should make the final gate call from that output.

## 5. Provisional Local Decision Rule

If an immediate local answer is needed before the orchestrator responds:

- choose `SoM viable` only if:
  - at least 10 diagram/mixed pages total
  - `overall.diagram_like_som_rate >= 0.85`
  - `overall.medium_dense_som_rate >= 0.75`
  - no obvious systematic failures on dense pages
- otherwise choose `SoM not viable -> tiles`

This rule is intentionally conservative because current `som_viable` is
lexical-only.

## 6. Record the Result

Capture these in the closeout note or PR 2 handoff:

- corpus folder used
- total PDFs tested
- total diagram/mixed pages
- overall `som_viable` rate
- medium/dense `som_viable` rate
- concrete failure modes
- final decision:
  - `SoM viable for PR 2`
  - or `SoM not viable - PR 2 uses tiles fallback`

## Checklist Notes to Carry Forward

PR 1 was not review-clean. Keep these in the PR 2 checklist:

- `som_viable` is lexical-only, not spatial-overlay validated
- `image_blank` was added; PR 2 must preserve the hybrid blank gating behavior
- `pdfium -> pdfplumber` fallback exists for soft text-extraction failure
- `inspect_pages()` degrades per-page failures instead of crashing the document
