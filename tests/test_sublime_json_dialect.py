"""
The JSON dialect of `sublime.decode_value()`.

Sublime Text documents it as "JSON ... comments and trailing commas are allowed", and this plugin
leans on that: settings files are written by hand, and so is an `AutoSetSyntax.rules.v*.sublime-settings`
file that a package ships. The stub in `conftest.py` therefore has to accept the same dialect -- if
it were plain `json.loads`, every test here would pass while the plugin itself failed on a file the
documentation says is valid, or the reverse.
"""

import sys

import pytest

decode_value = sys.modules["sublime"].decode_value


class TestDialect:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ('{"a": 1}', {"a": 1}),
            # line comments, which is how every `.sublime-settings` file explains itself
            ('{\n  // why\n  "a": 1\n}', {"a": 1}),
            ('{"a": 1} // trailing', {"a": 1}),
            # block comments
            ('{/* why */ "a": 1}', {"a": 1}),
            ('{"a": /* inline */ 1}', {"a": 1}),
            # trailing commas
            ('{"a": 1,}', {"a": 1}),
            ('{"a": [1, 2,],}', {"a": [1, 2]}),
            ("[1, 2,]", [1, 2]),
            # all at once, the way a hand-written file actually looks
            (
                '{\n  // comment\n  "rules": [\n    {"a": 1,},\n  ],\n}\n',
                {"rules": [{"a": 1}]},
            ),
        ],
    )
    def test_accepts_comments_and_trailing_commas(self, text, expected):
        assert decode_value(text) == expected

    def test_a_comment_marker_inside_a_string_is_not_a_comment(self):
        """Stripping `//` naively would eat the rest of the value."""
        assert decode_value('{"url": "https://example.com//x"}') == {"url": "https://example.com//x"}

    def test_a_comma_inside_a_string_is_not_a_trailing_comma(self):
        assert decode_value('{"a": "b,}"}') == {"a": "b,}"}

    def test_still_rejects_text_that_is_not_json(self):
        with pytest.raises(ValueError):
            decode_value("{not json")
