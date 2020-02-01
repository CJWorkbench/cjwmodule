from collections import namedtuple

__all__ = ["I18nMessage"]

I18nMessage = namedtuple("I18nMessage", ["id", "arguments", "source"])
"""
A message for Workbench to translate.

This is a data-transfer format for passing messages from modules to Workbench.
Module authors should invoke :py:func:`i18n.trans()` instead of creating raw
``I18nMessage`` objects: Workbench's i18n tools parse ``trans()`` calls to
manipulate ``.po`` files.

:param id: String message ID (e.g., "errors.notEnoughColumns").
:type id: str
:param arguments: Keyword arguments for the message.
:type arguments: Dict[str, Union[int, float, str]]
:param source: Indication of where the message is coming from (`"module"` or `"cjwmodule"`).
:type source: str
"""
