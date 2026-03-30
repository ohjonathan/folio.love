"""Tier 3 lifecycle integration test (spec §8).

Simulates a synthetic engagement lifecycle covering the 14 steps from §8.2
and the 12 required assertions from §8.6:

  context init → seed evidence (with supersedes) → entity import →
  entity confirm → ingest (mocked LLM) → entity stubs → enrich (mocked LLM) →
  provenance (mocked LLM) → confirm-doc → status / scan / refresh → final status

Steps that cross LLM boundaries (ingest analysis, enrich, provenance) are
mocked at the analysis-function level so the pipeline executes end-to-end
without real API calls.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from dataclasses import field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from folio.cli import cli
from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute
from folio.context import create_context_document
from folio.tracking import registry
from folio.tracking.registry import RegistryEntry, entry_from_dict, load_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_folio_yaml(root: Path, *, source_dirs: list[Path] | None = None) -> Path:
    """Write a folio.yaml and return its path.

    Includes source roots when provided so that `folio scan` exercises
    the context-row guard (S-1).
    """
    folio_yaml = root / "folio.yaml"
    lib = root / "library"
    lines = [
        f"library_root: {lib}",
    ]
    if source_dirs:
        lines.append("sources:")
        for idx, src_dir in enumerate(source_dirs):
            lines.append(f"  - name: source-{idx}")
            lines.append(f"    path: {src_dir}")
    # Add minimal LLM config so enrich/provenance can find a route
    lines += [
        "llm:",
        "  profiles:",
        "    default:",
        "      provider: anthropic",
        "      model: test-model",
        "  routing:",
        "    default:",
        "      primary: default",
        "    enrich:",
        "      primary: default",
        "    provenance:",
        "      primary: default",
        "    ingest:",
        "      primary: default",
    ]
    folio_yaml.write_text("\n".join(lines) + "\n")
    return folio_yaml


def _make_evidence_note(
    library: Path, *, deck_id: str, title: str, source_path: Path,
    source_hash: str, client: str, engagement: str, subtype: str = "research",
    supersedes: str | None = None,
    extra_fm: dict | None = None,
) -> Path:
    """Write a synthetic evidence note with deterministic evidence blocks."""
    client_token = client.lower().replace(" ", "")
    deck_dir = library / client_token / f"deck_{deck_id.split('_')[-1]}"
    deck_dir.mkdir(parents=True, exist_ok=True)
    md_path = deck_dir / f"{deck_id.split('_')[-1]}.md"

    fm: dict = {
        "id": deck_id,
        "title": title,
        "type": "evidence",
        "subtype": subtype,
        "status": "active",
        "authority": "captured",
        "curation_level": "L0",
        "source": str(source_path),
        "source_hash": source_hash,
        "source_type": "pdf",
        "version": 1,
        "slide_count": 3,
        "created": "2026-03-30",
        "modified": "2026-03-30",
        "converted": "2026-03-30T00:00:00Z",
        "client": client,
        "engagement": engagement,
        "review_status": "clean",
        "review_flags": [],
        "extraction_confidence": 0.85,
        "tags": ["research"],
        "grounding_summary": {
            "total_claims": 3,
            "high_confidence": 2,
            "medium_confidence": 1,
            "low_confidence": 0,
            "validated": 2,
            "unvalidated": 1,
        },
    }
    if supersedes:
        fm["supersedes"] = supersedes
    if extra_fm:
        fm.update(extra_fm)

    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    body = (
        f"---\n{yaml_str}---\n\n# {title}\n\n"
        f"**Source:** `{source_path.name}`\n\n---\n\n"
        "## Slide 1\n\n"
        "![Slide 1](slides/slide-001.png)\n\n"
        "### Text (Verbatim)\n\n"
        "> Original text.\n\n"
        "### Analysis\n\n"
        "**Slide Type:** data\n"
        "**Framework:** none\n"
        "**Visual Description:** Chart showing metrics.\n"
        "**Key Data:** Revenue growth is 15% YoY\n"
        "**Main Insight:** Growth observed.\n\n"
        "**Evidence:**\n"
        "- claim: Revenue growth is 15% YoY\n"
        '  - quote: "Revenue grew 15% YoY."\n'
        "  - confidence: high\n"
        "  - validated: yes\n"
        "- claim: Market share expanded to 40%\n"
        '  - quote: "Market share reached 40%."\n'
        "  - confidence: high\n"
        "  - validated: yes\n"
        "- claim: Cost savings total $10M\n"
        '  - quote: "Savings reached $10M."\n'
        "  - confidence: medium\n"
        "  - validated: yes\n\n"
        "---\n\n"
        "## Version History\n\n"
        "| Version | Date | Changes |\n"
        "|---------|------|---------|\n"
        "| 1 | 2026-03-30 | Initial |\n"
    )
    md_path.write_text(body)

    # Register it
    md_rel = str(md_path.relative_to(library)).replace("\\", "/")
    dd_rel = str(deck_dir.relative_to(library)).replace("\\", "/")
    entry = RegistryEntry(
        id=deck_id,
        title=title,
        markdown_path=md_rel,
        deck_dir=dd_rel,
        source_relative_path=str(source_path),
        source_hash=source_hash,
        source_type="pdf",
        version=1,
        converted="2026-03-30T00:00:00Z",
        type="evidence",
        subtype=subtype,
        client=client,
        engagement=engagement,
        authority="captured",
        curation_level="L0",
        staleness_status="current",
        review_status="clean",
        review_flags=[],
        extraction_confidence=0.85,
    )
    registry.upsert_entry(library / "registry.json", entry)
    return md_path


def _read_fm(path: Path) -> dict:
    content = path.read_text()
    if content.startswith("---\n"):
        end = content.index("\n---", 4)
        return yaml.safe_load(content[4:end]) or {}
    return {}


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------

class TestTier3Lifecycle:
    """End-to-end lifecycle covering all 12 assertions from spec §8.6."""

    def test_full_lifecycle(self, tmp_path):
        """Full 14-step lifecycle per §8.2 with all 12 assertions from §8.6."""
        # ----- Setup -----
        root = tmp_path
        source_dir = root / "sources"
        source_dir.mkdir()

        # Create source files for evidence notes and a transcript
        source_v1 = source_dir / "market_v1.pdf"
        source_v1.write_bytes(b"dummy PDF v1")
        source_v2 = source_dir / "market_v2.pdf"
        source_v2.write_bytes(b"dummy PDF v2")
        transcript_src = source_dir / "expert_interview.txt"
        transcript_src.write_text(
            "Alice Chen: Bob has been leading the intake redesign.\n\n"
            "Interviewer: What does the CEO want?\n\n"
            "Bob Martinez: The CEO wants Engineering to standardize.\n"
        )

        # Write folio.yaml WITH source roots (S-1 fix)
        folio_yaml = _write_folio_yaml(root, source_dirs=[source_dir])
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        runner = CliRunner()

        from folio.tracking.sources import compute_file_hash
        hash_v1 = compute_file_hash(source_v1)
        hash_v2 = compute_file_hash(source_v2)

        # ===== STEP 1 (§8.2 step 2): folio context init =====
        result = runner.invoke(cli, [
            "context", "init",
            "--client", "TestCo",
            "--engagement", "DD Q1 2026",
        ], obj={"config": config})
        assert result.exit_code == 0, f"context init failed: {result.output}"
        assert "Created context document" in result.output

        # -- Assertion 1: context file at canonical path --
        context_path = None
        for md_file in library.rglob("_context.md"):
            context_path = md_file
            break
        assert context_path is not None and context_path.exists(), (
            f"Context doc not found under {library}"
        )

        # -- Assertion 2: required frontmatter + body headings --
        ctx_content = context_path.read_text()
        ctx_fm = _read_fm(context_path)
        assert ctx_fm["type"] == "context"
        assert ctx_fm["subtype"] == "engagement"
        assert ctx_fm["review_status"] == "clean"
        assert ctx_fm["review_flags"] == []
        assert ctx_fm["extraction_confidence"] is None
        assert ctx_fm["authority"] == "aligned"
        assert ctx_fm["curation_level"] == "L1"
        for section in [
            "## Client Background", "## Engagement Snapshot",
            "## Objectives / SOW", "## Timeline", "## Team",
            "## Stakeholders", "## Starting Hypotheses",
            "## Risks / Open Questions",
        ]:
            assert section in ctx_content, f"Missing section: {section}"

        # -- Assertion 3: context doc in registry, round-trips --
        reg_data = load_registry(library / "registry.json")
        ctx_id = ctx_fm["id"]
        assert ctx_id in reg_data["decks"], "Context doc not in registry"
        ctx_row = reg_data["decks"][ctx_id]
        assert ctx_row["type"] == "context"
        assert ctx_row["subtype"] == "engagement"
        ctx_entry = entry_from_dict(ctx_row)
        assert ctx_entry.type == "context"
        assert ctx_entry.source_relative_path is None
        assert ctx_entry.source_hash is None

        # ===== STEP 2 (§8.2 step 3): Seed two evidence notes with supersedes =====
        ev_v1_path = _make_evidence_note(
            library,
            deck_id="testco_evidence_20260330_market_v1",
            title="Market Research v1",
            source_path=source_v1,
            source_hash=hash_v1,
            client="TestCo",
            engagement="DD Q1 2026",
        )
        ev_v2_path = _make_evidence_note(
            library,
            deck_id="testco_evidence_20260330_market_v2",
            title="Market Research v2",
            source_path=source_v2,
            source_hash=hash_v2,
            client="TestCo",
            engagement="DD Q1 2026",
            supersedes="testco_evidence_20260330_market_v1",
        )

        # ===== STEP 3 (§8.2 step 4): folio entities import =====
        # Write a CSV fixture
        csv_path = tmp_path / "org_chart.csv"
        csv_path.write_text(
            "name,title,department,reports_to,aliases\n"
            "Alice Chen,CEO,Executive,,Alice;the CEO\n"
            "Bob Martinez,CTO,Engineering,Alice Chen,Bob;the CTO\n"
        )
        result = runner.invoke(cli, [
            "entities", "import", str(csv_path),
        ], obj={"config": config})
        assert result.exit_code == 0, f"entities import failed: {result.output}"
        assert "Imported" in result.output

        # ===== STEP 4 (§8.2 step 5): Confirm entities =====
        # Imported entities from org-chart CSV are confirmed by default
        entities_path = library / "entities.json"
        assert entities_path.exists()
        ent_data = json.loads(entities_path.read_text())
        # Verify at least Alice and Bob were imported
        people = ent_data.get("entities", {}).get("person", {})
        assert len(people) >= 2, f"Expected >=2 people, got {len(people)}"

        # ===== STEP 5 (§8.2 step 6): folio ingest (mocked LLM) =====
        from folio.pipeline.interaction_analysis import (
            InteractionAnalysisResult as _IAR,
            InteractionFinding,
            InteractionQuote,
        )
        from folio.pipeline.entity_resolution import ResolutionResult as _RR

        mock_analysis = _IAR(
            summary="Team discussed prioritization.",
            tags=["expert-interview"],
            entities={
                "people": ["Alice Chen", "Bob Martinez"],
                "departments": ["Engineering"],
                "systems": [],
                "processes": [],
            },
            claims=[
                InteractionFinding(
                    statement="CEO wants standardization",
                    quote="The CEO wants Engineering to standardize.",
                    element_type="statement",
                    confidence="high",
                    validated=True,
                ),
            ],
            notable_quotes=[
                InteractionQuote(
                    quote="The CEO wants Engineering to standardize.",
                    element_type="statement",
                    confidence="high",
                    validated=True,
                ),
            ],
            review_status="clean",
            extraction_confidence=0.9,
            grounding_summary={
                "total_claims": 1, "high_confidence": 1,
                "medium_confidence": 0, "low_confidence": 0,
                "validated": 1, "unvalidated": 0,
            },
            llm_status="executed",
            provider_name="anthropic",
            model_name="test-model",
        )
        mock_resolution = _RR(
            entities={
                "people": ["Alice Chen", "Bob Martinez"],
                "departments": ["Engineering"],
                "systems": [],
                "processes": [],
            },
            warnings=[],
            created_entities=[],
        )

        with patch("folio.ingest.analyze_interaction_text", return_value=mock_analysis), \
             patch("folio.ingest.resolve_interaction_entities", return_value=mock_resolution):
            result = runner.invoke(cli, [
                "ingest", str(transcript_src),
                "--type", "expert_interview",
                "--date", "2026-03-30",
                "--client", "TestCo",
                "--engagement", "DD Q1 2026",
                "--participants", "Alice Chen, Bob Martinez",
            ], obj={"config": config})
        assert result.exit_code == 0, f"ingest failed: {result.output}"

        # -- Assertion 7: interaction ingest creates note with entity resolution --
        # Find the interaction note
        interaction_path = None
        for md_file in library.rglob("*.md"):
            fm = _read_fm(md_file)
            if fm.get("type") == "interaction":
                interaction_path = md_file
                break
        assert interaction_path is not None, "Interaction note not created"
        interaction_content = interaction_path.read_text()
        interaction_fm = _read_fm(interaction_path)
        assert interaction_fm["type"] == "interaction"
        assert "[[Alice Chen]]" in interaction_content, (
            "Entity resolution should have produced wikilinks for confirmed entities"
        )

        # ===== STEP 6 (§8.2 step 7): folio entities generate-stubs =====
        result = runner.invoke(cli, [
            "entities", "generate-stubs", "--force",
        ], obj={"config": config})
        assert result.exit_code == 0, f"generate-stubs failed: {result.output}"

        # -- Assertion 8: entity stubs created --
        entities_dir = library / "_entities"
        assert entities_dir.exists(), "_entities directory not created"
        stub_files = list(entities_dir.rglob("*.md"))
        assert len(stub_files) >= 2, f"Expected >=2 stubs, got {len(stub_files)}"

        # -- Assertion 9: org hierarchy fields on person stubs --
        person_stubs = list((entities_dir / "person").rglob("*.md")) if (entities_dir / "person").exists() else []
        if person_stubs:
            sample_stub = person_stubs[0].read_text()
            # Stubs from org-chart import should have hierarchy metadata
            # (title, department, or reports_to)
            assert any(
                field in sample_stub.lower()
                for field in ["title:", "department:", "reports_to:", "cto", "ceo"]
            ), "Org hierarchy fields missing from person stub"

        # ===== STEP 7 (§8.2 step 8): folio enrich (mocked LLM) =====
        from folio.pipeline.enrich_analysis import EnrichAnalysisOutput
        from folio.pipeline.entity_resolution import ResolutionResult

        mock_enrich_analysis = EnrichAnalysisOutput(
            tag_candidates=["market-sizing", "revenue"],
            entity_mention_candidates={"people": ["Alice Chen"], "systems": []},
            relationship_cues=[],
        )
        mock_resolution = ResolutionResult(
            entities={"people": ["Alice Chen"], "departments": [], "systems": [], "processes": []},
            warnings=[],
            created_entities=[],
            registry_changed=False,
        )

        with patch("folio.enrich.analyze_note_for_enrichment", return_value=mock_enrich_analysis), \
             patch("folio.enrich.resolve_entities", return_value=mock_resolution), \
             patch("folio.enrich.evaluate_relationships", return_value=[]):
            result = runner.invoke(cli, [
                "enrich",
            ], obj={"config": config})
        assert result.exit_code == 0, f"enrich failed: {result.output}"

        # -- Assertion 10: enrich updates evidence/interaction, ignores context --
        # Context doc should NOT have enrich metadata
        ctx_fm_after = _read_fm(context_path)
        assert "_llm_metadata" not in ctx_fm_after or \
               "enrich" not in ctx_fm_after.get("_llm_metadata", {}), \
            "Context doc should not be enriched"
        # Evidence notes SHOULD have enrich metadata from the mock
        ev_v2_fm_after_enrich = _read_fm(ev_v2_path)
        assert "_llm_metadata" in ev_v2_fm_after_enrich, (
            "Evidence note should have _llm_metadata after enrich"
        )
        assert "enrich" in ev_v2_fm_after_enrich.get("_llm_metadata", {}), (
            "Evidence note _llm_metadata should contain 'enrich' key after enrichment"
        )

        # ===== STEP 8 (§8.2 steps 9-10): folio provenance + confirm-doc =====
        from folio.pipeline.provenance_analysis import ProvenanceMatch

        # Mock returns a match using the C/T ref format that evaluate_provenance_matches uses
        # Note: _build_prompt_payload uses 1-based indexing (C1, T1, C2, T2, ...)
        mock_match = ProvenanceMatch(
            claim_ref="C1",
            target_ref="T1",
            confidence="high",
            rationale="Same revenue metric across versions.",
        )

        with patch("folio.provenance.evaluate_provenance_matches", return_value=[mock_match]):
            result = runner.invoke(cli, [
                "provenance",
            ], obj={"config": config})
        assert result.exit_code == 0, f"provenance failed: {result.output}"

        # Confirm proposals on the v2 note, scoped to the v1 target
        result = runner.invoke(cli, [
            "provenance", "confirm-doc",
            "testco_evidence_20260330_market_v2",
            "--target", "testco_evidence_20260330_market_v1",
        ], obj={"config": config})
        # confirm-doc may return 0 even if no proposals were found (just 0 confirmed)
        assert result.exit_code == 0, f"confirm-doc failed: {result.output}"

        # -- Assertion 11: provenance creates pair metadata and confirm-doc yields links --
        ev_v2_fm = _read_fm(ev_v2_path)
        # Check that provenance metadata AND confirmed links exist on v2
        has_provenance_meta = (
            "_llm_metadata" in ev_v2_fm
            and "provenance" in ev_v2_fm.get("_llm_metadata", {})
        )
        prov_links = ev_v2_fm.get("provenance_links", [])
        has_provenance_links = bool(prov_links)
        prov_pairs = ev_v2_fm.get("_llm_metadata", {}).get("provenance", {}).get("pairs", {})
        pair_info = {k: (v.get("status"), len(v.get("proposals", []))) for k, v in prov_pairs.items()} if isinstance(prov_pairs, dict) else {}
        assert has_provenance_meta and has_provenance_links, (
            f"v2 note should have provenance metadata AND confirmed links after provenance + confirm-doc. "
            f"meta={has_provenance_meta}, links={prov_links}, pairs={pair_info}"
        )
        # Assert the confirmed link references the correct target pair
        confirmed_links = [
            link for link in prov_links
            if isinstance(link, dict) and link.get("link_status") == "confirmed"
        ]
        assert len(confirmed_links) >= 1, (
            f"Expected at least one confirmed provenance link, got: {prov_links}"
        )
        assert any(
            link.get("target_doc") == "testco_evidence_20260330_market_v1"
            for link in confirmed_links
        ), (
            f"No confirmed link targets v1 (testco_evidence_20260330_market_v1). "
            f"Links: {confirmed_links}"
        )

        # ===== STEP 9 (§8.2 steps 11-14): status / scan / refresh =====
        # -- Assertion 4: status --refresh --
        result = runner.invoke(cli, [
            "status", "--refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"status failed: {result.output}"
        assert "documents" in result.output
        assert "By type:" in result.output
        assert "context" in result.output.lower()

        # -- Assertion 5: scan ignores context rows, exercises source-root guard --
        result = runner.invoke(cli, [
            "scan",
        ], obj={"config": config})
        assert result.exit_code == 0, f"scan failed: {result.output}"
        # With source roots configured, scan should actually exercise the guard
        # and NOT emit _context.md as a bogus source-backed entry
        assert "_context.md" not in result.output, (
            "Context doc should not appear in scan output"
        )

        # -- Assertion 6: refresh skips context doc --
        result = runner.invoke(cli, [
            "refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"refresh failed: {result.output}"
        assert "skipping context document" in result.output

        # ===== STEP 10: Final registry state =====
        final_reg = load_registry(library / "registry.json")

        # -- Assertion 12: final library has expected mix of types --
        types_present = {
            entry_from_dict(row).type
            for row in final_reg["decks"].values()
        }
        assert "context" in types_present, "context type missing from final registry"
        assert "evidence" in types_present, "evidence type missing from final registry"
        assert "interaction" in types_present, "interaction type missing from final registry"
        assert ctx_id in final_reg["decks"], "Context row still in registry"

        # Verify entity-stub files exist alongside registry docs
        assert entities_dir.exists(), "_entities still present"

        # ===== Duplicate guard =====
        result = runner.invoke(cli, [
            "context", "init",
            "--client", "TestCo",
            "--engagement", "DD Q1 2026",
        ], obj={"config": config})
        assert result.exit_code != 0, "Duplicate context init should fail"
        assert "already exists" in result.output

    def test_rebuild_preserves_context_during_corrupt_recovery(self, tmp_path):
        """Corrupt registry recovery must preserve context rows."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        ctx_id, ctx_path = create_context_document(
            config, client="Acme", engagement="Ops Sprint 2026",
        )
        assert ctx_path.exists()

        reg_path = library / "registry.json"
        reg_path.write_text("not valid json{{{")

        data = registry.rebuild_registry(library)
        assert ctx_id in data["decks"], "Context row lost during rebuild"
        assert data["decks"][ctx_id]["type"] == "context"

    def test_schema_v2_written_on_save(self, tmp_path):
        """Registry should write schema version 2."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        create_context_document(config, client="X", engagement="Y")

        reg_data = json.loads((library / "registry.json").read_text())
        assert reg_data["_schema_version"] == 2

    def test_status_no_crash_with_only_context(self, tmp_path):
        """status --refresh on a library with only context docs must not crash."""
        root = tmp_path
        folio_yaml = _write_folio_yaml(root)
        config = FolioConfig.load(folio_yaml)
        library = config.library_root.resolve()
        library.mkdir(parents=True, exist_ok=True)

        create_context_document(config, client="Solo", engagement="Only Context")

        runner = CliRunner()
        result = runner.invoke(cli, [
            "status", "--refresh",
        ], obj={"config": config})
        assert result.exit_code == 0, f"status failed: {result.output}"
        assert "documents" in result.output
