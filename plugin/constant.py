from pathlib import Path
import re
import sublime
import sys

################################################################################

VERSION_INFO = (2, 1, 8, "stable")
VERSION = ".".join(map(str, VERSION_INFO[:3]))
if next(filter(None, VERSION_INFO[3:4]), None):
    VERSION += f"-{VERSION_INFO[3]}"

################################################################################

ST_ARCH = sublime.arch()  # like "x64"
ST_CHANNEL = sublime.channel()  # like "dev"
ST_PLATFORM = sublime.platform()  # like "windows"
ST_PLATFORM_ARCH = f"{ST_PLATFORM}_{ST_ARCH}"  # like "windows_x64"
ST_VERSION = int(sublime.version())  # like 4113
PY_VERSION_FULL = sys.version  # like "3.8.8 (default, Mar 10 2021, 13:30:47) [MSC v.1915 64 bit (AMD64)]"
PY_VERSION = PY_VERSION_FULL.partition(" ")[0]  # like "3.8.8"

################################################################################

PLUGIN_NAME = __package__.partition(".")[0]  # like "AutoSetSyntax"

PLUGIN_CUSTOM_DIR = Path(sublime.packages_path()) / f"{PLUGIN_NAME}-Custom"
PLUGIN_CUSTOM_MODULE_PATHS = {
    "constraint": PLUGIN_CUSTOM_DIR / "constraints",
    "match": PLUGIN_CUSTOM_DIR / "matches",
}

VIEW_RUN_ID_SETTINGS_KEY = f"{PLUGIN_NAME}/run_id"
VIEW_IS_TRANSIENT_SETTINGS_KEY = f"{PLUGIN_NAME}/is_transient"

RE_VIM_SYNTAX_LINE = re.compile(r"\bsyntax=(?P<syntax>[^\s]+)")
