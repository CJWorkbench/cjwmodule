from cjwmodule import i18n


def test_trans_happy_path():
    assert i18n.trans(
        "errors.allNull",
        "The column “{column}” must contain non-null values.",
        {"column": "A"},
    ) == i18n.I18nMessage(
        "errors.allNull", 
        {"column": "A"}, 
        "module"
    )

def test_trans_cjwmodule():
    assert i18n._trans_cjwmodule(
        "errors.allNull",
        "The column “{column}” must contain non-null values.",
        {"column": "A"},
    ) == i18n.I18nMessage(
        "errors.allNull", 
        {"column": "A"}, 
        "cjwmodule"
    )
