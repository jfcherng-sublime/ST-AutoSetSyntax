import re
import sublime
from .Globals import Globals


def snake_to_camel(snake: str, upper_first: bool = False) -> str:
    # title-cased words
    words = [word.title() for word in snake.split("_")]

    if words and not upper_first:
        words[0] = words[0].lower()

    return "".join(words)


def camel_to_snake(camel: str) -> str:
    # first upper-cased camel
    camel = camel[0].upper() + camel[1:]

    return "_".join(re.findall(r"[A-Z][^A-Z]*", camel)).lower()


def view_assign_syntax(view: sublime.View, syntax_file: str, reason: str = "") -> None:
    view.assign_syntax(syntax_file)

    if reason:
        msg = 'Assign syntax to "{syntax}" because {reason}'
    else:
        msg = 'Assign syntax to "{syntax}"'

    Globals.logger.info(msg.format(syntax=syntax_file, reason=reason))
