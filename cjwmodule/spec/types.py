"""ALPHA API - NOT USING SEMVER

We're not happy with this API yet. It might change in minor or patch releases
of `cjwmodule`.
"""
from typing import Dict, List, NamedTuple, Optional

from .paramfield import ParamField
from .paramschema import ParamSchema


class ModuleSpec(NamedTuple):
    """Dict-like object representing a valid module spec."""

    id_name: str
    name: str
    category: str
    deprecated: Optional[Dict[str, str]]
    icon: str
    link: str
    description: str
    loads_data: bool
    uses_data: bool
    html_output: bool  # janky -- really we should check ModuleZipfile
    has_zen_mode: bool
    row_action_menu_entry_title: str
    help_url: str
    param_fields: List[ParamField]
    param_schema: ParamSchema.Dict
