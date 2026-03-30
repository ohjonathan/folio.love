#!/usr/bin/env python3
"""Phase 4 validation: frontmatter, markdown structure, and silent failure detection."""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml


OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# --- Schema constants from Folio Ontology Architecture v2 ---

BASE_REQUIRED_FIELDS = [
    "id", "title", "type", "subtype", "status", "authority",
    "curation_level", "source_hash", "version", "created", "modified",
    "converted",
]
REQUIRED_EVIDENCE_FIELDS = ["source", "source_type", "slide_count"]
REQUIRED_INTERACTION_FIELDS = ["source_transcript", "date", "impacts"]

ALLOWED_TYPES = {"context", "analysis", "evidence", "deliverable", "reference", "interaction", "diagram"}
ALLOWED_SUBTYPES_EVIDENCE = {"research", "data_extract", "external_report", "benchmark"}
ALLOWED_SUBTYPES_INTERACTION = {
    "client_meeting", "expert_interview", "internal_sync", "partner_check_in", "workshop",
}
ALLOWED_STATUS = {"active", "draft", "archived", "superseded", "complete"}
ALLOWED_AUTHORITY = {"captured", "analyzed", "aligned", "decided"}
ALLOWED_CURATION_LEVELS = {"L0", "L1", "L2", "L3"}
ALLOWED_SOURCE_TYPES = {"deck", "pdf", "report"}

ALLOWED_SLIDE_TYPES = {
    "title", "executive-summary", "framework", "data", "narrative",
    "next-steps", "appendix", "pending", "unknown",
}
ALLOWED_FRAMEWORKS = {
    "2x2-matrix", "scr", "mece", "waterfall", "gantt", "timeline",
    "process-flow", "org-chart", "tam-sam-som", "porter-five-forces",
    "value-chain", "bcg-matrix", "none", "pending",
}

GROUNDING_SUMMARY_FIELDS = [
    "total_claims", "high_confidence", "medium_confidence",
    "low_confidence", "validated", "unvalidated",
]


def validate_deck(md_path: Path) -> dict:
    """Validate a single converted markdown file. Returns a result dict."""
    result = {
        "file": md_path.name,
        "dir": md_path.parent.name,
        "errors": [],
        "warnings": [],
        "metrics": {},
    }

    content = md_path.read_text()

    # --- 4.1 Frontmatter Validation ---
    fm = _parse_frontmatter(content, result)
    if fm is None:
        result["errors"].append(("Silent-Invalid-YAML", "Failed to parse YAML frontmatter"))
        return result

    # PR 6: Diagram notes have different required fields
    if fm.get("type") == "diagram":
        _validate_diagram_note(fm, result)
        return result

    if fm.get("type") == "interaction":
        _validate_required_fields(fm, result, "interaction")
        _validate_field_types(fm, result, "interaction")
        _validate_enum_values(fm, result)
        _validate_grounding_summary(fm, result)
        _validate_version_fields(fm, result)
        _validate_llm_metadata(fm, result)
        _validate_interaction_markdown_structure(content, result)
        return result

    if fm.get("type") == "context":
        _validate_context_note(fm, content, result)
        return result

    _validate_required_fields(fm, result, "evidence")
    _validate_field_types(fm, result, "evidence")
    _validate_enum_values(fm, result)
    _validate_grounding_summary(fm, result)
    _validate_version_fields(fm, result)
    _validate_llm_metadata(fm, result)

    # --- 4.2 Markdown Structure Validation ---
    slide_count_fm = fm.get("slide_count", 0)
    slides_in_body = _validate_markdown_structure(content, slide_count_fm, result)

    # --- 4.3 Silent Failure Detection ---
    _detect_silent_failures(content, fm, slides_in_body, result)

    return result


def _parse_frontmatter(content: str, result: dict) -> dict | None:
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        result["errors"].append(("Silent-Invalid-YAML", "No opening --- fence"))
        return None
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        result["errors"].append(("Silent-Invalid-YAML", "No closing --- fence"))
        return None
    yaml_block = "\n".join(lines[1:end_idx])
    try:
        fm = yaml.safe_load(yaml_block)
        if not isinstance(fm, dict):
            result["errors"].append(("Silent-Invalid-YAML", "Frontmatter is not a dict"))
            return None
        return fm
    except yaml.YAMLError as e:
        result["errors"].append(("Silent-Invalid-YAML", f"YAML parse error: {e}"))
        return None


def _validate_required_fields(fm: dict, result: dict, doc_type: str):
    required_fields = list(BASE_REQUIRED_FIELDS)
    if doc_type == "interaction":
        required_fields.extend(REQUIRED_INTERACTION_FIELDS)
    else:
        required_fields.extend(REQUIRED_EVIDENCE_FIELDS)

    for field in required_fields:
        if field not in fm:
            result["errors"].append(("Silent-Malformed-Frontmatter", f"Missing required field: {field}"))
        elif fm[field] is None or (isinstance(fm[field], str) and not fm[field].strip()):
            result["errors"].append(("Silent-Malformed-Frontmatter", f"Empty required field: {field}"))


def _validate_field_types(fm: dict, result: dict, doc_type: str):
    type_checks: dict[str, type] = {
        "id": str, "title": str, "type": str, "subtype": str,
        "status": str, "authority": str, "curation_level": str,
        "source_hash": str, "version": int,
    }
    if doc_type == "interaction":
        type_checks.update({
            "source_transcript": str,
            "date": str,
        })
        optional_type_checks = {
            "duration_minutes": int,
        }
    else:
        type_checks.update({
            "source": str,
            "source_type": str,
            "slide_count": int,
        })
        optional_type_checks = {}
    for field, expected_type in type_checks.items():
        if field in fm and fm[field] is not None:
            if not isinstance(fm[field], expected_type):
                result["errors"].append((
                    "Silent-Malformed-Frontmatter",
                    f"Field '{field}' should be {expected_type.__name__}, got {type(fm[field]).__name__}",
                ))

    for field, expected_type in optional_type_checks.items():
        if field in fm and fm[field] is not None and not isinstance(fm[field], expected_type):
            result["errors"].append((
                "Silent-Malformed-Frontmatter",
                f"Field '{field}' should be {expected_type.__name__}, got {type(fm[field]).__name__}",
            ))

    list_fields = ["frameworks", "slide_types", "tags", "industry", "impacts", "participants"]
    for field in list_fields:
        if field in fm and fm[field] is not None:
            if not isinstance(fm[field], list):
                result["errors"].append((
                    "Silent-Malformed-Frontmatter",
                    f"Field '{field}' should be list, got {type(fm[field]).__name__}",
                ))


def _validate_enum_values(fm: dict, result: dict):
    if fm.get("type") and fm["type"] not in ALLOWED_TYPES:
        result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid type: {fm['type']}"))
    if fm.get("type") == "interaction":
        if fm.get("subtype") and fm["subtype"] not in ALLOWED_SUBTYPES_INTERACTION:
            result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid interaction subtype: {fm['subtype']}"))
    elif fm.get("subtype") and fm["subtype"] not in ALLOWED_SUBTYPES_EVIDENCE:
        result["warnings"].append(f"Unusual subtype: {fm['subtype']}")
    if fm.get("status") and fm["status"] not in ALLOWED_STATUS:
        result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid status: {fm['status']}"))
    if fm.get("authority") and fm["authority"] not in ALLOWED_AUTHORITY:
        result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid authority: {fm['authority']}"))
    if fm.get("curation_level") and fm["curation_level"] not in ALLOWED_CURATION_LEVELS:
        result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid curation_level: {fm['curation_level']}"))
    if fm.get("source_type") and fm["source_type"] not in ALLOWED_SOURCE_TYPES:
        result["errors"].append(("Silent-Malformed-Frontmatter", f"Invalid source_type: {fm['source_type']}"))

    if isinstance(fm.get("slide_types"), list):
        for st in fm["slide_types"]:
            if st not in ALLOWED_SLIDE_TYPES:
                result["warnings"].append(f"Non-standard slide_type: {st}")
    if isinstance(fm.get("frameworks"), list):
        for fw in fm["frameworks"]:
            if fw not in ALLOWED_FRAMEWORKS:
                result["warnings"].append(f"Non-standard framework: {fw}")


def _validate_grounding_summary(fm: dict, result: dict):
    gs = fm.get("grounding_summary")
    if gs is None:
        result["warnings"].append("grounding_summary missing")
        return
    if not isinstance(gs, dict):
        result["errors"].append(("Silent-Malformed-Frontmatter", "grounding_summary is not a dict"))
        return
    for field in GROUNDING_SUMMARY_FIELDS:
        if field not in gs:
            result["errors"].append(("Silent-Malformed-Frontmatter", f"grounding_summary missing: {field}"))
        elif not isinstance(gs[field], int):
            result["errors"].append((
                "Silent-Malformed-Frontmatter",
                f"grounding_summary.{field} should be int, got {type(gs[field]).__name__}",
            ))

    result["metrics"]["total_claims"] = gs.get("total_claims", 0)
    result["metrics"]["validated"] = gs.get("validated", 0)
    result["metrics"]["unvalidated"] = gs.get("unvalidated", 0)
    total = gs.get("total_claims", 0)
    validated = gs.get("validated", 0)
    result["metrics"]["validation_rate"] = validated / total if total > 0 else 0.0


def _validate_version_fields(fm: dict, result: dict):
    if "version" not in fm:
        result["errors"].append(("Silent-Malformed-Frontmatter", "Missing version field"))
    if "created" not in fm:
        result["errors"].append(("Silent-Malformed-Frontmatter", "Missing created field"))
    if "modified" not in fm:
        result["errors"].append(("Silent-Malformed-Frontmatter", "Missing modified field"))
    if "converted" not in fm:
        result["errors"].append(("Silent-Malformed-Frontmatter", "Missing converted field"))


def _validate_llm_metadata(fm: dict, result: dict):
    llm = fm.get("_llm_metadata")
    if llm is None:
        result["warnings"].append("_llm_metadata missing")
        return
    if not isinstance(llm, dict):
        result["errors"].append(("Silent-Malformed-Frontmatter", "_llm_metadata is not a dict"))
        return
    for route_name, route_data in llm.items():
        if not isinstance(route_data, dict):
            continue
        result["metrics"]["llm_provider"] = route_data.get("provider", "unknown")
        result["metrics"]["llm_model"] = route_data.get("model", "unknown")
        result["metrics"]["llm_status"] = route_data.get("status", "unknown")
        result["metrics"]["llm_fallback_used"] = route_data.get("fallback_used", False)
        if route_data.get("status") not in ("executed", "skipped", "pending"):
            result["warnings"].append(f"_llm_metadata.{route_name}.status unexpected: {route_data.get('status')}")


def _validate_markdown_structure(content: str, expected_slides: int, result: dict) -> int:
    slide_sections = re.findall(r"^## Slide \d+", content, re.MULTILINE)
    actual_slides = len(slide_sections)
    result["metrics"]["slides_in_body"] = actual_slides
    result["metrics"]["expected_slides"] = expected_slides

    if actual_slides != expected_slides:
        result["errors"].append((
            "Silent-Missing-Content",
            f"Slide count mismatch: frontmatter says {expected_slides}, body has {actual_slides} sections",
        ))

    analysis_blocks = re.findall(r"^### Analysis", content, re.MULTILINE)
    result["metrics"]["analysis_blocks"] = len(analysis_blocks)
    # M2 fix: diagram transclusions replace ### Analysis blocks;
    # count them toward expected analysis coverage
    transclusion_blocks = len(re.findall(r"^!\[\[.*?#Diagram\]\]", content, re.MULTILINE))
    result["metrics"]["transclusion_blocks"] = transclusion_blocks
    total_coverage = len(analysis_blocks) + transclusion_blocks
    if total_coverage < actual_slides:
        result["warnings"].append(
            f"Missing analysis blocks: {total_coverage} of {actual_slides} slides"
        )

    text_blocks = re.findall(r"^### Text \(Verbatim\)", content, re.MULTILINE)
    result["metrics"]["text_blocks"] = len(text_blocks)

    image_refs = re.findall(r"!\[Slide \d+\]\(([^)]+)\)", content)
    result["metrics"]["image_refs"] = len(image_refs)

    if content.rstrip().endswith("---"):
        pass
    elif re.search(r"## Slide \d+[^#]*$", content) and not content.rstrip().endswith("---"):
        last_section = content.split("## Slide")[-1]
        if "### Analysis" not in last_section and "### Text" not in last_section:
            result["errors"].append(("Silent-Missing-Content", "File appears truncated"))

    return actual_slides


def _detect_silent_failures(content: str, fm: dict, slides_in_body: int, result: dict):
    slide_types = []
    frameworks = []
    all_pending = True

    for m in re.finditer(r"\*\*Slide Type:\*\* (\S+)", content):
        st = m.group(1)
        slide_types.append(st)
        if st not in ("pending", "unknown"):
            all_pending = False

    for m in re.finditer(r"\*\*Framework:\*\* (\S+)", content):
        frameworks.append(m.group(1))

    result["metrics"]["slide_type_counts"] = dict(Counter(slide_types))
    result["metrics"]["framework_counts"] = dict(Counter(frameworks))
    result["metrics"]["unknown_type_count"] = slide_types.count("unknown")
    result["metrics"]["pending_type_count"] = slide_types.count("pending")
    result["metrics"]["none_framework_count"] = frameworks.count("none")

    if all_pending and slides_in_body > 0:
        result["errors"].append((
            "Silent-Wrong-Output",
            "All slides have 'pending' analysis — LLM analysis likely failed silently",
        ))

    evidence_entries = re.findall(r"^- \*\*(.+?) \((\w+)(?:, pass \d+)?\):\*\*", content, re.MULTILINE)
    result["metrics"]["evidence_count"] = len(evidence_entries)
    if evidence_entries:
        confidence_counts = Counter(conf for _, conf in evidence_entries)
        result["metrics"]["evidence_confidence"] = dict(confidence_counts)

    analyses = []
    for m in re.finditer(
        r"\*\*Slide Type:\*\* (\S+)\s+\n\*\*Framework:\*\* (\S+)\s+\n"
        r"\*\*Visual Description:\*\* (.+?)\s+\n\*\*Key Data:\*\* (.+?)\s+\n"
        r"\*\*Main Insight:\*\* (.+)",
        content,
    ):
        analyses.append(m.groups())

    if len(analyses) >= 2:
        seen = set()
        for a in analyses:
            key = (a[0], a[1], a[4])
            if key in seen and key[0] != "pending":
                result["errors"].append((
                    "Silent-Wrong-Output",
                    f"Duplicate analysis detected: type={a[0]}, framework={a[1]}",
                ))
                break
            seen.add(key)

    gs = fm.get("grounding_summary", {})
    total_claims_fm = gs.get("total_claims", 0)
    evidence_in_body = len(evidence_entries)
    result["metrics"]["claims_match"] = total_claims_fm == evidence_in_body
    if total_claims_fm != evidence_in_body and total_claims_fm > 0:
        result["warnings"].append(
            f"Grounding mismatch: frontmatter total_claims={total_claims_fm}, "
            f"body evidence count={evidence_in_body}"
        )


def _validate_interaction_markdown_structure(content: str, result: dict):
    required_sections = [
        "## Summary",
        "## Key Findings",
        "## Entities Mentioned",
        "## Quotes / Evidence",
        "## Impact on Hypotheses",
    ]
    for section in required_sections:
        if section not in content:
            result["errors"].append((
                "Silent-Missing-Content",
                f"Interaction note missing required section: {section}",
            ))
    if "> [!quote]- Raw Transcript" not in content:
        result["errors"].append((
            "Silent-Missing-Content",
            "Interaction note missing raw transcript callout",
        ))


def _validate_diagram_note(fm: dict, result: dict):
    """Validate a standalone diagram note (type: diagram)."""
    required = [
        "type", "diagram_type", "title", "source_deck", "source_page",
        "extraction_confidence", "confidence_reasoning",
        "review_required", "review_questions", "abstained",
        "folio_freeze", "tags", "_review_history",
    ]
    for field in required:
        if field not in fm:
            result["errors"].append(
                ("Silent-Malformed-Frontmatter", f"Diagram note missing: {field}")
            )
        elif fm[field] is None and field not in ("review_questions", "_review_history"):
            result["errors"].append(
                ("Silent-Malformed-Frontmatter", f"Diagram note null field: {field}")
            )
    # Type-check optional fields when present
    if "components" in fm and not isinstance(fm["components"], list):
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", "components must be list")
        )
    if "technologies" in fm and not isinstance(fm["technologies"], list):
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", "technologies must be list")
        )
    if "_extraction_metadata" in fm and not isinstance(fm["_extraction_metadata"], dict):
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", "_extraction_metadata must be dict")
        )
    # Must NOT have deck-only fields
    for deck_field in ("source", "source_hash", "source_type"):
        if deck_field in fm:
            result["errors"].append(
                ("Silent-Malformed-Frontmatter",
                 f"Diagram note must not contain deck field: {deck_field}")
            )

    # S-NEW-4 fix: warn on zero confidence with non-abstained (likely pipeline bug)
    conf = fm.get("extraction_confidence")
    abstained = fm.get("abstained", False)
    if conf is not None and conf == 0.0 and not abstained:
        result["warnings"].append(
            "extraction_confidence is 0.0 on non-abstained diagram — may indicate pipeline failure"
        )

    # m9 doc: frozen mixed slides intentionally retain Pass 1 LLM cost because
    # the consulting analysis portion still needs fresh extraction. This is
    # documented behavior, not a bug. Only the diagram extraction/rendering
    # portions are bypassed on frozen mixed pages.


# --- Context document validation ---

_ALLOWED_SUBTYPES_CONTEXT = {"engagement", "client_profile", "workstream"}

_CONTEXT_REQUIRED_FIELDS = [
    "id", "title", "type", "subtype", "status", "authority",
    "curation_level", "review_status", "review_flags",
    "extraction_confidence",
    "client", "tags", "created", "modified",
]

# engagement is required only for subtype=engagement
_CONTEXT_ENGAGEMENT_REQUIRED_FIELDS = ["engagement"]

_CONTEXT_REQUIRED_BODY_SECTIONS = [
    "## Client Background",
    "## Engagement Snapshot",
    "## Objectives / SOW",
    "## Timeline",
    "## Team",
    "## Stakeholders",
    "## Starting Hypotheses",
    "## Risks / Open Questions",
]


def _validate_context_note(fm: dict, content: str, result: dict):
    """Validate a context document (type: context)."""
    # Required fields (common to all context subtypes)
    for field_name in _CONTEXT_REQUIRED_FIELDS:
        if field_name not in fm:
            result["errors"].append(
                ("Silent-Malformed-Frontmatter", f"Context note missing: {field_name}")
            )
        elif fm[field_name] is None and field_name not in ("extraction_confidence",):
            result["errors"].append(
                ("Silent-Malformed-Frontmatter", f"Context note null field: {field_name}")
            )

    # engagement is required only for subtype=engagement
    if fm.get("subtype") == "engagement":
        for field_name in _CONTEXT_ENGAGEMENT_REQUIRED_FIELDS:
            if field_name not in fm:
                result["errors"].append(
                    ("Silent-Malformed-Frontmatter",
                     f"Context note (subtype=engagement) missing: {field_name}")
                )
            elif fm[field_name] is None:
                result["errors"].append(
                    ("Silent-Malformed-Frontmatter",
                     f"Context note (subtype=engagement) null field: {field_name}")
                )

    # extraction_confidence must be explicitly null
    if "extraction_confidence" in fm and fm["extraction_confidence"] is not None:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter",
             "Context note extraction_confidence must be null")
        )

    # Subtype validation
    if fm.get("subtype") and fm["subtype"] not in _ALLOWED_SUBTYPES_CONTEXT:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", f"Invalid context subtype: {fm['subtype']}")
        )

    # review_status must be "clean" for context docs (hard-fail)
    if fm.get("review_status") != "clean":
        result["errors"].append(
            ("Silent-Malformed-Frontmatter",
             f"Context note review_status is '{fm.get('review_status')}', must be 'clean'")
        )

    # review_flags must be empty list (hard-fail)
    if fm.get("review_flags") and len(fm["review_flags"]) > 0:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter",
             f"Context note has non-empty review_flags: {fm['review_flags']}")
        )

    # Must NOT have source-backed fields
    _source_backed_fields = ("source", "source_hash", "source_type", "slide_count",
                             "version", "converted", "source_transcript", "date")
    source_field_hits = [f for f in _source_backed_fields if f in fm]
    for source_field in source_field_hits:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter",
             f"Context note must not contain source field: {source_field}")
        )

    # Spoof detection: if 3+ source-backed fields are present, this looks
    # like an evidence/interaction note masquerading as type: context.
    if len(source_field_hits) >= 3:
        result["errors"].append(
            ("Spoof-Detection",
             f"Context note contains {len(source_field_hits)} source-backed fields "
             f"({', '.join(source_field_hits)}); likely an evidence-shaped note "
             f"mislabelled as type: context")
        )

    # Must NOT have evidence-only generated fields
    for gen_field in ("grounding_summary", "_llm_metadata"):
        if gen_field in fm:
            result["errors"].append(
                ("Silent-Malformed-Frontmatter",
                 f"Context note must not contain generated field: {gen_field}")
            )

    # Validate enum values shared with other types
    if fm.get("status") and fm["status"] not in ALLOWED_STATUS:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", f"Invalid status: {fm['status']}")
        )
    if fm.get("authority") and fm["authority"] not in ALLOWED_AUTHORITY:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", f"Invalid authority: {fm['authority']}")
        )
    if fm.get("curation_level") and fm["curation_level"] not in ALLOWED_CURATION_LEVELS:
        result["errors"].append(
            ("Silent-Malformed-Frontmatter", f"Invalid curation_level: {fm['curation_level']}")
        )

    # Required body sections
    for section in _CONTEXT_REQUIRED_BODY_SECTIONS:
        if section not in content:
            result["errors"].append(
                ("Silent-Missing-Content",
                 f"Context note missing required section: {section}")
            )

def validate_all() -> list[dict]:
    """Validate all converted markdown files in the output directory."""
    results = []
    md_files = sorted(OUTPUT_DIR.rglob("*.md"))
    if not md_files:
        print("ERROR: No markdown files found in output directory")
        return results

    print(f"Validating {len(md_files)} converted decks...\n")

    for md_path in md_files:
        result = validate_deck(md_path)
        results.append(result)

        status = "PASS" if not result["errors"] else "FAIL"
        error_count = len(result["errors"])
        warn_count = len(result["warnings"])
        metrics = result["metrics"]
        print(
            f"  [{status}] {result['dir']}: "
            f"{metrics.get('expected_slides', '?')} slides, "
            f"{metrics.get('evidence_count', 0)} evidence, "
            f"{metrics.get('validation_rate', 0):.0%} validated"
            f"{f', {error_count} errors' if error_count else ''}"
            f"{f', {warn_count} warnings' if warn_count else ''}"
        )
        if result["errors"]:
            for etype, emsg in result["errors"]:
                print(f"    ERROR [{etype}]: {emsg}")

    return results


def print_summary(results: list[dict]):
    """Print validation summary tables."""
    total = len(results)
    passed = sum(1 for r in results if not r["errors"])
    failed = total - passed

    all_errors = []
    for r in results:
        for etype, emsg in r["errors"]:
            all_errors.append((r["dir"], etype, emsg))

    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total decks validated: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if all_errors:
        print(f"\n--- Failure Catalog ({len(all_errors)} errors) ---")
        error_types = Counter(etype for _, etype, _ in all_errors)
        for etype, count in error_types.most_common():
            print(f"  {etype}: {count}")
        print()
        for deck, etype, emsg in all_errors:
            print(f"  [{etype}] {deck}: {emsg}")

    all_evidence = [r["metrics"].get("evidence_count", 0) for r in results]
    all_vrates = [r["metrics"].get("validation_rate", 0) for r in results if r["metrics"].get("total_claims", 0) > 0]
    all_unknown = [r["metrics"].get("unknown_type_count", 0) for r in results]
    all_pending = [r["metrics"].get("pending_type_count", 0) for r in results]
    all_none_fw = [r["metrics"].get("none_framework_count", 0) for r in results]
    all_claims_match = [r["metrics"].get("claims_match", False) for r in results]

    print(f"\n--- Quality Distribution ---")
    if all_evidence:
        print(f"Evidence count:      min={min(all_evidence)}, max={max(all_evidence)}, "
              f"median={sorted(all_evidence)[len(all_evidence)//2]}")
    if all_vrates:
        print(f"Validation rate:     min={min(all_vrates):.0%}, max={max(all_vrates):.0%}, "
              f"median={sorted(all_vrates)[len(all_vrates)//2]:.0%}")
    if all_unknown:
        print(f"Unknown types/deck:  min={min(all_unknown)}, max={max(all_unknown)}, "
              f"median={sorted(all_unknown)[len(all_unknown)//2]}")
    if all_pending:
        print(f"Pending types/deck:  min={min(all_pending)}, max={max(all_pending)}, "
              f"median={sorted(all_pending)[len(all_pending)//2]}")
    if all_none_fw:
        print(f"'none' fw/deck:      min={min(all_none_fw)}, max={max(all_none_fw)}, "
              f"median={sorted(all_none_fw)[len(all_none_fw)//2]}")
    claims_accurate = sum(1 for c in all_claims_match if c)
    print(f"Grounding accuracy:  {claims_accurate}/{total} decks match (frontmatter vs body)")

    # Save results as JSON for report generation
    output_path = Path(__file__).resolve().parent / "validation_results.json"
    serializable = []
    for r in results:
        serializable.append({
            "file": r["file"],
            "dir": r["dir"],
            "errors": [(t, m) for t, m in r["errors"]],
            "warnings": r["warnings"],
            "metrics": r["metrics"],
        })
    output_path.write_text(json.dumps(serializable, indent=2))
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    results = validate_all()
    print_summary(results)
    sys.exit(1 if any(r["errors"] for r in results) else 0)
