import pytest

from cjwmodule.spec.loader import load_spec
from cjwmodule.spec.paramschema import ParamSchema


def test_schema_errors():
    with pytest.raises(
        ValueError,
        match=r"'id_name' is a required property.*'category' is a required property.*'not a link at all' is not a 'uri'.*'NotABoolean' is not of type 'boolean'",
    ):
        load_spec(
            {
                "name": "Hello",
                "link": "not a link at all",
                "loads_data": "NotABoolean",
                "parameters": [],
            }
        )


def test_unique_params():
    with pytest.raises(ValueError, match="Param 'dup' appears twice"):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {"id_name": "dup", "type": "string"},
                    {"id_name": "original", "type": "string"},
                    {"id_name": "dup", "type": "string"},
                ],
            }
        )


def test_missing_menu_options():
    with pytest.raises(ValueError):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [{"id_name": "menu", "type": "menu"}],
            }
        )


def test_missing_radio_options():
    with pytest.raises(ValueError):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [{"id_name": "radio", "type": "radio"}],
            }
        )


def test_invalid_visible_if():
    with pytest.raises(
        ValueError, match="Param 'a' has visible_if id_name 'b', which does not exist"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "string",
                        "visible_if": {"id_name": "b", "value": True},
                    }
                ],
            }
        )


def test_valid_visible_if():
    # does not raise
    spec = load_spec(
        {
            "id_name": "id",
            "name": "Name",
            "category": "Clean",
            "parameters": [
                {
                    "id_name": "a",
                    "type": "string",
                    "visible_if": {"id_name": "b", "value": True},
                },
                {"id_name": "b", "type": "string"},
            ],
        }
    )
    assert spec.param_fields[0].visible_if == {"id_name": "b", "value": True}


def test_valid_visible_if_menu_options():
    # does not raise
    load_spec(
        {
            "id_name": "id",
            "name": "Name",
            "category": "Clean",
            "parameters": [
                {
                    "id_name": "a",
                    "type": "string",
                    "visible_if": {"id_name": "b", "value": ["a", "b"]},
                },
                {
                    "id_name": "b",
                    "type": "menu",
                    "options": [
                        {"value": "a", "label": "A"},
                        "separator",
                        {"value": "b", "label": "B"},
                        {"value": "c", "label": "C"},
                    ],
                },
            ],
        }
    )


def test_invalid_visible_if_menu_options():
    with pytest.raises(
        ValueError, match=r"Param 'a' has visible_if values \{'x'\} not in 'b' options"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "string",
                        "visible_if": {"id_name": "b", "value": ["a", "x"]},
                    },
                    {
                        "id_name": "b",
                        "type": "menu",
                        "options": [
                            {"value": "a", "label": "A"},
                            {"value": "c", "label": "C"},
                        ],
                    },
                ],
            }
        )


def test_multicolumn_missing_tab_parameter():
    with pytest.raises(
        ValueError, match="Param 'a' has a 'tab_parameter' that is not in 'parameters'"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "column",
                        "tab_parameter": "b",  # does not exist
                    }
                ],
            }
        )


def test_multicolumn_non_tab_parameter():
    with pytest.raises(
        ValueError, match="Param 'a' has a 'tab_parameter' that is not a 'tab'"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {"id_name": "a", "type": "column", "tab_parameter": "b"},
                    {"id_name": "b", "type": "string"},  # Not a 'tab'
                ],
            }
        )


def test_multicolumn_tab_parameter():
    # does not raise
    load_spec(
        {
            "id_name": "id",
            "name": "Name",
            "category": "Clean",
            "parameters": [
                {"id_name": "a", "type": "column", "tab_parameter": "b"},
                {"id_name": "b", "type": "tab"},
            ],
        }
    )


def test_validate_menu_with_default():
    # does not raise
    load_spec(
        {
            "id_name": "id",
            "name": "Name",
            "category": "Clean",
            "parameters": [
                {
                    "id_name": "a",
                    "type": "menu",
                    "placeholder": "Select something",
                    "options": [
                        {"value": "x", "label": "X"},
                        "separator",
                        {"value": "y", "label": "Y"},
                        {"value": "z", "label": "Z"},
                    ],
                    "default": "y",
                }
            ],
        }
    )


def test_validate_menu_invalid_default():
    with pytest.raises(
        ValueError, match="Param 'a' has a 'default' that is not in its 'options'"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "menu",
                        "options": [{"value": "x", "label": "X"}],
                        "default": "y",
                    },
                    {
                        # Previously, we gave the wrong id_name
                        "id_name": "not-a",
                        "type": "string",
                    },
                ],
            }
        )


def test_validate_gdrivefile_missing_secret():
    with pytest.raises(
        ValueError, match="Param 'b' has a 'secret_parameter' that is not a 'secret'"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {"id_name": "b", "type": "gdrivefile", "secret_parameter": "a"}
                ],
            }
        )


def test_validate_gdrivefile_non_secret_secret():
    with pytest.raises(
        ValueError, match="Param 'b' has a 'secret_parameter' that is not a 'secret'"
    ):
        load_spec(
            {
                "id_name": "id",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {"id_name": "a", "type": "string"},
                    {"id_name": "b", "type": "gdrivefile", "secret_parameter": "a"},
                ],
            }
        )


def test_validate_gdrivefile_invalid_secret():
    with pytest.raises(
        ValueError, match="Param 'b' 'secret_parameter' does not refer to a 'google'"
    ):
        load_spec(
            {
                "id_name": "twitter",  # only twitter is allowed a twitter secret
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "twitter_credentials",
                        "type": "secret",
                        "secret_logic": {
                            "provider": "oauth1a",
                            "service": "twitter",
                        },
                    },
                    {
                        "id_name": "b",
                        "type": "gdrivefile",
                        "secret_parameter": "twitter_credentials",
                    },
                ],
            }
        )


def test_validate_allow_secret_based_on_module_id_name():
    load_spec(
        {
            "id_name": "twitter",
            "name": "Name",
            "category": "Clean",
            "parameters": [
                {
                    "id_name": "a",
                    "type": "secret",
                    "secret_logic": {"provider": "oauth1a", "service": "twitter"},
                }
            ],
        }
    )


def test_validate_disallow_secret_based_on_module_id_name():
    with pytest.raises(ValueError, match="Denied access to global 'twitter' secrets"):
        load_spec(
            {
                "id_name": "eviltwitter",
                "name": "Name",
                "category": "Clean",
                "parameters": [
                    {
                        "id_name": "a",
                        "type": "secret",
                        "secret_logic": {
                            "provider": "oauth1a",
                            "service": "twitter",
                        },
                    }
                ],
            }
        )


def test_uses_data_default_true_if_loads_data_false():
    spec = load_spec(
        dict(
            id_name="id_name",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=False,
        )
    )
    assert spec.uses_data


def test_uses_data_default_false_if_loads_data_true():
    spec = load_spec(
        dict(
            id_name="id_name",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=True,
        )
    )
    assert not spec.uses_data


def test_uses_data_override():
    spec = load_spec(
        dict(
            id_name="id_name",
            name="Name",
            category="Add data",
            parameters=[],
            loads_data=True,
            uses_data=True,
        )
    )
    assert spec.uses_data


def test_param_schema_implicit():
    spec = load_spec(
        dict(
            id_name="googlesheets",
            name="x",
            category="Clean",
            parameters=[
                {"id_name": "foo", "type": "string", "default": "X"},
                {
                    "id_name": "bar",
                    "type": "secret",
                    "secret_logic": {"provider": "oauth2", "service": "google"},
                },
                {
                    "id_name": "baz",
                    "type": "menu",
                    "options": [
                        {"value": "a", "label": "A"},
                        "separator",
                        {"value": "c", "label": "C"},
                    ],
                    "default": "c",
                },
            ],
        )
    )

    assert spec.param_schema == ParamSchema.Dict(
        {
            "foo": ParamSchema.String(default="X"),
            # secret is not in param_schema
            "baz": ParamSchema.Enum(choices=frozenset({"a", "c"}), default="c"),
        }
    )


def test_param_schema_explicit():
    spec = load_spec(
        dict(
            id_name="x",
            name="x",
            category="Clean",
            parameters=[{"id_name": "whee", "type": "custom"}],
            param_schema={
                "id_name": {
                    "type": "dict",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "string", "default": "X"},
                    },
                }
            },
        )
    )

    assert spec.param_schema == ParamSchema.Dict(
        {
            "id_name": ParamSchema.Dict(
                {"x": ParamSchema.Integer(), "y": ParamSchema.String(default="X")}
            )
        }
    )
