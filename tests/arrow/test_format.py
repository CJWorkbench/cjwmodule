import datetime
import math

import pyarrow as pa
import pytest

from cjwmodule.arrow.format import (
    format_number_array,
    format_timestamp_array,
    parse_number_format,
)


def test_parse_disallow_too_many_arguments():
    with pytest.raises(ValueError, match="Can only format one number"):
        parse_number_format("{:d}{:f}")


def test_parse_disallow_non_format_is_valueerror():
    with pytest.raises(ValueError, match='Format must look like "{:...}"'):
        parse_number_format("%d")


def test_parse_disallow_field_number():
    with pytest.raises(ValueError, match="Field names or numbers are not allowed"):
        parse_number_format("{0:f}")


def test_disallow_field_name():
    with pytest.raises(ValueError, match="Field names or numbers are not allowed"):
        parse_number_format("{value:f}")


def test_disallow_field_converter():
    with pytest.raises(ValueError, match="Field converters are not allowed"):
        parse_number_format("{!r:f}")


def test_disallow_invalid_type():
    with pytest.raises(ValueError, match="Unknown format code 'T'"):
        parse_number_format("{:T}")


def test_format_general():
    f = parse_number_format("{}")
    assert f(1) == "1"
    assert f(1.0) == "1"  # must treat float like int
    assert f(3.2) == "3.2"
    assert (
        f(234234234233984229834752.0) == "234234234233984229834752"
    )  # not "2.3...e+23"
    assert f(-1234.4) == "-1234.4"


def test_format_int():
    f = parse_number_format("{:,d}")
    assert f(1) == "1"
    assert f(1.0) == "1"  # must treat float like int
    assert f(1.6) == "1"  # round towards 0
    assert f(-1.6) == "-1"  # round towards 0
    assert f(1_234_567) == "1,234,567"
    assert f(1125899906842624) == "1,125,899,906,842,624"  # int64


def test_format_float():
    f = parse_number_format("{:,.2f}")
    assert f(1) == "1.00"  # must treat int like float
    assert f(1.0) == "1.00"
    assert f(-1.6) == "-1.60"
    assert f(1_234_567) == "1,234,567.00"
    assert f(1125899906842624) == "1,125,899,906,842,624.00"  # int64
    assert f(1.234567) == "1.23"
    assert f(125899906842624.09) == "125,899,906,842,624.09"  # float64
    assert f(1.235) == "1.24"  # round


def test_format_int8_array():
    assert (
        format_number_array(
            pa.array([1, -1, 2, -2, 3, -3, 4, -4, None, None, 6, -6], pa.int8()),
            parse_number_format("{:d}"),
        ).to_pylist()
        == ["1", "-1", "2", "-2", "3", "-3", "4", "-4", None, None, "6", "-6"]
    )


def test_format_int8_array_no_validity_buffer():
    arr = pa.array([1, 2, 30, 4], pa.int8())
    valid_buf, num_buf = arr.buffers()
    format = parse_number_format("{:d}")
    scary_arr = pa.Array.from_buffers(arr.type, 4, [None, num_buf])
    assert format_number_array(scary_arr, format).to_pylist() == ["1", "2", "30", "4"]


def test_format_uint32_array():
    assert format_number_array(
        pa.array(
            [1, 1, 2, 2, 3_000, 3_000, 4_000_000, 4_000_000, None, None, 6, 6],
            pa.uint32(),
        ),
        parse_number_format("{:,d}"),
    ).to_pylist() == [
        "1",
        "1",
        "2",
        "2",
        "3,000",
        "3,000",
        "4,000,000",
        "4,000,000",
        None,
        None,
        "6",
        "6",
    ]


def test_format_float64_array():
    assert format_number_array(
        pa.array(
            [
                1,
                -1.1,
                2.3,
                -3.123,
                math.nan,
                math.inf,
                -math.inf,
                4_000_000.23123,
                -4_000_000.414213,
                None,
            ],
            pa.float64(),
        ),
        parse_number_format("{:,}"),
    ).to_pylist() == [
        "1",
        "-1.1",
        "2.3",
        "-3.123",
        None,
        None,
        None,
        "4,000,000.23123",
        "-4,000,000.414213",
        None,
    ]


def test_format_float64_create_validity_buffer_when_missing():
    arr = pa.array([1, math.inf, math.nan, 4], pa.float64())
    valid_buf, num_buf = arr.buffers()
    format = parse_number_format("{:d}")
    scary_arr = pa.Array.from_buffers(arr.type, 4, [None, num_buf])
    assert format_number_array(scary_arr, format).to_pylist() == ["1", None, None, "4"]


def test_format_timestamp():
    assert format_timestamp_array(
        pa.array(
            [
                datetime.datetime(2010, 1, 1),  # months (pos)
                datetime.datetime(1900, 11, 30),  # days (neg)
                datetime.datetime(2010, 1, 2, 3),  # hours (pos)
                datetime.datetime(1940, 1, 2, 3, 4),  # minutes (neg)
                datetime.datetime(2010, 1, 2, 3, 4, 5),  # seconds (pos)
                datetime.datetime(2010, 1, 2, 3, 4, 5, 6_000),  # ms
                datetime.datetime(1940, 1, 2, 0, 0, 0, 3),  # us (neg)
                None,
                1,  # ns
                -1,  # ns
            ],
            pa.timestamp("ns"),
        )
    ).to_pylist() == [
        "2010-01-01",
        "1900-11-30",
        "2010-01-02T03:00Z",
        "1940-01-02T03:04Z",
        "2010-01-02T03:04:05Z",
        "2010-01-02T03:04:05.006Z",
        "1940-01-02T00:00:00.000003Z",
        None,
        "1970-01-01T00:00:00.000000001Z",
        "1969-12-31T23:59:59.999999999Z",
    ]


def test_format_timestamp_no_valid_buf():
    arr = pa.array([datetime.datetime(2010, 1, 1)], pa.timestamp("ns"))
    valid_buf, num_buf = arr.buffers()
    scary_arr = pa.Array.from_buffers(arr.type, len(arr), [None, num_buf], 0, 0)
    assert format_timestamp_array(scary_arr).to_pylist() == ["2010-01-01"]
