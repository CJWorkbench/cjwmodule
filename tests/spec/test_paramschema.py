import pytest

from cjwmodule.spec.paramschema import ParamSchema as S


class TestBoolean:
    def test_default_false(self):
        assert S.Boolean().default is False

    def test_validate_ok(self):
        S.Boolean().validate(False)
        S.Boolean().validate(True)

    def test_validate_bad(self):
        with pytest.raises(ValueError):
            S.Boolean().validate(None)


class TestString:
    def test_validate_emoji(self):
        S.String().validate("💩")  # do not raise

    def test_validate_non_str(self):
        with pytest.raises(ValueError):
            S.String().validate(23)

    def test_validate_lone_surrogate(self):
        with pytest.raises(ValueError):
            S.String().validate("A\ud802B")

    def test_validate_zero_byte(self):
        with pytest.raises(ValueError):
            S.String().validate("A\x00B")


class TestFloat:
    def test_validate_int(self):
        S.Float().validate(10)  # do not raise


class TestFile:
    def test_validate_null(self):
        S.File().validate(None)  # do not raise

    def test_validate_uuid(self):
        S.File().validate("1e3a5177-ee1a-4832-bfbb-6480b93984ab")  # do not raise

    def test_validate_invalid_str(self):
        with pytest.raises(ValueError):
            # one character too many
            S.File().validate("f13aa5177-ee1a-4832-bfbb-6480b93984ab")

    def test_validate_non_str(self):
        with pytest.raises(ValueError):
            S.File().validate(0x13A5177)


class TestTimezone:
    def test_default(self):
        assert S.Timezone().default == "UTC"

    def test_validate_ok(self):
        S.Timezone().validate("America/Montreal")  # no error

    def test_validate_value_error(self):
        with pytest.raises(ValueError):
            S.Timezone().validate("America/NotMontreal")


class TestColumn:
    def test_default(self):
        # TODO consider changing this to None. [2021-04-20, adamhooper] I think
        # most/all modules would be compatible.
        assert S.Column().default == ""

    def test_validate_ok(self):
        S.Column().validate("A")

    def test_validate_not_string(self):
        with pytest.raises(ValueError, match="not a string"):
            S.Column().validate(3)


class TestTab:
    def test_default(self):
        # TODO consider changing this to None. [2021-04-20, adamhooper] I think
        # most/all modules would be compatible.
        assert S.Tab().default == ""

    def test_validate_ok(self):
        S.Tab().validate("tab-1")

    def test_validate_not_string(self):
        with pytest.raises(ValueError, match="not a string"):
            S.Tab().validate(3)


class TestMulticolumn:
    def test_default(self):
        assert S.Multicolumn().default == []

    def test_validate_list_of_str_ok(self):
        S.Multicolumn().validate(["x", "y"]),

    def test_validate_list_of_non_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multicolumn().validate([1, 2])

    def test_validate_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multicolumn().validate("X,Y")

    def test_validate_empty_column_is_error(self):
        with pytest.raises(ValueError, match="Empty column not allowed"):
            S.Multicolumn().validate([""])


class TestMultitab:
    def test_default(self):
        assert S.Multitab().default == []

    def test_validate_list_of_str_ok(self):
        S.Multitab().validate(["tab-1", "tab-2"]),

    def test_validate_list_of_non_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multitab().validate([1, 2])

    def test_validate_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multitab().validate("X,Y")

    def test_validate_empty_tab_is_error(self):
        with pytest.raises(ValueError, match="Empty tab not allowed"):
            S.Multitab().validate([""])


class TestOption:
    def test_validate_inner_ok(self):
        S.Option(S.String()).validate("foo")

    def test_validate_inner_error(self):
        with pytest.raises(ValueError):
            S.Option(S.String()).validate(3)

    def test_default(self):
        # [2019-06-05] We don't support non-None default on Option params
        assert S.Option(S.String(default="x")).default is None


class TestMap:
    def test_default(self):
        assert S.Map(S.String()).default == {}

    def test_validate_ok(self):
        schema = S.Map(value_schema=S.String())
        value = {"a": "b", "c": "d"}
        schema.validate(value)

    def test_validate_bad_inner_schema(self):
        with pytest.raises(ValueError, match="not a string"):
            S.Map(value_schema=S.String()).validate({"a": "1", "c": 2})

    def test_validate_not_dict(self):
        with pytest.raises(ValueError, match="not a dict"):
            S.Map(value_schema=S.String()).validate([])


class TestCondition:
    def test_default(self):
        assert S.Condition().default == {"operation": "and", "conditions": []}

    def test_validate_non_dict(self):
        with pytest.raises(ValueError):
            S.Condition().validate([])

    def test_validate_missing_operation(self):
        with pytest.raises(ValueError):
            S.Condition().validate({"condition": []})

    def test_validate_missing_conditions(self):
        with pytest.raises(ValueError):
            S.Condition().validate({"operation": "and", "condition": []})

    def test_validate_conditions_not_list(self):
        with pytest.raises(ValueError):
            S.Condition().validate({"operation": "and", "conditions": "hi"})

    def test_validate_and_with_extra_property(self):
        with pytest.raises(ValueError):
            S.Condition().validate({"operation": "and", "conditions": [], "foo": "bar"})

    def test_validate_not_2_levels(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        # level 0
        with pytest.raises(ValueError):
            S.Condition().validate(comparison)

        # level 1
        with pytest.raises(ValueError):
            S.Condition().validate({"operation": "and", "conditions": [comparison]})

        # level 2 is okay
        S.Condition().validate(
            {
                "operation": "and",
                "conditions": [{"operation": "or", "conditions": [comparison]}],
            }
        )

        # level 3
        with pytest.raises(ValueError):
            S.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": "or",
                            "conditions": [
                                {"operation": "and", "conditions": [comparison]}
                            ],
                        }
                    ],
                }
            )

    def test_validate_no_such_operation(self):
        comparison = {
            "operation": "text_is_blargy",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        with pytest.raises(ValueError):
            S.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_empty_operation_is_okay(self):
        # The UI lets users select nothing. We can't stop them.
        comparison = {
            "operation": "",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        S.Condition().validate(
            {
                "operation": "and",
                "conditions": [{"operation": "or", "conditions": [comparison]}],
            }
        )

    def test_validate_missing_key(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
        }

        with pytest.raises(ValueError):
            S.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_extra_key(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": True,
            "isSomethingElse": False,
        }

        with pytest.raises(ValueError):
            S.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_condition_value_wrong_type(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": 312,
            "isCaseSensitive": True,
            "isRegex": False,
        }

        with pytest.raises(ValueError):
            S.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )


class TestMultiChartSeries:
    def test_default(self):
        assert S.Multichartseries().default == []

    def test_validate_empty(self):
        S.Multichartseries().validate([])

    def test_validate_ok(self):
        S.Multichartseries().validate(
            [
                dict(column="A", color="#aaaaaa"),
                dict(column="B", color="#bbbbbb"),
            ]
        )

    def test_validate_empty_column_bad(self):
        with pytest.raises(ValueError, match="column must be non-empty"):
            S.Multichartseries().validate([dict(column="", color="#000000")])

    def test_validate_not_list(self):
        with pytest.raises(ValueError, match="not a list"):
            S.Multichartseries().validate(dict(column="A", color="#aaaaaa"))


class TestEnum:
    def test_validate_ok(self):
        S.Enum(choices=frozenset(["foo", "bar"]), default="foo").validate("bar")

    def test_validate_not_ok(self):
        with pytest.raises(ValueError, match="not in choices"):
            S.Enum(choices=frozenset(["foo", "bar"]), default="foo").validate("baz")


class TestDict:
    def test_default(self):
        assert S.Dict(
            {"foo": S.String(default="FOO"), "bar": S.Integer(default=3)}
        ).default == {"foo": "FOO", "bar": 3}

    def test_validate_ok(self):
        S.Dict({"foo": S.String(default="FOO"), "bar": S.Integer(default=3)}).validate(
            {"foo": "FOO", "bar": 3}
        )

    def test_validate_not_dict(self):
        with pytest.raises(ValueError, match="not a dict"):
            S.Dict({"foo": S.String()}).validate([])

    def test_validate_missing_key(self):
        with pytest.raises(ValueError, match="wrong keys"):
            S.Dict({"foo": S.String(), "bar": S.String()}).validate({"foo": "x"})

    def test_validate_extra_key(self):
        with pytest.raises(ValueError, match="wrong keys"):
            S.Dict({"foo": S.String()}).validate({"foo": "x", "bar": "y"})

    def test_validate_invalid_child(self):
        with pytest.raises(ValueError, match="not a string"):
            S.Dict({"foo": S.String()}).validate({"foo": 3})
