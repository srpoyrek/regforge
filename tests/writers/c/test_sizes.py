"""The generated header must add zero code/data when included but unused.

The claim behind the typed accessors -- and, soon, the typed peripheral
instances -- is that they cost nothing once optimized. This nails it down: at
``-Os``, a translation unit that includes the header but references nothing must
be byte-identical in size to one that never included it. It guards every future
feature from silently adding fixed overhead. The human-readable breakdown across
compilers and optimization levels lives in ``tools/size_report.py``
(``nox -s sizes``); this is the machine-checked floor.

Skipped when no GNU C compiler + ``size`` tool is available.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from tools.toolchains import resolve

_CC = resolve(("gcc", "cc", "clang"))
_SIZE = resolve(("size", "llvm-size"))

pytestmark = pytest.mark.skipif(
    _CC is None or _SIZE is None, reason="no GNU C compiler + size tool on PATH"
)


def _object_sizes(source_text: str, opt: str) -> tuple[int, int, int] | None:
    """Compile ``source_text`` at ``opt``; return (text, data, bss) bytes, or None."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        source = directory / "unit.c"
        source.write_text(source_text, encoding="utf-8")
        obj = directory / "unit.o"
        compiled = subprocess.run(
            [_CC, opt, "-c", str(source), "-o", str(obj)], capture_output=True, text=True
        )
        if compiled.returncode != 0:
            return None
        measured = subprocess.run([_SIZE, str(obj)], capture_output=True, text=True)
        if measured.returncode != 0:
            return None
        rows = measured.stdout.strip().splitlines()
        text, data, bss, _dec = (int(value) for value in rows[1].split()[:4])
        return text, data, bss


def test_included_header_is_zero_cost_when_unused_at_os(golden_header_path):
    baseline = _object_sizes("int main(void) { return 0; }\n", "-Os")
    with_header = _object_sizes(
        f'#include "{golden_header_path.as_posix()}"\nint main(void) {{ return 0; }}\n',
        "-Os",
    )
    assert baseline is not None and with_header is not None
    # Including the header must add no code (text), no initialized data, no bss.
    assert with_header == baseline
