from typing import Dict, Literal, NamedTuple, Union

__all__ = ["I18nMessage"]


class I18nMessage(NamedTuple):
    """A message for Workbench to translate.

    This is a data-transfer format for passing messages between modules and
    Workbench. Module authors should invoke :py:func:`i18n.trans()` instead of
    creating raw ``I18nMessage`` objects: Workbench's i18n tools parse
    ``trans()`` calls to manipulate ``.po`` files.
    """

    id: str
    """String message ID (e.g., "errors.notEnoughColumns")."""

    arguments: Dict[str, Union[int, float, str]] = {}
    """Keyword arguments for the message."""

    source: Literal["module", "cjwmodule", None] = None
    """Indication of where the message is coming from.

    None means, "Workbench proper.
    """
