import re
from dataclasses import dataclass
from typing import List, Optional, Protocol, Tuple

from cjwmodule.i18n import I18nMessage, _trans_cjwmodule


class Settings(Protocol):
    MAX_BYTES_PER_COLUMN_NAME: int = 100


class DefaultSettings(Settings):
    pass


@dataclass(frozen=True)
class CleanColname:
    """
    A column name (or ""), plus information about its provenance.

    This column name is either the empty string, or it's safe to insert into a
    table that does not contain this column name already.
    """

    name: str
    """
    Column name, valid as per `clean_colname`.
    """

    is_ascii_cleaned: bool = False
    """
    If True, the input column had ASCII control characters and we removed them.

    For example: "line 1line 2" (instead of "line 1\nline 2")
    """

    is_unicode_fixed: bool = False
    """
    If True, the column name had invalid Unicode surrogate pairs.

    For example: "x � x"
    """

    is_truncated: bool = False
    """
    If True, the input column name was too long, so we truncated it.

    For example: "abcdef<...100+ chars...>gehij" (instead of a 1MB colname)
    """


@dataclass(frozen=True)
class UniqueCleanColname:
    """
    A column to add to a table, plus information of its provenance.
    """

    name: str
    """
    Column name, unique and valid as per `gen_unique_clean_colnames()`.
    """

    is_ascii_cleaned: bool = False
    """
    If True, the input column had ASCII control characters and we removed them.

    For example: "line 1line 2" (instead of "line 1\nline 2")
    """

    is_unicode_fixed: bool = False
    """
    If True, the column name had invalid Unicode surrogate pairs.

    For example: "x � x"
    """

    is_default: bool = False
    """
    If True, gen_unique_clean_colnames() supplied a default 'Column %x' name.

    For example: "Column 3" (instead of "")

    Though it may seem quirky, `is_number_added` may be applied as well. For
    example: "Column 3 2" (instead of "")

    Also, `is_ascii_cleaned` may apply. For example: "Column 3" (instead of "\n")
    """

    is_truncated: bool = False
    """
    If True, the input column name was too long, so we truncated it.

    For example: "abcdef<...100+ chars...>gehij" (instead of a 1MB colname)

    Truncation can cause duplicate column names, so `is_number_added` may also
    apply. For example: "abcdef<...100+ chars...>geh 2"
    """

    is_numbered: bool = False
    """
    If True, a number was added to the column name (or changed) for uniqueness.

    For example: "Amount 2" (instead of "Amount" or "Amount 1")
    """


def _truncate_str_to_max_n_bytes(s: str, max_n_bytes: int):
    b = s.encode("utf-8")
    if len(b) <= max_n_bytes:
        return s

    while True:
        b = b[:max_n_bytes]
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            # We nixed a continuation byte. Nix more bytes until we fit.
            max_n_bytes -= 1


_ASCII_CONTROL_CHARACTER_RE = re.compile("[\x00-\x1f]")


def clean_colname(name: str, *, settings: Settings = DefaultSettings()) -> CleanColname:
    r"""
    Make a column name suitable for inserting into a table.

    The return value is a CleanColname so the caller can detect behavior the
    user might not expect.

    >>> colname = clean_colname("abcd")
    CleanColname("abcd")

    ASCII control characters are removed:

    >>> colname = clean_colname("ab\ncd")
    CleanColname("abcd", is_ascii_cleaned=True)

    Invalid Unicode is fixed:

    >>> colname = clean_colname("ab\ud800\udc00cd")
    CleanColname("ab��cd", is_unicode_fixed=True)

    If the column length (utf-8 encoded) exceeds
    `settings.MAX_BYTES_PER_COLUMN_NAME`, it is truncated to a valid length:

    >>> clean_colname("acé", settings=namedtuple("settings", "MAX_BYTES_PER_COLUMN_NAME")(3))
    CleanColname("ac", is_truncated=True)
    """

    name_ascii_cleaned = _ASCII_CONTROL_CHARACTER_RE.sub("", name)
    is_ascii_cleaned = len(name_ascii_cleaned) < len(name)
    name = name_ascii_cleaned

    # str.encode(errors="replace") replaces with '?' instead of '�' so we
    # replace during decode instead.
    #
    # also,
    # "\ud800".encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
    # creates _three_ Unicode replacement characters. Use utf-32be to make a single one,
    # since that's easier for a user to understand. (NodeJS gives just one replacement
    # character.)
    name_unicode_fixed = name.encode("utf-32be", errors="surrogatepass").decode(
        "utf-32be", errors="replace"
    )
    is_unicode_fixed = name_unicode_fixed != name
    name = name_unicode_fixed

    name_truncated = _truncate_str_to_max_n_bytes(
        name, settings.MAX_BYTES_PER_COLUMN_NAME
    )
    is_truncated = len(name_truncated) < len(name)
    name = name_truncated

    return CleanColname(
        name=name,
        is_ascii_cleaned=is_ascii_cleaned,
        is_unicode_fixed=is_unicode_fixed,
        is_truncated=is_truncated,
    )


_NUMBERED_COLNAME_PATTERN = re.compile(r"^(.+?) (\d+)$")


def _parse_colname_key_and_optional_number(name: str) -> Tuple[str, Optional[int]]:
    match = _NUMBERED_COLNAME_PATTERN.fullmatch(name)
    if match:
        return match.group(1), int(match.group(2))
    else:
        return name, None


def gen_unique_clean_colnames(
    names: List[str],
    *,
    existing_names: List[str] = [],
    settings: Settings = DefaultSettings(),
) -> List[UniqueCleanColname]:
    r"""
    Create UniqueCleanColname instances to help append columns to a table.

    This helps generate column names from arbitrary data. (It's suitable for
    CSV data or transpose.) The calling convention:

        existing_names = ["foo", "bar"]  # names in a table (or [] for new table)
        new_names = ["foo 2", "foo", ""]
        for valid_colname in (
            gen_unique_clean_colnames(new_names, existing_names=existing_names)
        ):
            table[valid_colname.name] = whatever
            # the first valid_colname would have name="foo 2"
            # the second valid_colname would have name="foo 3", is_number_added=True
            # the third valid_colname would have name="Column 5", is_default=True

    See `ValidColname` for all the modifications that can occur.

    The returned list will have the same length as `names`, and each name is
    guaranteed to pass Workbench's validation routines.

    To make a column name unique, we number it with a special algorithm. Match
    all names against "[name] [number]": everything before " [number]" is the
    'key' and the digits are the 'number'. Maintain a blacklist of numbers, for
    each key; when a new key+number conflict, find the first _free_ number with
    that key to construct a new column name.

    This algorithm is not good for all cases. In particular, users probably
    can't predict how output column names will be mangled:

    >>> gen_unique_clean_colnames(["foo", "foo 2"], ["foo 2", "foo"])
    [UniqueCleanColname("foo 3", is_numbered=True), UniqueCleanColname("foo 4", is_numbered=True)]

    We do, however, "reserve" each column name. If we add a number to the
    first column, that number will never overwrite the second column's
    number:

    >>> gen_unique_clean_colnames(["foo", "foo 2"], ["foo 2", "foo 3"])
    [UniqueCleanColname("foo 4", is_numbered=True), UniqueCleanColname("foo 3")]

    The reason we return `UniqueCleanColname` instead of plain strings is so
    module authors can warn users when names are mangled. If _any_
    `UniqueCleanColname` attribute is `True`, consider whether the user expects
    this behavior.

    Here are all the mutations that can affect a column name. (All are
    described in `ValidColname` docstrings.)

    1. Column names are cleaned. (`is_ascii_cleaned`, `is_unicode_fixed`,
       `is_truncated`)
    2. If the name is empty, a default "Column N" is chosen based on the
       column's position, being sure not to conflict with other column names.
       (`is_default`)
    3. If the name is a duplicate, a number is added or changed. If the number
       makes us exceed `MAX_BYTES_PER_COLUMN_NAME`, we truncate further until
       it doesn't. (`is_number_added`, `is_truncated`)
    """

    # 1. clean column names
    clean_names = [clean_colname(name, settings=settings) for name in names]

    # 2a. populate our blacklist with all existing column names. So if we see
    # ["foo", "foo", "foo 2"] we won't give ["foo", "foo 2", "foo 3"]. (That
    # would appear to "move" a column name, which is wrong.) It should be
    # ["foo", "foo 3", "foo 2"].
    blacklist = {}  # key => { (num or None) => column index }
    for index, name in enumerate(existing_names):
        key, num = _parse_colname_key_and_optional_number(name)
        blacklist.setdefault(key, {}).setdefault(num, index)
    for i, colname in enumerate(clean_names):
        index = i + len(existing_names)
        key, num = _parse_colname_key_and_optional_number(colname.name)
        blacklist.setdefault(key, {}).setdefault(num, index)

    # 2b. blacklist _default_ column names, too
    for i, colname in enumerate(clean_names):
        if not colname.name:
            key = "Column"
            index = i + len(existing_names)
            num = index + 1
            blacklist.setdefault(key, {}).setdefault(num, index)

    # 3. Generate column names, using and modifying our blacklist.
    ret = []
    for i, clean_name in enumerate(clean_names):
        index = i + len(existing_names)
        is_truncated = False
        is_numbered = False

        if clean_name.name:
            key, num = _parse_colname_key_and_optional_number(clean_name.name)
            name = clean_name.name  # may not include num
        else:
            key, num = "Column", index + 1
            name = f"{key} {num}"  # always includes num

        if blacklist[key][num] != index:
            # We conflict with a different column. Find a new number, to build
            # a name like, "{key} {num}".
            is_numbered = True
            while num in blacklist[key]:
                # Increment num until we get a fresh (key, num).
                #
                # If we're about to build a column name that's too long,
                # truncate key to fit. (Don't reset num.)
                #
                # This algorithm strives for simplicity over dream output. A
                # 100-byte colname is _never_ what the user wants.
                if num is None:
                    # "foo" has implicit number 1.
                    #
                    # If input is "foo 1", check "foo 1", "foo 2", "foo 3", ...
                    # If input is "foo", check "foo", "foo 2", "foo 3", ... (skip 1)
                    num = 2
                else:
                    num += 1

                if (
                    len(f"{key} {num}".encode("utf-8"))
                    > settings.MAX_BYTES_PER_COLUMN_NAME
                ):
                    is_truncated = True
                    key = _truncate_str_to_max_n_bytes(
                        key, settings.MAX_BYTES_PER_COLUMN_NAME - len(f" {num}")
                    )
                    blacklist.setdefault(key, {})

            name = f"{key} {num}"
            blacklist[key][num] = index

        ret.append(
            UniqueCleanColname(
                name=name,
                is_ascii_cleaned=clean_name.is_ascii_cleaned,
                is_unicode_fixed=clean_name.is_unicode_fixed,
                is_default=(not clean_name.name),
                is_numbered=is_numbered,
                is_truncated=clean_name.is_truncated or is_truncated,
            )
        )

    return ret


def gen_unique_clean_colnames_and_warn(
    names: List[str],
    *,
    existing_names: List[str] = [],
    settings: Settings = DefaultSettings(),
) -> Tuple[List[str], List[I18nMessage]]:
    """
    Create UniqueCleanColname instances to help append columns to a table.

    Warn if ASCII-cleaning names, renaming duplicates, truncating names,
    auto-generating names, or fixing Unicode errors.
    """
    n_ascii_cleaned = 0
    first_ascii_cleaned = None
    n_default = 0
    first_default = None
    n_truncated = 0
    first_truncated = None
    n_numbered = 0
    first_numbered = None
    n_unicode_fixed = 0
    first_unicode_fixed = None

    ret = []

    for uccolname in gen_unique_clean_colnames(
        names, existing_names=existing_names, settings=settings
    ):
        name = uccolname.name
        ret.append(name)
        if uccolname.is_ascii_cleaned:
            if n_ascii_cleaned == 0:
                first_ascii_cleaned = name
            n_ascii_cleaned += 1
        if uccolname.is_default:
            if n_default == 0:
                first_default = name
            n_default += 1
        if uccolname.is_truncated:
            if n_truncated == 0:
                first_truncated = name
            n_truncated += 1
        if uccolname.is_numbered:
            if n_numbered == 0:
                first_numbered = name
            n_numbered += 1
        if uccolname.is_unicode_fixed:
            if n_unicode_fixed == 0:
                first_unicode_fixed = name
            n_unicode_fixed += 1

    warnings = []
    if n_ascii_cleaned > 0:
        warnings.append(
            _trans_cjwmodule(
                "util.colnames.warnings.ascii_cleaned",
                "Removed special characters from "
                "{n_columns, plural,"
                " other{# column names (see “{first_colname}”)}"
                " one{column name “{first_colname}”}"
                "}",
                {"n_columns": n_ascii_cleaned, "first_colname": first_ascii_cleaned},
            )
        )
    if n_default > 0:
        warnings.append(
            _trans_cjwmodule(
                "util.colnames.warnings.default",
                "{n_columns, plural,"
                " other{Renamed # column names because values were empty (see “{first_colname}”)}"
                " one{Renamed column name “{first_colname}” because value was empty}"
                "}",
                {"n_columns": n_default, "first_colname": first_default},
            )
        )
    if n_truncated > 0:
        warnings.append(
            _trans_cjwmodule(
                "util.colnames.warnings.truncated",
                "{n_columns, plural,"
                " other{Truncated # column names to {n_bytes} bytes each (see “{first_colname}”)}"
                " one{Truncated column name “{first_colname}” to {n_bytes} bytes}"
                "}",
                {
                    "n_columns": n_truncated,
                    "first_colname": first_truncated,
                    "n_bytes": settings.MAX_BYTES_PER_COLUMN_NAME,
                },
            )
        )
    if n_numbered > 0:
        warnings.append(
            _trans_cjwmodule(
                "util.colnames.warnings.numbered",
                "{n_columns, plural,"
                " other{Renamed # duplicate column names (see “{first_colname}”)}"
                " one{Renamed duplicate column name “{first_colname}”}"
                "}",
                {"n_columns": n_numbered, "first_colname": first_numbered},
            )
        )
    if n_unicode_fixed > 0:
        warnings.append(
            _trans_cjwmodule(
                "util.colnames.warnings.unicode_fixed",
                "{n_columns, plural,"
                " other{Fixed # column names with invalid Unicode (see “{first_colname}”)}"
                " one{Fixed Unicode in column name “{first_colname}”}"
                "}",
                {"n_columns": n_unicode_fixed, "first_colname": first_unicode_fixed},
            )
        )

    return ret, warnings
