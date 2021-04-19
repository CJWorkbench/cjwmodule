Utilities for [CJWorkbench](https://github.com/CJWorkbench/cjworkbench) modules.

Workbench modules may _optionally_ depend on the latest version of this Python
package for its handy utilities:

* `cjwmodule.arrow.condition`: functions to create Arrow table masks.
* `cjwmodule.arrow.format`: functions to convert Arrow arrays to text.
* `cjwmodule.arrow.types`: types your Arrow module may accept and return.
* `cjwmodule.arrow.testing`: helpers for programming tests.
* `cjwmodule.http`: HTTP helpers, including the handy `httpfile` format.
* `cjwmodule.i18n`: A `trans()` function for producing translatable text.
* `cjwmodule.testing`: Functions to help in unit testing.
* `cjwmodule.util.colnames`: Functions to help build a valid table's column names.
* `cjwmodule.spec`: Functions to load and validate module spec files.
* `cjwmodule.types`: Types your module may accept and return.

Developing
==========

0. Run `tox` to confirm that unit tests pass
1. Write a failing unit test in `tests/`. (`tox` should fail now.)
2. Make it pass by editing code in `cjwmodule/`
3. Run `poetry run extract-messages` if i18n data changed
4. Run `tox` to confirm that unit tests pass again
5. Submit a pull request

Preserve a consistent API. Workbench will upgrade this dependency without module
authors' consent. Add new features; fix bugs. Don't alter existing behavior.

I18n
====

### Marking strings for translation

Strings in `cjwmodule` can be marked for translation using `cjwmodule.i18n._trans_cjwmodule`.
Each translation message must have a (unique) ID. ICU is supported for the content.
For example,

```python
from cjwmodule.i18n import _trans_cjwmodule

err = "Error 404"

with_arguments = _trans_cjwmodule(
    "greatapi.exception.message",
    "Something is wrong: {error}",
    {"error": err}
)

without_arguments = _trans_cjwmodule(
    "greatapi.exception.general",
    "Something is wrong",
)
```

Workbench is wired to accept the return value of `_trans_cjwmodule` wherever an
error/warning or quick fix is expected.

### Creating `po` catalogs

Calls to `_trans_cjwmodule` can (and must) be parsed to create `cjwmodule`'s
`.po` files.  Update the `.po` files with:

```
poetry run extract-messages
```

### Unit testing

In case a `_trans_cjwmodule` invocation needs to be unit tested, you can use
`cjwmodule.testing.i18n.cjwmodule_i18n_message` like this:

```python
from cjwmodule.testing.i18n import cjwmodule_i18n_message
import with_arguments, without_arguments

assert with_arguments == cjwmodule_i18n_message("greatapi.exception.message", {"error": "Error 404"})
assert without_arguments == cjwmodule_i18n_message("greatapi.exception.general")
```

### Message deprecation

For backwards compatibility, *messages in `cjwmodule`'s `po` files are never deleted*!


Publishing
==========

1. Prepend notes to `CHANGELOG.md` about the new version
2. `git commit`
3. `git push` and wait for Travis to report success
4. `git tag v1.x.y && git push --tags`
5. Wait for Travis to push our changes to PyPI
