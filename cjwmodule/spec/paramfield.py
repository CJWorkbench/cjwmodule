"""ALPHA API - NOT USING SEMVER

We're not happy with this API yet. It might change in minor or patch releases
of `cjwmodule`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Literal, Optional

import re2

from .paramschema import ParamSchema

__all__ = ["ParamField"]


VisibleIf = Dict[str, Dict[str, Any]]
ColumnTypeString = Literal["text", "number", "timestamp"]


_lookup = {}  # dict of e.g., {'column': ParamFieldColumn}


@dataclass(frozen=True)
class ParamField(ABC):
    """Form field that Workbench will show the user.

    A module spec lists these, in order, in its `parameters` list.

    Each field has an underlying data representation: a `ParamSchema`.
    ParamField describes the field we present the user; ParamSchema
    describes the data we present the module. For example: `ParamField.Column`
    means, "column-select dropdown"; `ParamSchema.Column` means,
    "string with default ''".
    """

    id_name: str
    """The JSON Object key (or HTML field "name") of this field."""

    visible_if: Optional[VisibleIf] = None
    """JSON object with logic deciding when the field should appear.

    Even when the field does not appear, it still has a value.

    The default is `None`, which means: "always visible."
    """

    # Some common other properties are documented here, since they're reused in
    # several subclasses:

    @abstractmethod
    def to_schema(self) -> Optional[ParamSchema]:
        """ParamSchema of values this field returns.

        Usually, a ParamField maps to a single ParamSchema -- meaning a single
        JSON value. Exceptions like "statictext" (zero DTypes) return zero
        DTypes.
        """

    @classmethod
    def from_dict(cls, json_value: Dict[str, Any]) -> ParamField:
        """Parse a parameter from the module specification.

        At this point the schema has been validated; assume it is valid and any
        exception raised from this method is a bug.

        The logic is: look up the subclass by `json_value['type']`, and then
        call its `._from_kwargs()` method with the rest of the JSON dict.
        """
        json_value = dict(json_value)  # shallow copy
        json_type = json_value.pop("type")
        subcls = _lookup[json_type]
        return subcls._from_kwargs(**json_value)

    @classmethod
    def _from_kwargs(cls, **kwargs) -> ParamField:
        return cls(**kwargs)


def _register_type(type_name):
    """Add immutable 'type' field for JSON serialization and connect globals.

    For instance: ...

        @dataclass(frozen=True)
        @register_type("foo")
        class ParamFieldFoo:
            ...

    ... adds:

    * `_lookup['foo'] == ParamFieldFoo`
    * `ParamField.Foo == ParamFieldFoo` (always a dot after "ParamField").
    * ParamFieldFoo(...).type == 'foo' -- this is a dataclass field!
    """

    def decorator(cls):
        setattr(cls, "type", type_name)

        name = cls.__name__
        assert name.lower() == f"paramfield{type_name}"
        subname = name[len("ParamField") :]
        _lookup[type_name] = cls
        setattr(ParamField, subname, cls)

        return cls

    return decorator


@dataclass(frozen=True)
class _HasName:
    name: str = ""
    """The _label_ of this field. (Beware this misleading property name!)

    The default is `""`, meaning: no label.
    """


@dataclass(frozen=True)
class _HasPlaceholder:
    placeholder: str = ""
    """The text appearing in this field when there is no value.

    The default is '', which means: "component-specific default behavior."
    """


@_register_type("statictext")
@dataclass(frozen=True)
class ParamFieldStatictext(_HasName, ParamField):
    """Text the user sees, with no underlying value."""

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return None


class SecretLogic(ABC):
    @classmethod
    def _from_dict(cls, json_value) -> SecretLogic:
        provider = json_value["provider"]
        if provider == "oauth":  # DEPRECATED
            return cls.Oauth2(provider="oauth2", service=json_value["service"])
        elif provider == "oauth2":
            return cls.Oauth2(**json_value)
        elif provider == "oauth1a":
            return cls.Oauth1a(**json_value)
        elif provider == "string":
            return cls.String(**json_value)


@dataclass(frozen=True)
class SecretLogicOauth1a:
    provider: str  # 'oauth1a', always
    service: str


@dataclass(frozen=True)
class SecretLogicOauth2:
    provider: str  # 'oauth2', always
    service: str


@dataclass(frozen=True)
class SecretLogicString:
    provider: str  # 'string', always
    label: str
    pattern: str
    placeholder: str
    help: str
    help_url_prompt: str
    help_url: str

    def __post_init__(self):
        re2.compile(self.pattern)  # raise error if invalid


@_register_type("secret")
@dataclass(frozen=True)
class ParamFieldSecret(ParamField):
    """Secret such as an API key the user can set.

    Secrets are not stored in undo history (because we only want the owner to
    see them, not readers). So they don't have JSON values.
    """

    secret_logic: SecretLogic = NotImplementedError

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return None  # secrets aren't param values -- they're a separate dict

    # override
    @classmethod
    def _from_kwargs(cls, *, secret_logic: Dict[str, str], **kwargs):
        secret_logic = SecretLogic._from_dict(secret_logic)
        return cls(secret_logic=secret_logic, **kwargs)


ParamFieldSecret.Logic = SecretLogic
SecretLogic.Oauth2 = SecretLogicOauth2
SecretLogic.Oauth1a = SecretLogicOauth1a
SecretLogic.String = SecretLogicString


@_register_type("button")
@dataclass(frozen=True)
class ParamFieldButton(_HasName, ParamField):
    """Button the user can click to submit data.

    This does not store a value. It does not send any different data over the
    wire. Some modules show buttons; others use the default "Execute" button.

    The "name" is what appears _inside_ the button, not outside it.
    """

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return None


@_register_type("string")
@dataclass(frozen=True)
class ParamFieldString(_HasPlaceholder, _HasName, ParamField):
    """Text the user can type."""

    default: str = ""

    multiline: bool = False
    """If True, newlines are permitted in data."""

    syntax: Optional[Literal["python", "sql"]] = None
    """If set, this String is user-supplied code."""

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.String(self.default)


@_register_type("numberformat")
@dataclass(frozen=True)
class ParamFieldNumberFormat(_HasName, ParamField):
    """Textual number-format string, like '${:0,.2f}'"""

    default: str = "{:,}"

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.String(self.default)


@_register_type("custom")
@dataclass(frozen=True)
class ParamFieldCustom(_HasName, ParamField):
    """Deprecated "custom" value -- behavior depends on id_name.

    Tread very carefully here. Don't add functionality: remove it. Nobody knows
    how this works.
    """

    default: Any = ""  # for version_select

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.String(self.default)  # dunno why


@_register_type("column")
@dataclass(frozen=True)
class ParamFieldColumn(_HasPlaceholder, _HasName, ParamField):
    """Column selector. Selects a str; default value `""` means "no column"."""

    column_types: Optional[List[ColumnTypeString]] = None
    """Column-type restrictions for the underlying ParamSchema.Column."""

    tab_parameter: Optional[str] = None
    """If set, the ParamFieldTab id_name that determines valid columns.

    For instance, a "join" module might want to list columns from a different
    tab.

    The default `None` means, "this tab."
    """

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Column(
            column_types=(frozenset(self.column_types) if self.column_types else None),
            tab_parameter=self.tab_parameter,
        )


@_register_type("condition")
@dataclass(frozen=True)
class ParamFieldCondition(ParamField):
    """Condition and combinatorial logic of conditions.

    Condition JSON is _stored_ (and passed to the user interface) as a
    2-level-deep nested array of and/or operations. But modules' render()
    methods see something more normalized: "and/or/not" operations with no
    unneeded info.
    """

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Condition()


@_register_type("multicolumn")
@dataclass(frozen=True)
class ParamFieldMulticolumn(_HasPlaceholder, _HasName, ParamField):
    """Multicolumn selector. Selects FrozenSet of str."""

    column_types: Optional[List[ColumnTypeString]] = None
    """Column-type restrictions for the underlying ParamSchema.Multicolumn."""

    tab_parameter: Optional[str] = None
    """If set, the ParamFieldTab id_name that determines valid columns.

    For instance, a "join" module might want to list columns from a different
    tab.

    The default `None` means, "this tab."
    """

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Multicolumn(
            column_types=(frozenset(self.column_types) if self.column_types else None),
            tab_parameter=self.tab_parameter,
        )


@_register_type("multichartseries")
@dataclass(frozen=True)
class ParamFieldMultichartseries(_HasPlaceholder, _HasName, ParamField):
    """Selects { column, color } pairs."""

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Multichartseries()


@_register_type("integer")
@dataclass(frozen=True)
class ParamFieldInteger(_HasPlaceholder, _HasName, ParamField):
    """Integer the user can type."""

    default: int = 0

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Integer(self.default)


@_register_type("float")
@dataclass(frozen=True)
class ParamFieldFloat(_HasPlaceholder, _HasName, ParamField):
    """Decimal (stored as floating-point) the user can type."""

    default: float = 0.0

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Float(self.default)


@_register_type("timezone")
@dataclass(frozen=True)
class ParamFieldTimezone(_HasName, ParamField):
    """Timezone such as 'America/Montreal' or 'UTC'."""

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Timezone()


@_register_type("checkbox")
@dataclass(frozen=True)
class ParamFieldCheckbox(_HasName, ParamField):
    """Boolean selected by checkbox."""

    default: bool = False

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Boolean(self.default)


@dataclass(frozen=True)
class EnumOption:
    """An enum (menu/radio) option the user can select."""

    label: str
    """Text visible to the user."""

    value: Any
    """Value stored when the user selects this option."""

    @property
    def schema_choices(self) -> FrozenSet[Any]:
        return frozenset([self.value])


class MenuOption(ABC):
    @property
    def schema_choices(self) -> FrozenSet[Any]:
        return frozenset()

    @classmethod
    def _from_dict(cls, json_value) -> MenuOption:
        if json_value == "separator":
            return cls.Separator
        else:
            return cls.Value(**json_value)


class MenuOptionEnum(EnumOption, MenuOption):
    pass


class _MenuOptionSeparator(MenuOption):
    def __deepcopy__(self, _memo):
        # Used by dataclasses.asdict() when serializing
        #
        # This breaks deep-copy ... but deep-copy isn't really our style in
        # Workbench: we prefer immutable variables, and shallow-copy is the way
        # to copy those.
        return "separator"


MenuOptionSeparator = _MenuOptionSeparator()  # singleton


@_register_type("menu")
@dataclass(frozen=True)
class ParamFieldMenu(_HasPlaceholder, _HasName, ParamField):
    """Enum value selected by drop-down menu.

    `options` may contain `"separator"` to improve styling.
    """

    options: List[MenuOption] = NotImplementedError
    """Enumeration options.

    Some may be "separator" -- it appears to the client but is not part of the
    ParamSchema.
    """

    default: Any = None  # None is invalid ... reconsider?

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Enum(
            choices=frozenset.union(*[o.schema_choices for o in self.options]),
            default=self.default,
        )

    # override
    @classmethod
    def _from_kwargs(
        cls, *, options: List[Dict[str, str]] = None, default: Any = None, **kwargs
    ):
        options = [MenuOption._from_dict(option) for option in options]
        if default is None:
            # TODO consider allowing None instead of forcing a default? Menus
            # could have a "placeholder"
            default = options[0].value
        return cls(options=options, default=default, **kwargs)


ParamFieldMenu.Option = MenuOption  # type
ParamFieldMenu.Option.Value = MenuOptionEnum  # class
ParamFieldMenu.Option.Separator = MenuOptionSeparator  # singleton


@_register_type("radio")
@dataclass(frozen=True)
class ParamFieldRadio(_HasName, ParamField):
    """Enum values which are all visible at the same time."""

    options: List[EnumOption] = NotImplementedError
    """Enumeration options. All are visible at once."""

    default: Any = None  # None is an invalid default -- this is a radio

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Enum(
            choices=frozenset.union(*[o.schema_choices for o in self.options]),
            default=self.default,
        )

    # override
    @classmethod
    def _from_kwargs(
        cls, *, options: List[Dict[str, str]], default: Any = None, **kwargs
    ):
        options = [EnumOption(**option) for option in options]
        if default is None:
            default = options[0].value
        return cls(options=options, default=default, **kwargs)


ParamFieldRadio.Option = EnumOption


@_register_type("tab")
@dataclass(frozen=True)
class ParamFieldTab(_HasPlaceholder, _HasName, ParamField):
    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Tab()


@_register_type("multitab")
@dataclass(frozen=True)
class ParamFieldMultitab(_HasPlaceholder, _HasName, ParamField):
    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Multitab()


@_register_type("file")
@dataclass(frozen=True)
class ParamFieldFile(ParamField):
    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.File()


@_register_type("list")
@dataclass(frozen=True)
class ParamFieldList(_HasName, ParamField):
    child_parameters: List[ParamField] = NotImplementedError

    # override
    @classmethod
    def _from_kwargs(
        cls, *, child_parameters: List[Dict[str, Any]], **kwargs
    ) -> ParamFieldList:
        # Parse child parameters recursively
        child_parameters = [ParamField.from_dict(cp) for cp in child_parameters]
        return cls(child_parameters=child_parameters, **kwargs)

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        child_schemas = {
            cp.id_name: cp.to_schema()
            for cp in self.child_parameters
            if cp.to_schema() is not None
        }
        return ParamSchema.List(ParamSchema.Dict(child_schemas))


@_register_type("gdrivefile")
@dataclass(frozen=True)
class ParamFieldGdrivefile(_HasName, ParamField):
    secret_parameter: str = ""
    """id_name of the `secret` parameter this chooser will use."""

    # override
    def to_schema(self) -> Optional[ParamSchema]:
        return ParamSchema.Option(
            ParamSchema.Dict(
                {
                    "id": ParamSchema.String(),
                    "name": ParamSchema.String(),
                    "url": ParamSchema.String(),
                    "mimeType": ParamSchema.String(),
                }
            )
        )
