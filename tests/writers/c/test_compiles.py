"""Generated headers must compile cleanly on every C/C++ compiler available.

String checks prove shape; only a compiler proves the output is valid. This is a
data-driven matrix built from the shared toolchain registry
(``tools/toolchains.py``) -- each compiler found on PATH is exercised across the
standards it supports, and absent compilers are *skipped*, never failed, so the
suite stays green whether a machine has one toolchain or five.

GNU-family compilers are held to ``-Werror`` (output must be warning-free); MSVC
is checked for compilability only (its MMIO-header warnings are noisy and
unverified). armcc / IAR are licensed and skip unless installed; their command
shapes are best-effort. See the README "Compiler support" section.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from tools.toolchains import SOURCE_EXTENSION, cases, compile_command, resolve

_CASES = cases()
_IDS = [f"{language}-{toolchain.key}-{std}" for language, toolchain, std in _CASES]


@pytest.mark.parametrize("language,toolchain,std", _CASES, ids=_IDS)
def test_golden_header_compiles(language, toolchain, std, tmp_path, golden_header_path):
    exe = resolve(toolchain.executables)
    if exe is None:
        pytest.skip(f"{toolchain.key} not on PATH")
    if toolchain.style == "msvc" and not os.environ.get("INCLUDE"):
        pytest.skip("cl found but no MSVC environment (INCLUDE unset)")

    source = tmp_path / f"main.{SOURCE_EXTENSION[language]}"
    source.write_text(
        f'#include "{golden_header_path.as_posix()}"\n'
        "int main(void) {\n"
        "    volatile uint32_t v = DC_GPIOA_MODER; (void)v;\n"
        "    return (int)demomcu_irq_prio(1);\n"
        "}\n",
        encoding="utf-8",
    )
    output = tmp_path / ("out.obj" if toolchain.style == "msvc" else "out.o")
    result = subprocess.run(
        compile_command(toolchain, exe, std, str(source), str(output)),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{toolchain.key} {std}:\n{result.stdout}\n{result.stderr}"


def _gnu_c_compiler() -> str | None:
    return resolve(("gcc", "cc", "clang"))


@pytest.mark.skipif(_gnu_c_compiler() is None, reason="no GNU C compiler on PATH")
def test_unused_helper_is_warning_free_on_c89(tmp_path, golden_header_path):
    # On C89 the priority helper degrades to `static __attribute__((unused))`; a
    # TU that includes the header but never calls it must stay warning-free under
    # -Wall -Werror -- the REGFORGE_INLINE unused attribute is what guarantees it.
    exe = _gnu_c_compiler()
    source = tmp_path / "unused.c"
    source.write_text(
        f'#include "{golden_header_path.as_posix()}"\nint main(void) {{ return 0; }}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            exe,
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
