import sublime
import sublime_plugin
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))
from SyntaxMappings import *


PLUGIN_NAME = 'AutoSetNewFileSyntax'
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(name)s: [%(levelname)s] %(message)s"

settings = None
syntaxMappings = None
loggingStreamHandler = None
logger = None


def plugin_unloaded():
    global settings, loggingStreamHandler, logger

    settings.clear_on_change("syntax_mapping")
    logger.removeHandler(loggingStreamHandler)


def plugin_loaded():
    global settings, syntaxMappings, loggingStreamHandler, logger

    # create logger stream handler
    loggingStreamHandler = logging.StreamHandler()
    loggingStreamHandler.setFormatter(logging.Formatter(LOG_FORMAT))
    # config logger
    logger = logging.getLogger(PLUGIN_NAME)
    logger.setLevel(LOG_LEVEL)
    logger.addHandler(loggingStreamHandler)

    settings = sublime.load_settings(PLUGIN_NAME+".sublime-settings")

    syntaxMappings = SyntaxMappings(settings=settings, logger=logger)

    # rebuilt syntax mappings if there is an user settings update
    settings.add_on_change("syntax_mapping", syntaxMappings.rebuildSyntaxMappings)


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    global settings, syntaxMappings

    def on_activated_async(self, view):
        if (
            self.isEventListenerEnabled('on_activated_async') and
            self.isScopePlainText(view)
        ):
            self.matchAndSetSyntax(view)

    def on_clone_async(self, view):
        if (
            self.isEventListenerEnabled('on_clone_async') and
            self.isScopePlainText(view)
        ):
            self.matchAndSetSyntax(view)

    def on_load_async(self, view):
        if (
            self.isEventListenerEnabled('on_load_async') and
            self.isScopePlainText(view)
        ):
            self.matchAndSetSyntax(view)

    def on_modified_async(self, view):
        if (
            self.isEventListenerEnabled('on_modified_async') and
            self.isOnlyOneCursor(view) and
            self.isFirstCursorNearBeginning(view) and
            self.isScopePlainText(view)
        ):
            self.matchAndSetSyntax(view)

    def on_pre_save_async(self, view):
        if (
            self.isEventListenerEnabled('on_pre_save_async') and
            self.isScopePlainText(view)
        ):
            self.matchAndSetSyntax(view)

    def isEventListenerEnabled(self, event):
        try:
            return settings.get("event_listeners", None)[event]
        except:
            return False

    def isOnlyOneCursor(self, view):
        """ check there is only one cursor """

        return len(view.sel()) == 1

    def isFirstCursorNearBeginning(self, view):
        """ check the cursor is at first few lines """

        return view.rowcol(view.sel()[0].a)[0] < 2

    def isScopePlainText(self, view):
        """ check the scope of the first line is plain text """

        return view.scope_name(0).strip() == 'text.plain'

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
