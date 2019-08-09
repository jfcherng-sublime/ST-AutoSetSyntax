import sublime
import time


def get_package_name() -> str:
    """
    @brief Getsthe package name.

    @return The package name.
    """

    return __package__


def get_package_path() -> str:
    """
    @brief Gets the package path.

    @return The package path.
    """

    return "Packages/" + get_package_name()


def get_settings_file() -> str:
    """
    @brief Get the settings file name.

    @return The settings file name.
    """

    return "AutoSetSyntax.sublime-settings"


def get_settings_object() -> sublime.Settings:
    """
    @brief Get the plugin settings object.

    @return The settings object.
    """

    return sublime.load_settings(get_settings_file())


def get_setting(key: str, default=None):
    """
    @brief Get the plugin setting with the key.

    @param key     The key
    @param default The default value if the key doesn't exist

    @return The setting's value.
    """

    return get_settings_object().get(key, default)


def get_timestamp() -> float:
    """
    @brief Get the current timestamp (in second).

    @return The timestamp.
    """

    return time.time()
