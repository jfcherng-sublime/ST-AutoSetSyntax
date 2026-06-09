"""Tests for encoding translation between Sublime and Python names."""

import pytest

from plugin.encodings import from_sublime
from plugin.encodings import to_sublime


class TestFromSublime:
    def test_utf8(self):
        assert from_sublime("UTF-8") == "utf-8"

    def test_utf8_with_bom(self):
        assert from_sublime("UTF-8 with BOM") == "utf-8-sig"

    def test_utf16_le(self):
        assert from_sublime("UTF-16 LE") == "utf-16-le"

    def test_utf16_be(self):
        assert from_sublime("UTF-16 BE") == "utf-16-be"

    def test_western_windows(self):
        assert from_sublime("Western (Windows 1252)") == "cp1252"

    def test_western_iso(self):
        assert from_sublime("Western (ISO 8859-1)") == "iso8859-1"

    def test_cyrillic_koi8(self):
        assert from_sublime("Cyrillic (KOI8-R)") == "koi8-r"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown Sublime encoding"):
            from_sublime("Nonexistent Encoding")


class TestToSublime:
    def test_utf8(self):
        assert to_sublime("utf-8") == "UTF-8"

    def test_utf8_sig(self):
        assert to_sublime("utf-8-sig") == "UTF-8 with BOM"

    def test_cp1252(self):
        assert to_sublime("cp1252") == "Western (Windows 1252)"

    def test_koi8_r(self):
        assert to_sublime("koi8-r") == "Cyrillic (KOI8-R)"

    def test_utf16_roundtrip(self):
        """UTF-16 maps to 'UTF-16 LE with BOM' in the reverse mapping."""
        assert to_sublime("utf-16") == "UTF-16 LE with BOM"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown Python encoding"):
            to_sublime("nonexistent_encoding")


class TestRoundtrip:
    """Test that common encodings survive a roundtrip."""

    @pytest.mark.parametrize(
        "st_name",
        [
            "UTF-8",
            "UTF-8 with BOM",
            "UTF-16 LE",
            "UTF-16 BE",
            "Western (Windows 1252)",
            "Western (ISO 8859-1)",
            "Cyrillic (KOI8-R)",
            "Hebrew (Windows 1255)",
        ],
    )
    def test_roundtrip(self, st_name):
        assert to_sublime(from_sublime(st_name)) == st_name
