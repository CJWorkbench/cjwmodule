import datetime
import re
from typing import Any, Dict

import numpy as np
import pyarrow as pa
import pytest

from cjwmodule.arrow.condition import condition_to_mask


def NOT(condition):
    return {"operation": "not", "condition": condition}


def AND(*conditions):
    return {"operation": "and", "conditions": conditions}


def OR(*conditions):
    return {"operation": "or", "conditions": conditions}


def TEXT(op, column, value, case_sensitive=False, regex=False):
    return dict(
        operation=f"text_{op}",
        column=column,
        value=value,
        isCaseSensitive=case_sensitive,
        isRegex=regex,
    )


def NUMBER(op, column, value):
    return dict(operation=f"number_{op}", column=column, value=value)


def TIMESTAMP(op, column, value):
    return dict(operation=f"timestamp_{op}", column=column, value=value)


def CELL(op, column):
    return dict(operation=f"cell_{op}", column=column)


def _assert_condition_mask(
    table_spec: Dict[str, pa.Array], condition: Dict[str, Any], expect_str: str
) -> None:
    """Helper function, for writing tests quickly.

    Parameters:

        table: dictionary argument to `pa.table()`
        condition: input condition
        expect_mask: String like `"00110"` (meaning, in this example, "we expect
                     the result to be `[False, False, True, True, False]`")
    """
    table = pa.table(table_spec)
    result = condition_to_mask(table, condition)
    result_list = result.to_pylist()
    encoder = {True: "1", False: "0", None: "."}
    result_str = "".join(encoder[v] for v in result_list)
    assert result_str == expect_str


def test_text_contains_empty():
    _assert_condition_mask(
        {"A": ["a", None, "ba", ""]}, TEXT("contains", "A", ""), "1011"
    )


def test_text_contains_case_insensitive():
    _assert_condition_mask(
        {"A": ["fred", "frederson", None, "maggie", "Fredrick"]},
        TEXT("contains", "A", "fred", case_sensitive=False),
        "11001",
    )


def test_text_contains_case_sensitive():
    _assert_condition_mask(
        {"A": ["fred", "frederson", None, "maggie", "Fredrick"]},
        TEXT("contains", "A", "fred", case_sensitive=True),
        "11000",
    )


def test_text_contains_case_insensitive_dictionary():
    _assert_condition_mask(
        {
            "A": pa.array(
                ["fred", "frederson", None, "maggie", "Fredrick"]
            ).dictionary_encode()
        },
        TEXT("contains", "A", "fred", case_sensitive=False),
        "11001",
    )


def test_text_contains_case_sensitive_dictionary():
    _assert_condition_mask(
        {
            "A": pa.array(
                ["fred", "frederson", None, "maggie", "Fredrick"]
            ).dictionary_encode()
        },
        TEXT("contains", "A", "fred", case_sensitive=True),
        "11000",
    )


def test_text_contains_regex_case_sensitive():
    _assert_condition_mask(
        {"A": ["fred", "frederson", None, "maggie", "Fredrick"]},
        TEXT("contains", "A", "f[a-zA-Z]+d", case_sensitive=False, regex=True),
        "11001",
    )


def test_text_contains_regex_case_insensitive():
    _assert_condition_mask(
        {"A": ["fred", "frederson", None, "maggie", "Fredrick"]},
        TEXT("contains", "A", "f[a-zA-Z]+d", case_sensitive=True, regex=True),
        "11000",
    )


def test_text_contains_regex_parse_error():
    with pytest.raises(re.error, match="no argument for repetition operator: *"):
        condition_to_mask(pa.table({"A": ["x"]}), TEXT("is", "A", "*", regex=True))


def test_text_contains_regex_null_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["a", None]).dictionary_encode()},
        TEXT("contains", "A", "a", regex=True),
        "10",
    )


def test_text_is():
    _assert_condition_mask(
        {"A": ["fred", "not fred", None]},
        TEXT("is", "A", "fred", case_sensitive=False),
        "100",
    )


def test_text_is_case_sensitive():
    _assert_condition_mask(
        {"A": ["Fred", "fred", "not fred", None]},
        TEXT("is", "A", "fred", case_sensitive=True),
        "0100",
    )


def test_text_is_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["fred", "not fred", None]).dictionary_encode()},
        TEXT("is", "A", "fred", case_sensitive=False),
        "100",
    )


def test_text_is_case_sensitive_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["Fred", "fred", "not fred", None]).dictionary_encode()},
        TEXT("is", "A", "fred", case_sensitive=True),
        "0100",
    )


def test_text_is_empty_str():
    _assert_condition_mask(
        {"A": [" ", "", None]}, TEXT("is", "A", "", case_sensitive=False), "010"
    )


def test_text_is_empty_str_case_sensitive():
    _assert_condition_mask(
        {"A": [" ", "", None]}, TEXT("is", "A", "", case_sensitive=True), "010"
    )


def test_text_is_regex_case_sensitive():
    _assert_condition_mask(
        {"A": ["Fred", "fred", "wilfred", None]},
        TEXT("is", "A", ".*fred", regex=True, case_sensitive=True),
        "0110",
    )


def test_text_is_regex_case_insensitive():
    _assert_condition_mask(
        {"A": ["Fred", "fred", "wilfred", None]},
        TEXT("is", "A", ".*fred", regex=True, case_sensitive=False),
        "1110",
    )


def test_text_is_empty_regex():
    _assert_condition_mask(
        {"A": [" ", "", None]},
        TEXT("is", "A", "", regex=True, case_sensitive=False),
        "010",
    )


def test_text_is_empty_regex_case_sensitive():
    _assert_condition_mask(
        {"A": [" ", "", None]},
        TEXT("is", "A", "", regex=True, case_sensitive=True),
        "010",
    )


def test_text_is_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["fred", "not fred", None]).dictionary_encode()},
        TEXT("is", "A", "fred"),
        "100",
    )


def test_cell_is_empty_number():
    _assert_condition_mask({"A": pa.array([1, 2, None])}, CELL("is_empty", "A"), "001")


def test_cell_is_empty_timestamp():
    _assert_condition_mask(
        {"A": pa.array([datetime.datetime.now(), None], pa.timestamp("ns"))},
        CELL("is_empty", "A"),
        "01",
    )


def test_cell_is_empty_text():
    _assert_condition_mask({"A": ["a", None, ""]}, CELL("is_empty", "A"), "011")


def test_cell_is_empty_text_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["a", None, ""]).dictionary_encode()},
        CELL("is_empty", "A"),
        "011",
    )


def test_cell_is_null_number():
    _assert_condition_mask({"A": [1, 2, None]}, CELL("is_null", "A"), "001")


def test_cell_is_null_timestamp():
    _assert_condition_mask(
        {"A": pa.array([datetime.datetime.now(), None], pa.timestamp("ns"))},
        CELL("is_null", "A"),
        "01",
    )


def test_cell_is_null_text():
    _assert_condition_mask({"A": ["a", None, ""]}, CELL("is_null", "A"), "010")


def test_cell_is_null_text_dictionary():
    _assert_condition_mask(
        {"A": pa.array(["a", None, ""]).dictionary_encode()},
        CELL("is_null", "A"),
        "010",
    )


def test_number_is():
    _assert_condition_mask({"A": [1, 2, 3, 1, 4, None]}, NUMBER("is", "A", 1), "100100")


def test_number_is_int_round_float():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is", "A", 1.0), "100100"
    )


def test_number_is_int_float():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is", "A", 1.1), "000000"
    )


def test_number_is_uint8_int32():
    _assert_condition_mask(
        {"A": pa.array([1, 2, 3, 1, 4, None], pa.int8())},
        NUMBER("is", "A", -123456),
        "000000",
    )


def test_number_is_float_int():
    _assert_condition_mask(
        {"A": [1.0, 2, 3, 1, 4, None]}, NUMBER("is", "A", 1), "100100"
    )


def test_number_is_greater_than():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is_greater_than", "A", 2), "001010"
    )


def test_number_is_greater_than_int_float():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is_greater_than", "A", 1.9), "011010"
    )


def test_number_is_greater_than_float_int():
    _assert_condition_mask(
        {"A": [1.9, 2, 3, 1, 4, None]}, NUMBER("is_greater_than", "A", 1), "111010"
    )


def test_number_is_greater_than_int_positive_overflow():
    _assert_condition_mask(
        {"A": pa.array([1, 2, 3, 1, 4, None], pa.int8())},
        NUMBER("is_greater_than", "A", 200),
        "000000",
    )


def test_number_is_greater_than_int_negative_overflow():
    _assert_condition_mask(
        {"A": pa.array([1, 2, 3, 1, 4, None], pa.int8())},
        NUMBER("is_greater_than", "A", -200),
        "111110",
    )


def test_number_is_greater_than_or_equals():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]},
        NUMBER("is_greater_than_or_equals", "A", 2),
        "011010",
    )


def test_number_is_less_than():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is_less_than", "A", 3), "110100"
    )


def test_number_is_less_than_or_equals():
    _assert_condition_mask(
        {"A": [1, 2, 3, 1, 4, None]}, NUMBER("is_less_than_or_equals", "A", 3), "111100"
    )


def test_timestamp_is():
    _assert_condition_mask(
        {
            "A": np.array(
                ["2020-01-01", "2020-01-01T00:00:00.000000001", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is", "A", "2020-01-01"),
        "100",
    )


def test_timestamp_is_with_timezone():
    _assert_condition_mask(
        {
            "A": np.array(
                ["2020-01-01", "2020-01-01T00:00:00.000000001", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is", "A", "2020-01-01T05:00:00.000000001+05:00"),
        "010",
    )


def test_timestamp_after():
    _assert_condition_mask(
        {
            "A": np.array(
                # midnight 2020-01-01 is not _after_ 2020-01-01
                ["2020-01-01", "2020-01-01T11:11", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is_after", "A", "2020-01-01"),
        "010",
    )


def test_timestamp_after_or_equals():
    _assert_condition_mask(
        {
            "A": np.array(
                # midnight 2020-01-01 is not _after_ 2020-01-01
                ["2020-01-01", "2020-01-01T11:11", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is_after_or_equals", "A", "2020-01-01"),
        "110",
    )


def test_timestamp_is_before():
    _assert_condition_mask(
        {
            "A": np.array(
                ["2020-01-01", "2020-01-01T11:11", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is_before", "A", "2020-01-01T11:11"),
        "100",
    )


def test_timestamp_is_before_or_equals():
    _assert_condition_mask(
        {
            "A": np.array(
                ["2020-01-01", "2020-01-01T11:11", None],
                dtype="datetime64[ns]",
            )
        },
        TIMESTAMP("is_before_or_equals", "A", "2020-01-01T11:11"),
        "110",
    )


def test_and():
    _assert_condition_mask(
        {"A": [1, 2, 3], "B": [2, 3, 4]},
        AND(NUMBER("is_less_than", "A", 3), NUMBER("is_greater_than", "B", 2)),
        "010",
    )


def test_or():
    _assert_condition_mask(
        {"A": [1, 2, 3], "B": [2, 3, 4]},
        OR(NUMBER("is_less_than", "A", 2), NUMBER("is_greater_than", "B", 3)),
        "101",
    )


def test_not():
    _assert_condition_mask(
        {"A": ["fred", "frederson", None, "maggie", "Fredrick"]},
        NOT(TEXT("contains", "A", "fred")),
        "00110",
    )


def test_recurse():
    # https://www.pivotaltracker.com/story/show/165434277
    # I couldn't reproduce -- dunno what the issue was. But it's good to
    # test for it!
    _assert_condition_mask(
        {"A": [1, 2, 3, 4, 5, 6]},
        AND(
            AND(
                NUMBER("is_greater_than", "A", 1),
                NUMBER("is_greater_than_or_equals", "A", 5),
            ),
            AND(AND(NUMBER("is_greater_than", "A", 2))),
        ),
        "000011",
    )
