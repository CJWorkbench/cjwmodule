import contextlib
import tempfile
from pathlib import Path
from typing import ContextManager

import pytest

from cjwmodule.spec.testing import param_factory


@contextlib.contextmanager
def _temporary_spec(b: bytes) -> ContextManager[Path]:
    with tempfile.NamedTemporaryFile(suffix=".yaml") as tf:
        tf.write(b)
        tf.flush()

        yield Path(tf.name)


def test_param_factory_defaults():
    with _temporary_spec(
        b"""
id_name: mymodule
name: name
category: Clean
parameters:
- id_name: foo
  name: foo
  type: string
  default: bar
- id_name: moo
  type: integer
  default: 4
"""
    ) as path:
        P = param_factory(path)
        assert P() == {"foo": "bar", "moo": 4}
        assert P(foo="moo") == {"foo": "moo", "moo": 4}


def test_param_factory_defaults_do_not_nest():
    with _temporary_spec(
        b"""
id_name: mymodule
name: name
category: Clean
parameters:
- id_name: outer
  type: list
  child_parameters:
  - id_name: innerstring
    name: foo
    type: string
    default: avalue
"""
    ) as path:
        P = param_factory(path)
        assert P() == {"outer": []}
        assert P(outer=[{"innerstring": "foo"}]) == {"outer": [{"innerstring": "foo"}]}
        with pytest.raises(ValueError, match="has wrong keys"):
            assert P(outer=[{}])


def test_param_factory_check_types():
    with _temporary_spec(
        b"""
id_name: mymodule
name: name
category: Clean
parameters:
- id_name: s
  name: s
  type: string
- id_name: i
  name: i
  type: integer
- id_name: f
  name: f
  type: float
"""
    ) as path:
        P = param_factory(path)
        P(s="s", i=1, f=2.1)  # ok
        with pytest.raises(ValueError, match="Value 1 is not a string"):
            P(s=1, i=1, f=2.1)
        with pytest.raises(ValueError, match="Value 2.1 is not an integer"):
            P(s="s", i=2.1, f=2.1)
        with pytest.raises(ValueError, match="Value 'f' is not a float"):
            P(s="s", i=1, f="f")
        P(s="s", i=1, f=2)  # int is a valid float


def test_param_factory_check_unwanted_values():
    with _temporary_spec(
        b"""
id_name: mymodule
name: name
category: Clean
parameters:
- id_name: foo
  name: foo
  type: string
  default: foo
"""
    ) as path:
        P = param_factory(path)
        with pytest.raises(ValueError, match="has wrong keys"):
            P(foo="bar", bar="baz")


def test_param_factory_oserror():
    with pytest.raises(FileNotFoundError):
        param_factory(Path(__file__).parent / "no-this-is-not-a-file.yaml")


def test_param_factory_validate_spec():
    with _temporary_spec(
        b"""
id_name: mymodule
name: name
category: Clean
parameters:
- id_name: s
  name: s
"""
    ) as path:
        with pytest.raises(ValueError, match="is not valid"):
            param_factory(path)
