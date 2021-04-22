import array
import codecs
import datetime
import io
import math
import time
from string import Formatter
from typing import Callable, Iterator, Literal, NewType, Optional, Union

import pyarrow as pa

DateUnit = Literal["day", "week", "month", "quarter", "year"]

__all__ = [
    "parse_number_format",
    "format_number_array",
]

_IntTypeSpecifiers = set("bcdoxXn")
"""
Type names that operate on integer (as opposed to float).

Python `format()` auto-converts int to float, but it doesn't auto-convert
float to int. Workbench does auto-convert float to int: any format that
works for one Number must work for all Numbers.

(Workbench Numbers behave like JavaScript Numbers, except an array of int64
can be stored exactly.)
"""


NumberFormatter = NewType("NumberFormatter", Callable[[Union[int, float]], str])


def parse_number_format(format_s: str) -> NumberFormatter:
    """
    Parse `format_s` to create a formatter function.

    Usage:

        format_number = parse_number_format("${:,.2f}")  # raises ValueError
        format_number(1234.56)  # => "$1,234.56"

    This is similar to Python `format()` but different:

    * It allows formatting float as int: `NumberFormatter('{:d}').format(0.1)`
    * It disallows "conversions" (e.g., `{!r:s}`)
    * It disallows variable name/numbers (e.g., `{1:d}`, `{value:d}`)
    * It raises ValueError on construction if format is imperfect
    * The function it returns will never raise an exception
    """

    if not isinstance(format_s, str):
        raise TypeError("Format must be str")

    # parts: a list of (literal_text, field_name, format_spec, conversion)
    #
    # The "literal_text" always comes _before_ the field. So we end up
    # with three possibilities:
    #
    #    "prefix{}suffix": [(prefix, "", "", ""), (suffix, None...)]
    #    "prefix{}": [(prefix, "", "", '")]
    #    "{}suffix": [("", "", "", ""), (suffix, None...)]
    parts = list(Formatter().parse(format_s))

    if len(parts) > 2 or len(parts) == 2 and parts[1][1] is not None:
        raise ValueError("Can only format one number")

    if not parts or parts[0][1] is None:
        raise ValueError('Format must look like "{:...}"')

    if parts[0][1] != "":
        raise ValueError("Field names or numbers are not allowed")

    if parts[0][3] is not None:
        raise ValueError("Field converters are not allowed")

    prefix = parts[0][0]
    format_spec = parts[0][2]
    if len(parts) == 2:
        suffix = parts[1][0]
    else:
        suffix = ""
    need_int = format_spec and format_spec[-1] in _IntTypeSpecifiers

    # Test it!
    #
    # A reading of cpython 3.7 Python/formatter_unicode.c
    # parse_internal_render_format_spec() suggests the following unobvious
    # details:
    #
    # * Python won't parse a format spec unless you're formatting a number
    # * _PyLong_FormatAdvancedWriter() accepts a superset of the formats
    #   _PyFloat_FormatAdvancedWriter() accepts. (Workbench accepts that
    #   superset.)
    #
    # Therefore, if we can format an int, the format is valid.
    format(1, format_spec)  # raise ValueError on invalid format

    def fn(value: Union[int, float]) -> str:
        if need_int:
            value = int(value)
        else:
            # Format float64 _integers_ as int. For instance, '3.0' should be
            # formatted as though it were the int, '3'.
            #
            # Python would normally format '3.0' as '3.0' by default; that's
            # not acceptable to us because we can't write a JavaScript
            # formatter that would do the same thing. (Javascript doesn't
            # distinguish between float and int.)
            int_value = int(value)
            if int_value == value:
                value = int_value

        return prefix + format(value, format_spec) + suffix

    return fn


def format_number_array(arr: pa.Array, fn: NumberFormatter) -> pa.Array:
    """
    Build a PyArrow utf8 array from a number array.

    The output Array will have the same length as the input. Input NULL, NaN and
    NaT will become NULL outputs.

    The output Array will consume RAM using three new, contiguous buffers.
    """
    # num_buf: byte-buffer holding numbers. num_buf[i*size:(i+1)*size] is the
    # little-endian ith value in arr.
    #
    # valid_buf: bitset of "valid" integers. valid_buf[(1 << i)] is 1 when
    # the ith entry in arr is set; it's 0 when the ith entry in arr is pa.NULL.
    valid_buf, num_buf = arr.buffers()
    for detect, struct_format in [
        (pa.types.is_uint8, "B"),
        (pa.types.is_uint16, "H"),
        (pa.types.is_uint32, "I"),
        (pa.types.is_uint64, "L"),
        (pa.types.is_int8, "b"),
        (pa.types.is_int16, "h"),
        (pa.types.is_int32, "i"),
        (pa.types.is_int64, "l"),
        (pa.types.is_float16, "e"),
        (pa.types.is_float32, "f"),
        (pa.types.is_float64, "d"),
    ]:
        if detect(arr.type):
            break
    else:
        raise TypeError("Unknown array type %r" % arr.type)  # pragma: no cover

    if valid_buf is None:
        # HACK: give the same interface as PyArrow bitmap buffer.
        # Make validity bitmap all-ones.
        valid_buf = b"\xff" * ((len(arr) + 8) // 8)

    nums = memoryview(num_buf).cast(struct_format)
    num_iter = iter(nums)
    offset = 0
    n_extra_nulls = 0

    out_valid8s = array.array("B")  # uint8
    out_offsets = array.array("I")  # uint32
    out_utf8 = io.BytesIO()

    # valid_buf is a bitset: 8 numbers per byte.
    # Iterate in groups of 8.
    for in_valid8 in valid_buf:
        out_valid8 = in_valid8
        try:
            for valid_i in range(8):
                valid_mask = 1 << valid_i
                is_valid = in_valid8 & valid_mask
                num = next(num_iter)
                # At each number, output the _start_ offset of that number
                out_offsets.append(offset)
                if is_valid:
                    if math.isfinite(num):
                        formatted, _ = codecs.utf_8_encode(fn(num))
                        out_utf8.write(formatted)
                        offset += len(formatted)
                    else:
                        n_extra_nulls += 1
                        # Input was NaN, inf, -inf. We don't format those: we
                        # set them to null.
                        #
                        # Flip output bit to 0
                        out_valid8 &= out_valid8 ^ valid_mask
                        # ... and offset does not change: next number will write
                        # the same offset, meaning _this_ number consumes 0
                        # bytes in out_utf8.
        except StopIteration:
            pass
        out_valid8s.append(out_valid8)

    out_offsets.append(offset)

    return pa.StringArray.from_buffers(
        length=len(arr),
        value_offsets=pa.py_buffer(out_offsets.tobytes()),
        data=pa.py_buffer(bytes(out_utf8.getbuffer())),
        null_bitmap=pa.py_buffer(out_valid8s.tobytes()),
        null_count=arr.null_count + n_extra_nulls,
    )


_NS_PER_US = 1_000
_NS_PER_MS = 1_000_000
_NS_PER_SECOND = 1_000_000_000
_NS_PER_MINUTE = _NS_PER_SECOND * 60
_NS_PER_HOUR = _NS_PER_MINUTE * 60
_NS_PER_DAY = _NS_PER_HOUR * 24
_EPOCH_DATE_ORDINAL = datetime.date(1970, 1, 1).toordinal()


def _ns_to_iso8601(ns: int) -> str:
    # if ns < 0, days will be negative and ns will be positive (as we want)
    days, ns = divmod(ns, _NS_PER_DAY)
    days_str = datetime.date.fromordinal(days + _EPOCH_DATE_ORDINAL).isoformat()
    if ns == 0:
        return days_str
    else:
        hours, ns = divmod(ns, _NS_PER_HOUR)
        minutes, ns = divmod(ns, _NS_PER_MINUTE)
        parts = [days_str, "T", format(hours, "02d"), ":", format(minutes, "02d")]

        if ns != 0:
            seconds, ns = divmod(ns, _NS_PER_SECOND)
            parts.append(":")
            parts.append(format(seconds, "02d"))

            if ns != 0:
                ms, ns = divmod(ns, _NS_PER_MS)
                parts.append(".")
                parts.append(format(ms, "03d"))

                if ns != 0:
                    us, ns = divmod(ns, _NS_PER_US)
                    parts.append(format(us, "03d"))

                    if ns != 0:
                        parts.append(format(ns, "03d"))

        parts.append("Z")
        return "".join(parts)


def _num_iter(
    valid_buf: Optional[pa.Buffer], nums: memoryview
) -> Iterator[Optional[Union[int, float]]]:
    if valid_buf is None:
        yield from nums
    else:
        num_iter = iter(nums)
        # valid_buf is a bitset: 8 numbers per byte.
        # Iterate in groups of 8.
        try:
            for in_valid8 in valid_buf:
                for valid_i in range(8):
                    valid_mask = 1 << valid_i
                    is_valid = in_valid8 & valid_mask
                    num = next(num_iter)  # raise StopIteration at end
                    if is_valid:
                        yield num
                    else:
                        yield None
        except StopIteration:
            pass  # we expect it


def format_timestamp_array(arr: pa.Array) -> pa.Array:
    """Build a PyArrow utf8 array from a timestamp array.

    The output Array will have the same length as the input.

    The output Array will consume RAM using two new, contiguous buffers.

    The format will be ISO8601, as precise as needed.
    """
    valid_buf, num_buf = arr.buffers()
    if arr.type.unit != "ns":
        raise NotImplementedError("TODO handle non-ns")  # pragma: no cover

    nums = memoryview(num_buf).cast("l")  # l = int64
    num_iter = _num_iter(valid_buf, nums)

    offset = 0
    out_offsets = array.array("I")  # uint32
    out_utf8 = io.BytesIO()

    for num in num_iter:
        # At each number, output the _start_ offset of that number
        out_offsets.append(offset)
        if num is not None:
            formatted, n = codecs.readbuffer_encode(_ns_to_iso8601(num))
            out_utf8.write(formatted)
            offset += n

    out_offsets.append(offset)

    return pa.StringArray.from_buffers(
        length=len(arr),
        value_offsets=pa.py_buffer(out_offsets.tobytes()),
        data=pa.py_buffer(bytes(out_utf8.getbuffer())),
        null_bitmap=valid_buf,
        null_count=arr.null_count,
    )


def format_date_array(arr: pa.Array, unit: DateUnit) -> pa.Array:
    """Build a PyArrow utf8 array from a date32 array.

    The output Array will have the same length as the input.

    The output Array will consume RAM using two new, contiguous buffers.

    Formats (for date "2022-08-01", a Monday):

    * day: "2022-08-01"
    * week: "2022-08-01"
    * month: "2022-08"
    * quarter: "2022 Q3"
    * year: "2022"

    The format will be ISO8601, as precise as needed.
    """
    valid_buf, num_buf = arr.buffers()
    nums = memoryview(num_buf).cast("i")  # i = int32
    num_iter = _num_iter(valid_buf, nums)

    offset = 0
    out_offsets = array.array("I")  # uint32
    out_utf8 = io.BytesIO()

    # date32 allows negative years; Python `datetime.date` doesn't. Don't use
    # datetime.date.
    if unit == "year":

        def _format(day: int) -> str:
            return str(time.gmtime(86400 * day).tm_year)

    elif unit == "quarter":

        def _format(day: int) -> str:
            st = time.gmtime(86400 * day)
            return str(st.tm_year) + " Q" + str((st.tm_mon + 2) // 3)

    elif unit == "month":

        def _format(day: int) -> str:
            st = time.gmtime(86400 * day)
            return str(st.tm_year) + "-" + str(st.tm_mon).zfill(2)

    else:

        def _format(day: int) -> str:
            st = time.gmtime(86400 * day)
            return (
                str(st.tm_year)
                + "-"
                + str(st.tm_mon).zfill(2)
                + "-"
                + str(st.tm_mday).zfill(2)
            )

    for num in num_iter:
        # At each number, output the _start_ offset of that number
        out_offsets.append(offset)
        if num is not None:
            formatted, n = codecs.readbuffer_encode(_format(num))
            out_utf8.write(formatted)
            offset += n

    out_offsets.append(offset)

    return pa.StringArray.from_buffers(
        length=len(arr),
        value_offsets=pa.py_buffer(out_offsets.tobytes()),
        data=pa.py_buffer(bytes(out_utf8.getbuffer())),
        null_bitmap=valid_buf,
        null_count=arr.null_count,
    )
