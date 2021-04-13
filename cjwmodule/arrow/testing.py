"""Helpers surrounding valid Arrow v1 data structures.

These APIs are to be invoked thousands of times, in Workbench test suites and
in module test suites. Rule #1: make it fun and easy to read and write tests.
"""
from typing import Any, List, NamedTuple, Optional

import pyarrow as pa

from .format import parse_number_format
from .types import ArrowRenderResult

__all__ = [
    "assert_arrow_table_equals",
    "assert_result_equals",
    "make_column",
    "make_table",
]


class _Column(NamedTuple):
    """Value returned by `make_column()` for `make_table()`."""

    field: pa.Field
    """Schema information."""

    array: pa.Array
    """Data."""


def make_column(
    name: str,
    values: List[Any],
    type: pa.DataType = None,
    *,
    dictionary: bool = False,
    format: Optional[str] = None,
    unit: Optional[str] = None,
) -> _Column:
    """Create a column of data for `make_table()`.

    The behavior is similar to `pyarrow.array()` ... with Workbench flavor:

    * `column()` ensures all timestamp units are "ns"
    * `column()` ensures all numeric arrays have "format" metadata
    * `column()` ensures all date32 arrays have "unit" metadata
    * `column(..., dictionary=True)` dictionary-encodes text columns
    """
    array = pa.array(values, type)
    if (
        type is None
        and pa.types.is_timestamp(array.type)
        and array.type != pa.timestamp("ns")
    ):
        array = pa.array(values, type=pa.timestamp("ns"))

    if pa.types.is_floating(array.type) or pa.types.is_integer(array.type):
        assert not dictionary
        assert unit is None
        if format is None:
            format = "{:,}"
        else:
            parse_number_format(format)  # or raise -- broken test!
        metadata = {"format": format}
    elif pa.types.is_date32(array.type):
        assert not dictionary
        assert format is None
        if unit is None:
            unit = "day"
        else:
            if unit not in {"day", "week", "month", "quarter", "year"}:
                raise ValueError(
                    "unit must be day, week, month, quarter or year; got: %s" % unit
                )
        metadata = {"unit": unit}
    elif pa.types.is_string(array.type) and dictionary:
        assert format is None
        assert unit is None
        array = array.dictionary_encode()
        metadata = None
    else:
        assert not dictionary
        assert format is None
        assert unit is None
        metadata = None

    field = pa.field(name, array.type, metadata=metadata)
    return _Column(field, array)


def make_table(*columns: _Column) -> pa.Table:
    """Create a Workbench-compatible Arrow table in memory.

    Usage:

        table = make_table(
            column("my-text", ["x"]),
            column("my-number", [1], pa.int32(), format="{:,d}"),
            column("my-date", [datetime.date(2021, 1, 1)], unit="year"),
            column("my-timestamp", [datetime.datetime(2021, 1, 1, 1, 1, 1)]),
        )

    This table will have one row group. You can reuse its schema to build a
    zero-row-group or multi-row-group table. For instance:

        zero_row_group_table = pa.Table.from_batches([], table.schema)

    The behavior is similar to `pyarrow.table()` ... but the resulting table
    has a Workbench-compatible schema.

    Your module test suite should use `make_table()` to create an input table
    (since anything it returns is something your module might expect as input);
    and it should compare results against a `make_table()`-generated table
    (since that table will be a valid Workbench table).
    """
    schema = pa.schema([column.field for column in columns])
    return pa.table([column.array for column in columns], schema=schema)


def assert_arrow_table_equals(actual: pa.Table, expected: pa.Table) -> None:
    """Assert that `actual` and `expected` mean the same table, in Workbench.

    Workbench rules:

        * Numbers must have the same type: int16 and uint16 are different.
        * Numbers must have the same format.
        * Numbers must be the same ... within a margin of error.
        * Dates must have the same unit: day and month are different.
    """
    assert (
        actual.column_names == expected.column_names
    ), "actual columns != expected columns\n-%r\n+%r" % (
        expected.column_names,
        actual.column_names,
    )
    assert (
        actual.schema.metadata == expected.schema.metadata
    ), "actual table metadata != expected table metadata\n-%r\n+%r" % (
        expected.schema.metadata,
        actual.schema.metadata,
    )
    for i in range(actual.num_columns):
        actual_field = actual.field(i)
        expected_field = expected.field(i)
        assert (
            actual_field == expected_field
        ), "column %r: actual field != expected field\n-%r\n+%r" % (
            actual_field.name,
            expected_field,
            actual_field,
        )
        assert (
            actual_field.metadata == expected_field.metadata
        ), "column %r: actual metadata != expected metadata\n-%r\n+%r" % (
            actual_field.name,
            expected_field.metadata,
            actual_field.metadata,
        )
    for column_name, actual_column, expected_column in zip(
        actual.column_names, actual.itercolumns(), expected.itercolumns()
    ):
        assert actual_column.num_chunks == expected_column.num_chunks
        for chunk_index, (actual_chunk, expected_chunk) in enumerate(
            zip(actual_column.chunks, expected_column.chunks)
        ):
            diff = actual_chunk.diff(expected_chunk)
            assert not diff, "actual != expected data in column %r, chunk %d:%s" % (
                column_name,
                chunk_index,
                diff,
            )


def assert_result_equals(
    actual: ArrowRenderResult, expected: ArrowRenderResult
) -> None:
    """Assert that `actual` and `expected` behave identically, in Workbench.

    Workbench rules:

        * Numbers must have the same type: int16 and uint16 are different.
        * Numbers must have the same format.
        * Numbers must be the same ... within a margin of error.
        * Dates must have the same unit: day and month are different.
    """
    assert (
        actual.errors == expected.errors
    ), "actual errors != expected errors\n-%r\n+%r" % (expected.errors, actual.errors)
    assert actual.json == expected.json, "actual json != expected json\n-%r\n+%r" % (
        expected.json,
        actual.json,
    )
    assert_arrow_table_equals(actual.table, expected.table)
