from cjwmodule.spec.paramschema import ParamSchema
from cjwmodule.spec.paramschemaparser import parse


def test_dict_recurse():
    assert parse(
        {"type": "dict", "properties": {"x": {"type": "string"}}}
    ) == ParamSchema.Dict(properties={"x": ParamSchema.String()})


def test_list_recurse():
    assert parse(
        {"type": "list", "inner_dtype": {"type": "string"}}
    ) == ParamSchema.List(ParamSchema.String())


def test_map_recurse():
    assert parse({"type": "map", "value_dtype": {"type": "string"}}) == ParamSchema.Map(
        value_schema=ParamSchema.String()
    )


def test_column_column_types_is_frozenset():
    assert parse(
        {"type": "column", "column_types": ["timestamp", "number"]}
    ) == ParamSchema.Column(column_types=frozenset(["timestamp", "number"]))


def test_multicolumn_column_types_is_frozenset():
    assert parse(
        {"type": "multicolumn", "column_types": ["timestamp", "number"]}
    ) == ParamSchema.Multicolumn(column_types=frozenset(["timestamp", "number"]))
