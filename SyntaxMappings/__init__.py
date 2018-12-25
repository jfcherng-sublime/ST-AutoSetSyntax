import os
import plistlib
import re
import sublime
import yaml

ST_SUPPORT_SYNTAX = int(sublime.version()) >= 3084
ST_LANGUAGES = ['.sublime-syntax', '.tmLanguage'] if ST_SUPPORT_SYNTAX else ['.tmLanguage']


class SyntaxMappings():
    settings = None
    logger = None

    # contents of this list are dict whose keys are
    #     file_extensions
    #     file_path
    #     first_line_match
    #     first_line_match_compiled
    syntaxMappings = []
    syntaxMappingsSt = [] # cache, syntax mappings built drom ST packages

    syntaxFiles = []

    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = logger

        self.syntaxFiles = self.findSyntaxResources(True)
        self.syntaxMappingsSt = self.buildSyntaxMappingsFromSt()
        self.buildSyntaxMappings()

        self.logger.debug('found syntax files: {0}'.format(self.syntaxFiles))

    def __iter__(self):
        return iter(self.value())

    def __len__(self):
        return len(self.value())

    def value(self, val=None):
        if val is None:
            return self.syntaxMappings
        else:
            self.syntaxMappings = val

    def buildSyntaxMappings(self):
        self.syntaxMappings = self.buildSyntaxMappingsFromUser() + self.syntaxMappingsSt

    def buildSyntaxMappingsFromUser(self):
        """ load from user settings """

        syntaxMappings = []
        for syntaxFilePartial, firstLineMatches in self.settings.get('syntax_mapping').items():
            firstLineMatchRegexes = []
            for firstLineMatch in firstLineMatches:
                try:
                    firstLineMatchRegexes.append(re.compile(firstLineMatch))
                except:
                    self.logger.error('regex compilation failed in user settings "{0}": {1}'.format(syntaxFilePartial, firstLineMatch))

            if firstLineMatchRegexes:
                # syntaxFilePartial could be partial path
                # we try to get the real path here
                isSyntaxFileFound = False
                for syntaxFile in self.syntaxFiles:
                    if syntaxFile.find(syntaxFilePartial) >= 0:
                        self.logger.info('match syntax file "{0}" with "{1}"'.format(syntaxFilePartial, syntaxFile))
                        isSyntaxFileFound = True

                        syntaxMappings.append({
                            'file_extensions': None,
                            'file_path': syntaxFile,
                            'first_line_match': firstLineMatches,
                            'first_line_match_compiled': firstLineMatchRegexes,
                        })
                        break

                if isSyntaxFileFound is False:
                    self.logger.error('cannot find a syntax file in user settings "{0}"'.format(syntaxFilePartial))

        return syntaxMappings

    def buildSyntaxMappingsFromSt(self):
        """ load from ST packages (one-time job, unless restart ST) """

        syntaxMappings = []
        for syntaxFile in self.syntaxFiles:

            syntaxFileContent = sublime.load_resource(syntaxFile).strip()

            attrs = self.getAttributesFromSyntaxFileContent(syntaxFileContent, [
                'file_extensions',
                'file_types', # i.e., the 'file_extensions' in XML
                'first_line_match',
            ])

            if attrs is None:
                self.logger.error('fail parsing file: {0}'.format(syntaxFile))
                continue

            # use 'file_extensions' as the formal key
            if attrs['file_types'] is not None:
                attrs['file_extensions'] = attrs['file_types']
                attrs.pop('file_types')

            attrs.update({
                'file_path': syntaxFile,
                'first_line_match_compiled': None,
            })

            if attrs['first_line_match'] is not None:
                try:
                    attrs['first_line_match_compiled'] = [re.compile(attrs['first_line_match'])]
                except:
                    self.logger.error('regex compilation failed in "{0}": {1}'.format(syntaxFile, attrs['first_line_match']))

                attrs['first_line_match'] = [attrs['first_line_match']]

            syntaxMappings.append(attrs)

        return syntaxMappings

    def findSyntaxResources(self, dropDuplicated=False):
        """
        find all syntax resources

        dropDuplicated:
            If True, for a syntax, only the highest priority resource will be returned.
        """

        if dropDuplicated is False:
            syntaxFiles = []
            for syntaxFileExt in ST_LANGUAGES:
                syntaxFiles += sublime.find_resources('*'+syntaxFileExt)
        else:
            # key   = syntax resource path without extension
            # value = the corresponding extension
            # example: { 'Packages/Java/Java': '.sublime-syntax' }
            syntaxGriddle = {}
            for syntaxFileExt in ST_LANGUAGES:
                resources = sublime.find_resources('*'+syntaxFileExt)
                for resource in resources:
                    resourceName, resourceExt = os.path.splitext(resource)
                    if resourceName not in syntaxGriddle:
                        syntaxGriddle[resourceName] = resourceExt
            # combine a name and an extension back into a full path
            syntaxFiles = [n+e for n, e in syntaxGriddle.items()]
        return syntaxFiles

    def getAttributesFromSyntaxFileContent(self, content='', attrs=[]):
        """ find "first_line_match" or "firstLineMatch" in syntax file content """

        if content.startswith('<'):
            return self.getAttributesFromXmlSyntaxFileContent(content, attrs)
        else:
            return self.getAttributesFromYamlSyntaxFileContent(content, attrs)

    def getAttributesFromYamlSyntaxFileContent(self, content='', attrs=[]):
        """ find attributes in .sublime-syntax content """

        results = {}

        try:
            # "contexts:" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "contexts:"
            cutPos = content.find('contexts:')
            if cutPos != -1:
                content = content[:cutPos]

            parsed = yaml.safe_load(content)

            if parsed is None:
                raise Exception('fail parsing YAML content')
        except:
            return None

        for attr in attrs:
            if attr in parsed:
                results[attr] = parsed[attr]
            else:
                results[attr] = None

        return results

    def getAttributesFromXmlSyntaxFileContent(self, content='', attrs=[]):
        """ find attributes in .tmLanguage content """

        results = {}

        attrs = [self.snakeToCamel(attr) for attr in attrs]

        try:
            # "<key>patterns</key>" is usually the last (and largest) part of a syntax deinition.
            # to speed up searching, strip everything behinds "<key>patterns</key>"
            cutPos = content.find('<key>patterns</key>')
            if cutPos != -1:
                content = content[:cutPos] + r'</dict></plist>'

            parsed = plistlib.readPlistFromBytes(content.encode('UTF-8'))
        except:
            return None

        for attr in attrs:
            if attr in parsed:
                results[self.camelToSnake(attr)] = parsed[attr]
            else:
                results[self.camelToSnake(attr)] = None

        return results

    def snakeToCamel(self, snake):
        parts = snake.split('_')
        return parts[0] + ''.join(part.title() for part in parts[1:])

    def camelToSnake(self, camel):
        s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()
