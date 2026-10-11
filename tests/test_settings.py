"""Tests for the AioSettings class and related settings utilities."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

# These need to be imported after sublime stubs are set up by conftest
from plugin.settings import AioSettings
from plugin.settings import extra_settings_producer
from plugin.settings import get_merged_plugin_setting
from plugin.settings import get_st_setting
from plugin.settings import get_st_settings
from plugin.settings import pref_syntax_rules
from plugin.settings import pref_trim_suffixes

# ── get_st_setting / get_st_settings ────────────────────────────────────────


class TestStSettings:
    def test_get_st_settings_returns_mock(self):
        settings = get_st_settings()
        assert settings is not None

    def test_get_st_setting_default(self):
        with patch("plugin.settings.get_st_settings") as mock_settings:
            mock_settings.return_value.get.return_value = "fallback"
            assert get_st_setting("nonexistent_key", "fallback") == "fallback"

    def test_get_st_setting_none_default(self):
        with patch("plugin.settings.get_st_settings") as mock_settings:
            mock_settings.return_value.get.return_value = None
            assert get_st_setting("nonexistent_key") is None


# ── get_merged_plugin_setting ────────────────────────────────────────────────


class TestGetMergedPluginSetting:
    def setup_method(self):
        AioSettings._merged_plugin_settings.clear()

    def test_returns_value_when_present(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 501
        AioSettings._merged_plugin_settings[501] = {"debounce": 5}
        assert get_merged_plugin_setting("debounce", 0, window=mock_window) == 5

    def test_returns_default_when_key_absent(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 502
        AioSettings._merged_plugin_settings[502] = {}
        assert get_merged_plugin_setting("debounce", 3, window=mock_window) == 3

    def test_null_value_falls_back_to_default_not_none(self):
        """Regression: a key explicitly set to `null` (e.g. a user trying to "unset" an
        override) is present with value None, not absent -- `dict.get(key, default)`'s default
        only covers the latter case. Every caller that passes a non-None default needs a usable
        value back, not None (e.g. `int(None)`/`None > 0`/`None.lower()` would all raise), so an
        explicit null must be treated the same as "not configured"."""
        mock_window = MagicMock()
        mock_window.id.return_value = 503
        AioSettings._merged_plugin_settings[503] = {"debounce": None}
        assert get_merged_plugin_setting("debounce", 3, window=mock_window) == 3

    def test_null_value_with_no_requested_default_stays_none(self):
        """When the caller doesn't ask for a real fallback (default=None, e.g. Logger.log's
        enable_log check), an explicit null is indistinguishable from absent either way, so
        behavior is unchanged."""
        mock_window = MagicMock()
        mock_window.id.return_value = 504
        AioSettings._merged_plugin_settings[504] = {"enable_log": None}
        assert get_merged_plugin_setting("enable_log", window=mock_window) is None


# ── AioSettings lifecycle ────────────────────────────────────────────────────


class TestAioSettingsLifecycle:
    def setup_method(self):
        AioSettings._plugin_settings_object = None
        AioSettings._settings_normalizer = None
        AioSettings._settings_producer = None
        AioSettings._tracked_windows.clear()
        AioSettings._plugin_settings.clear()
        AioSettings._project_plugin_settings.clear()
        AioSettings._merged_plugin_settings.clear()

    def test_set_up_initializes_plugin_settings(self):
        AioSettings.plugin_name = "TestPlugin"
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {"key1": "val1", "trim_file_size": 100}

        with patch("sublime.load_settings", return_value=mock_settings):
            AioSettings.set_up()

        assert AioSettings._plugin_settings_object is mock_settings
        assert AioSettings._plugin_settings.get("key1") == "val1"
        mock_settings.add_on_change.assert_called_once()

    def test_tear_down_clears_callback(self):
        AioSettings.plugin_name = "TestPlugin"
        mock_settings = MagicMock()

        with patch("sublime.load_settings", return_value=mock_settings):
            AioSettings.set_up()
            AioSettings.tear_down()

        mock_settings.clear_on_change.assert_called_once()

    def test_tear_down_clears_per_window_state(self):
        """A window closed during a plugin unload/reload cycle (no on_pre_close_window) must not leak."""
        AioSettings.plugin_name = "TestPlugin"
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {}

        mock_window = MagicMock()
        mock_window.id.return_value = 777
        mock_window.project_data.return_value = None

        with patch("sublime.load_settings", return_value=mock_settings):
            AioSettings.set_up()
            AioSettings._on_settings_change([mock_window], run_callbacks=False)

        assert AioSettings._tracked_windows == {777}
        assert 777 in AioSettings._merged_plugin_settings
        assert 777 in AioSettings._project_plugin_settings

        AioSettings.tear_down()

        assert AioSettings._tracked_windows == set()
        assert AioSettings._merged_plugin_settings == {}
        assert AioSettings._project_plugin_settings == {}

    def test_add_on_change_callback_is_stored(self):
        def callback(w):
            return None

        AioSettings.add_on_change("my_key", callback)
        assert AioSettings._on_settings_change_callbacks.get("my_key") is callback
        AioSettings.clear_on_change("my_key")

    def test_clear_on_change_removes_callback(self):
        def callback(w):
            return None

        AioSettings.add_on_change("my_key", callback)
        AioSettings.clear_on_change("my_key")
        assert "my_key" not in AioSettings._on_settings_change_callbacks

    def test_get_returns_default_for_untracked_window(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 999
        assert AioSettings.get(mock_window, "anything", "default") == "default"

    def test_get_all_returns_empty_for_untracked_window(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 999
        assert AioSettings.get_all(mock_window) == {}


# ── extra_settings_producer ──────────────────────────────────────────────────


class TestExtraSettingsProducer:
    def test_trim_suffixes_merged_deduplicated(self):
        result = extra_settings_producer({
            "project_trim_suffixes": ["a", "b"],
            "user_trim_suffixes": ["b", "c"],
            "default_trim_suffixes": ["c", "d"],
        })
        suffixes = result["trim_suffixes"]
        assert "a" in suffixes
        assert "b" in suffixes
        assert "c" in suffixes
        assert "d" in suffixes
        # Deduplicated: a,b,c,d (order preserved, unique)
        assert suffixes == ("a", "b", "c", "d")

    def test_trim_suffixes_empty(self):
        result = extra_settings_producer({})
        assert result["trim_suffixes"] == ()

    def test_trim_suffixes_drops_falsy_values(self):
        result = extra_settings_producer({
            "user_trim_suffixes": ["ok", "", None, "also_ok"],
        })
        assert result["trim_suffixes"] == ("ok", "also_ok")

    def test_null_trim_suffixes_setting_does_not_raise(self):
        """Same regression as above, for trim_suffixes' chain() instead of +."""
        result = extra_settings_producer({
            "project_trim_suffixes": None,
            "user_trim_suffixes": ["ok"],
            "default_trim_suffixes": None,
        })
        assert result["trim_suffixes"] == ("ok",)


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


# ── pref_trim_suffixes ──────────────────────────────────────────────────────


class TestPrefTrimSuffixes:
    def test_returns_tuple_from_settings(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 42

        with patch("plugin.settings.get_merged_plugin_setting", return_value=[".bak", "~"]):
            result = pref_trim_suffixes(window=mock_window)
            assert result == [".bak", "~"]

    def test_returns_empty_tuple_when_unset(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 42

        with patch("plugin.settings.get_merged_plugin_setting", return_value=[]):
            result = pref_trim_suffixes(window=mock_window)
            assert result == []

    def test_default_is_a_hashable_tuple_when_key_absent(self):
        """Regression: this flows into is_extension's build_reversed_trie(), which is
        lru_cache-decorated and requires a hashable argument. A window with no merged settings
        yet (key genuinely absent, unlike the mocked-return_value tests above) must fall through
        to pref_trim_suffixes()'s own default -- that default has to be a tuple, not a list, or
        build_reversed_trie() raises `TypeError: unhashable type: 'list'`."""
        mock_window = MagicMock()
        mock_window.id.return_value = 123456789
        AioSettings._merged_plugin_settings.pop(123456789, None)

        result = pref_trim_suffixes(window=mock_window)
        assert result == ()
        hash(result)


# ── AioSettings settings normalizer ──────────────────────────────────────────


class TestAioSettingsNormalizer:
    def setup_method(self):
        AioSettings._plugin_settings_object = None
        AioSettings._settings_normalizer = None
        AioSettings._settings_producer = None
        AioSettings._tracked_windows.clear()
        AioSettings._plugin_settings.clear()
        AioSettings._project_plugin_settings.clear()
        AioSettings._merged_plugin_settings.clear()

    def test_normalizer_applied_to_plugin_settings(self):
        AioSettings.plugin_name = "TestPlugin"
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {"key": "VALUE"}

        def normalizer(d):
            d["key"] = d["key"].lower()

        AioSettings.set_settings_normalizer(normalizer)

        with patch("sublime.load_settings", return_value=mock_settings):
            AioSettings.set_up()

        assert AioSettings._plugin_settings["key"] == "value"

    def test_normalizer_applied_to_project_settings(self):
        AioSettings.plugin_name = "TestPlugin"
        AioSettings.set_settings_normalizer(lambda d: d.update({"normalized": True}))

        mock_window = MagicMock()
        mock_window.id.return_value = 42
        mock_window.project_data.return_value = {
            "settings": {"TestPlugin": {"project_key": "val"}},
        }

        AioSettings._update_project_plugin_settings(mock_window)
        assert AioSettings._project_plugin_settings[42]["normalized"] is True
        assert AioSettings._project_plugin_settings[42]["project_key"] == "val"


class TestUpdateProjectPluginSettingsHandlesNull:
    """Regression: `.get(key, {})`'s default only applies when `key` is absent. A .sublime-project
    file with "settings": null or "settings": {"<plugin_name>": null} (a plausible way a user
    tries to "unset" project overrides) leaves the key present with value None, which used to
    crash with AttributeError/TypeError instead of being treated as "no project overrides"."""

    def setup_method(self):
        AioSettings.plugin_name = "TestPlugin"
        AioSettings._settings_normalizer = None
        AioSettings._project_plugin_settings.clear()

    def test_null_settings_key_does_not_raise(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 601
        mock_window.project_data.return_value = {"settings": None}

        AioSettings._update_project_plugin_settings(mock_window)  # must not raise
        assert AioSettings._project_plugin_settings[601] == {"__comment": "project_settings"}

    def test_null_plugin_key_does_not_raise(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 602
        mock_window.project_data.return_value = {"settings": {"TestPlugin": None}}

        AioSettings._update_project_plugin_settings(mock_window)  # must not raise
        assert AioSettings._project_plugin_settings[602] == {"__comment": "project_settings"}

    def test_real_project_settings_still_applied(self):
        mock_window = MagicMock()
        mock_window.id.return_value = 603
        mock_window.project_data.return_value = {"settings": {"TestPlugin": {"key": "val"}}}

        AioSettings._update_project_plugin_settings(mock_window)
        assert AioSettings._project_plugin_settings[603]["key"] == "val"


# ── AioSettings event handlers ──────────────────────────────────────────────


class TestAioSettingsEvents:
    def setup_method(self):
        AioSettings._plugin_settings_object = None
        AioSettings._settings_normalizer = None
        AioSettings._settings_producer = None
        AioSettings._tracked_windows.clear()
        AioSettings._plugin_settings.clear()
        AioSettings._project_plugin_settings.clear()
        AioSettings._merged_plugin_settings.clear()

    def test_on_new_window_calls_on_settings_change(self):
        listener = AioSettings()
        mock_window = MagicMock()
        mock_window.id.return_value = 55

        # First call should process the window
        with patch.object(AioSettings, "_on_settings_change") as mock:
            listener.on_new_window(mock_window)
            mock.assert_called_once_with([mock_window])

    def test_on_new_window_already_tracked_skips(self):
        listener = AioSettings()
        mock_window = MagicMock()
        mock_window.id.return_value = 55
        AioSettings._tracked_windows.add(55)

        with patch.object(AioSettings, "_on_settings_change") as mock:
            listener.on_new_window(mock_window)
            mock.assert_not_called()

    def test_on_pre_close_window_cleans_up(self):
        listener = AioSettings()
        mock_window = MagicMock()
        mock_window.id.return_value = 77
        AioSettings._tracked_windows.add(77)
        AioSettings._merged_plugin_settings[77] = {"key": "val"}
        AioSettings._project_plugin_settings[77] = {"pkey": "pval"}

        listener.on_pre_close_window(mock_window)
        assert 77 not in AioSettings._merged_plugin_settings
        assert 77 not in AioSettings._project_plugin_settings
        assert 77 not in AioSettings._tracked_windows

    def test_on_load_project_async_updates_settings(self):
        listener = AioSettings()
        mock_window = MagicMock()
        mock_window.id.return_value = 88

        with patch.object(AioSettings, "_on_settings_change") as mock:
            listener.on_load_project_async(mock_window)
            mock.assert_called_once_with([mock_window])
