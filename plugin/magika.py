from collections import deque
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .cache import clearable_lru_cache
from .logger import Logger

if TYPE_CHECKING:
    import magika


@clearable_lru_cache()
def get_magika_ignored_labels() -> frozenset[magika.ContentTypeLabel]:
    """
    Get the set of Magika content types which will be ignored by this plugin.

    A `frozenset` because this is an lru-cached shared object -- a mutable return value would
    let one accidental `.add()` corrupt global plugin state until reload.

    Note that the plugin compares against the raw `magika_result.dl.label`, not the final
    output label, so generic text-ish labels (which have no `magika.syntax_map.*` entry)
    must be ignored here to avoid pointless syntax-map resolution failures.
    """
    if not get_magika_object():
        return frozenset()

    from magika import ContentTypeLabel

    return frozenset({
        ContentTypeLabel.DIRECTORY,
        ContentTypeLabel.EMPTY,
        ContentTypeLabel.TXT,
        ContentTypeLabel.TXTASCII,
        ContentTypeLabel.TXTUTF16,
        ContentTypeLabel.TXTUTF8,
        ContentTypeLabel.UNDEFINED,
        ContentTypeLabel.UNKNOWN,
        ContentTypeLabel.RANDOMASCII,
        ContentTypeLabel.RANDOMBYTES,
        ContentTypeLabel.RANDOMTXT,
    })


def is_magika_importable() -> bool:
    """
    Whether the `magika` package can be imported, without loading it or initializing a model.

    Cheaper than `get_magika_object()`, which constructs a full inference session.
    """
    import importlib.util

    return importlib.util.find_spec("magika") is not None


@clearable_lru_cache()
def get_magika_object() -> magika.Magika | None:
    """Get the Magika object if available. `None` otherwise."""
    try:
        from magika import Magika
        from magika import PredictionMode
    except ImportError:
        return None

    try:
        # the constructor reads model files from disk and loads the onnxruntime binary, which can
        # fail on a corrupt/partial dependency install or a missing native DLL
        return Magika(prediction_mode=PredictionMode.HIGH_CONFIDENCE)
    except Exception as e:
        Logger.log(f"🔮 Magika failed to initialize: {e}")
        return None


def resolve_magika_label_with_syntax_map(label: str, syntax_map: Mapping[str, list[str]]) -> list[str]:
    """
    Resolve a Magika label to a list of syntax like string.

    :param      label:       The syntax label from Magika.
    :param      syntax_map:  The syntax map. Key / value = Maigka label / list of syntax like string.
    """

    def notations_of(key: str) -> list[str]:
        # a key present in settings with an explicit `null` value (e.g. a user trying to "unset"
        # an override) comes back as None here, not the [] default -- `.get(key, [])`'s default
        # only applies when `key` is absent. deque()/reversed() would raise on None.
        value = syntax_map.get(key)
        return value if isinstance(value, list) else []

    # note that dict is insertion-ordered as of Python 3.7
    res: dict[str, bool] = {}

    deq = deque(notations_of(label))
    while deq:
        if (notation := deq.popleft()) in res:
            continue
        res[notation] = False  # visited

        # notation is in the form of "scope:text.xml" or "=xml"
        scope, _, ref = notation.partition("=")

        if ref:
            deq.extendleft(reversed(notations_of(ref)))
        else:
            res[scope] = True  # parsed

    return [scope for (scope, is_parsed) in res.items() if is_parsed]
