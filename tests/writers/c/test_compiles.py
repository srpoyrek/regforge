"""The generated C header must compile cleanly under C89, C99, and C11.

Skipped automatically when no C compiler is on PATH (e.g. minimal CI images).
This is the ground-truth test for a code generator: string checks prove shape,
but only a compiler proves the output is valid C.
"""

import shutil
import subprocess

import pytest

_CC = shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")
_IS_GNU = _CC is not None and any(name in _CC.lower() for name in ("gcc", "clang"))

pytestmark = pytest.mark.skipif(_CC is None, reason="no C compiler on PATH")


@pytest.mark.parametrize("std", ["c89", "c99", "c11"])
def test_golden_header_compiles(std, tmp_path, golden_header_path):
    source = tmp_path / "main.c"
    source.write_text(
        f'#include "{golden_header_path.as_posix()}"\n'
        "int main(void) {\n"
        "    volatile uint32_t v = DC_GPIOA_MODER; (void)v;\n"
        "    return (int)demomcu_irq_prio(1);\n"
        "}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            _CC,
            f"-std={std}",
            "-pedantic-errors",
            "-Wall",
            "-c",
            str(source),
            "-o",
            str(tmp_path / "out.o"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{std} compile failed:\n{result.stderr}"


@pytest.mark.skipif(not _IS_GNU, reason="unused attribute is GCC/Clang-specific")
def test_unused_helper_is_warning_free_on_c89(tmp_path, golden_header_path):
    # On C89 the priority helper is plain `static`; a TU that includes the
    # header but never calls it must stay warning-free under -Wall -Werror
    # (the __attribute__((unused)) guard).
    source = tmp_path / "unused.c"
    source.write_text(
        f'#include "{golden_header_path.as_posix()}"\nint main(void) {{ return 0; }}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            _CC,
            "-std=c89",
            "-pedantic-errors",
            "-Wall",
            "-Werror",
            "-c",
            str(source),
            "-o",
            str(tmp_path / "out.o"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
