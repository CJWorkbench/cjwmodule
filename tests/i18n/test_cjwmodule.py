from cjwmodule import i18n
from cjwmodule.i18n.cjwmodule import trans


def test_trans_happy_path():
    assert trans(
        "errors.allNull",
        "The column “{column}” must contain non-null values.",
        {"column": "A"},
    ) == i18n.I18nMessage(
        "errors.allNull", 
        {"column": "A"}, 
        "cjwmodule"
    )
