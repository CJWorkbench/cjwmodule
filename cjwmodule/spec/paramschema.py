from typing import Any, Dict, FrozenSet, List, NamedTuple, Optional, Protocol, Union

import pytz
import re2

__all__ = ["ParamSchema"]


# [2021-04-16] mypy can't recurse: https://github.com/python/mypy/issues/731
Jsonish = Any


class ParamSchema(Protocol):
    """Data type -- that is, storage format -- of a parameter.

    The ParamSchema describes the "shape" of user-input params. The user-input
    data is "JSON-ish": None, int, float, bool, str, list of these, or Dict of
    these keyed by str. A module's `render()` method's params looks "JSON-ish".

    ParamSchema _is not_ the user-input data. It _describes_ the user-input
    data. In general, the framework code relies on the ParamSchema to prepare
    params and the module itself only looks at user-input data.

    For instance:

        schema = ParamSchema.Dict({"A": ParamSchema.String(default="foo")})
        schema.validate({"A": "bar"})  # ok
        schema.validate("bar")  # not ok!

    Do not confuse "Schema" with "Field". A "Field" is an entry in the module
    spec's `parameters` list. (TODO rename it "fields".) A "ParamSchema"
    describes what JSON-ish values are allowed and what values are not.
    """

    default: Jsonish
    """Sensible default value.

    When a user creates a Step, its initial Params will be the schema's
    `default` value.
    """

    def validate(self, value: Jsonish) -> None:
        """Raise `ValueError` if `value` is not valid.

        Call this even on user-input data that was validated in the past.
        [2021-04-16, adamhooper] TODO consider loosening this restriction: we
        validate the `migrate_params()` output and user input, so values in the
        database with the correct version must be valid, right?.
        """


class ParamSchemaOption(NamedTuple):
    """Decorate a schema such that it may be None."""

    inner_schema: ParamSchema
    default: Jsonish = None

    def validate(self, value):
        if value is not None:
            self.inner_schema.validate(value)


def _validate_is_safe_str(value: Jsonish) -> None:
    if not isinstance(value, str):
        raise ValueError("Value %r is not a string" % (value,))
    if "\x00" in value:
        raise ValueError("Value %r is not valid text: zero byte not allowed" % (value,))
    try:
        value.encode("utf-8")
    except UnicodeError as err:
        raise ValueError("Value %r is not valid Unicode: %s" % (value, str(err)))


class ParamSchemaString(NamedTuple):
    r"""Accept valid Unicode text.

    This is stricter than Python `str`. In particular, `"\ud8002"` is invalid
    (because a lone surrogate isn't valid Unicode text) and `"\x00"` is invalid
    (because Postgres doesn't allow null bytes).
    """

    default: str = ""

    def validate(self, value):
        _validate_is_safe_str(value)


class ParamSchemaInteger(NamedTuple):
    """Accept integers."""

    default: int = 0

    def validate(self, value):
        if not isinstance(value, int):
            raise ValueError("Value %r is not an integer" % (value,))


class ParamSchemaFloat(NamedTuple):
    """Accept floats or integers. Akin to JSON 'number' type."""

    default: Union[float, int] = 0.0

    def validate(self, value):
        if not (isinstance(value, float) or isinstance(value, int)):
            raise ValueError("Value %r is not a float" % (value,))


class ParamSchemaBoolean(NamedTuple):
    """Accept `True` or `False`."""

    default: bool = False

    def validate(self, value):
        if not isinstance(value, bool):
            raise ValueError("Value %r is not a boolean" % (value,))


class ParamSchemaCondition(NamedTuple):
    """Valid JSON structure for column comparisons and combinations of them.

    Example valid value:

        {
            "operation": "text_contains",
            "column": "A",
            "value": "foo",
            "isCaseSensitive": True,
            "isRegex": False
        }

    Or:

        {
            "operation": "number_is_greater_than",
            "column": "A",
            "value": "4",
            "isCaseSensitive": True,
            "isRegex": True
        }

    There's nesting, too:

        {
            "operation": "and",
            "conditions": [ ... ]
        }

    List of valid operations (and arguments):

        * `and` (`conditions`)
        * `or` (`conditions`)
        * `cell_is_empty` ()
        * `cell_is_not_empty` ()
        * `cell_is_null` ()
        * `cell_is_not_null` ()
        * `text_contains` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_does_not_contain` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_is` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `text_is_not` (`column`, `value`, `isCaseSensitive`, `isRegex`)
        * `timestamp_is` (`column`, `value`)
        * `timestamp_is_after` (`column`, `value`)
        * `timestamp_is_after_or_equals` (`column`, `value`)
        * `timestamp_is_before` (`column`, `value`)
        * `timestamp_is_before_or_equals` (`column`, `value`)
        * `timestamp_is_not` (`column`, `value`)
        * `number_is` (`column`, `value`)
        * `number_is_greater_than` (`column`, `value`)
        * `number_is_greater_than_or_equal` (`column`, `value`)
        * `number_is_less_than` (`column`, `value`)
        * `number_is_less_than_or_equal` (`column`, `value`)
        * `number_is_not` (`column`, `value`)

    For ease of UI implementation, some nonsense is allowed: "value" is a String
    so it may be invalid for number/timestamp operations; "column" may be empty;
    "isCaseSensitive" and "isRegex" apply to number/timestamp operations;
    "column" may have the wrong type; and nested "conditions" may be empty. Look
    to `renderprep` to see how those inconsistencies are removed.

    XXX right now, for UI reasons, conditions with a `column` must be nested
    exactly two levels depe, and deeper nesting is not allowed. For instance:

        {
            "operation": "and",
            "conditions": [
                {
                    "operation": "or",
                    "conditions": [
                        { ...condition... }
                    ]
                }
            ]
        }

    XXX This is to handle restrictions built into the user interface.

    More than any other value, `condition` values show one thing in the UI (and
    the module's `migrate_params()` and another thing entirely when passed to a
    module's `render()` method. See `renderprep` for details. The gist:
    `render()` has a `not` (`condition`) operation and all invalid operations
    are omitted. (It can receive `condition: None`.)
    """

    @property
    def default(self) -> Dict[str, Jsonish]:
        return {"operation": "and", "conditions": []}

    def __validate_common(self, value):
        if not isinstance(value, dict) or "operation" not in value:
            raise ValueError("%r must be a dict with an 'operation' key" % (value,))

    def __validate_common_level_0_or_1(self, value):
        keys = frozenset(value.keys())
        if (
            keys != {"operation", "conditions"}
            or value["operation"] not in {"and", "or"}
            or not isinstance(value["conditions"], list)
        ):
            raise ValueError(
                "Value must look like {'operation': 'or|and', 'conditions': [...]}; got %r"
                % (value,)
            )

    def __validate_level2(self, value):
        self.__validate_common(value)
        keys = frozenset(value.keys())
        if keys != frozenset(
            ["operation", "column", "value", "isCaseSensitive", "isRegex"]
        ):
            raise ValueError(
                "Keys must be operation, column, value, isCaseSensitive, isRegex. Got: %r"
                % (value,)
            )
        if value["operation"] not in {
            "",
            "and",
            "or",
            "cell_is_empty",
            "cell_is_not_empty",
            "cell_is_null",
            "cell_is_not_null",
            "text_contains",
            "text_does_not_contain",
            "text_is",
            "text_is_not",
            "timestamp_is",
            "timestamp_is_after",
            "timestamp_is_after_or_equals",
            "timestamp_is_before",
            "timestamp_is_before_or_equals",
            "timestamp_is_not",
            "number_is",
            "number_is_greater_than",
            "number_is_greater_than_or_equals",
            "number_is_less_than",
            "number_is_less_than_or_equals",
            "number_is_not",
        }:
            raise ValueError("There is no such operation: %r" % (value["operation"],))
        for key, wanted_type in (
            ("column", str),
            ("value", str),
            ("isCaseSensitive", bool),
            ("isRegex", bool),
        ):
            if not isinstance(value[key], wanted_type):
                raise ValueError(
                    "Wrong type of %s: expected %s, got %r"
                    % (key, wanted_type.__name__, value[key])
                )

    def __validate_level1(self, value):
        self.__validate_common(value)
        self.__validate_common_level_0_or_1(value)
        for condition in value["conditions"]:
            self.__validate_level2(condition)

    def validate(self, value):
        self.__validate_common(value)
        self.__validate_common_level_0_or_1(value)
        for condition in value["conditions"]:
            self.__validate_level1(condition)


class ParamSchemaColumn(NamedTuple):
    column_types: Optional[FrozenSet[str]] = None
    tab_parameter: Optional[str] = None

    @property
    def default(self):
        return ""  # a legacy quirk

    def validate(self, value):
        _validate_is_safe_str(value)


class ParamSchemaMulticolumn(NamedTuple):
    column_types: Optional[FrozenSet[str]] = None
    tab_parameter: Optional[str] = None

    @property
    def default(self) -> List[str]:
        return []

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError("Value %r is not a list" % (value,))
        for v in value:
            if not v:
                raise ValueError("Empty column not allowed as a value in multitab")
            _validate_is_safe_str(v)


class ParamSchemaEnum(NamedTuple):
    choices: FrozenSet[Jsonish]
    default: Jsonish

    def validate(self, value):
        if value not in self.choices:
            raise ValueError(
                "Value %(value)r is not in choices %(choices)r"
                % {"value": value, "choices": self.choices}
            )


class ParamSchemaTimezone(NamedTuple):
    """Accept 'America/Montreal'-style strings or 'UTC'.

    The database is from https://www.iana.org/time-zones
    """

    @property
    def default(self):
        return "UTC"

    def validate(self, value):
        if value not in pytz.all_timezones_set:
            raise ValueError("Value %r is not an IANA timezone identifier" % (value,))


def _validate_is_list_of_valid_values(
    inner_schema: ParamSchema, value: Jsonish
) -> None:
    if not isinstance(value, list):
        raise ValueError("Value %r is not a list" % (value,))
    for v in value:
        inner_schema.validate(v)


class ParamSchemaList(NamedTuple):
    inner_schema: ParamSchema

    @property
    def default(self) -> List[Jsonish]:
        return []

    def validate(self, value):
        _validate_is_list_of_valid_values(self.inner_schema, value)


class ParamSchemaDict(NamedTuple):
    """A grouping of properties with a schema defined in the schema.

    This is different from ParamSchemaMap, which allows arbitrary keys and
    forces all values to have the same schema.
    """

    properties: Dict[str, ParamSchema]

    @property
    def default(self):
        return {k: v.default for k, v in self.properties.items()}

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError("Value %r is not a dict" % (value,))

        expect_keys = frozenset(self.properties.keys())
        actual_keys = frozenset(value.keys())
        if expect_keys != actual_keys:
            raise ValueError(
                "Value %(value)r has wrong keys: expected %(keys)r"
                % {"value": value, "keys": expect_keys}
            )

        for name, inner_schema in self.properties.items():
            inner_schema.validate(value[name])


class ParamSchemaMap(NamedTuple):
    """A key-value store with arbitrary keys and all-the-same-schema values.

    This is different from ParamSchemaDict, which is rigid about keys and their
    schemas.
    """

    value_schema: ParamSchema

    @property
    def default(self) -> Dict[str, Any]:
        return {}

    def validate(self, value):
        if not isinstance(value, dict):
            raise ValueError("Value %r is not a dict" % (value,))

        for v in value.values():
            self.value_schema.validate(v)


class ParamSchemaTab(NamedTuple):
    """A (str) tab slug, or "" if no tab is selected."""

    @property
    def default(self) -> str:
        return ""

    def validate(self, value):
        _validate_is_safe_str(value)


class ParamSchemaMultitab(NamedTuple):
    """A list of tabs; empty values not allowed."""

    @property
    def default(self) -> List[str]:
        return []

    def validate(self, value):
        if not isinstance(value, list):
            raise ValueError("Value %r is not a list" % (value,))
        for v in value:
            if not v:
                raise ValueError("Empty tab not allowed as a value in multitab")
            _validate_is_safe_str(v)


class ParamSchemaMultichartseries(NamedTuple):
    """A 'y_series' parameter: array of columns+colors.

    This is like a List[Dict], except when omitting table columns we omit the
    entire Dict if its Column is missing.
    """

    @property
    def default(self) -> List[Dict[str, str]]:
        return []

    def validate(self, value):
        inner_schema = ParamSchemaDict(
            {
                "column": ParamSchemaColumn(column_types=frozenset({"number"})),
                "color": ParamSchemaString(),  # TODO enforce '#abc123' pattern
            }
        )
        _validate_is_list_of_valid_values(inner_schema, value)
        for v in value:
            if not v["column"]:
                raise ValueError("multichartseries column must be non-empty")


_UUIDRegex = re2.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\z"
)


class ParamSchemaFile(NamedTuple):
    """String-encoded UUID pointing to an UploadedFile (and S3).

    The default, value, `null`, means "No file".
    """

    @property
    def default(self) -> Optional[str]:
        return None

    def validate(self, value):
        if value is None:
            return  # None is the default, and it's valid
        if not isinstance(value, str):
            raise ValueError("Value %r is not a string" % (value,))
        if not _UUIDRegex.match(value):
            raise ValueError("Value %r is not a UUID string representation" % (value,))


# Aliases to help with import. e.g.:
# from cjwmodule.spec.paramschema import ParamSchema
# schema = ParamSchema.String()
ParamSchema.Boolean = ParamSchemaBoolean
ParamSchema.Column = ParamSchemaColumn
ParamSchema.Condition = ParamSchemaCondition
ParamSchema.Dict = ParamSchemaDict
ParamSchema.Enum = ParamSchemaEnum
ParamSchema.File = ParamSchemaFile
ParamSchema.Float = ParamSchemaFloat
ParamSchema.Integer = ParamSchemaInteger
ParamSchema.List = ParamSchemaList
ParamSchema.Map = ParamSchemaMap
ParamSchema.Multichartseries = ParamSchemaMultichartseries
ParamSchema.Multicolumn = ParamSchemaMulticolumn
ParamSchema.Multitab = ParamSchemaMultitab
ParamSchema.Option = ParamSchemaOption
ParamSchema.String = ParamSchemaString
ParamSchema.Tab = ParamSchemaTab
ParamSchema.Timezone = ParamSchemaTimezone
