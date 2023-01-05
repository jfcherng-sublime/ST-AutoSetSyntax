import re
import sys
from pathlib import Path

import sublime

################################################################################

VERSION_INFO = (2, 10, 6, "stable")
VERSION = ".".join(map(str, VERSION_INFO[:3]))
if len(VERSION_INFO) > 3:
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

PLUGIN_STORAGE_DIR = Path(sublime.cache_path()).parent / f"Package Storage/{PLUGIN_NAME}"
PLUGIN_CUSTOM_DIR = Path(sublime.packages_path()) / f"{PLUGIN_NAME}-Custom"
PLUGIN_CUSTOM_MODULE_PATHS = {
    "constraint": PLUGIN_CUSTOM_DIR / "constraints",
    "match": PLUGIN_CUSTOM_DIR / "matches",
}

################################################################################

VIEW_RUN_ID_SETTINGS_KEY = f"{PLUGIN_NAME}/run_id"
VIEW_IS_TRANSIENT_SETTINGS_KEY = f"{PLUGIN_NAME}/is_transient"

################################################################################

RE_ST_SYNTAX_TEST_LINE = re.compile(r'\bSYNTAX\s+TEST\s+"(?P<syntax>[^"]+)"', re.IGNORECASE)
RE_VIM_SYNTAX_LINE = re.compile(r"\b(?:filetype|ft|syntax)=(?P<syntax>[^\s:]+):?(?=\s)", re.IGNORECASE)

################################################################################

GUESSLANG_SERVER_TAG = "server-0.1.7"
GUESSLANG_SERVER_URL = (
    f"https://github.com/jfcherng-sublime/ST-AutoSetSyntax/archive/refs/tags/{GUESSLANG_SERVER_TAG}.zip"
)
