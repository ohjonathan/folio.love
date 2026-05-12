"""Tests for document-oriented DOCX conversion."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from folio.config import FolioConfig
from folio.converter import FolioConverter, _detect_source_type
from folio.pipeline.text import SlideText


def _parse_frontmatter(path) -> dict:
    content = path.read_text()
    return yaml.safe_load(content.split("---", 2)[1].strip())


def test_detect_source_type_docx_is_document():
    assert _detect_source_type(SimpleNamespace(suffix=".docx")) == "document"


def test_docx_conversion_uses_document_path_and_skips_slide_images(tmp_path):
    library = tmp_path / "library"
    source = tmp_path / "sow.docx"
    source.write_bytes(b"placeholder docx bytes")
    converter = FolioConverter(FolioConfig(library_root=library))

    with (
        patch("folio.converter.normalize.to_pdf", side_effect=AssertionError("normalize should not run")),
        patch("folio.converter.images.extract_with_metadata", side_effect=AssertionError("images should not run")),
        patch(
            "folio.converter.text.extract_document_text",
            return_value=SlideText(
                slide_num=1,
                full_text="Statement of work\n\nFull document body for the engagement.",
                elements=[{"type": "title", "text": "Statement of work"}],
            ),
        ),
    ):
        result = converter.convert(
            source_path=source,
            client="Acme",
            engagement="Build",
            passes=1,
        )

    assert result.slide_count == 1
    assert result.renderer_used == "document-text"
    assert result.cache_stats is None
    assert result.output_path.exists()

    content = result.output_path.read_text()
    assert "## Document Text" in content
    assert "Full document body for the engagement." in content
    assert "![Slide 1]" not in content

    fm = _parse_frontmatter(result.output_path)
    assert fm["source_type"] == "document"
    assert fm["slide_count"] == 1
    assert fm["grounding_summary"]["total_claims"] == 1
    assert fm["_llm_metadata"]["convert"]["status"] == "skipped"

    registry = json.loads((library / "registry.json").read_text())
    entry = registry["decks"][result.deck_id]
    assert entry["source_type"] == "document"
    assert entry["version"] == 1
