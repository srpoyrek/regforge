"""C writer.

Renders the intermediate representation into a C header of CMSIS-style
preprocessor definitions: a base-address macro per peripheral, a volatile
pointer accessor per register, position and mask macros per field, and a
constant per enumerated value.

The output style lives in an editable Jinja2 template
(``templates/c/header.h.j2``); this module only supplies the data and the
formatting helpers the template needs.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..ir import Device
from ..provenance import Provenance
from .base import Writer

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "c"


def _hex32(value: int) -> str:
    """Format ``value`` as a zero-padded 32-bit hexadecimal literal."""
    return f"0x{value & 0xFFFFFFFF:08X}"


class CWriter(Writer):
    """Writer that emits a C register header."""

    target_name = "c"
    file_extension = ".h"
    language = "C"

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False,
        )
        self._env.filters["hex32"] = _hex32

    def render(self, device: Device, provenance: Provenance | None = None) -> str:
        """Render ``device`` into a C header string."""
        template = self._env.get_template("header.h.j2")
        return template.render(device=device, provenance=provenance)
