from .SyntaxMappings import SyntaxMappings
import logging
import os
import re
import sublime
import sublime_plugin


PLUGIN_NAME = __package__
PLUGIN_DIR = "Packages/%s" % PLUGIN_NAME
PLUGIN_SETTINGS = PLUGIN_NAME + '.sublime-settings'

LOG_LEVEL_DEFAULT = 'INFO'
LOG_FORMAT = "%(name)s: [%(levelname)s] %(message)s"

settings = None
workingScopeRegex = None
syntaxMappings = None
loggingStreamHandler = None
logger = None


def plugin_unloaded():
    global settings, loggingStreamHandler, logger

    settings.clear_on_change(PLUGIN_SETTINGS)
    logger.removeHandler(loggingStreamHandler)


def plugin_loaded():
    global settings, syntaxMappings, loggingStreamHandler, logger, workingScopeRegex

    settings = sublime.load_settings(PLUGIN_SETTINGS)

    logging.addLevelName(101, 'NOTHING')
    # create logger stream handler
    loggingStreamHandler = logging.StreamHandler()
    loggingStreamHandler.setFormatter(logging.Formatter(LOG_FORMAT))
    # config logger
    logger = logging.getLogger(PLUGIN_NAME)
    logger.addHandler(loggingStreamHandler)
    applyLogLevel(settings, logger)

    workingScopeRegex = compileWorkingScope(settings, logger)
    syntaxMappings = SyntaxMappings(settings, logger)

    # when the user settings is modified...
    settings.add_on_change(PLUGIN_SETTINGS, pluginSettingsListener)


def pluginSettingsListener():
    """ called when the settings file is changed """

    global settings, syntaxMappings, logger, workingScopeRegex

    applyLogLevel(settings, logger)
    workingScopeRegex = compileWorkingScope(settings, logger)
    syntaxMappings = SyntaxMappings(settings, logger)


def applyLogLevel(settings, logger):
    """ apply log_level to this plugin """

    logLevel = settings.get('log_level', 'debug')

    try:
        logger.setLevel(logging._levelNames[logLevel])
    except:
        logger.warning('unknown "{0}": {1} (assumed "{2}")'.format('log_level', logLevel, LOG_LEVEL_DEFAULT))
        logger.setLevel(logging._levelNames[LOG_LEVEL_DEFAULT])


def compileWorkingScope(settings, logger):
    """ compile workingScope into regex object to get better speed """

    workingScope = settings.get('working_scope', r'text\.plain')

    try:
        return re.compile(workingScope)
    except:
        errorMessage = 'regex compilation failed in user settings "{0}": {1}'.format('working_scope', workingScope)
        logger.critical(errorMessage)
        sublime.error_message(errorMessage)

        return None


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    global settings, workingScopeRegex

    def on_activated_async(self, view):
        """ called when a view gains input focus """

        if (
            self.isEventListenerEnabled('on_activated_async') and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def on_clone_async(self, view):
        """ called when a view is cloned from an existing one """

        if (
            self.isEventListenerEnabled('on_clone_async') and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def on_load_async(self, view):
        """ called when the file is finished loading """

        if view.scope_name(0).strip() == 'text.plain':
            view.run_command('auto_set_syntax_for_text_by_ext')

        if (
            self.isEventListenerEnabled('on_load_async') and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def on_modified_async(self, view):
        """ called after changes have been made to a view """

        if (
            self.isEventListenerEnabled('on_modified_async') and
            self.isOnlyOneCursor(view) and
            self.isFirstCursorNearBeginning(view) and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def on_new_async(self, view):
        """ called when a new buffer is created """

        if (
            self.isEventListenerEnabled('on_new_async') and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def on_post_text_command(self, view, command_name, args):
        """ called after a text command has been executed """

        if (
            self.isOnWorkingScope(view) and
            (
                self.isEventListenerEnabled('on_post_paste') and
                (
                    command_name == 'patse' or
                    command_name == 'paste_and_indent'
                )
            )
        ):
            view.run_command('auto_set_syntax')

    def on_pre_save_async(self, view):
        """ called just before a view is saved """

        if (
            self.isEventListenerEnabled('on_pre_save_async') and
            self.isOnWorkingScope(view)
        ):
            view.run_command('auto_set_syntax')

    def isEventListenerEnabled(self, event):
        """ check a event listener is enabled """

        try:
            return settings.get('event_listeners', None)[event]
        except:
            logger.warning('"{0}" is not set in user settings (assumed true)'.format('event_listeners -> '+event))

            return True

    def isOnlyOneCursor(self, view):
        """ check there is only one cursor """

        return len(view.sel()) == 1

    def isFirstCursorNearBeginning(self, view):
        """ check the cursor is at first few lines """

        return view.rowcol(view.sel()[0].begin())[0] < 2

    def isOnWorkingScope(self, view):
        """ check the scope of the first line is matched by working_scope """

        if (
            workingScopeRegex is None or
            workingScopeRegex.search(view.scope_name(0)) is None
        ):
            return False

        return True


class AutoSetSyntaxForTextByExtCommand(sublime_plugin.TextCommand):
    global settings, syntaxMappings, logger

    def run(self, edit):
        """ match the extension and set the corresponding syntax """

        view = self.view
        filePath = view.file_name()

        # make sure this is a real file
        if filePath is None:
            return

        fileBaseName = os.path.basename(filePath)
        tryFilenameRemoveExts = settings.get('try_filename_remove_exts', [])

        for tryFilenameRemoveExt in tryFilenameRemoveExts:
            if not fileBaseName.endswith(tryFilenameRemoveExt):
                continue

            fileBaseNameStripped = fileBaseName[0:-len(tryFilenameRemoveExt)]

            for syntaxMapping in syntaxMappings:
                syntaxFile = syntaxMapping['file_path']
                fileExtensions = syntaxMapping['file_extensions']

                if fileExtensions is None:
                    continue

                for fileExtension in fileExtensions:
                    if (
                        fileBaseNameStripped.endswith('.'+fileExtension) or
                        fileBaseNameStripped == fileExtension
                    ):
                        view.assign_syntax(syntaxFile)
                        logger.info('assign syntax to "{0}" due to stripped file name: {1}'.format(syntaxFile, fileBaseNameStripped))

                        return


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    global settings, syntaxMappings, logger

    def run(self, edit):
        """ match the first line and set the corresponding syntax """

        view = self.view

        # make sure the target view is not a panel
        if view.settings().get('is_widget'):
            return

        firstLine = self._getPartialFirstLine()

        for syntaxMapping in syntaxMappings:
            syntaxFile = syntaxMapping['file_path']
            firstLineMatchRegexes = syntaxMapping['first_line_match_compiled']

            if firstLineMatchRegexes is None:
                continue

            for firstLineMatchRegex in firstLineMatchRegexes:
                if firstLineMatchRegex.search(firstLine) is not None:
                    view.assign_syntax(syntaxFile)
                    logger.info('assign syntax to "{0}" due to: {1}'.format(syntaxFile, firstLineMatchRegex.pattern))

                    return

    def _getPartialFirstLine(self):
        """ get the (partial) first line """

        view = self.view
        region = view.line(0)
        firstLineLengthMax = settings.get('first_line_length_max', 80)

        if firstLineLengthMax >= 0:
            # if the first line is longer than the max line length,
            # then we use the max line length
            region = sublime.Region(0, min(region.end(), firstLineLengthMax))

        return view.substr(region)
