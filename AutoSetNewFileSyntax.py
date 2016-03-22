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
    syntaxFiles = sublime.find_resources("*.sublime-syntax") + sublime.find_resources("*.tmLanguage")
    for syntaxFile in syntaxFiles:
        fileName, fileExt = os.path.splitext(syntaxFile)
        # we prefer .sublime-syntax to .tmLanguage
        # so if a corresponding .sublime-syntax result already exists
        # we drop .tmLanguage directly to gain some speed up
        if fileExt == '.tmLanguage' and fileName+'.sublime-syntax' in syntaxMapping:
            continue
        fileContent = sublime.load_resource(syntaxFile)
        firstLineMatch = findFirstLineMatch(fileContent)
        if firstLineMatch is not None:
            try:
                syntaxMapping[syntaxFile] = re.compile(firstLineMatch)
            except:
                print("{0}: regex compilation failed in {1}".format(PLUGIN, syntaxFile))


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
    try:
        content = content[0:content.find('contexts:')]
    except:
        pass
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

    def on_modified_async(self, view):
        # check there is only one cursor
        cursorCnt = len(view.sel())
        if cursorCnt != 1:
            return
        # check the cursor is at first few lines
        rowPos = view.rowcol(view.sel()[0].a)[0]
        if rowPos > 1:
            return
        # check the scope of the first line is plain text
        if view.scope_name(0).strip() != 'text.plain':
            return
        # try to match the first line
        firstLine = view.substr(view.line(0))
        for syntaxFile, firstLineMatchRe in syntaxMapping.items():
            if firstLineMatchRe.search(firstLine) is not None:
                view.set_syntax_file(syntaxFile)
                return
