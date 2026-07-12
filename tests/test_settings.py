"""Tests for the AioSettings class and related settings utilities."""

from unittest.mock import MagicMock
from unittest.mock import patch

# These need to be imported after sublime stubs are set up by conftest
from plugin.settings import AioSettings
from plugin.settings import extra_settings_producer
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
    def test_merges_syntax_rules_in_order(self):
        result = extra_settings_producer({
            "core_syntax_rules": [{"match": "all", "syntaxes": ["Core"]}],
            "project_syntax_rules": [{"match": "all", "syntaxes": ["Project"]}],
            "user_syntax_rules": [{"match": "all", "syntaxes": ["User"]}],
            "default_syntax_rules": [{"match": "all", "syntaxes": ["Default"]}],
        })
        rules = result["syntax_rules"]
        assert len(rules) == 4
        assert rules[0]["syntaxes"] == ["Core"]
        assert rules[1]["syntaxes"] == ["Project"]
        assert rules[2]["syntaxes"] == ["User"]
        assert rules[3]["syntaxes"] == ["Default"]

    def test_empty_syntax_rules(self):
        result = extra_settings_producer({})
        assert result["syntax_rules"] == []

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

    def test_null_syntax_rules_setting_does_not_raise(self):
        """Regression: a key explicitly set to `null` (e.g. a user trying to "unset" an
        override) is present with value None, so `.get(key, [])`'s default never kicks in --
        the old `+`-concatenation crashed with `TypeError: can only concatenate list (not
        "NoneType") to list`. A null value must be treated the same as an absent/empty one."""
        result = extra_settings_producer({
            "core_syntax_rules": [{"match": "all", "syntaxes": ["Core"]}],
            "user_syntax_rules": None,
            "project_syntax_rules": [],
            "default_syntax_rules": None,
        })
        assert result["syntax_rules"] == [{"match": "all", "syntaxes": ["Core"]}]

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
    def test_parses_from_merged_settings(self, monkeypatch):
        """pref_syntax_rules should read from merged settings via get_merged_plugin_setting."""
        # Verify the function exists and delegates to get_merged_plugin_setting
        from plugin.types import StSyntaxRule

        mock_window = MagicMock()
        mock_window.id.return_value = 42

        with patch(
            "plugin.settings.get_merged_plugin_setting",
            return_value=[
                {"syntaxes": ["Python"], "rules": [{"constraint": "is_extension", "args": ["py"]}]},
            ],
        ):
            rules = pref_syntax_rules(window=mock_window)
            assert len(rules) == 1
            assert isinstance(rules[0], StSyntaxRule)
            assert rules[0].syntaxes == ["Python"]

    def test_typo_d_constraint_key_raises_instead_of_silently_becoming_a_no_op(self, monkeypatch):
        """Regression: StConstraintRule requires "constraint" but StMatchRule requires nothing,
        so a typo like "constrait" used to fail StConstraintRule validation and quietly succeed
        as an empty StMatchRule(match="any", rules=[]) instead -- silently dropping the user's
        rule with no error at all. extra="forbid" on both models turns this into a clear,
        catchable ValidationError."""
        import pytest
        from pydantic import ValidationError

        mock_window = MagicMock()
        mock_window.id.return_value = 43

        with (
            patch(
                "plugin.settings.get_merged_plugin_setting",
                return_value=[
                    {"syntaxes": ["Python"], "rules": [{"constrait": "is_extension", "args": ["py"]}]},
                ],
            ),
            pytest.raises(ValidationError),
        ):
            pref_syntax_rules(window=mock_window)


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
