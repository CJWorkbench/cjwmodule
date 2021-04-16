import pytest

from cjwmodule.spec.paramschema import ParamSchema as S


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
    def test_validate_ok(self):
        S.Timezone().validate("America/Montreal")  # no error

    def test_validate_value_error(self):
        with pytest.raises(ValueError):
            S.Timezone().validate("America/NotMontreal")


class TestMulticolumn:
    def test_multicolumn_default(self):
        assert S.Multicolumn().default == []

    def test_multicolumn_validate_list_of_str_ok(self):
        S.Multicolumn().validate(["x", "y"]),

    def test_multicolumn_validate_list_of_non_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multicolumn().validate([1, 2])

    def test_multicolumn_validate_str_is_error(self):
        with pytest.raises(ValueError):
            S.Multicolumn().validate("X,Y")


class TestOption:
    def test_option_validate_inner_ok(self):
        S.Option(S.String()).validate("foo")

    def test_option_validate_inner_error(self):
        with pytest.raises(ValueError):
            S.Option(S.String()).validate(3)

    def test_option_default_none(self):
        # [2019-06-05] We don't support non-None default on Option params
        assert S.Option(S.String(default="x")).default is None


class TestMap:
    def test_map_validate_ok(self):
        schema = S.Map(value_schema=S.String())
        value = {"a": "b", "c": "d"}
        schema.validate(value)

    def test_map_validate_bad_inner_schema(self):
        schema = S.Map(value_schema=S.String())
        value = {"a": 1, "c": 2}
        with pytest.raises(ValueError):
            schema.validate(value)


class TestCondition:
    def test_default(self):
        assert S.Condition().default == {"operation": "and", "conditions": []}

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
