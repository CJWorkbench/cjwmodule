from typing import Any, Dict

from .types import I18nMessage

__all__ = ["trans"]


def trans(id: str, default: str, args: Dict[str, Any] = {}) -> I18nMessage:
    """
    Build an I18nMessage.

    Use ``trans()`` rather than building a :py:class:`I18nMessage` directly.
    Workbench's i18n tooling parses ``trans()`` calls to maintain translation
    files.

    Example usage::

        from cjwmodule import i18n

        if all(column.isnull()):  # some module-specific problem
            return {
                "errors": [
                    i18n.trans(
                        "errors.allNull",
                        "The column “{column}” must contain non-null values.",
                        {"column": column.name}
                    )
                ]
            }

    :param id: Message ID unique to this module (e.g., ``"errors.allNull"``)
    :param default: English-language message, in ICU format. (e.g.,
                    ``"The column “{column}” must contain non-null values.")``
    :param args: Values to interpolate into the message. (e.g.,
                 ``{"column": "A"}```
    """
    return I18nMessage(id, args)
