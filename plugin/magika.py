from collections import deque
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .cache import clearable_lru_cache

if TYPE_CHECKING:
    import magika


@clearable_lru_cache()
def get_magika_ignored_labels() -> set[magika.ContentTypeLabel]:
    """Get the set of Magika content types which will be ignored by this plugin."""
    if not get_magika_object():
        return set()

    from magika import ContentTypeLabel

    return {
        ContentTypeLabel.DIRECTORY,
        ContentTypeLabel.EMPTY,
        ContentTypeLabel.TXT,
        ContentTypeLabel.UNDEFINED,
        ContentTypeLabel.UNKNOWN,
    }


@clearable_lru_cache()
def get_magika_object() -> magika.Magika | None:
    """Get the Magika object if available. `None` otherwise."""
    try:
        from magika import Magika, PredictionMode
    except ImportError:
        return None
    return Magika(prediction_mode=PredictionMode.HIGH_CONFIDENCE)


def resolve_magika_label_with_syntax_map(label: str, syntax_map: Mapping[str, list[str]]) -> list[str]:
    """
    Resolve a Magika label to a list of syntax like string.

    :param      label:       The syntax label from Magika.
    :param      syntax_map:  The syntax map. Key / value = Maigka label / list of syntax like string.
    """
    # note that dict is insertion-ordered as of Python 3.7
    res: dict[str, bool] = {}

    deq = deque(syntax_map.get(label, []))
    while deq:
        if (notation := deq.popleft()) in res:
            continue
        res[notation] = False  # visited

        # notation is in the form of "scope:text.xml" or "=xml"
        scope, _, ref = notation.partition("=")

        if ref:
            deq.extendleft(reversed(syntax_map.get(ref, [])))
        else:
            res[scope] = True  # parsed

    return [scope for (scope, is_parsed) in res.items() if is_parsed]
