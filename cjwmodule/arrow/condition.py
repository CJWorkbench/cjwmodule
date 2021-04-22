import math
import re
import warnings
from typing import Any, Callable, Dict, List, Literal, Optional, Pattern, Tuple, Union

import numpy as np
import pyarrow as pa
import pyarrow.compute
import re2

__all__ = ["ConditionError", "condition_to_mask"]


class ConditionError(Exception):
    def __init__(self, errors):
        super().__init__(self, errors[0].msg)
        self.errors = errors

    @property
    def msg(self):
        warnings.warn(
            "You should read ConditionError.errors now: a list of re.error",
            DeprecationWarning,
        )
        return self.errors[0].msg

    @property
    def pattern(self):
        warnings.warn(
            "You should read ConditionError.errors now: a list of re.error",
            DeprecationWarning,
        )
        return self.errors[0].pattern


def _str_to_regex(s: str, case_sensitive: bool) -> Pattern:
    """Compile to re2.Pattern, or raise UserVisibleError."""
    options = re2.Options()
    options.log_errors = False
    options.never_capture = True  # we don't capture anything: we filter
    options.case_sensitive = case_sensitive

    try:
        # Compile the actual regex, to generate the actual error message.
        return re2.compile(s, options)
    except re2.error as err:
        msg = str(err.args[0], encoding="utf-8", errors="replace")
        raise ConditionError([re.error(msg, pattern=s)]) from None


def _and_or_condition_to_mask(
    table, reducer, *, conditions: List[Dict[str, Any]]
) -> pa.ChunkedArray:
    errors = []
    mask = None
    for condition in conditions:
        try:
            new_mask = condition_to_mask(table, condition)
        except ConditionError as err:
            errors.extend(err.errors)
            new_mask = _all_false(table.columns[0])
        if mask is None:
            mask = new_mask
        else:
            mask = reducer(mask, new_mask)
    if errors:
        raise ConditionError(errors)
    return mask


def _and_condition_to_mask(
    table, *, conditions: List[Dict[str, Any]]
) -> pa.ChunkedArray:
    return _and_or_condition_to_mask(table, pa.compute.and_, conditions=conditions)


def _or_condition_to_mask(
    table, *, conditions: List[Dict[str, Any]]
) -> pa.ChunkedArray:
    return _and_or_condition_to_mask(table, pa.compute.or_, conditions=conditions)


def _not_condition_to_mask(table, *, condition: Dict[str, Any]) -> pa.ChunkedArray:
    return pa.compute.invert(
        condition_to_mask(table, condition)
    )  # raises ConditionError


def _array_map_to_bool(
    array: pa.Array, func: Callable[[Optional[Any]], bool]
) -> pa.BooleanArray:
    return pa.array((func(v) for v in array), type=pa.bool_(), size=len(array))


def _compute_map_to_bool(
    values: Union[pa.ChunkedArray, pa.Array], func: Callable[[Any], bool]
) -> pa.ChunkedArray:
    if hasattr(values, "chunks"):
        return pa.chunked_array(
            [_array_map_to_bool(chunk, func) for chunk in values.chunks],
            type=pa.bool_(),
        )
    else:
        return _array_map_to_bool(values, func)


def _build_text_array_masking_function(
    operation: Literal["text_is", "text_contains"],
    value: str,
    case_sensitive: bool,
    regex: bool,
) -> Callable[[Union[pa.Array, pa.StringArray]], pa.BooleanArray]:
    """Build a callback for converting Strings to a boolean mask.

    Raise ConditionError with `errors=[re.error(...)]` on invalid regex.

    Usage:

        masking_function = _build_text_array_masking_function("foo", "is", True, False)
        column = table["A"]  # pa.ChunkedArray
        mask = masking_function(column)
        array0 = column.chunks[0]
        mask0 = masking_function(array0)

    Why this indirection? Because with `pa.DictionaryArray` we compare the value
    Arrays, and with `pa.StringArray` we must compare the ChunkedArray itself.

    The returned function guarantees not-null outputs.
    """
    if regex:
        pattern = _str_to_regex(value, case_sensitive)  # raise ConditionError
        pattern_func = {"text_is": pattern.fullmatch, "text_contains": pattern.search}[
            operation
        ]
        valuewise_func = lambda v: v.is_valid and pattern_func(v.as_py()) is not None
        return lambda values: _compute_map_to_bool(values, valuewise_func)
    else:
        if case_sensitive:
            compute_func = {
                "text_is": pa.compute.equal,
                "text_contains": pa.compute.match_substring,
            }[operation]
            return lambda values: pa.compute.fill_null(
                compute_func(values, value), False
            )
        else:
            casefolded_value = value.casefold()
            valuewise_func = {
                "text_is": (
                    lambda v: v.is_valid and v.as_py().casefold() == casefolded_value
                ),
                "text_contains": (
                    lambda v: v.is_valid and casefolded_value in v.as_py().casefold()
                ),
            }[operation]
            return lambda values: _compute_map_to_bool(values, valuewise_func)


def _dictionary_array_to_mask(
    array: pa.DictionaryArray, func: Callable[[pa.StringArray], pa.BooleanArray]
) -> pa.BooleanArray:
    """Create a mask of the indices that point to values matching func().

    Usage:

        arr = pa.array(["a", "b", "c", "b", "b", None]).dictionary_encode()
        func = lambda arr: pa.compute.equal(arr, "b")
        _dictionary_array_to_mask(arr, func)  # [False, True, False, True, True, False]
    """
    index_mask = func(array.dictionary)  # index => [include?]
    index_set = pyarrow.array(
        [i for i, v in enumerate(index_mask) if v.is_valid and v.as_py()],
        type=array.indices.type,
        size=index_mask.true_count,
    )
    try:
        # pyarrow 3.x
        mask = pa.compute.is_in(array.indices, value_set=index_set, skip_nulls=True)
    except TypeError:
        # pyarrow 2.x
        mask = pa.compute.is_in(array.indices, value_set=index_set, skip_null=True)
    return pa.compute.fill_null(mask, False)


def _text_column_to_mask(
    column: pa.ChunkedArray, func: Callable[[pa.StringArray], pa.BooleanArray]
) -> pa.ChunkedArray:
    """Calls func(column) if column is StringArray; does dictionary magic otherwise.

    Raise ConditionError with `errors=[re.error(...)]` on invalid regex.
    """
    if pa.types.is_dictionary(column.type):
        return pa.chunked_array(
            [_dictionary_array_to_mask(chunk, func) for chunk in column.chunks],
            pa.bool_(),
        )
    else:
        return func(column)


def _text_condition_to_mask(
    table,
    operation: str,
    *,
    column: str,
    value: str,
    isCaseSensitive: bool,
    isRegex: bool
) -> pa.ChunkedArray:
    """Calculate a mask from `table` and arguments.

    Raise ConditionError with `errors=[re.error(...)]` on invalid regex.
    """

    func = _build_text_array_masking_function(
        operation, value, isCaseSensitive, isRegex
    )
    return _text_column_to_mask(table[column], func)


def _all_false(column: pa.ChunkedArray, value=None) -> pa.ChunkedArray:
    any_bools = pa.compute.is_valid(column)
    return pa.compute.xor(any_bools, any_bools)  # all-false


def _all_non_null_true(column: pa.ChunkedArray, value=None) -> pa.ChunkedArray:
    return pa.compute.is_valid(column)


def _prepare_for_number_column_operation(
    operation: str, value: Union[float, int], column_type: pa.DataType
) -> Tuple[
    Literal[
        "all_true",
        "all_false",
        "number_is",
        "number_is_greater_than",
        "number_is_greater_than_or_equals",
        "number_is_less_than",
        "number_is_less_than_or_equals",
    ],
    Optional[pa.Scalar],
]:
    """Tweak `operation` and `scalar` to match `column_type`.

    If the column type is float, `value` is cast to float. It may be infinity.

    If the column type is int, `value` is cast to int. Operations are tweaked
    to prevent invalid casts:

        * floats are rounded -- so "number_is_greater_than_or_equal" becomes,
          say, "number_is_greater_than"; and "number_is" becomes "all_false"
        * out-of-bounds integers become "all_true" or "all_false".

    >>> _prepare_for_number_column_operation("number_is", 3.0, pa.int8())  # round float can equal int
    ("number_is", pa.scalar(3, pa.int8()))
    >>> _prepare_for_number_column_operation("number_is", 3.1, pa.int8())  # float can't equal int
    ("all_false", None)
    >>> _prepare_for_number_column_operation("number_is_greater_than", 3.4, pa.int8())  # greater-than shifts to int
    ("number_is_greater_than_or_equals", pa.scalar(3, pa.int8()))
    >>> _prepare_for_number_column_operation("number_is_greater_than", 1234, pa.int8())  # out-of-bounds is all-false
    ("all_false", None)
    >>> _prepare_for_number_column_operation("number_is_less_than", 1234, pa.int8())  # out-of-bounds is all-true
    ("all_true", None)
    >> _prepare_for_number_column_operation("number_is", 3, pa.float64())  # int can equal float
    ("number_is", pa.scalar(3, pa.float64()))
    """
    if pa.types.is_floating(column_type):
        # The column is float; make the value float, too.
        # inf and -inf will work for comparisons
        return operation, pa.scalar(float(value), pa.float64())

    # The column is int -- int8, int16, int32, int64, uint8, uint16, uint32, uint64
    #
    # Let's not bother casting the input column for such simple comparisons.
    # Instead, we can cast the _value_ to match the input-column type.
    #
    # The two kinds of errors: out-of-range and rounding. We can prep the
    # value in Python before we compare.

    if int(value) != value:
        # We want integer comparisons; but we weren't given an integer! Convert
        # to integer (of arbitrary size -- Python int is unlimited). This will
        # prevent rounding errors.
        #
        # We'll mutate `operation` and `value` at the same time

        if operation == "number_is":
            # The value is a floating-point number; nothing matches. Abort.
            return ("all_false", None)

        if "greater_than" in operation:
            operation = "number_is_greater_than"
            value = math.floor(value)
        else:
            operation = "number_is_less_than"
            value = math.ceil(value)
    else:
        value = int(value)

    # Check for out-of-range
    if pa.types.is_unsigned_integer(column_type):
        type_min = 0
        type_max = (1 << column_type.bit_width) - 1
    else:
        type_max = (1 << column_type.bit_width - 1) - 1
        type_min = -1 - type_max  # two's-complement cleverness

    if value < type_min:
        if "greater_than" in operation:
            return ("all_true", None)
        else:
            return ("all_false", None)
    if value > type_max:
        if "less_than" in operation:
            return ("all_true", None)
        else:
            return ("all_false", None)

    # watch out: we tweaked `operation` above
    return operation, pa.scalar(value, column_type)


def _number_condition_to_mask(
    table, operation: str, *, column: str, value: Union[float, int]
) -> pa.ChunkedArray:
    operation, value = _prepare_for_number_column_operation(
        operation, value, table[column].type
    )

    func = {
        "all_true": _all_non_null_true,
        "all_false": _all_false,
        "number_is": pa.compute.equal,
        "number_is_greater_than": pa.compute.greater,
        "number_is_greater_than_or_equals": pa.compute.greater_equal,
        "number_is_less_than": pa.compute.less,
        "number_is_less_than_or_equals": pa.compute.less_equal,
    }[operation]

    compared = func(table[column], value)
    return pa.compute.fill_null(compared, False)


def _parse_date32(value: str) -> pa.scalar:
    with warnings.catch_warnings():
        # numpy warns with DeprecationWarning when converting timezone offsets
        # to UTC. Even though converting timezone offsets to UTC is obviously
        # what everybody wants.
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return pa.scalar(np.datetime64(value, "D").astype(int), pa.date32())


def _parse_timestamp(value: str) -> pa.scalar:
    with warnings.catch_warnings():
        # numpy warns with DeprecationWarning when converting timezone offsets
        # to UTC. Even though converting timezone offsets to UTC is obviously
        # what everybody wants.
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return pa.scalar(np.datetime64(value, "ns"), pa.timestamp("ns"))


def _timestamp_condition_to_mask(
    table, operation: str, *, column: str, value: str
) -> pa.ChunkedArray:
    func = {
        "timestamp_is": pa.compute.equal,
        "timestamp_is_after": pa.compute.greater,
        "timestamp_is_after_or_equals": pa.compute.greater_equal,
        "timestamp_is_before": pa.compute.less,
        "timestamp_is_before_or_equals": pa.compute.less_equal,
    }[operation]

    field = table.schema.field(column)
    if pa.types.is_date32(field.type):
        compared_value = _parse_date32(value)
    else:
        compared_value = _parse_timestamp(value)
    compared = func(table[column], compared_value)
    return pa.compute.fill_null(compared, False)


def _cell_is_empty(column: pa.ChunkedArray) -> pa.ChunkedArray:
    if pa.types.is_unicode(column.type) or (
        pa.types.is_dictionary(column.type)
        and pa.types.is_unicode(column.type.value_type)
    ):
        func = lambda values: pa.compute.fill_null(pa.compute.equal(values, ""), False)
        return pa.compute.or_(
            pa.compute.is_null(column), _text_column_to_mask(column, func)
        )
    else:
        return pa.compute.is_null(column)


def _cell_condition_to_mask(table, operation: str, *, column: str) -> pa.ChunkedArray:
    func = {"cell_is_null": pa.compute.is_null, "cell_is_empty": _cell_is_empty}[
        operation
    ]
    return func(table[column])


def _condition_to_mask_by_kwargs(
    table: pa.Table, *, operation: str, **kwargs
) -> pa.ChunkedArray:
    # and/or/not: we don't pass an "operation" kwarg
    if operation == "and":
        return _and_condition_to_mask(table, **kwargs)
    elif operation == "or":
        return _or_condition_to_mask(table, **kwargs)
    elif operation == "not":
        return _not_condition_to_mask(table, **kwargs)
    else:
        # Everything else: we do pass the "operation" kwarg
        if operation.startswith("text_"):
            func = _text_condition_to_mask
        elif operation.startswith("number_"):
            func = _number_condition_to_mask
        elif operation.startswith("timestamp_"):
            func = _timestamp_condition_to_mask
        elif operation.startswith("cell_"):
            func = _cell_condition_to_mask
        else:
            raise NotImplementedError("Unknown operation %r" % operation)

    return func(table, operation, **kwargs)


def condition_to_mask(table: pa.Table, condition: Dict[str, Any]) -> pa.ChunkedArray:
    """Build a Boolean ChunkedArray showing which rows of `table` match `condition`.

    condition must look like:

        { "operation": "not", "condition": <recurse> }
        { "operation": "and", "conditions": [<recurse>, ...] }
        { "operation": "or", "conditions": [<recurse>, ...] }

        # "text" operates on int=>utf8 dictionaries and utf8 columns
        { "operation": "text_is", "column": "A", "value": "x", "isCaseSensitive": False, "isRegex": False },
        { "operation": "text_contains", "column": "A", "value": "x", "isCaseSensitive": False, "isRegex": False },

        # "number" operates on all primitive number columns; value may be int|float
        { "operation": "number_is", "column": "A", "value": 3.14 }
        { "operation": "number_is_greater_than", "column": "A", "value": 3.14 }
        { "operation": "number_is_greater_than_or_equals", "column": "A", "value": 3.14 }
        { "operation": "number_is_less_than", "column": "A", "value": 3.14 }
        { "operation": "number_is_less_than_or_equals", "column": "A", "value": 3.14 }

        # "timestamp" operates on timestamp("ns") columns
        { "operation": "timestamp_is", "column": "A", "value": "2020-01-01T02:31-03:00" }
        { "operation": "timestamp_is_after", "column": "A", "value": "2020-01-01T02:31-03:00" }
        { "operation": "timestamp_is_after_or_equals", "column": "A", "value": "2020-01-01T02:31-03:00" }
        { "operation": "timestamp_is_before", "column": "A", "value": "2020-01-01T02:31-03:00" }
        { "operation": "timestamp_is_before_or_equals", "column": "A", "value": "2020-01-01T02:31-03:00" }

        # "empty" means "null, or zero-length text"
        { "operation": "cell_is_empty", "column": "A" }
        { "operation": "cell_is_null", "column": "A" }

    The output has no nulls.

    Raise ConditionError on invalid regex. `condition_errors.errors` is a
    list of `re.error` with valid `pattern` and `msg`. (The regex format is re2,
    but we wrap it in `re.error` for the `.pattern` that callers may want.)
    """
    return _condition_to_mask_by_kwargs(table, **condition)
