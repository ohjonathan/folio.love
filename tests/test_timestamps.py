"""Unit tests for the shared timestamp canonicalizer (issue #75)."""

import pytest

from folio.pipeline.timestamps import CanonResult, canonicalize_timestamp


class TestAlreadyCanonical:
    @pytest.mark.parametrize(
        "value",
        [
            "00:03:18.819",
            "01:20:49.519",
            "00:00:01.200",
            "00:03:03.650 - 00:03:18.819",
        ],
    )
    def test_canonical_input_is_unchanged_and_ok(self, value):
        result = canonicalize_timestamp(value)
        assert result.value == value
        assert result.status == "ok"
        assert result.ok is True

    def test_hms_without_ms_is_preserved(self):
        # Seconds precision is valid and must not gain fabricated milliseconds.
        result = canonicalize_timestamp("01:20:49")
        assert result == CanonResult("01:20:49", "ok")


class TestRepairableColonMilliseconds:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            # Issue #75 examples: colon before the milliseconds.
            ("01:20:49:519", "01:20:49.519"),
            ("01:22:44:700", "01:22:44.700"),
            ("04:21:900", "00:04:21.900"),  # MM:SS:mmm -> HH:MM:SS.mmm
        ],
    )
    def test_colon_milliseconds_are_repaired(self, raw, expected):
        result = canonicalize_timestamp(raw)
        assert result.value == expected
        assert result.status == "repaired"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("00:00:01,200", "00:00:01.200"),  # SRT comma decimal
            ("03:18.819", "00:03:18.819"),  # MM:SS.mmm -> padded HH:MM:SS.mmm
            ("1:2:3", "01:02:03"),  # zero padding
            ("0:0:5.5", "00:00:05.500"),  # fractional-second width normalized
            ("  01:20:49:519  ", "01:20:49.519"),  # surrounding whitespace
        ],
    )
    def test_other_unambiguous_normalizations(self, raw, expected):
        result = canonicalize_timestamp(raw)
        assert result.value == expected
        assert result.status == "repaired"


class TestRanges:
    def test_inverted_range_is_flagged(self):
        # Issue #75's headline example: the end (00:03:18.819) precedes the
        # start (03:03:03.650), so the range cannot be repaired safely.
        result = canonicalize_timestamp("03:03:03.650 - 03:18:819")
        assert result.value is None
        assert result.status == "flagged"
        assert result.ok is False

    def test_repairable_range_with_colon_ms_end(self):
        result = canonicalize_timestamp("00:03:03.650 - 00:03:18:819")
        assert result.value == "00:03:03.650 - 00:03:18.819"
        assert result.status == "repaired"

    def test_arrow_separator_is_accepted(self):
        result = canonicalize_timestamp("00:03:03.650 --> 00:03:18.819")
        assert result.value == "00:03:03.650 - 00:03:18.819"

    def test_milliseconds_are_consistent_across_range_ends(self):
        # If either end carries milliseconds, both ends render them.
        result = canonicalize_timestamp("00:01:00 - 00:02:00.500")
        assert result.value == "00:01:00.000 - 00:02:00.500"

    def test_equal_endpoints_allowed(self):
        result = canonicalize_timestamp("00:00:05.000 - 00:00:05.000")
        assert result.ok is True


class TestFlagged:
    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "",
            "   ",
            "abc",
            "519",  # bare three-digit number is not a valid time
            "00:90:00",  # minutes out of range
            "00:00:90",  # seconds out of range
            "01:02:03:04:05",  # too many components
            "12:34 - ",  # malformed range half
        ],
    )
    def test_unparseable_inputs_are_flagged(self, raw):
        result = canonicalize_timestamp(raw)
        assert result.value is None
        assert result.status == "flagged"
        assert result.ok is False
