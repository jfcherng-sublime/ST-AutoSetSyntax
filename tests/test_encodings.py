"""Tests for encoding translation between Sublime and Python names."""

import pytest

from plugin.encodings import from_sublime
from plugin.encodings import to_sublime


class TestTranslation:
    def test_bom_variants_keep_their_bom(self):
        assert from_sublime("UTF-8 with BOM") == "utf-8-sig"

    def test_utf16_has_no_unique_inverse_so_it_maps_to_le_with_bom(self):
        assert to_sublime("utf-16") == "UTF-16 LE with BOM"

    def test_unknown_sublime_name_raises(self):
        with pytest.raises(ValueError, match="Unknown Sublime encoding"):
            from_sublime("Nonexistent Encoding")

    def test_unknown_python_name_raises(self):
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
