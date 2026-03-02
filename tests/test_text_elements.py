"""Tests for SlideText dataclass and element detection."""

import pytest

from folio.pipeline.text import SlideText, _detect_elements
from folio.tracking.versions import detect_changes


class TestSlideText:
    """Test SlideText dataclass behavior."""

    def test_basic_creation(self):
        st = SlideText(slide_num=1, full_text="Hello world")
        assert st.slide_num == 1
        assert st.full_text == "Hello world"
        assert st.elements == []

    def test_with_elements(self):
        elements = [
            {"type": "title", "text": "Slide Title"},
            {"type": "body", "text": "Body content here"},
        ]
        st = SlideText(slide_num=3, full_text="Slide Title\nBody content here", elements=elements)
        assert len(st.elements) == 2
        assert st.elements[0]["type"] == "title"


class TestDetectElements:
    """Test element type detection from slide text."""

    def test_h1_title(self):
        text = "# Market Analysis\n\nRevenue grew 15% YoY"
        elements = _detect_elements(text)
        titles = [e for e in elements if e["type"] == "title"]
        bodies = [e for e in elements if e["type"] == "body"]
        assert len(titles) == 1
        assert titles[0]["text"] == "Market Analysis"
        assert len(bodies) == 1
        assert "Revenue grew" in bodies[0]["text"]

    def test_h2_title(self):
        text = "## Executive Summary\n\nKey findings below"
        elements = _detect_elements(text)
        titles = [e for e in elements if e["type"] == "title"]
        assert len(titles) == 1
        assert titles[0]["text"] == "Executive Summary"

    def test_bold_title(self):
        text = "**Strategic Recommendations**\n\nWe recommend three actions"
        elements = _detect_elements(text)
        titles = [e for e in elements if e["type"] == "title"]
        assert len(titles) == 1
        assert titles[0]["text"] == "Strategic Recommendations"

    def test_no_title(self):
        text = "Just some body text\nSpanning multiple lines"
        elements = _detect_elements(text)
        titles = [e for e in elements if e["type"] == "title"]
        bodies = [e for e in elements if e["type"] == "body"]
        assert len(titles) == 0
        assert len(bodies) == 1

    def test_speaker_notes(self):
        text = "# Title\n\nBody content\n\nNotes: These are speaker notes for the presenter"
        elements = _detect_elements(text)
        notes = [e for e in elements if e["type"] == "note"]
        assert len(notes) == 1
        assert "speaker notes" in notes[0]["text"]

    def test_speaker_notes_variant(self):
        text = "Content here\n\nSpeaker Notes: Mention the key metrics"
        elements = _detect_elements(text)
        notes = [e for e in elements if e["type"] == "note"]
        assert len(notes) == 1
        assert "key metrics" in notes[0]["text"]

    def test_empty_text(self):
        elements = _detect_elements("")
        assert elements == []

    def test_only_title(self):
        text = "# Just A Title"
        elements = _detect_elements(text)
        titles = [e for e in elements if e["type"] == "title"]
        assert len(titles) == 1
        assert titles[0]["text"] == "Just A Title"


class TestDetectChangesWithSlideText:
    """Test that detect_changes works with SlideText objects."""

    def test_no_changes(self):
        old = {1: "Same text", 2: "Also same"}
        new = {
            1: SlideText(slide_num=1, full_text="Same text", elements=[]),
            2: SlideText(slide_num=2, full_text="Also same", elements=[]),
        }
        changes = detect_changes(old, new)
        assert not changes.has_changes
        assert changes.unchanged == [1, 2]

    def test_modified_slide(self):
        old = {1: "Original text"}
        new = {1: SlideText(slide_num=1, full_text="Modified text", elements=[])}
        changes = detect_changes(old, new)
        assert changes.modified == [1]

    def test_added_slide(self):
        old = {1: "Slide one"}
        new = {
            1: SlideText(slide_num=1, full_text="Slide one", elements=[]),
            2: SlideText(slide_num=2, full_text="New slide", elements=[]),
        }
        changes = detect_changes(old, new)
        assert changes.added == [2]

    def test_mixed_str_and_slidetext(self):
        """Old cache is always str, new is SlideText."""
        old = {1: "Hello world", 2: "Second slide"}
        new = {
            1: SlideText(slide_num=1, full_text="Hello world", elements=[]),
            2: SlideText(slide_num=2, full_text="Updated second slide", elements=[]),
        }
        changes = detect_changes(old, new)
        assert changes.unchanged == [1]
        assert changes.modified == [2]
