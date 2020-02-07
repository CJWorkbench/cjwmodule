from cjwmodule.testing.i18n import cjwmodule_i18n_message
from cjwmodule.util.rowranges import RangeFormatError, parse_intervals


def test_zero_gives_error():
    try:
        parse_intervals("0-1")
        assert False
    except RangeFormatError as err:
        assert err.i18n_message == cjwmodule_i18n_message(
            "badParam.rows.invalidRange", {"value": "0-1"}
        )


def test_non_numeric_gives_error():
    try:
        parse_intervals("hi")
        assert False
    except RangeFormatError as err:
        assert err.i18n_message == cjwmodule_i18n_message(
            "badParam.rows.invalidRange", {"value": "hi"}
        )


def test_single_row():
    assert parse_intervals("5") == [(4, 4)]


def test_single_range():
    assert parse_intervals("1-3") == [(0, 2)]


def test_mutliple_ranges():
    assert parse_intervals("1, 3-5,9") == [(0, 0), (2, 4), (8, 8)]
