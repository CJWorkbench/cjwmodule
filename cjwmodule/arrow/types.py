from typing import Any, Dict, List, NamedTuple

import pyarrow as pa

from ..types import RenderError

__all__ = ["ArrowRenderResult"]


class TabOutput(NamedTuple):
    """Output from a different tab, to be used as input into a render function."""

    tab_name: str
    """Name of the tab.

    This is used in, e.g., concattabs for adding a "Source" column.
    """

    table: pa.Table
    """Table data."""


class ArrowRenderResult(NamedTuple):
    """Return value from a `def render_arrow_v1()`.

    This value can be compared in unit tests. See `cjwmodule.arrow.testing`.
    """

    table: pa.Table
    r"""pyarrow.Table holding tabular data.

    `table.schema.metadata` must be empty.

    Date32 fields must have `{b"unit": b"day"}` or other unit specifier.

    Numeric fields must have `{b"format": b"{:,}"}` or other format specifier,
    encoded as UTF-8.

    Other fields must not have any metadata.
    """

    errors: List[RenderError] = []
    """User-facing errors or warnings reported by the module."""

    json: Dict[str, Any] = {}
    """JSON to pass to the module's HTML, if it has HTML."""
