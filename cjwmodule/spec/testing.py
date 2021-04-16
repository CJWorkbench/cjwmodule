"""Helpers for working with your spec file in module unit tests."""
from pathlib import Path
from typing import Any, Callable, Dict

from .loader import load_spec_file


def param_factory(spec_path: Path) -> Callable[..., Dict[str, Any]]:
    """Make a factory function for your `param` dict, from your module YAML.

    Invocation (from your test suite):

        from pathlib import Path

        from cjwmodule.spec.testing import param_factory

        # "P" is our factory function. It generates a dict.
        P = param_factory(Path(__file__).parent.parent / "mymodule.yaml")

        def test_render():
            render_arrow_v1(..., params=P(foo="bar"), ...)

    Features:

    * Default parameters. If you omit a "foo" param with a default of "bar",
      the return value will include foo="bar". (This is "shallow": it only
      happens for top-level parameters, not nested parameters).
    * Crash on invalid parameters. If you supply a param "foo" that your module
      spec doesn't have, you'll raise ValueError.
    """
    spec = load_spec_file(spec_path)  # raises ValueError, OSError
    schema = spec.param_schema

    def P(**kwargs):
        kwargs_with_defaults = {**schema.default, **kwargs}
        schema.validate(kwargs_with_defaults)  # raise ValueError on bad input
        return kwargs_with_defaults

    return P
