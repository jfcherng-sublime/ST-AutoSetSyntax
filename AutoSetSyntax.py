import logging
import os
import re
import sublime
import sublime_plugin
from .Globals import Globals
from .settings import get_package_name, get_setting, get_settings_object, get_settings_file
from .SyntaxMappings import SyntaxMappings


LOG_LEVEL_DEFAULT = "INFO"
LOG_FORMAT = "[%(name)s][%(levelname)s] %(message)s"


def plugin_loaded() -> None:
    def plugin_settings_listener() -> None:
        """ called when the settings file is changed """

        Globals.working_scope_regex_obj = compile_working_scope()
        Globals.syntax_mappings = SyntaxMappings(get_settings_object(), Globals.logger)
        apply_log_level()

    def compile_working_scope():
        """ compile working_scope into regex object to get better speed """

        working_scope = get_setting("working_scope")

        try:
            # todo: use "triegex" to improve regex
            return re.compile(working_scope)
        except Exception as e:
            error_message = 'Fail to compile regex for "working_scope" `{regex} because {reason}`'.format(
                regex=working_scope, reason=e
            )

            Globals.logger.critical(error_message)
            sublime.error_message(error_message)

    def apply_log_level() -> None:
        """ apply log_level to this plugin """

        log_level = get_setting("log_level")

        try:
            Globals.logger.setLevel(logging._levelNames[log_level])
        except Exception:
            Globals.logger.setLevel(logging._levelNames[LOG_LEVEL_DEFAULT])
            Globals.logger.warning(
                'Unknown "log_level": {1} (assumed "{2}")'.format(log_level, LOG_LEVEL_DEFAULT)
            )

    def get_plugin_logger() -> logging.Logger:
        def set_logger_hander(logger: logging.Logger) -> None:
            # remove all log handlers
            for handler in logger.handlers:
                logger.removeHandler(handler)

            logging_handler = logging.StreamHandler()
            logging_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(logging_handler)

        logging.addLevelName(101, "NOTHING")
        logger = logging.getLogger(get_package_name())
        logger.propagate = False  # prevent appear multiple same log messages
        set_logger_hander(logger)

        return logger

    Globals.logger = get_plugin_logger()

    # when the user settings is modified...
    get_settings_object().add_on_change(get_settings_file(), plugin_settings_listener)
    plugin_settings_listener()


def plugin_unloaded() -> None:
    get_settings_object().clear_on_change(get_settings_file())


class AutoSetNewFileSyntax(sublime_plugin.EventListener):
    def on_activated_async(self, view: sublime.View) -> None:
        """ called when a view gains input focus """

        if self._is_event_listener_enabled("on_activated_async") and self._is_on_working_scope(
            view
        ):
            view.run_command("auto_set_syntax")

    def on_clone_async(self, view: sublime.View) -> None:
        """ called when a view is cloned from an existing one """

        if self._is_event_listener_enabled("on_clone_async") and self._is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def on_load_async(self, view: sublime.View) -> None:
        """ called when the file is finished loading """

        self._apply_syntax_for_stripped_file_name(view)

        if self._is_event_listener_enabled("on_load_async") and self._is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def on_modified_async(self, view: sublime.View) -> None:
        """ called after changes have been made to a view """

        if (
            self._is_event_listener_enabled("on_modified_async")
            and self._is_only_one_cursor(view)
            and self._is_first_cursor_near_beginning(view)
            and self._is_on_working_scope(view)
        ):
            view.run_command("auto_set_syntax")

    def on_new_async(self, view: sublime.View) -> None:
        """ called when a new buffer is created """

        if self._is_event_listener_enabled("on_new_async") and self._is_on_working_scope(view):
            view.run_command("auto_set_syntax")

        self._apply_file_syntax_for_new_file(view)

    def on_post_text_command(self, view: sublime.View, command_name: str, args: dict) -> None:
        """ called after a text command has been executed """

        if (
            self._is_on_working_scope(view)
            and self._is_event_listener_enabled("on_post_paste")
            and (command_name == "patse" or command_name == "paste_and_indent")
        ):
            view.run_command("auto_set_syntax")

    def on_pre_save_async(self, view: sublime.View) -> None:
        """ called just before a view is saved """

        if self._is_event_listener_enabled("on_pre_save_async") and self._is_on_working_scope(view):
            view.run_command("auto_set_syntax")

    def _is_event_listener_enabled(self, event: str) -> bool:
        """ check a event listener is enabled """

        try:
            return bool(get_setting("event_listeners", {})[event])
        except KeyError:
            Globals.logger.warning(
                '"{0}" is not set in user settings (assumed true)'.format(
                    "event_listeners -> " + event
                )
            )

            return True

    def _is_only_one_cursor(self, view: sublime.View) -> bool:
        """ check there is only one cursor """

        return len(view.sel()) == 1

    def _is_first_cursor_near_beginning(self, view: sublime.View) -> bool:
        """ check the cursor is at first few lines """

        return view.rowcol(view.sel()[0].begin())[0] < 2

    def _is_on_working_scope(self, view: sublime.View) -> bool:
        """ check the scope of the first line is matched by working_scope """

        return Globals.working_scope_regex_obj.search(view.scope_name(0))

    def _apply_file_syntax_for_new_file(self, view: sublime.View) -> None:
        """ may apply a syntax for a new buffer """

        syntax_file_partial = get_setting("new_file_syntax")

        if not syntax_file_partial or view.scope_name(0).strip() != "text.plain":
            return

        for syntax_map in Globals.syntax_mappings:
            syntax_file = syntax_map["file_path"]

            if syntax_file.find(syntax_file_partial) >= 0:
                view.assign_syntax(syntax_file)
                Globals.logger.info(
                    'Assign syntax to "{0}" due to new_file_syntax: {1}'.format(
                        syntax_file, syntax_file_partial
                    )
                )

                return

    def _apply_syntax_for_stripped_file_name(self, view: sublime.View) -> None:
        """ may match the extension and set the corresponding syntax """

        if view.scope_name(0).strip() != "text.plain":
            return

        file_path = view.file_name()

        # make sure this is not a buffer
        if file_path is None:
            return

        file_base_name = os.path.basename(file_path)
        try_filename_remove_exts = get_setting("try_filename_remove_exts")

        for try_filename_remove_ext in try_filename_remove_exts:
            if not file_base_name.endswith(try_filename_remove_ext):
                continue

            file_base_name_stripped = file_base_name[0 : -len(try_filename_remove_ext)]

            for syntax_mapping in Globals.syntax_mappings:
                syntax_file = syntax_mapping["file_path"]
                fileExtensions = syntax_mapping["file_extensions"]

                if fileExtensions is None:
                    continue

                for fileExtension in fileExtensions:
                    if (
                        not file_base_name_stripped.endswith("." + fileExtension)
                        and file_base_name_stripped != fileExtension
                    ):
                        continue

                    view.assign_syntax(syntax_file)
                    Globals.logger.info(
                        'Assign syntax to "{syntax}" due to stripped file name: "{old_name}" -> "{new_name}"'.format(
                            syntax=syntax_file,
                            old_name=file_base_name,
                            new_name=file_base_name_stripped,
                        )
                    )

                    return
