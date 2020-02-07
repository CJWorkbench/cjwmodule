import re
from typing import List, Tuple

from cjwmodule import i18n


class RangeFormatError(ValueError):
    def __init__(self, value):
        self.value = value

    @property
    def i18n_message(self) -> i18n.I18nMessage:
        return i18n._trans_cjwmodule(
            "badParam.rows.invalidRange",
            'Rows must look like "1-2", "5" or "1-2, 5"; got "{value}"',
            {"value": self.value},
        )


numbers = re.compile("(?P<first>[1-9]\d*)(?:-(?P<last>[1-9]\d*))?")


def parse_interval(s: str) -> Tuple[int, int]:
    """
    Parse a string 'interval' into a tuple

    >>> parse_interval('1')
    (0, 0)
    >>> parse_interval('1-3')
    (0, 2)
    >>> parse_interval('5')
    (4, 4)
    >>> parse_interval('hi')
    Traceback (most recent call last):
        ...
    RangeFormatError: Rows must look like "1-2", "5" or "1-2, 5"; got "hi"
    """
    match = numbers.fullmatch(s)
    if not match:
        raise RangeFormatError(s)

    first = int(match.group("first"))
    last = int(match.group("last") or first)
    return (first - 1, last - 1)


commas = re.compile("\\s*,\\s*")


def parse_intervals(rows: str) -> List[Tuple[int, int]]:
    return [parse_interval(s) for s in commas.split(rows.strip()) if s.strip()]
