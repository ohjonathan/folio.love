#!/usr/bin/env python3
"""Dev iteration harness for diagram extraction prompt tuning.

Usage:
    python tools/diagram_iterate.py sample.pdf --page 3,5-7 --pass a
    python tools/diagram_iterate.py sample.pdf --page 3 --pass full --no-cache
    python tools/diagram_iterate.py sample.pdf --page 3 --pass b --out-dir tmp/iter/

Writes intermediate artifacts: raw LLM responses, parsed JSON, graph snapshots,
mutation logs, and final DiagramAnalysis.to_dict().
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _parse_page_spec(spec: str) -> list[int]:
    """Parse page spec like '3,5-7' into [3, 5, 6, 7]."""
    pages = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return sorted(set(pages))


def main():
    parser = argparse.ArgumentParser(
        description="Diagram extraction dev iteration harness",
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument(
        "--page", type=str, required=True,
        help="Page spec: '3', '3,5', or '3-7'",
    )
    parser.add_argument(
        "--pass", dest="pass_name", default="full",
        choices=["a", "b", "c", "sweep", "full"],
        help="Which pass to run (default: full)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--llm-profile", type=str, default=None)
    parser.add_argument(
        "--out-dir", type=Path, default=None,
        help="Output directory (default: tmp/diagram_iter/<pdf-stem>/)",
    )

    args = parser.parse_args()

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    pages = _parse_page_spec(args.page)
    out_dir = args.out_dir or Path(f"tmp/diagram_iter/{args.pdf.stem}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"PDF: {args.pdf}")
    print(f"Pages: {pages}")
    print(f"Pass: {args.pass_name}")
    print(f"Output: {out_dir}")
    print(f"Cache: {'disabled' if args.no_cache else 'enabled'}")

    # Import pipeline modules
    from folio.config import FolioConfig
    from folio.pipeline import inspect as page_inspect
    from folio.pipeline import images
    from folio.pipeline import diagram_extraction as diag_ext
    from folio.pipeline.text import extract_text

    # Load config
    config = FolioConfig.load()
    profile = config.llm.resolve_profile(override=args.llm_profile)

    # Step 1: Inspect pages
    print("\n--- Step 1: Inspecting pages ---")
    page_profiles = page_inspect.inspect_pages(args.pdf)
    for p in pages:
        pp = page_profiles.get(p)
        if pp:
            print(f"  Page {p}: {pp.classification} ({pp.escalation_level})")
        else:
            print(f"  Page {p}: NOT FOUND in profiles")

    # Step 2: Extract images
    print("\n--- Step 2: Extracting images ---")
    image_results = images.extract_with_metadata(
        args.pdf, out_dir, page_profiles=page_profiles,
    )

    # Step 3: Extract text
    print("\n--- Step 3: Extracting text ---")
    slide_texts = extract_text(args.pdf, pages=pages)

    # Step 4: Build pass-1 stubs (DiagramAnalysis placeholders)
    from folio.pipeline.analysis import DiagramAnalysis, SlideAnalysis
    pass1 = {}
    for p in pages:
        pp = page_profiles.get(p)
        dtype = pp.classification if pp else "unknown"
        pass1[p] = DiagramAnalysis(
            slide_type="diagram",
            diagram_type=dtype,
        )

    # Step 5: Run extraction
    print(f"\n--- Step 5: Running diagram extraction (pass={args.pass_name}) ---")
    results, stats, meta = diag_ext.analyze_diagram_pages(
        pass1_results=pass1,
        page_profiles=page_profiles,
        image_results=image_results,
        slide_texts=slide_texts,
        cache_dir=out_dir if not args.no_cache else None,
        force_miss=args.no_cache,
        provider_name=profile.provider,
        model=profile.model,
        api_key_env=profile.api_key_env,
        slide_numbers=pages,
    )

    # Step 6: Write artifacts
    print(f"\n--- Step 6: Writing artifacts to {out_dir} ---")
    for slide_num, result in sorted(results.items()):
        if isinstance(result, DiagramAnalysis):
            artifact_path = out_dir / f"slide_{slide_num:03d}_analysis.json"
            artifact_path.write_text(json.dumps(result.to_dict(), indent=2))
            print(f"  Wrote {artifact_path.name}")

            if result.graph:
                graph_path = out_dir / f"slide_{slide_num:03d}_graph.json"
                graph_path.write_text(json.dumps(result.graph.to_dict(), indent=2))
                print(f"  Wrote {graph_path.name}")

    # Summary
    print(f"\n--- Summary ---")
    print(f"Cache: {stats.hits} hits, {stats.misses} misses")
    print(f"Usage: {meta.usage_total.total_tokens} total tokens")
    for slide_num, result in sorted(results.items()):
        if isinstance(result, DiagramAnalysis):
            print(
                f"  Slide {slide_num}: type={result.diagram_type}, "
                f"confidence={result.diagram_confidence:.2f}, "
                f"nodes={len(result.graph.nodes) if result.graph else 0}, "
                f"edges={len(result.graph.edges) if result.graph else 0}"
            )


if __name__ == "__main__":
    main()
