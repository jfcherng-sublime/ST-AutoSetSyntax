import copy
import json
import logging
import os
import plistlib
import re
import sublime
import yaml
from .functions import snake_to_camel, camel_to_snake

ST_SYNTAX_FILE_EXTS = [".sublime-syntax", ".tmLanguage"]


class SyntaxMappings(object):
    settings = None
    logger = None

    # items of this list are dicts whose keys are
    #     rule_source: str
    #     file_extensions: set[str]
    #     file_path: str
    #     first_line_match: list[str]
    #     first_line_match_compiled: list[compiled regex object]
    syntax_mappings = []

    # the path of all syntax files
    syntax_files = []

    def __init__(self, settings: sublime.Settings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

        self.syntax_files = self._find_syntax_file_paths()
        self.syntax_mappings = self._build_syntax_mappings()

        self.logger.debug("Found syntax files: {}".format(self.syntax_files))

    def __iter__(self):
        return iter(self.value())

    def __len__(self) -> int:
        return len(self.value())

    def __str__(self) -> str:
        def regex_object_prestringify(re_obj):
            return (re_obj.pattern, re_obj.flags) if re_obj else None

        syntax_mappings = []
        for syntax_mapping in self.syntax_mappings:
            syntax_mapping = copy.copy(syntax_mapping)

            syntax_mapping["file_extensions"] = list(syntax_mapping["file_extensions"])
            syntax_mapping["first_line_match_compiled"] = [
                regex_object_prestringify(regex_object)
                for regex_object in syntax_mapping["first_line_match_compiled"]
            ]

            syntax_mappings.append(syntax_mapping)

        return json.dumps(syntax_mappings)

    def value(self, val=...):
        if val is ...:
            return self.syntax_mappings
        else:
            self.syntax_mappings = val

    def _find_syntax_file_paths(
        self, drop_duplicated: bool = True, remove_useless: bool = True
    ) -> list:
        """
        @brief find the path of all syntax files

        @param drop_duplicated if True, for a syntax, only the highest priority resource will be returned

        @return list[str] the path of all syntax files
        """

        syntax_files = []
        for syntax_file_ext in ST_SYNTAX_FILE_EXTS:
            syntax_files += sublime.find_resources("*" + syntax_file_ext)

        if drop_duplicated:
            # key   = syntax resource path without extension
            # value = the corresponding extension
            # example: { 'Packages/Java/Java': '.sublime-syntax' }
            syntax_griddle = {}

            for syntax_file in syntax_files:
                file_name, file_ext = os.path.splitext(syntax_file)

                # ".sublime-syntax" is always preferred than ".tmLanguage"
                if file_name not in syntax_griddle or file_ext == ".sublime-syntax":
                    syntax_griddle[file_name] = file_ext

            # combine a name and an extension back into a full path
            syntax_files = [name + ext for name, ext in syntax_griddle.items()]

        if remove_useless:
            useless_paths = ["/sublime_lib/tests/"]

            syntax_files = filter(
                lambda syntax_file: all(
                    useless_path not in syntax_file for useless_path in useless_paths
                ),
                syntax_files,
            )

        return sorted(syntax_files)

    def _build_syntax_mappings(self) -> list:
        return list(
            map(
                self._normalize_syntax_mapping_attrs,
                # prefer user settings than built-in rules
                self._build_syntax_mappings_from_user() + self._build_syntax_mappings_from_st(),
            )
        )

    def _build_syntax_mappings_from_user(self) -> list:
        """ load from user settings """

        mapping_settings = self.settings.get("syntax_mapping", {}).items()
        syntax_mappings = []

        for syntax_file_partial, first_line_matches in mapping_settings:
            # syntax_file_partial could be partial path
            # we try to get the full path here
            for syntax_file in self.syntax_files:
                if syntax_file.find(syntax_file_partial) >= 0:
                    self.logger.info(
                        'Match syntax file "{}" with "{}"'.format(syntax_file_partial, syntax_file)
                    )

                    attrs = {
                        "rule_source": "user",
                        "file_path": syntax_file,
                        "file_extensions": set(),
                        "first_line_match": first_line_matches,
                    }

                    syntax_mappings.append(attrs)

                    break
            else:
                self.logger.error('Cannot find a syntax file for "{}"'.format(syntax_file_partial))

        return syntax_mappings

    def _build_syntax_mappings_from_st(self) -> list:
        """ load from ST packages (one-time job, unless restart ST) """

        syntax_mappings = []

        for syntax_file in self.syntax_files:
            syntax_file_content = sublime.load_resource(syntax_file)

            attrs = self._get_attributes_from_syntax_file_content(
                syntax_file_content,
                [
                    # 'file_types' in YAML is the same with 'file_extensions' in XML
                    "file_extensions",
                    "file_types",
                    "first_line_match",
                ],
            )

            if not attrs:
                self.logger.error("Failed to parse file: " + syntax_file)

                continue

            attrs.update({"rule_source": "ST", "file_path": syntax_file})

            syntax_mappings.append(attrs)

        return syntax_mappings

    def _normalize_syntax_mapping_attrs(self, attrs: dict) -> dict:
        attrs = copy.copy(attrs)

        # prevent from None and nonexisting keys
        if "file_types" not in attrs or not attrs["file_types"]:
            attrs["file_types"] = []
        if "file_extensions" not in attrs or not attrs["file_extensions"]:
            attrs["file_extensions"] = []
        if "first_line_match" not in attrs or not attrs["first_line_match"]:
            attrs["first_line_match"] = []

        attrs["file_types"] = set(attrs["file_types"])
        attrs["file_extensions"] = set(attrs["file_extensions"])

        if not isinstance(attrs["first_line_match"], list):
            attrs["first_line_match"] = [attrs["first_line_match"]]

        # compile "first_line_match" into "first_line_match_compiled"
        attrs["first_line_match_compiled"] = []
        for first_line_match in attrs["first_line_match"]:
            try:
                attrs["first_line_match_compiled"].append(
                    self._st_syntax_regex_compile(first_line_match)
                )
            except Exception as e:
                # we want to maintain the same index with "first_line_match"
                # so we apppend a None here
                attrs["first_line_match_compiled"].append(None)
                self.logger.error(
                    'Failed to compile "first_line_match" regex in "{syntax}" `{regex}` because {reason}'.format(
                        syntax=attrs["file_path"], regex=first_line_match, reason=e
                    )
                )

        # use 'file_extensions' as the formal key rather than 'file_types'
        attrs["file_extensions"] |= attrs["file_types"]
        # remove the "file_types" key
        attrs.pop("file_types", None)

        return attrs

    def _st_syntax_regex_compile(self, regex: str):
        """
        @brief Compile regex which is from ST's syntax file
        @details Inline regex flag like "(?x: ... )" is unsupported in Python 3.3 (Python 3.7 is fine).

        @param self  The object
        @param regex The regular expression

        @return The compiled regex object
        """

        import sys

        # no atomic group in Python
        regex = re.sub(r"\(\?>", "(?:", regex)

        if sys.version_info >= (3, 6):
            return re.compile(regex)

        inline_flags = {
            "a": re.ASCII,
            "i": re.IGNORECASE,
            "L": re.LOCALE,
            "m": re.MULTILINE,
            "s": re.DOTALL,
            "u": re.UNICODE,  # default enabled in Python 3
            "x": re.VERBOSE,
        }

        re_pattern = r"\(\?(?P<flags>[{flags}]+):".format(flags="".join(inline_flags.keys()))

        re_flags = 0
        for m in re.finditer(re_pattern, regex):
            for flag in m.group("flags"):
                re_flags |= inline_flags[flag]

        if not (re_flags & re.ASCII):
            re_flags |= re.UNICODE

        regex = re.sub(re_pattern, "(?:", regex)

        return re.compile(regex, re_flags)

    def _get_attributes_from_syntax_file_content(self, content: str = "", attrs: list = []) -> dict:
        """ find "first_line_match" or "first_line_match" in syntax file content """

        if content.lstrip().startswith("<"):
            return self._get_attributes_from_xml_string(content, attrs)
        else:
            return self._get_attributes_from_yaml_string(content, attrs)

    def _get_attributes_from_yaml_string(self, content: str = "", attrs: list = []) -> dict:
        """ find attributes in .sublime-syntax content """

        attrs = map(camel_to_snake, attrs)

        try:
            # "contexts:" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "contexts:"
            cut_pos = content.find("contexts:")
            if cut_pos >= 0:
                content = content[:cut_pos]

            parsed = yaml.safe_load(content)

            if parsed is None:
                raise Exception("fail parsing YAML content")
        except Exception:
            return None

        return {attr: parsed.get(attr, None) for attr in attrs}

    def _get_attributes_from_xml_string(self, content: str = "", attrs: list = []) -> dict:
        """ find attributes in .tmLanguage content """

        attrs = map(camel_to_snake, attrs)

        try:
            # "<key>patterns</key>" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "<key>patterns</key>"
            cut_pos = content.find("<key>patterns</key>")
            if cut_pos >= 0:
                content = content[:cut_pos] + "</dict></plist>"

            parsed = plistlib.readPlistFromBytes(content.encode("UTF-8"))
        except Exception:
            return None

        return {attr: parsed.get(snake_to_camel(attr), None) for attr in attrs}
