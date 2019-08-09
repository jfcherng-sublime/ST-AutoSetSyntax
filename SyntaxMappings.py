from . import functions
import os
import plistlib
import re
import sublime
import yaml

ST_LANGUAGES = [".sublime-syntax", ".tmLanguage"]


class SyntaxMappings:
    settings = None
    logger = None

    # contents of this list are dict whose keys are
    #     file_extensions
    #     file_path
    #     first_line_match
    #     first_line_match_compiled
    syntax_mappings = []

    # the path of all syntax files
    syntax_files = []

    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger

        self.syntax_files = self._find_syntax_file_paths(True)
        self.syntax_mappings = self._build_syntax_mappings()

        self.logger.debug("found syntax files: {0}".format(self.syntax_files))

    def __iter__(self):
        return iter(self.value())

    def __len__(self):
        return len(self.value())

    def value(self, val=None):
        if val is None:
            return self.syntax_mappings
        else:
            self.syntax_mappings = val

    def _find_syntax_file_paths(self, drop_duplicated: bool = False) -> list[str]:
        """
        @brief find the path of all syntax files

        @param drop_duplicated if True, for a syntax, only the highest priority resource will be returned

        @return list<string> the path of all syntax files
        """

        if drop_duplicated is False:
            syntax_files = []
            for syntax_file_ext in ST_LANGUAGES:
                syntax_files += sublime.find_resources("*" + syntax_file_ext)
        else:
            # key   = syntax resource path without extension
            # value = the corresponding extension
            # example: { 'Packages/Java/Java': '.sublime-syntax' }
            syntax_griddle = {}
            for syntax_file_ext in ST_LANGUAGES:
                resources = sublime.find_resources("*" + syntax_file_ext)
                for resource in resources:
                    resource_name, resource_ext = os.path.splitext(resource)
                    if resource_name not in syntax_griddle:
                        syntax_griddle[resource_name] = resource_ext

            # combine a name and an extension back into a full path
            syntax_files = [n + e for n, e in syntax_griddle.items()]

        return syntax_files

    def _build_syntax_mappings(self) -> list:
        return self._build_syntax_mappings_from_user() + self._build_syntax_mappings_from_st()

    def _build_syntax_mappings_from_user(self) -> list:
        """ load from user settings """

        mapping_settings = self.settings.get("syntax_mapping", {}).items()
        syntax_mappings = []

        for syntax_file_partial, first_line_matches in mapping_settings:
            first_line_match_regexes = []
            for first_line_match in first_line_matches:
                try:
                    first_line_match_regexes.append(re.compile(first_line_match))
                except Exception:
                    self.logger.error(
                        'regex compilation failed in user settings "{0}": {1}'.format(
                            syntax_file_partial, first_line_match
                        )
                    )

            if first_line_match_regexes:
                # syntax_file_partial could be partial path
                # we try to get the real path here
                is_syntax_file_found = False
                for syntax_file in self.syntax_files:
                    if syntax_file.find(syntax_file_partial) >= 0:
                        self.logger.info(
                            'match syntax file "{0}" with "{1}"'.format(
                                syntax_file_partial, syntax_file
                            )
                        )
                        is_syntax_file_found = True

                        syntax_mappings.append(
                            {
                                "file_extensions": None,
                                "file_path": syntax_file,
                                "first_line_match": first_line_matches,
                                "first_line_match_compiled": first_line_match_regexes,
                            }
                        )

                        break

                if is_syntax_file_found is False:
                    self.logger.error(
                        'cannot find a syntax file in user settings "{0}"'.format(
                            syntax_file_partial
                        )
                    )

        return syntax_mappings

    def _build_syntax_mappings_from_st(self) -> list:
        """ load from ST packages (one-time job, unless restart ST) """

        syntax_mappings = []
        for syntax_file in self.syntax_files:

            syntax_file_content = sublime.load_resource(syntax_file).strip()

            attrs = self._get_attributes_from_syntax_file_content(
                syntax_file_content,
                [
                    "file_extensions",
                    "file_types",  # i.e., the 'file_extensions' in XML
                    "first_line_match",
                ],
            )

            if attrs is None:
                self.logger.error("fail parsing file: {0}".format(syntax_file))

                continue

            # use 'file_extensions' as the formal key
            if attrs["file_types"] is not None:
                attrs["file_extensions"] = attrs["file_types"]
                attrs.pop("file_types")

            attrs.update({"file_path": syntax_file, "first_line_match_compiled": None})

            if attrs["first_line_match"] is not None:
                try:
                    attrs["first_line_match_compiled"] = [re.compile(attrs["first_line_match"])]
                except Exception:
                    self.logger.error(
                        'regex compilation failed in "{0}": {1}'.format(
                            syntax_file, attrs["first_line_match"]
                        )
                    )

                attrs["first_line_match"] = [attrs["first_line_match"]]

            syntax_mappings.append(attrs)

        return syntax_mappings

    def _get_attributes_from_syntax_file_content(self, content: str = "", attrs: list = []) -> dict:
        """ find "first_line_match" or "first_line_match" in syntax file content """

        if content.lstrip().startswith("<"):
            return self._get_attributes_from_xml_syntax_file_content(content, attrs)
        else:
            return self._get_attributes_from_yaml_syntax_file_content(content, attrs)

    def _get_attributes_from_yaml_syntax_file_content(
        self, content: str = "", attrs: list = []
    ) -> dict:
        """ find attributes in .sublime-syntax content """

        results = {}

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

        for attr in attrs:
            results[attr] = parsed[attr] if attr in parsed else None

        return results

    def _get_attributes_from_xml_syntax_file_content(
        self, content: str = "", attrs: list = []
    ) -> dict:
        """ find attributes in .tmLanguage content """

        attrs = [functions.snake_to_camel(attr) for attr in attrs]

        results = {}

        try:
            # "<key>patterns</key>" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "<key>patterns</key>"
            cut_pos = content.find("<key>patterns</key>")
            if cut_pos >= 0:
                content = content[:cut_pos] + r"</dict></plist>"

            parsed = plistlib.readPlistFromBytes(content.encode("UTF-8"))
        except Exception:
            return None

        for attr in attrs:
            attr_snake = functions.camel_to_snake(attr)
            results[attr_snake] = parsed[attr] if attr in parsed else None

        return results
