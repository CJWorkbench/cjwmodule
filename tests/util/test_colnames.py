from cjwmodule.util.colnames import (
    CleanColname,
    Settings,
    UniqueCleanColname,
    clean_colname,
    gen_unique_clean_colnames,
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


def test_clean_truncate():
    assert clean_colname("acé", settings=MockSettings(3)) == CleanColname(
        "ac", is_truncated=True
    )


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
