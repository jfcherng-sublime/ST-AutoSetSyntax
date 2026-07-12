"""Tests for plugin/magika.py -- previously zero dedicated coverage.

get_magika_object()/get_magika_ignored_labels() aren't exercised here since the `magika` package
isn't a dev dependency (it's fetched separately via the "Download Dependencies" command); both
already degrade to None/empty-set when it's not importable, which every other test in this suite
exercises indirectly. resolve_magika_label_with_syntax_map() is pure graph-resolution logic with
no such dependency, so it's covered directly and thoroughly here.
"""

from plugin.magika import resolve_magika_label_with_syntax_map


class TestResolveMagikaLabelWithSyntaxMap:
    def test_direct_scope_resolves_as_is(self):
        syntax_map = {"python": ["scope:source.python"]}
        assert resolve_magika_label_with_syntax_map("python", syntax_map) == ["scope:source.python"]

    def test_multiple_direct_scopes_preserve_order(self):
        syntax_map = {"c": ["scope:source.c", "C++/C"]}
        assert resolve_magika_label_with_syntax_map("c", syntax_map) == ["scope:source.c", "C++/C"]

    def test_unknown_label_resolves_empty(self):
        assert resolve_magika_label_with_syntax_map("nonexistent", {}) == []

    def test_reference_resolves_through_to_target(self):
        syntax_map = {
            "csharp": ["=c_sharp"],
            "c_sharp": ["scope:source.cs"],
        }
        assert resolve_magika_label_with_syntax_map("csharp", syntax_map) == ["scope:source.cs"]

    def test_reference_mixed_with_direct_scope(self):
        syntax_map = {
            "a": ["=b", "scope:direct.a"],
            "b": ["scope:direct.b"],
        }
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == ["scope:direct.b", "scope:direct.a"]

    def test_reference_to_missing_label_contributes_nothing(self):
        syntax_map = {"a": ["=missing"]}
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == []

    def test_self_reference_cycle_terminates_and_resolves_empty(self):
        """Must not infinite-loop when a label references itself."""
        syntax_map = {"a": ["=a"]}
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == []

    def test_two_label_reference_cycle_terminates_and_resolves_empty(self):
        syntax_map = {"a": ["=b"], "b": ["=a"]}
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == []

    def test_cycle_with_a_real_value_still_resolves_the_value(self):
        """A cycle that also contains a genuine scope must not lose that scope just because part
        of the resolution loops back on itself."""
        syntax_map = {
            "a": ["=b", "scope:text.direct"],
            "b": ["=a"],
        }
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == ["scope:text.direct"]

    def test_duplicate_notation_within_same_list_is_not_repeated(self):
        syntax_map = {"a": ["scope:x", "scope:x"]}
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == ["scope:x"]

    def test_diamond_shaped_references_resolve_once(self):
        """a -> b, c; b -> shared; c -> shared -- "shared" must appear only once even though it's
        reachable via two different paths."""
        syntax_map = {
            "a": ["=b", "=c"],
            "b": ["=shared"],
            "c": ["=shared"],
            "shared": ["scope:text.shared"],
        }
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == ["scope:text.shared"]

    def test_null_value_for_label_resolves_empty_instead_of_raising(self):
        """Regression: a settings key present with an explicit `null` value (e.g. a user trying
        to "unset" an override) comes back as None from `.get(key, [])` -- `deque(None)` used to
        raise `TypeError: 'NoneType' object is not iterable`."""
        syntax_map = {"python": None}
        assert resolve_magika_label_with_syntax_map("python", syntax_map) == []

    def test_null_value_for_referenced_label_resolves_empty_instead_of_raising(self):
        syntax_map = {"a": ["=b"], "b": None}
        assert resolve_magika_label_with_syntax_map("a", syntax_map) == []
