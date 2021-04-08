import datetime

import pyarrow as pa
import pytest

from cjwmodule.arrow.testing import assert_result, make_column, make_table
from cjwmodule.arrow.types import ArrowRenderResult
from cjwmodule.types import I18nMessage, RenderError


def test_build_table_infer_type():
    table = make_table(
        make_column("A", ["x"]),
        make_column("B", [datetime.date(2021, 4, 7)]),
        make_column("C", [datetime.datetime(2021, 4, 7, 19, 24, 1, 1)]),
        make_column("D", [1.0]),
    )
    assert table["A"].type == pa.string()
    assert table["B"].type == pa.date32()
    assert table["C"].type == pa.timestamp("ns")
    assert table["D"].type == pa.float64()


def test_make_column_accept_number_format():
    column = make_column("A", [1.0], format="${:,.2f}")
    assert column.field.metadata == {b"format": b"${:,.2f}"}


def test_make_column_assert_number_format():
    with pytest.raises(ValueError, match="unmatched '{' in format spec"):
        make_column("A", [1.0], format="{:,")


def test_make_column_infer_number_format():
    column = make_column("A", [1.0])
    assert column.field.metadata == {b"format": b"{:,}"}


def test_make_column_accept_date_unit():
    column = make_column("A", [datetime.date(2021, 4, 5)], unit="week")
    assert column.field.metadata == {b"unit": b"week"}


def test_make_column_assert_date_unit():
    with pytest.raises(
        ValueError, match="unit must be day, week, month, quarter or year; got: days"
    ):
        make_column("A", [datetime.date(2021, 4, 5)], unit="days")


def test_make_column_infer_date_unit():
    column = make_column("A", [datetime.date(2021, 4, 5)])
    assert column.field.metadata == {b"unit": b"day"}


def test_make_column_timestamp():
    # Basically, this unit test is documentation for module authors. Here are
    # ways to build timestamp columns!
    #
    # Beware: datetime.datetime(...) defaults to non-UTC.
    column = make_column("A", [datetime.datetime.utcfromtimestamp(1617889141.123456)])
    assert column.array.type == pa.timestamp("ns")
    assert column.array.cast(pa.int64()) == pa.array([1617889141123456000])


def test_make_column_timestamp_nix_utc_timezone():
    # Requires the "pytz" module...
    column = make_column(
        "A",
        [
            datetime.datetime(
                2021, 4, 8, 13, 39, 1, 123456, tzinfo=datetime.timezone.utc
            )
        ],
    )
    assert column.array.type == pa.timestamp("ns")  # no TZ info
    assert column.array.cast(pa.int64()) == pa.array([1617889141123456000])


def test_make_column_timestamp_interpret_local_datetime_as_utc():
    column = make_column("A", [datetime.datetime(2021, 4, 8, 13, 39, 1, 123456)])
    assert column.array.type == pa.timestamp("ns")  # no TZ info
    assert column.array.cast(pa.int64()) == pa.array([1617889141123456000])


def test_assert_result_check_number_type():
    table1 = make_table(make_column("A", [1, 2, 3], pa.int16()))
    table2 = make_table(make_column("A", [1, 2, 3], pa.uint16()))
    with pytest.raises(AssertionError):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_number_format():
    table1 = make_table(make_column("A", [1, 2, 3], format="{:,}"))
    table2 = make_table(make_column("A", [1, 2, 3], format="${:,}"))
    with pytest.raises(AssertionError):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_number_equal():
    table1 = make_table(make_column("A", [0.0, 0.6, None]))
    table2 = make_table(make_column("A", [-0.0, 0.6, None]))
    assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_number_different():
    table1 = make_table(make_column("A", [1, 2, 3]))
    table2 = make_table(make_column("A", [1, 2, -3]))
    with pytest.raises(AssertionError, match=r"\n-3\n\+-3"):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_date_unit():
    table1 = make_table(make_column("A", [datetime.date(2021, 4, 1)], unit="day"))
    table2 = make_table(make_column("A", [datetime.date(2021, 4, 1)], unit="month"))
    with pytest.raises(
        AssertionError, match=r"-\{b'unit': b'month'\}\n\+\{b'unit': b'day'\}"
    ):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_column_names():
    table1 = make_table(make_column("A", [1]), make_column("B", [1]))
    table2 = make_table(make_column("A", [1]), make_column("C", [1]))
    with pytest.raises(AssertionError, match=r"-\['A', 'C'\]\n\+\['A', 'B'\]"):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_timestamp_tz():
    table1 = pa.table({"A": pa.array([1617889141123456000], pa.timestamp("ns", "UTC"))})
    table2 = pa.table({"A": pa.array([1617889141123456000], pa.timestamp("ns"))})
    with pytest.raises(
        AssertionError,
        match=r"-pyarrow.Field<A: timestamp\[ns\]>\n\+pyarrow.Field<A: timestamp\[ns, tz=UTC\]>",
    ):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_field_metadata():
    table1 = pa.table(
        {"A": [1]},
        schema=pa.schema(
            [pa.field("A", pa.int64(), metadata={"format": "{:,}", "foo": "bar"})]
        ),
    )
    table2 = pa.table(
        {"A": [1]},
        schema=pa.schema([pa.field("A", pa.int64(), metadata={"format": "{:,}"})]),
    )
    with pytest.raises(AssertionError, match=r"\n\+\{b.*?b'bar'\}"):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_table_metadata():
    table1 = make_table(make_column("A", [1])).replace_schema_metadata({"foo": "bar"})
    table2 = make_table(make_column("A", [1]))
    with pytest.raises(AssertionError, match=r"-None\n\+\{"):
        assert_result(ArrowRenderResult(table1), ArrowRenderResult(table2))


def test_assert_result_check_errors():
    with pytest.raises(AssertionError, match=r"-\[Render.*\n\+\[\]"):
        assert_result(
            ArrowRenderResult(make_table()),
            ArrowRenderResult(
                make_table(), errors=[RenderError(I18nMessage("foo", {}, "module"))]
            ),
        )


def test_assert_result_check_json():
    with pytest.raises(AssertionError, match=r"-\{'foo': 'bar'\}\n\+\{\}"):
        assert_result(
            ArrowRenderResult(make_table()),
            ArrowRenderResult(make_table(), json={"foo": "bar"}),
        )
