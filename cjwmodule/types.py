"""Types that may be passed to and returned from modules.

These are `typing.NamedTuple` because:

* They're immutable.
* Unit tests compare them with "==".
* We like to see their `repr()` in assertions and debugging sessions.
"""

import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Union

from .i18n import I18nMessage


class QuickFixActionPrependStep(NamedTuple):
    """Instruction that upon clicking a button, we should create a Step."""

    module_slug: str
    """Module to prepend."""

    partial_params: Dict[str, Any]
    """Some params to set on the new Step (atop the module's defaults)."""


QuickFixAction = Union[QuickFixActionPrependStep]
"""Instruction for what happens when the user clicks a QuickFix button."""

QuickFixAction.PrependStep = QuickFixActionPrependStep


class QuickFix(NamedTuple):
    """Button the user can click in response to an error message.

    Either Workbench or the module code may generate QuickFix objects for a
    RenderError.
    """

    button_text: I18nMessage
    action: QuickFixAction


class RenderError(NamedTuple):
    """Error or warning encountered during `render()`.

    If `render()` output is a zero-column table, then its result's errors are
    "errors" -- they prevent the workflow from executing. If `render()` outputs
    columns, though, then its result's errors are "warnings" -- execution
    continues and these messages are presented to the user.
    """

    message: I18nMessage
    """Message describing what the human reader did wrong and how to fix it."""

    quick_fixes: List[QuickFix] = []
    """One-click buttons that should fix the error."""


class FetchError(NamedTuple):
    """Error or warning encountered during `fetch()`."""

    message: I18nMessage
    """Message describing what went wrong and how the human reader can cope."""


class FetchResult(NamedTuple):
    """The module executed a Step's fetch() without crashing.

    This data structure is output by `fetch()` (as a return value) and input
    into `render()` (as its `fetch_result` argument).
    """

    path: Path
    """File written in fetch().

    It may be an empty file.
    """

    errors: List[FetchError] = []
    """User-facing errors (or warnings) reported by the module.

    Modules may opt to ignore this field entirely and encode errors into the
    fetch() file. This `errors` field is merely a convenient tool for a common
    pattern: it will be passed to render() as `fetch_result.errors`.
    """


class UploadedFile(NamedTuple):
    """File uploaded by the user."""

    name: str
    """Name as the user uploaded it.

    This is an "unsafe" value: it could point to, say, `/etc/passwd`.
    """

    path: Path
    """Filename on disk containing the data."""

    uploaded_at: datetime.datetime
    """Moment when the user finished uploading the file, in UTC."""
