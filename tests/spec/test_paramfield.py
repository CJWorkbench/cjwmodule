from cjwmodule.spec.paramfield import ParamField
from cjwmodule.spec.paramschema import ParamSchema


def test_checkbox_default_false():
    param_spec = ParamField.from_dict(dict(id_name="b", type="checkbox", name="hi"))
    assert param_spec.default is False


def test_bool_radio_default_false():
    # Handle odd edge case seen on production:
    #
    # If enum options are booleans and the first is True, and the _default_
    # is False, don't overwrite the default.
    param_spec = ParamField.from_dict(
        dict(
            id_name="r",
            type="radio",
            options=[
                {"value": True, "label": "First"},
                {"value": False, "label": "Second"},
            ],
            default=False,  # a valid option
        )
    )
    assert param_spec.to_schema().default is False


def test_list_schema():
    # Check that ParamField's with List type produce correct nested DTypes
    param_spec = ParamField.from_dict(
        dict(
            id_name="p",
            type="list",
            child_parameters=[
                {"id_name": "intparam", "type": "integer", "name": "my number"},
                {"id_name": "colparam", "type": "column", "name": "my column"},
            ],
        )
    )
    assert param_spec == ParamField.List(
        id_name="p",
        child_parameters=[
            ParamField.Integer(id_name="intparam", name="my number"),
            ParamField.Column(id_name="colparam", name="my column"),
        ],
    )

    assert param_spec.to_schema() == ParamSchema.List(
        ParamSchema.Dict(
            {"intparam": ParamSchema.Integer(), "colparam": ParamSchema.Column()}
        )
    )


def test_list_schema_with_falsy_params():
    # Bug on 2021-04-21: a ParamSchema.Condition() evaluates to False (it is
    # an empty tuple), but it should still appear in the condition list.
    field = ParamField.List(
        id_name="p",
        child_parameters=[
            ParamField.Condition(id_name="cond"),
            ParamField.Statictext(id_name="static", name="Static"),
        ],
    )
    assert field.to_schema() == ParamSchema.List(
        ParamSchema.Dict({"cond": ParamSchema.Condition()})
    )


def test_parse_menu_options():
    param_spec = ParamField.from_dict(
        dict(
            type="menu",
            id_name="id",
            name="name",
            options=[
                {"value": True, "label": "t"},
                "separator",
                {"value": False, "label": "f"},
            ],
        )
    )
    assert param_spec == ParamField.Menu(
        id_name="id",
        name="name",
        default=True,  # Menu value can't be null. TODO reconsider?
        options=[
            ParamField.Menu.Option.Value("t", True),
            ParamField.Menu.Option.Separator,
            ParamField.Menu.Option.Value("f", False),
        ],
    )


def test_parse_radio_options():
    param_spec = ParamField.from_dict(
        dict(
            type="radio",
            id_name="id",
            name="name",
            options=[{"value": True, "label": "t"}, {"value": False, "label": "f"}],
        )
    )
    assert param_spec == ParamField.Radio(
        id_name="id",
        name="name",
        options=[
            ParamField.Radio.Option("t", True),
            ParamField.Radio.Option("f", False),
        ],
        default=True,
    )


def test_column_column_types():
    param_spec = ParamField.from_dict(
        dict(id_name="c", type="column", column_types=["text", "number"])
    )
    assert param_spec.column_types == ["text", "number"]
    assert param_spec.to_schema().column_types == frozenset(["text", "number"])


def test_multicolumn_column_types():
    param_spec = ParamField.from_dict(
        dict(id_name="c", type="multicolumn", column_types=["text", "number"])
    )
    assert param_spec.column_types == ["text", "number"]
    assert param_spec.to_schema().column_types == frozenset(["text", "number"])


def test_timestamp_type():
    param_spec = ParamField.from_dict(
        dict(id_name="tz", name="Timezone", type="timezone")
    )
    assert param_spec == ParamField.Timezone(id_name="tz", name="Timezone")
    assert param_spec.to_schema() == ParamSchema.Timezone()
