from . import functions
import os
import plistlib
import re
import sublime
import yaml

ST_SUPPORT_SYNTAX = int(sublime.version()) >= 3084
ST_LANGUAGES = [".sublime-syntax", ".tmLanguage"] if ST_SUPPORT_SYNTAX else [".tmLanguage"]


class SyntaxMappings:
    settings = None
    logger = None

    # contents of this list are dict whose keys are
    #     file_extensions
    #     file_path
    #     first_line_match
    #     first_line_match_compiled
    syntaxMappings = []

    # the path of all syntax files
    syntaxFiles = []

    def __init__(self, settings, logger):
        self.settings = settings
        self.logger = logger

        self.syntaxFiles = self.findSyntaxFilePaths(True)
        self.syntaxMappings = self._buildSyntaxMappings()

        self.logger.debug("found syntax files: {0}".format(self.syntaxFiles))

    def __iter__(self):
        return iter(self.value())

    def __len__(self):
        return len(self.value())

    def value(self, val=None):
        if val is None:
            return self.syntaxMappings
        else:
            self.syntaxMappings = val

    def findSyntaxFilePaths(self, dropDuplicated=False):
        """
        @brief find the path of all syntax files

        @param dropDuplicated if True, for a syntax, only the highest priority resource will be returned

        @return list<string> the path of all syntax files
        """

        if dropDuplicated is False:
            syntaxFiles = []
            for syntaxFileExt in ST_LANGUAGES:
                syntaxFiles += sublime.find_resources("*" + syntaxFileExt)
        else:
            # key   = syntax resource path without extension
            # value = the corresponding extension
            # example: { 'Packages/Java/Java': '.sublime-syntax' }
            syntaxGriddle = {}
            for syntaxFileExt in ST_LANGUAGES:
                resources = sublime.find_resources("*" + syntaxFileExt)
                for resource in resources:
                    resourceName, resourceExt = os.path.splitext(resource)
                    if resourceName not in syntaxGriddle:
                        syntaxGriddle[resourceName] = resourceExt

            # combine a name and an extension back into a full path
            syntaxFiles = [n + e for n, e in syntaxGriddle.items()]

        return syntaxFiles

    def _buildSyntaxMappings(self):
        return self._buildSyntaxMappingsFromUser() + self._buildSyntaxMappingsFromSt()

    def _buildSyntaxMappingsFromUser(self):
        """ load from user settings """

        mappingSettings = self.settings.get("syntax_mapping", {}).items()
        syntaxMappings = []

        for syntaxFilePartial, firstLineMatches in mappingSettings:
            firstLineMatchRegexes = []
            for firstLineMatch in firstLineMatches:
                try:
                    firstLineMatchRegexes.append(re.compile(firstLineMatch))
                except:
                    self.logger.error(
                        'regex compilation failed in user settings "{0}": {1}'.format(
                            syntaxFilePartial, firstLineMatch
                        )
                    )

            if firstLineMatchRegexes:
                # syntaxFilePartial could be partial path
                # we try to get the real path here
                isSyntaxFileFound = False
                for syntaxFile in self.syntaxFiles:
                    if syntaxFile.find(syntaxFilePartial) >= 0:
                        self.logger.info(
                            'match syntax file "{0}" with "{1}"'.format(
                                syntaxFilePartial, syntaxFile
                            )
                        )
                        isSyntaxFileFound = True

                        syntaxMappings.append(
                            {
                                "file_extensions": None,
                                "file_path": syntaxFile,
                                "first_line_match": firstLineMatches,
                                "first_line_match_compiled": firstLineMatchRegexes,
                            }
                        )

                        break

                if isSyntaxFileFound is False:
                    self.logger.error(
                        'cannot find a syntax file in user settings "{0}"'.format(syntaxFilePartial)
                    )

        return syntaxMappings

    def _buildSyntaxMappingsFromSt(self):
        """ load from ST packages (one-time job, unless restart ST) """

        syntaxMappings = []
        for syntaxFile in self.syntaxFiles:

            syntaxFileContent = sublime.load_resource(syntaxFile).strip()

            attrs = self._getAttributesFromSyntaxFileContent(
                syntaxFileContent,
                [
                    "file_extensions",
                    "file_types",  # i.e., the 'file_extensions' in XML
                    "first_line_match",
                ],
            )

            if attrs is None:
                self.logger.error("fail parsing file: {0}".format(syntaxFile))

                continue

            # use 'file_extensions' as the formal key
            if attrs["file_types"] is not None:
                attrs["file_extensions"] = attrs["file_types"]
                attrs.pop("file_types")

            attrs.update({"file_path": syntaxFile, "first_line_match_compiled": None})

            if attrs["first_line_match"] is not None:
                try:
                    attrs["first_line_match_compiled"] = [re.compile(attrs["first_line_match"])]
                except:
                    self.logger.error(
                        'regex compilation failed in "{0}": {1}'.format(
                            syntaxFile, attrs["first_line_match"]
                        )
                    )

                attrs["first_line_match"] = [attrs["first_line_match"]]

            syntaxMappings.append(attrs)

        return syntaxMappings

    def _getAttributesFromSyntaxFileContent(self, content="", attrs=[]):
        """ find "first_line_match" or "firstLineMatch" in syntax file content """

        if content.lstrip().startswith("<"):
            return self._getAttributesFromXmlSyntaxFileContent(content, attrs)
        else:
            return self._getAttributesFromYamlSyntaxFileContent(content, attrs)

    def _getAttributesFromYamlSyntaxFileContent(self, content="", attrs=[]):
        """ find attributes in .sublime-syntax content """

        results = {}

        try:
            # "contexts:" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "contexts:"
            cutPos = content.find("contexts:")
            if cutPos >= 0:
                content = content[:cutPos]

            parsed = yaml.safe_load(content)

            if parsed is None:
                raise Exception("fail parsing YAML content")
        except:
            return None

        for attr in attrs:
            results[attr] = parsed[attr] if attr in parsed else None

        return results

    def _getAttributesFromXmlSyntaxFileContent(self, content="", attrs=[]):
        """ find attributes in .tmLanguage content """

        attrs = [functions.snakeToCamel(attr) for attr in attrs]

        results = {}

        try:
            # "<key>patterns</key>" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "<key>patterns</key>"
            cutPos = content.find("<key>patterns</key>")
            if cutPos >= 0:
                content = content[:cutPos] + r"</dict></plist>"

            parsed = plistlib.readPlistFromBytes(content.encode("UTF-8"))
        except:
            return None

        for attr in attrs:
            attr_snake = functions.camelToSnake(attr)
            results[attr_snake] = parsed[attr] if attr in parsed else None

        return results
