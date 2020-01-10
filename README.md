Utilities for [CJWorkbench](https://github.com/CJWorkbench/cjworkbench) modules.

Workbench modules may _optionally_ depend on the latest version of this Python
package for its handy utilities:

* `cjwmodule.http`: HTTP helpers, including the handy `httpfile` format.
* `cjwmodule.i18n`: A `trans()` function for producing translatable text.
* `cjwmodule.util.colnames`: Functions to help build a valid table's column names.


Developing
==========

1. Write a failing unit test in `tests/`
2. Make it pass by editing code in `cjwmodule/`
3. Submit a pull request

Be very, very, very careful to preserve a consistent API. Workbench will
upgrade this dependency without module authors' explicit consent. Add new
features; fix bugs. Never change functionality.


Publishing
==========

1. Write a new `__version__` to `cjwmodule/__init__.py`. Adhere to
   [semver](https://semver.org). (As changes must be backwards-compatible,
   the version will always start with `1` and look like `1.x.y`.)
2. Prepend notes to `CHANGELOG.md` about the new version
3. `git commit`
4. `git tag v1.x.y`
5. `git push --tags && git push`
6. Wait for Travis to push our changes to PyPI
