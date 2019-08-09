from .SyntaxMappings import SyntaxMappings
import logging
import os
import re
import sublime
import sublime_plugin


PLUGIN_NAME = __package__
PLUGIN_DIR = "Packages/%s" % PLUGIN_NAME
PLUGIN_SETTINGS = PLUGIN_NAME + ".sublime-settings"

LOG_LEVEL_DEFAULT = "INFO"
LOG_FORMAT = "%(name)s: [%(levelname)s] %(message)s"

settings = None
working_scope_regex = None
syntax_mappings = None
logging_stream_handler = None
logger = None


def plugin_unloaded():
    global settings, logging_stream_handler, logger

    settings.clear_on_change(PLUGIN_SETTINGS)
    logger.removeHandler(logging_stream_handler)


def plugin_loaded():
    global settings, syntax_mappings, logging_stream_handler, logger, working_scope_regex

    settings = sublime.load_settings(PLUGIN_SETTINGS)

    logging.addLevelName(101, "NOTHING")
    # create logger stream handler
    logging_stream_handler = logging.StreamHandler()
    logging_stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    # config logger
    logger = logging.getLogger(PLUGIN_NAME)
    logger.addHandler(logging_stream_handler)
    apply_log_level(settings, logger)

    working_scope_regex = compile_working_scope(settings, logger)
    syntax_mappings = SyntaxMappings(settings, logger)

    # when the user settings is modified...
    settings.add_on_change(PLUGIN_SETTINGS, plugin_settings_listener)


def plugin_settings_listener():
    """ called when the settings file is changed """

    global settings, syntax_mappings, logger, working_scope_regex

    apply_log_level(settings, logger)
    working_scope_regex = compile_working_scope(settings, logger)
    syntax_mappings = SyntaxMappings(settings, logger)


def apply_log_level(settings, logger):
    """ apply log_level to this plugin """

    log_level = settings.get("log_level", "debug")

    try:
        logger.setLevel(logging._levelNames[log_level])
    except re.error:
        logger.warning(
            'unknown "{0}": {1} (assumed "{2}")'.format("log_level", log_level, LOG_LEVEL_DEFAULT)
        )
        logger.setLevel(logging._levelNames[LOG_LEVEL_DEFAULT])


def compile_working_scope(settings, logger):
    """ compile working_scope into regex object to get better speed """

    working_scope = settings.get("working_scope", r"text\.plain")

    try:
        return re.compile(working_scope)
    except re.error:
        error_message = 'regex compilation failed in user settings "{0}": {1}'.format(
            "working_scope", working_scope
        )
        logger.critical(error_message)
        sublime.error_message(error_message)

        return None


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    global settings, syntax_mappings, working_scope_regex, logger

    def on_activated_async(self, view):
        """ called when a view gains input focus """

        if self.is_event_listener_enabled("on_activated_async") and self.is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def on_clone_async(self, view):
        """ called when a view is cloned from an existing one """

        if self.is_event_listener_enabled("on_clone_async") and self.is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def on_load_async(self, view):
        """ called when the file is finished loading """

        self._apply_syntax_for_stripped_file_name(view, logger)

        if self.is_event_listener_enabled("on_load_async") and self.is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def on_modified_async(self, view):
        """ called after changes have been made to a view """

        if (
            self.is_event_listener_enabled("on_modified_async")
            and self.is_only_one_cursor(view)
            and self.is_first_cursor_near_beginning(view)
            and self.is_on_working_scope(view)
        ):
            view.run_command("auto_set_syntax")

    def on_new_async(self, view):
        """ called when a new buffer is created """

        if self.is_event_listener_enabled("on_new_async") and self.is_on_working_scope(view):
            view.run_command("auto_set_syntax")

        self._apply_file_syntax_for_new_file(view)

    def on_post_text_command(self, view, command_name, args):
        """ called after a text command has been executed """

        if (
            self.is_on_working_scope(view)
            and self.is_event_listener_enabled("on_post_paste")
            and (command_name == "patse" or command_name == "paste_and_indent")
        ):
            view.run_command("auto_set_syntax")

    def on_pre_save_async(self, view):
        """ called just before a view is saved """

        if self.is_event_listener_enabled("on_pre_save_async") and self.is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def is_event_listener_enabled(self, event):
        """ check a event listener is enabled """

        try:
            return settings.get("event_listeners", {})[event]
        except KeyError:
            logger.warning(
                '"{0}" is not set in user settings (assumed true)'.format(
                    "event_listeners -> " + event
                )
            )

            return True

    def is_only_one_cursor(self, view):
        """ check there is only one cursor """

        return len(view.sel()) == 1

    def is_first_cursor_near_beginning(self, view):
        """ check the cursor is at first few lines """

        return view.rowcol(view.sel()[0].begin())[0] < 2

    def is_on_working_scope(self, view):
        """ check the scope of the first line is matched by working_scope """

        if working_scope_regex is None or working_scope_regex.search(view.scope_name(0)) is None:
            return False

        return True

    def _apply_file_syntax_for_new_file(self, view):
        """ may apply a syntax for a new buffer """

        syntax_file_partial = settings.get("new_file_syntax", "")

        if syntax_file_partial != "" and view.scope_name(0).strip() == "text.plain":
            for syntax_map in syntax_mappings:
                syntax_file = syntax_map["file_path"]

                if syntax_file.find(syntax_file_partial) >= 0:
                    view.assign_syntax(syntax_file)
                    logger.info(
                        'assign syntax to "{0}" due to new_file_syntax: {1}'.format(
                            syntax_file, syntax_file_partial
                        )
                    )

                    return

    def _apply_syntax_for_stripped_file_name(self, view, logger):
        """ may match the extension and set the corresponding syntax """

        global settings, syntax_mappings

        if view.scope_name(0).strip() != "text.plain":
            return

        file_path = view.file_name()

        # make sure this is a real file
        if file_path is None:
            return

        file_base_name = os.path.basename(file_path)
        try_filename_remove_exts = settings.get("try_filename_remove_exts", [])

        for try_filename_remove_ext in try_filename_remove_exts:
            if not file_base_name.endswith(try_filename_remove_ext):
                continue

            file_base_name_stripped = file_base_name[0 : -len(try_filename_remove_ext)]

            for syntax_mapping in syntax_mappings:
                syntax_file = syntax_mapping["file_path"]
                fileExtensions = syntax_mapping["file_extensions"]

                if fileExtensions is None:
                    continue

                for fileExtension in fileExtensions:
                    if (
                        file_base_name_stripped.endswith("." + fileExtension)
                        or file_base_name_stripped == fileExtension
                    ):
                        view.assign_syntax(syntax_file)
                        logger.info(
                            'assign syntax to "{0}" due to stripped file name: {1}'.format(
                                syntax_file, file_base_name_stripped
                            )
                        )

                        return


class AutoSetSyntaxCommand(sublime_plugin.TextCommand):
    global settings, syntax_mappings, logger

    def run(self, edit):
        """ match the first line and set the corresponding syntax """

        view = self.view

        # make sure the target view is not a panel
        if view.settings().get("is_widget"):
            return

        first_line = self._get_partial_first_line()

        for syntax_mapping in syntax_mappings:
            syntax_file = syntax_mapping["file_path"]
            first_line_match_regexes = syntax_mapping["first_line_match_compiled"]

            if first_line_match_regexes is None:
                continue

            for first_line_match_regex in first_line_match_regexes:
                if first_line_match_regex.search(first_line) is not None:
                    view.assign_syntax(syntax_file)
                    logger.info(
                        'assign syntax to "{0}" due to: {1}'.format(
                            syntax_file, first_line_match_regex.pattern
                        )
                    )

                    return

    def _get_partial_first_line(self):
        """ get the (partial) first line """

        view = self.view
        region = view.line(0)
        first_line_length_max = settings.get("first_line_length_max", 80)

        if first_line_length_max >= 0:
            # if the first line is longer than the max line length,
            # then we use the max line length
            region = sublime.Region(0, min(region.end(), first_line_length_max))

        return view.substr(region)
