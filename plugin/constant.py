from pathlib import Path
import sublime
import sys

################################################################################

VERSION_INFO = (2, 0, 1, "dev")
VERSION = ".".join(map(str, VERSION_INFO[:3]))
if next(filter(None, VERSION_INFO[3:4]), None):
    VERSION += f"-{VERSION_INFO[3]}"

################################################################################

ST_ARCH = sublime.arch()
ST_CHANNEL = sublime.channel()
ST_PLATFORM = sublime.platform()
ST_PLATFORM_ARCH = f"{ST_PLATFORM}_{ST_ARCH}"
ST_VERSION = int(sublime.version())
PY_VERSION_FULL = sys.version
PY_VERSION = PY_VERSION_FULL.partition(" ")[0]

################################################################################

PLUGIN_NAME = __package__.partition(".")[0]

PLUGIN_CUSTOM_DIR = Path(sublime.packages_path()) / f"{PLUGIN_NAME}-Custom"
PLUGIN_CUSTOM_MODULE_PATHS = {
    "constraint": PLUGIN_CUSTOM_DIR / "constraints",
    "match": PLUGIN_CUSTOM_DIR / "matches",
}

VIEW_RUN_ID_SETTINGS_KEY = f"{PLUGIN_NAME}/run_id"
VIEW_IS_TRANSIENT_SETTINGS_KEY = f"{PLUGIN_NAME}/is_transient"
