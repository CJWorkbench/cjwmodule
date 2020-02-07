from typing import Dict, Union

from cjwmodule import i18n

__all__ = ["I18nMessage"]


def I18nMessage(id: str, arguments: Dict[str, Union[int, float, str]] = {}):
    """The result of calling `i18n.trans`

    :param id: String message ID (e.g., "errors.notEnoughColumns").
    :type id: str
    :param arguments: Keyword arguments for the message.
    :type arguments: Dict[str, Union[int, float, str]]
    """
    return i18n.I18nMessage(id, arguments, "module")


def CjwmoduleI18nMessage(id: str, arguments: Dict[str, Union[int, float, str]] = {}):
    """An i18n message that is returned from calling an internal `cjwmodule` helper.

    :param id: String message ID (e.g., "errors.notEnoughColumns").
    :type id: str
    :param arguments: Keyword arguments for the message.
    :type arguments: Dict[str, Union[int, float, str]]
    """
    return i18n.I18nMessage(id, arguments, "cjwmodule")
