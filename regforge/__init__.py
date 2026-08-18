"""regforge: convert register descriptions between formats.

regforge reads a device's register map from an input format (such as
CMSIS-SVD) into a format-independent intermediate representation, then renders
it to a target language (such as C). Readers and writers are pluggable, so new
input formats and output languages can be added independently.

Typical usage::

    from regforge import get_reader, get_writer

    device = get_reader("svd").read("device.svd")
    header = get_writer("c").render(device)
"""

from __future__ import annotations

from .check import Finding, Severity, check_address_math
from .ir import Access, Cpu, Device, EnumeratedValue, Field, Peripheral, Register
from .provenance import PatchRef, Provenance, build_provenance
from .readers import available_readers, get_reader, reader_for_path
from .resolve import resolve_defaults
from .writers import available_writers, get_writer, writer_for_path

__version__ = "0.0.1"

__all__ = [
    "Device",
    "Cpu",
    "Peripheral",
    "Register",
    "Field",
    "EnumeratedValue",
    "Access",
    "resolve_defaults",
    "Provenance",
    "PatchRef",
    "build_provenance",
    "check_address_math",
    "Finding",
    "Severity",
    "get_reader",
    "reader_for_path",
    "available_readers",
    "get_writer",
    "writer_for_path",
    "available_writers",
    "__version__",
]
