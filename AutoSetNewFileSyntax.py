import sublime
import sublime_plugin
import sys
import os
import re
import logging

sys.path.insert(0, os.path.dirname(__file__))
import yaml


PLUGIN_NAME = 'AutoSetNewFileSyntax'
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(name)s: %(levelname)s - %(message)s"

settings = None

# contents of this list are tuples whose values are
#     [0] = path of a syntax file
#     [1] = a list of compiled first_line_match regexes
syntaxMappings = []
syntaxMappingsSt = [] # cache, syntax mappings built drom ST packages

# create logger stream handler
loggingStreamHandler = logging.StreamHandler()
loggingStreamHandler.setFormatter(logging.Formatter(LOG_FORMAT))
# config logger
logger = logging.getLogger(PLUGIN_NAME)
logger.setLevel(LOG_LEVEL)
logger.addHandler(loggingStreamHandler)


def plugin_loaded():
    global settings, syntaxMappingsSt

    settings = sublime.load_settings(PLUGIN_NAME+".sublime-settings")
    # rebuilt syntax mappings if there is an user settings update
    settings.add_on_change("syntax_mapping", rebuildSyntaxMappings)

    syntaxMappingsSt = buildSyntaxMappingsFromSt()
    rebuildSyntaxMappings()


def rebuildSyntaxMappings():
    global syntaxMappings, syntaxMappingsSt

    syntaxMappings = buildSyntaxMappingsFromUser() + syntaxMappingsSt


def buildSyntaxMappingsFromUser():
    """ load from user settings """

    global settings

    syntaxMappings = []
    for syntaxFile, firstLineMatches in settings.get('syntax_mapping').items():
        firstLineMatchRegexes = []
        for firstLineMatch in firstLineMatches:
            try:
                firstLineMatchRegexes.append(re.compile(firstLineMatch))
            except:
                logger.error("regex compilation failed in user settings {0}: {1}".format(syntaxFile, firstLineMatch))
        if len(firstLineMatchRegexes) > 0:
            syntaxMappings.append((syntaxFile, firstLineMatchRegexes))
    return syntaxMappings


def buildSyntaxMappingsFromSt():
    """ load from ST packages (one-time job, unless restart ST) """

    syntaxMappings = []
    for syntaxFile in findSyntaxResources(True):
        firstLineMatch = findFirstLineMatch(sublime.load_resource(syntaxFile))
        if firstLineMatch is not None:
            try:
                syntaxMappings.append((syntaxFile, [re.compile(firstLineMatch)]))
            except:
                logger.error("regex compilation failed in {0}: {1}".format(syntaxFile, firstLineMatch))
    return syntaxMappings


def findSyntaxResources(dropDuplicated=False):
    """
    find all syntax resources

    dropDuplicated:
        If True, for a syntax, only the highest priority resource will be returned.
    """

    # syntax priority is from high to low
    syntaxFileExts = ['.sublime-syntax', '.tmLanguage']
    if dropDuplicated is False:
        syntaxFiles = []
        for syntaxFileExt in syntaxFileExts:
            syntaxFiles += sublime.find_resources('*'+syntaxFileExt)
    else:
        # key   = syntax resource path without extension
        # value = the corresponding extension
        # example: { 'Packages/Java/Java': '.sublime-syntax' }
        syntaxGriddle = {}
        for syntaxFileExt in syntaxFileExts:
            resources = sublime.find_resources('*'+syntaxFileExt)
            for resource in resources:
                resourceName, resourceExt = os.path.splitext(resource)
                if resourceName not in syntaxGriddle:
                    syntaxGriddle[resourceName] = resourceExt
        # combine a name and an extension back into a full path
        syntaxFiles = [n+e for n, e in syntaxGriddle.items()]
    return syntaxFiles


def findFirstLineMatch(content=''):
    """ find "first_line_match" or "firstLineMatch" in syntax file content """

    content = content.strip()
    if content[0] == '%':
        return findFirstLineMatchYaml(content)
    else:
        return findFirstLineMatchXml(content)


def findFirstLineMatchYaml(content=''):
    """ find "first_line_match" in .sublime-syntax content """

    # strip everything since "contexts:" to speed up searching
    cutPos = content.find('contexts:')
    if cutPos != -1:
        content = content[0:cutPos]
    # early return
    if content.find('first_line_match') == -1:
        return None
    # start parsing
    yamlDict = yaml.load(content)
    if 'first_line_match' in yamlDict:
        return yamlDict['first_line_match']
    else:
        return None


def findFirstLineMatchXml(content=''):
    """ find "firstLineMatch" in .tmLanguage content """

    cutPoint = content.find('firstLineMatch')
    # early return
    if cutPoint == -1:
        return None
    # cut string to speed up searching
    content = content[cutPoint:]
    matches = re.search(r"firstLineMatch</key>\s*<string>(.*?)</string>", content, re.DOTALL)
    if matches is not None:
        return matches.group(1)
    else:
        return None


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    global settings, syntaxMappings

    def on_modified_async(self, view):
        # check there is only one cursor
        if len(view.sel()) != 1:
            return
        # check the cursor is at first few lines
        if view.rowcol(view.sel()[0].a)[0] > 1:
            return
        # check the scope of the first line is plain text
        if view.scope_name(0).strip() != 'text.plain':
            return
        # try to match the first line
        self.matchAndSetSyntax(view)

    def matchAndSetSyntax(self, view):
        firstLine = self.getPartialFirstLine(view)
        for syntaxMapping in syntaxMappings:
            syntaxFile, firstLineMatchRegexes = syntaxMapping
            for firstLineMatchRegex in firstLineMatchRegexes:
                if firstLineMatchRegex.search(firstLine) is not None:
                    view.set_syntax_file(syntaxFile)
                    return

    def getPartialFirstLine(self, view):
        firstLineLengthMax = settings.get('first_line_length_max')
        if firstLineLengthMax < 0:
            region = view.line(0)
        else:
            # if the first line is longer than the max line length,
            # then use the max line length
            # otherwise use the actual length of the first line
            partialLineEndPos = min(view.line(0).end(), settings.get('first_line_length_max'))
            # get the partial first line
            region = sublime.Region(0, partialLineEndPos)
        return view.substr(region)
