from __future__ import annotations

import re
import sys
from pathlib import Path

import sublime

assert __package__

################################################################################

VERSION_INFO = (4, 1, 0)
VERSION = ".".join(map(str, VERSION_INFO))

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

VIEW_KEY_IS_CREATED = f"{PLUGIN_NAME}/is_created"
"""This view setting indicates that this view is created by AutoSetSyntax."""
VIEW_KEY_IS_ASSIGNED = f"{PLUGIN_NAME}/is_assigned"
"""This view setting indicates that the syntax of this view is assigned by AutoSetSyntax."""
VIEW_KEY_IS_TRANSIENT = f"{PLUGIN_NAME}/is_transient"
"""This view setting is just a temporary flag during running AutoSetSyntax on a transient view."""

################################################################################

RE_ST_SYNTAX_TEST_LINE = re.compile(r'\bSYNTAX\s+TEST\s+"(?P<syntax>[^"]+)"', re.IGNORECASE)
RE_VIM_SYNTAX_LINE = re.compile(r"\b(?:filetype|ft|syntax)=(?P<syntax>[^\s:]+):?(?=\s)", re.IGNORECASE)

################################################################################

PLUGIN_PY_LIBS_DIR_NAME = f"libs-py38@{ST_PLATFORM_ARCH}"
PLUGIN_PY_LIBS_DIR = PLUGIN_STORAGE_DIR / PLUGIN_PY_LIBS_DIR_NAME
PLUGIN_PY_LIBS_ZIP_NAME = f"{PLUGIN_PY_LIBS_DIR_NAME}.zip"
PLUGIN_PY_LIBS_URL = "https://github.com/{repo}/raw/{ref}/{file}".format(
    repo="jfcherng-sublime/ST-AutoSetSyntax",
    ref="dependencies",
    file=PLUGIN_PY_LIBS_ZIP_NAME,
)
