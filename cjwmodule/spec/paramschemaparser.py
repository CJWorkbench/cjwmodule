from typing import Any, Dict

from .paramschema import ParamSchema

# [2021-04-16] mypy can't recurse: https://github.com/python/mypy/issues/731
Jsonish = Any


_Types = {
    "boolean": ParamSchema.Boolean,
    "column": ParamSchema.Column,
    "condition": ParamSchema.Condition,
    "dict": ParamSchema.Dict,
    "enum": ParamSchema.Enum,
    "file": ParamSchema.File,
    "float": ParamSchema.Float,
    "integer": ParamSchema.Integer,
    "list": ParamSchema.List,
    "map": ParamSchema.Map,
    "multichartseries": ParamSchema.Multichartseries,
    "multicolumn": ParamSchema.Multicolumn,
    "option": ParamSchema.Option,
    "string": ParamSchema.String,
    "tab": ParamSchema.Tab,
    "tabs": ParamSchema.Multitab,
    "timezone": ParamSchema.Timezone,
}


def _parse_kwargs(type: str, **kwargs) -> ParamSchema:
    cls = _Types[type]

    if cls == ParamSchema.Option or cls == ParamSchema.List:
        kwargs["inner_schema"] = parse(kwargs.pop("inner_dtype"))
    elif cls == ParamSchema.Column or cls == ParamSchema.Multicolumn:
        # column_types comes from JSON as a list. We need a set.
        if "column_types" in kwargs:
            kwargs["column_types"] = frozenset(kwargs["column_types"])
    elif cls == ParamSchema.Enum:
        kwargs["choices"] = frozenset(kwargs["choices"])
        if kwargs["default"] not in kwargs["choices"]:
            raise ValueError(
                "Default %(default)r is not in choices %(choices)r" % kwargs
            )
    elif cls == ParamSchema.Dict:
        kwargs["properties"] = {k: parse(v) for k, v in kwargs["properties"].items()}
    elif cls == ParamSchema.Map:
        kwargs["value_schema"] = parse(kwargs.pop("value_dtype"))

    return cls(**kwargs)


def parse(json_value: Dict[str, Jsonish]) -> ParamSchema:
    """Utility to deserialize a ParamSchema from JSON.

    Currently, we only JSON-serialize when the module specification has an
    explicit `param_schema`. This is rare, and [2021-04-12] we want to remove
    this feature entirely. TODO when `param_schema` is gone, nix this class.

    This feature is for compatibility with old modules; and so it parses weird
    stuff. For example, it parses `{"type": "map", "value_dtype": ...}` because
    that's the old terminology that has made it into old modules. TODO nix this
    function, and then the old "dtype" terminology will be gone.
    """
    return _parse_kwargs(**json_value)
