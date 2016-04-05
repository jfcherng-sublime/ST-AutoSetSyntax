import os
import re
import sublime
import yaml


ST_SUPPORT_SYNTAX = int(sublime.version()) >= 3084
ST_LANGUAGES = ['.sublime-syntax', '.tmLanguage'] if ST_SUPPORT_SYNTAX else ['.tmLanguage']


class SyntaxMappings():
    settings = None
    logger = None

    # contents of this list are tuples whose values are
    #     [0] = path of a syntax file
    #     [1] = a list of compiled first_line_match regexes
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
                syntaxFileFound = False
                for syntaxFile in self.syntaxFiles:
                    if syntaxFile.find(syntaxFilePartial) >= 0:
                        self.logger.info('match syntax file "{0}" with "{1}"'.format(syntaxFilePartial, syntaxFile))
                        syntaxFileFound = True
                        syntaxMappings.append((syntaxFile, firstLineMatchRegexes))
                        break
                if syntaxFileFound is False:
                    self.logger.error('cannot find a syntax file in user settings "{0}"'.format(syntaxFilePartial))
        return syntaxMappings

    def buildSyntaxMappingsFromSt(self):
        """ load from ST packages (one-time job, unless restart ST) """

        syntaxMappings = []
        for syntaxFile in self.syntaxFiles:
            firstLineMatch = self.findFirstLineMatch(sublime.load_resource(syntaxFile))
            if firstLineMatch is False:
                self.logger.error('fail parsing file: {0}'.format(syntaxFile))
            elif firstLineMatch is not None:
                try:
                    syntaxMappings.append((syntaxFile, [re.compile(firstLineMatch)]))
                except:
                    self.logger.error('regex compilation failed in "{0}": {1}'.format(syntaxFile, firstLineMatch))
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

    def findFirstLineMatch(self, content=''):
        """ find "first_line_match" or "firstLineMatch" in syntax file content """

        content = content.strip()
        if content.startswith('<'):
            return self.findFirstLineMatchXml(content)
        else:
            return self.findFirstLineMatchYaml(content)

    def findFirstLineMatchYaml(self, content=''):
        """ find "first_line_match" in .sublime-syntax content """

        # strip everything since "contexts:" to speed up searching
        cutPos = content.find('contexts:')
        if cutPos != -1:
            content = content[:cutPos]
        # early return
        if content.find('first_line_match') == -1:
            return None
        # start parsing
        try:
            parsed = yaml.load(content)
            if 'first_line_match' in parsed:
                return parsed['first_line_match']
            else:
                return None
        except:
            return False

    def findFirstLineMatchXml(self, content=''):
        """ find "firstLineMatch" in .tmLanguage content """

        cutPos = content.find('<key>firstLineMatch</key>')
        # early return
        if cutPos == -1:
            return None
        # cut string to speed up searching
        content = content[cutPos:]
        matches = re.search(r'<key>firstLineMatch</key>\s*<string>(.*?)</string>', content, re.DOTALL)
        if matches is not None:
            return matches.group(1)
        else:
            return None
