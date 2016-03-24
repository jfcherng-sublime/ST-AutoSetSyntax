import sublime
import sublime_plugin
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))
from SyntaxMappings import *


PLUGIN_NAME = 'AutoSetNewFileSyntax'
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(name)s: %(levelname)s - %(message)s"

settings = None
syntaxMappings = None

# create logger stream handler
loggingStreamHandler = logging.StreamHandler()
loggingStreamHandler.setFormatter(logging.Formatter(LOG_FORMAT))
# config logger
logger = logging.getLogger(PLUGIN_NAME)
logger.setLevel(LOG_LEVEL)
logger.addHandler(loggingStreamHandler)


def plugin_loaded():
    global settings, syntaxMappings, logger

    settings = sublime.load_settings(PLUGIN_NAME+".sublime-settings")
    syntaxMappings = SyntaxMappings(settings=settings, logger=logger)


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
        for syntaxMapping in syntaxMappings.value():
            syntaxFile, firstLineMatchRegexes = syntaxMapping
            for firstLineMatchRegex in firstLineMatchRegexes:
                if firstLineMatchRegex.search(firstLine) is not None:
                    view.set_syntax_file(syntaxFile)
                    return

    def getPartialFirstLine(self, view):
        region = view.line(0)
        firstLineLengthMax = settings.get('first_line_length_max')
        if firstLineLengthMax >= 0:
            # if the first line is longer than the max line length,
            # then use the max line length
            # otherwise use the actual length of the first line
            region = sublime.Region(0, min(region.end(), firstLineLengthMax))
        return view.substr(region)
