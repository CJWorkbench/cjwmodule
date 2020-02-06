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
