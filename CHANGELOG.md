v3.1.0 - 2020-11-18
-------------------

* `cjwmodule.arrow.condition`: Accumulate regex errors into `ConditionError`.
  `.msg` and `.pattern` remain available for backwards compatibility.

v3.0.0 - 2020-11-17
-------------------

* Bump pyarrow dependency to ~=2.0
* Require `google-re2==0.0.5` -- an old version that matches the version
  of `libre2-5` in Debian Buster.
* `cjwmodule.arrow.condition`: calculates masks using a condition DSL.

This is a major version change because dependencies have changed.

v2.0.1 - 2020-10-26
-------------------

* Bump httpx dependency

v2.0.0 - 2020-09-22
-------------------

* Bump dependency to pyarrow~=1.0.1

This is a major version change.

v1.5.7 - 2020-09-22
-------------------

* `cjwmodule.util.colnames`: fix KeyError on colnames like " 1".

v1.5.6 - 2020-09-14
-------------------

* `cjwmodule.util.colnames.Settings`: use python3.8 `typing.Protocol` (only
  changes type-checking, not code)
* `cjwmodule.testing.i18n`: add type hints

v1.5.5 - 2020-09-14
-------------------

* `cjwmodule.http`: nix errant `print()`

v1.5.4 - 2020-09-14
-------------------

* `cjwmodule.http`: revert API change from v1.5.3. Headers should be str, not
  bytes, because a change to bytes would mean changing the API.

v1.5.3 - 2020-09-11
-------------------

**DO NOT USE: not API-compatible with the other v1 releases**

* `cjwmodule.http`: treat headers as ISO-8859-1, always. (We're a spec-compliant
  library; callers are welcome to second-guess server responses.) Fixes a crash
  when dealing with UTF-8 Content-Disposition.

v1.5.2 - 2020-08-31
-------------------

* `cjwmodule.http.httpfile`: omit filename from gzip header. Now output will be
  deterministic, so if the upstream doesn't change the gzip doesn't change.
* Bump black, httpx, pytest

v1.5.1 - 2020-06-05
-------------------

* `cjwmodule.arrow.format`: handle null validity buffers. (We saw timestamp
  problems in the wild.)

v1.5.0 - 2020-03-08
-------------------

* `cjwmodule.arrow.format`: convert Arrow arrays to text.

v1.4.2 - 2020-02-20
-------------------

* Fix extracting some i18n messages.

v1.4.1 - 2020-02-17
-------------------

* Introduce `cjwmodule.testing.i18n` module.

v1.4.0 - 2020-02-14
-------------------

* Test with Python 3.8.
* Extract i18n messages with `./setup.py extract_messages`
* `util.colnames.gen_unique_clean_colnames_and_warn()`: new utility runs
  `gen_unique_clean_colnames()` and converts warnings to i18n messages.

v1.3.1 - 2020-02-06
-------------------

* Fix packaging.


v1.3.0 - 2020-02-06
-------------------

* Generate some i18n-ready messages. [BROKEN]

v1.2.2 - 2020-02-05
-------------------

* Add some dummy i18n catalogs.

v1.2.1 - 2020-01-16
-------------------

* Test and bugfix `cjwmodule.http.httpfile.read()` and `.write()`.

v1.2.0 - 2020-01-10
-------------------

* `cjwmodule.http` module, featuring `client.download()` (async with i18n-ready
  exceptions) and `httpfile.download()` / `httpfile.read()` to write and read
  "raw" HTTP responses in a Workbench-standard format.

v1.1.3 - 2019-12-17
-------------------

* `gen_unique_clean_colnames()`: consider byte length, not char length, when
  truncating after adding a number to a column name.

v1.1.2 - 2019-12-16
-------------------

* Fix packaging. (v1.1.1 was a dud.)

v1.1.0 - 2019-12-13
-------------------

* Add `cjwmodule.util.colnames` module with `clean_colname()` and
  `gen_unique_clean_colnames()`.

v1.0.0 - 2019-11-21
-------------------

* Initial release. We only have `cjwmodule.i18n.trans()` for now....
