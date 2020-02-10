from cjwmodule.testing.i18n import cjwmodule_i18n_message
from cjwmodule.util.colnames import (
    CleanColname,
    Settings,
    UniqueCleanColname,
    clean_colname,
    gen_unique_clean_colnames,
    gen_unique_clean_colnames_and_warn,
)


class MockSettings(Settings):
    def __init__(self, max_bytes_per_column_name: int):
        self.MAX_BYTES_PER_COLUMN_NAME = max_bytes_per_column_name


def test_clean_empty_str():
    assert clean_colname("") == CleanColname("")


def test_clean_ascii_control_characters():
    assert clean_colname("ab\0\n\tcd") == CleanColname("abcd", is_ascii_cleaned=True)


def test_clean_fix_unicode():
    assert clean_colname("ab\ud800\udc00cd") == CleanColname(
        "ab��cd", is_unicode_fixed=True
    )


def test_clean_truncate_nix_partial_unicode_character():
    assert clean_colname("acé", settings=MockSettings(3)) == CleanColname(
        "ac", is_truncated=True
    )


def test_clean_truncate_allow_full_unicode_character():
    assert clean_colname("acé", settings=MockSettings(4)) == CleanColname("acé")


def test_clean_ascii_before_truncate():
    assert clean_colname("ab\n\ncd", settings=MockSettings(3)) == CleanColname(
        "abc", is_ascii_cleaned=True, is_truncated=True
    )


def test_clean_fix_unicode_before_truncate():
    # [adamhooper, 2019-12-13] I don't think we can actually test this in pure
    # Python. We'd need a string that has invalid UTF-8 encoding, and I don't
    # know how to generate one. The only thing I know how to generate is
    # invalid _Unicode_ with surrogate pairs ... but the replacement character
    # happens to have the same number of bytes as an erroneous surrogate.
    #
    # Oh well. Test that we can actually generate is_unicode_fixed+is_truncated,
    # at least.
    assert clean_colname("\ud800abcd", settings=MockSettings(4)) == CleanColname(
        "�a", is_unicode_fixed=True, is_truncated=True
    )


def test_gen_calls_clean():
    assert gen_unique_clean_colnames(["ab\n\ud800cd"], settings=MockSettings(6)) == [
        UniqueCleanColname(
            "ab�c", is_ascii_cleaned=True, is_unicode_fixed=True, is_truncated=True
        )
    ]


def test_gen_number_1_is_unique():
    assert gen_unique_clean_colnames(["A", "A 1", "A 2"]) == [
        UniqueCleanColname("A"),
        UniqueCleanColname("A 1"),
        UniqueCleanColname("A 2"),
    ]


def test_gen_add_number():
    assert gen_unique_clean_colnames(["A", "A", "A"]) == [
        UniqueCleanColname("A"),
        UniqueCleanColname("A 2", is_numbered=True),
        UniqueCleanColname("A 3", is_numbered=True),
    ]


def test_gen_add_number_that_does_not_overwrite_existing_number():
    assert gen_unique_clean_colnames(["A", "A", "A 2"]) == [
        UniqueCleanColname("A"),
        UniqueCleanColname("A 3", is_numbered=True),
        UniqueCleanColname("A 2"),
    ]


def test_gen_name_default_columns():
    assert gen_unique_clean_colnames(["", ""]) == [
        UniqueCleanColname("Column 1", is_default=True),
        UniqueCleanColname("Column 2", is_default=True),
    ]


def test_gen_name_default_columns_without_conflict():
    assert gen_unique_clean_colnames(["Column 2", "", ""]) == [
        UniqueCleanColname("Column 2"),
        UniqueCleanColname("Column 4", is_default=True, is_numbered=True),
        UniqueCleanColname("Column 3", is_default=True),  # this 3 is "reserved"
    ]


def test_gen_avoid_existing_names():
    assert gen_unique_clean_colnames(
        ["", "foo"], existing_names=["Column 3", "foo"]
    ) == [
        UniqueCleanColname("Column 4", is_default=True, is_numbered=True),
        UniqueCleanColname("foo 2", is_numbered=True),
    ]


def test_gen_truncate_during_conflict():
    assert gen_unique_clean_colnames(
        [
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "a 100",
        ],
        settings=MockSettings(4),
    ) == [
        UniqueCleanColname("abcd"),
        UniqueCleanColname("ab 2", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 3", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 4", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 5", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 6", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 7", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 8", is_numbered=True, is_truncated=True),
        UniqueCleanColname("ab 9", is_numbered=True, is_truncated=True),
        UniqueCleanColname("a 11", is_numbered=True, is_truncated=True),
        UniqueCleanColname("a 10", is_truncated=True),  # was "a 100"
    ]


def test_gen_truncate_during_conflict_consider_unicode():
    assert gen_unique_clean_colnames(["aéé"] * 10, settings=MockSettings(5)) == [
        UniqueCleanColname("aéé"),
        UniqueCleanColname("aé 2", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 3", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 4", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 5", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 6", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 7", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 8", is_numbered=True, is_truncated=True),
        UniqueCleanColname("aé 9", is_numbered=True, is_truncated=True),
        UniqueCleanColname("a 10", is_numbered=True, is_truncated=True),
    ]


def test_gen_and_warn_calls_clean():
    assert gen_unique_clean_colnames_and_warn(
        ["ab\n\ud800cd"], settings=MockSettings(6)
    ) == (
        ["ab�c"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.removedSpecialCharactersFromColumnNames",
                {"n_columns": 1, "column_name": "ab�c"},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.truncatedColumnNames",
                {"n_columns": 1, "column_name": "ab�c", "n_bytes": 6},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 1, "column_name": "ab�c"},
            ),
        ],
    )


def test_gen_and_warn_number_1_is_unique():
    assert gen_unique_clean_colnames_and_warn(["A", "A 1", "A 2"]) == (
        ["A", "A 1", "A 2"],
        [],
    )


def test_gen_and_warn_add_number():
    assert gen_unique_clean_colnames_and_warn(["A", "A", "A"]) == (
        ["A", "A 2", "A 3"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 2, "column_name": "A 2"},
            ),
        ],
    )


def test_gen_and_warn_add_number_that_does_not_overwrite_existing_number():
    assert gen_unique_clean_colnames_and_warn(["A", "A", "A 2"]) == (
        ["A", "A 3", "A 2"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 1, "column_name": "A 3"},
            ),
        ],
    )


def test_gen_and_warn_name_default_columns():
    assert gen_unique_clean_colnames_and_warn(["", ""]) == (
        ["Column 1", "Column 2"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedEmptyColumnNames",
                {"n_columns": 2, "column_name": "Column 1"},
            ),
        ],
    )


def test_gen_and_warn_name_default_columns_without_conflict():
    assert gen_unique_clean_colnames_and_warn(["Column 2", "", ""]) == (
        ["Column 2", "Column 4", "Column 3"],  # this 3 is "reserved"
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedEmptyColumnNames",
                {"n_columns": 2, "column_name": "Column 4"},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 1, "column_name": "Column 4"},
            ),
        ],
    )


def test_gen_and_warn_avoid_existing_names():
    assert gen_unique_clean_colnames_and_warn(
        ["", "foo"], existing_names=["Column 3", "foo"]
    ) == (
        ["Column 4", "foo 2"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedEmptyColumnNames",
                {"n_columns": 1, "column_name": "Column 4"},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 2, "column_name": "Column 4"},
            ),
        ],
    )


def test_gen_and_warn_truncate_during_conflict():
    assert gen_unique_clean_colnames_and_warn(
        [
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "abcd",
            "a 100",
        ],
        settings=MockSettings(4),
    ) == (
        [
            "abcd",
            "ab 2",
            "ab 3",
            "ab 4",
            "ab 5",
            "ab 6",
            "ab 7",
            "ab 8",
            "ab 9",
            "a 11",
            "a 10",  # was "a 100"
        ],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.truncatedColumnNames",
                {"n_columns": 10, "column_name": "ab 2", "n_bytes": 4},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 9, "column_name": "ab 2"},
            ),
        ],
    )


def test_gen_and_warn_truncate_during_conflict_consider_unicode():
    assert gen_unique_clean_colnames_and_warn(
        ["aéé"] * 10, settings=MockSettings(5)
    ) == (
        ["aéé", "aé 2", "aé 3", "aé 4", "aé 5", "aé 6", "aé 7", "aé 8", "aé 9", "a 10"],
        [
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.truncatedColumnNames",
                {"n_columns": 9, "column_name": "aé 2", "n_bytes": 5},
            ),
            cjwmodule_i18n_message(
                "util.colnames.gen_unique_clean_colnames.warnings.renamedDuplicateColumnNames",
                {"n_columns": 9, "column_name": "aé 2"},
            ),
        ],
    )
