from typing import Dict, Union

from cjwmodule import i18n

__all__ = ["i18n_message", "cjwmodule_i18n_message"]


def i18n_message(
    id: str, arguments: Dict[str, Union[int, float, str]] = {}
) -> i18n.I18nMessage:
    """The result of calling `i18n.trans`

    :param id: String message ID (e.g., "errors.notEnoughColumns").
    :type id: str
    :param arguments: Keyword arguments for the message.
    :type arguments: Dict[str, Union[int, float, str]]
    """
    return i18n.I18nMessage(id, arguments, "module")


def cjwmodule_i18n_message(
    id: str, arguments: Dict[str, Union[int, float, str]] = {}
) -> i18n.I18nMessage:
    """An i18n message that is returned from calling an internal `cjwmodule` helper.

    :param id: String message ID (e.g., "errors.notEnoughColumns").
    :type id: str
    :param arguments: Keyword arguments for the message.
    :type arguments: Dict[str, Union[int, float, str]]
    """
    return i18n.I18nMessage(id, arguments, "cjwmodule")
