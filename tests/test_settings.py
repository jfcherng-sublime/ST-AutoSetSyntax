"""Tests for the AioSettings class and related settings utilities."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from conftest import DEFAULT_SETTINGS

from plugin.constants import PLUGIN_NAME

# These need to be imported after sublime stubs are set up by conftest
from plugin.settings import AioSettings
from plugin.settings import get_merged_plugin_setting
from plugin.settings import get_st_setting
from plugin.settings import pref_syntax_rules

# ── get_st_setting / get_st_settings ────────────────────────────────────────


@pytest.mark.parametrize(("stored", "expected"), [(7, 7), (None, 3)])
def test_get_st_setting_treats_null_as_unset(stored, expected):
    with patch("plugin.settings.get_st_settings") as mock_settings:
        mock_settings.return_value.get.return_value = stored
        assert get_st_setting("some_key", 3) == expected


# ── AioSettings ──────────────────────────────────────────────────────────────


def _window(window_id: int, project_settings: dict | None = None) -> MagicMock:
    window = MagicMock()
    window.id.return_value = window_id
    window.project_data.return_value = {"settings": {PLUGIN_NAME: project_settings}} if project_settings else None
    return window


def _reset_aio_settings() -> None:
    AioSettings.tear_down()


def _set_up(plugin_settings: dict, windows: list, on_change=None) -> MagicMock:
    file_settings = MagicMock()
    file_settings.to_dict.return_value = plugin_settings
    with patch("sublime.load_settings", return_value=file_settings), patch("sublime.windows", return_value=windows):
        AioSettings.set_up(on_change or MagicMock())
    return file_settings


class TestAioSettings:
    def setup_method(self):
        _reset_aio_settings()

    def teardown_method(self):
        _reset_aio_settings()

    def test_set_up_loads_every_window_without_calling_on_change(self):
        window, on_change = _window(1), MagicMock()
        _set_up({"debounce": 5}, [window], on_change)

        assert get_merged_plugin_setting("debounce", 0, window=window) == 5
        on_change.assert_not_called()

    def test_project_settings_override_plugin_settings(self):
        window = _window(2, {"debounce": 9})
        _set_up({"debounce": 5, "modeline_lines": 7}, [window])

        assert get_merged_plugin_setting("debounce", 0, window=window) == 9
        assert get_merged_plugin_setting("modeline_lines", 0, window=window) == 7

    def test_a_window_is_unknown_until_tracked(self):
        _set_up({}, [])
        window = _window(3)
        assert AioSettings.get_all(window) == {}

        AioSettings.track(window)
        assert AioSettings.get_all(window) != {}

    def test_refresh_rereads_the_project_settings_and_tells_on_change(self):
        window, on_change = _window(4), MagicMock()
        _set_up({"debounce": 5}, [window], on_change)
        window.project_data.return_value = {"settings": {PLUGIN_NAME: {"debounce": 1}}}

        AioSettings.refresh(window)

        assert get_merged_plugin_setting("debounce", 0, window=window) == 1
        on_change.assert_called_once_with(window)

    def test_track_rereads_without_telling_on_change(self):
        window, on_change = _window(5), MagicMock()
        _set_up({}, [window], on_change)

        AioSettings.track(window)

        on_change.assert_not_called()

    def test_forget_drops_the_window(self):
        window = _window(6)
        _set_up({"debounce": 5}, [window])

        AioSettings.forget(window)

        assert AioSettings.get_all(window) == {}

    def test_editing_the_plugin_settings_file_refreshes_every_window(self):
        windows, on_change = [_window(7), _window(8)], MagicMock()
        file_settings = _set_up({"debounce": 5}, windows, on_change)
        file_settings.to_dict.return_value = {"debounce": 2}
        [(_, callback)] = [call.args for call in file_settings.add_on_change.call_args_list]

        with patch("sublime.windows", return_value=windows):
            callback()

        assert [call.args[0] for call in on_change.call_args_list] == windows
        assert get_merged_plugin_setting("debounce", 0, window=windows[0]) == 2

    def test_tear_down_forgets_everything_and_stops_listening(self):
        window = _window(9)
        file_settings = _set_up({"debounce": 5}, [window])

        AioSettings.tear_down()

        file_settings.clear_on_change.assert_called_once()
        assert AioSettings.get_all(window) == {}

    def test_null_in_plugin_settings_reads_as_absent(self):
        window = _window(10)
        _set_up({"debounce": None, "modeline_lines": 7}, [window])

        assert get_merged_plugin_setting("debounce", 3, window=window) == 3
        assert get_merged_plugin_setting("modeline_lines", 0, window=window) == 7

    def test_null_project_override_falls_through_to_the_plugin_value(self):
        window = _window(11, {"debounce": None})
        _set_up({"debounce": 5}, [window])

        assert get_merged_plugin_setting("debounce", 3, window=window) == 5

    @pytest.mark.parametrize("project_data", [{"settings": None}, {"settings": {PLUGIN_NAME: None}}, None])
    def test_null_project_data_means_no_project_overrides(self, project_data):
        window = _window(12)
        window.project_data.return_value = project_data
        _set_up({"debounce": 5}, [window])

        assert get_merged_plugin_setting("debounce", 0, window=window) == 5


class TestTrimSuffixesAreMergedAcrossLayers:
    def setup_method(self):
        _reset_aio_settings()

    def teardown_method(self):
        _reset_aio_settings()

    def _trim_suffixes(self, plugin_settings: dict, project_settings: dict | None = None):
        window = _window(20, project_settings)
        _set_up(plugin_settings, [window])
        return get_merged_plugin_setting("trim_suffixes", window=window)

    def test_merged_in_priority_order_and_deduplicated(self):
        result = self._trim_suffixes(
            {"user_trim_suffixes": ["b", "c"], "default_trim_suffixes": ["c", "d"]},
            {"project_trim_suffixes": ["a", "b"]},
        )
        assert result == ("a", "b", "c", "d")

    def test_empty_when_nothing_configured(self):
        assert self._trim_suffixes({}) == ()

    def test_falsy_values_are_dropped(self):
        assert self._trim_suffixes({"user_trim_suffixes": ["ok", "", None, "also_ok"]}) == ("ok", "also_ok")

    def test_null_layers_are_tolerated(self):
        result = self._trim_suffixes({"user_trim_suffixes": ["ok"], "default_trim_suffixes": None})
        assert result == ("ok",)


# ── pref_syntax_rules ────────────────────────────────────────────────────────


class TestPrefSyntaxRules:
    @staticmethod
    def _pref(settings: dict):
        with patch("plugin.settings.get_merged_plugin_settings", return_value=settings):
            return pref_syntax_rules(window=MagicMock())

    def test_reads_every_source_in_test_order(self):
        valid, invalid = self._pref({
            "default_syntax_rules": [{"syntaxes": ["Default"]}],
            "user_syntax_rules": [{"syntaxes": ["User"]}],
            "project_syntax_rules": [{"syntaxes": ["Project"]}],
            "core_syntax_rules": [{"syntaxes": ["Core"]}],
        })

        assert [rule.syntaxes for rule in valid] == [["Core"], ["Project"], ["User"], ["Default"]]
        assert invalid == []

    def test_unknown_event_name_is_reported_not_silently_dropped(self):
        valid, invalid = self._pref({"user_syntax_rules": [{"syntaxes": ["Python"], "on_events": ["load", "LOAD"]}]})

        assert valid == []
        assert "'LOAD'" in invalid[0].reason
        assert invalid[0].reason.startswith("invalid setting at user_syntax_rules[0]: ")

    def test_invalid_rule_is_dropped_alone_and_located(self):
        """One malformed rule used to fail validation of the whole merged list, so every rule --
        the bundled ones included -- was ignored. A typo'd key ("constrait") is the classic case:
        extra="forbid" rejects it rather than letting it validate as an empty no-op match."""
        bad = {"syntaxes": ["Python"], "rules": [{"constrait": "is_extension", "args": ["py"]}]}

        valid, invalid = self._pref({
            "user_syntax_rules": [{"syntaxes": ["A"]}, bad],
            "default_syntax_rules": [{"syntaxes": ["B"]}],
        })

        assert [rule.syntaxes for rule in valid] == [["A"], ["B"]]
        assert len(invalid) == 1
        assert invalid[0].reason.startswith("invalid setting at user_syntax_rules[1]: ")
        assert "constrait" in invalid[0].reason
        assert invalid[0].rule == bad

    @pytest.mark.parametrize(
        ("rule", "problem"),
        [
            ({"rules": [{"constrait": "is_extension"}]}, "rules[0].constrait: Extra inputs are not permitted"),
            ({"rules": [{"constraint": "is_extension", "args": "py"}]}, "rules[0].args: Input should be a valid list"),
            (
                {"rules": [{"match": "all", "rules": [{"constrait": "x"}]}]},
                "rules[0].rules[0].constrait: Extra inputs are not permitted",
            ),
        ],
    )
    def test_reason_points_at_the_setting_in_the_users_terms(self, rule, problem):
        """The reason is shown verbatim in Debug Information: it must name the offending key as
        the user wrote it, with no model class names, and only the problems of the one kind of
        rule it can be (a "constraint" key makes a constraint rule)."""
        _, [dropped] = self._pref({"user_syntax_rules": [rule]})

        assert dropped.reason == f"invalid setting at user_syntax_rules[0]: {problem}"

    def test_null_source_means_unset(self):
        """A key explicitly set to `null` (a user trying to "unset" an override) is present with
        value None, so it has to be treated like an absent one, not crash or be reported."""
        valid, invalid = self._pref({"core_syntax_rules": [{"syntaxes": ["Core"]}], "user_syntax_rules": None})

        assert [rule.syntaxes for rule in valid] == [["Core"]]
        assert invalid == []

    def test_non_list_source_is_reported(self):
        """Forgetting the brackets around a single rule used to be ignored without a word."""
        valid, invalid = self._pref({"user_syntax_rules": {"syntaxes": ["Python"]}})

        assert valid == []
        assert len(invalid) == 1
        assert invalid[0].reason.startswith("invalid setting at user_syntax_rules: ")


@pytest.mark.parametrize(
    "key",
    [
        "debounce",
        "magika.min_confidence",
        "modeline_lines",
        "trim_file_size",
        "trim_first_line_length",
        "trim_suffixes_auto",
    ],
)
def test_settings_read_without_a_fallback_have_a_shipped_default(key):
    """The code indexes these keys directly, so the shipped settings file is their only default."""
    assert key in DEFAULT_SETTINGS
