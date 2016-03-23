import sublime
import sublime_plugin
import sys
import os
import re

sys.path.insert(0, os.path.dirname(__file__))
import yaml


PLUGIN = 'AutoSetNewFileSyntax'

# key   = path of a syntax file
# value = compiled first_line_match regex
syntaxMapping = {}


def plugin_loaded():
    global syntaxMapping

    syntaxMapping = {}
    syntaxFiles = findSyntaxResources(True)
    for syntaxFile in syntaxFiles:
        firstLineMatch = findFirstLineMatch(sublime.load_resource(syntaxFile))
        if firstLineMatch is not None:
            try:
                syntaxMapping[syntaxFile] = re.compile(firstLineMatch)
            except:
                print("{0}: regex compilation failed in {1}".format(PLUGIN, syntaxFile))


def findSyntaxResources (dropDuplicated=False):
    """
    find all syntax resources

    dropDuplicated: if True, for a syntax, only the highest priority resource will be returned
    """

    # priority from high to low
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
        # combine a name and an extension into a full path
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
    content = content.split('contexts:', 1)[0]
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
    matches = re.search(r"firstLineMatch</key>[\r\n\s]*<string>(.*?)</string>", content, re.DOTALL)
    if matches is not None:
        return matches.group(1)
    else:
        return None


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    global syntaxMapping

    # we only take partial from the first line to prevent from a large one-line content
    firstLineLengthMax = 80

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
        for syntaxFile, firstLineMatchRe in syntaxMapping.items():
            if firstLineMatchRe.search(firstLine) is not None:
                view.set_syntax_file(syntaxFile)
                return

    def getPartialFirstLine(self, view):
        # if the first line is longer than the max line length,
        #  then use the max line length
        # otherwise use the actual length of the first line
        partialLineEndPos = min(view.line(0).end(), self.firstLineLengthMax)
        # get the partial first line
        return view.substr(sublime.Region(0, partialLineEndPos))
