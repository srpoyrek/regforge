"""Toolchains for verifying generated output, organized by target language.

Single source of truth shared by the compile matrix
(``tests/writers/c/test_compiles.py``) and the size report
(``tools/size_report.py``): a compiler is described once, never duplicated.
Keyed by target language, mirroring the writer registry -- adding a language
(rust, python, ...) is one entry here, and both the matrix and the report pick
it up.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class Toolchain:
    """One compiler/verifier for a target language."""

    key: str  # stable id used in test names ("gcc", "armcc", ...)
    executables: tuple[str, ...]  # PATH candidates, first match wins
    standards: tuple[str, ...]  # dialects to exercise ("c11", "c++17", ...)
    style: str  # command shape: "gnu" | "msvc" | "armcc" | "iar"
    extra_flags: tuple[str, ...] = ()  # cross target/cpu flags
    size_tools: tuple[str, ...] = ()  # `size` tool candidates; () = no size measurement


#: Source-file extension per target language.
SOURCE_EXTENSION = {"c": "c", "c++": "cpp"}

#: Target language -> the toolchains that build that language's output. Extend
#: with "rust"/"python" entries when those writers land.
TOOLCHAINS: dict[str, tuple[Toolchain, ...]] = {
    "c": (
        Toolchain("gcc", ("gcc", "cc"), ("c89", "c99", "c11"), "gnu", size_tools=("size",)),
        Toolchain(
            "clang", ("clang",), ("c89", "c99", "c11"), "gnu", size_tools=("llvm-size", "size")
        ),
        Toolchain(
            "arm-gnu",
            ("arm-none-eabi-gcc",),
            ("c89", "c99", "c11"),
            "gnu",
            ("-mcpu=cortex-m0",),
            ("arm-none-eabi-size", "size"),
        ),
        # Commercially licensed; skip unless installed. Command shapes UNVERIFIED.
        Toolchain(
            "armclang",
            ("armclang",),
            ("c99", "c11"),
            "gnu",
            ("--target=arm-arm-none-eabi", "-mcpu=cortex-m0"),
        ),
        Toolchain("armcc", ("armcc",), ("c90", "c99"), "armcc", ("--cpu=Cortex-M0",)),
        Toolchain("iar", ("iccarm",), ("c89", "c11"), "iar", ("--cpu=Cortex-M0",)),
        Toolchain("msvc", ("cl",), ("c11", "c17"), "msvc"),
    ),
    "c++": (
        Toolchain("g++", ("g++",), ("c++11", "c++17"), "gnu", size_tools=("size",)),
        Toolchain(
            "clang++", ("clang++",), ("c++11", "c++17"), "gnu", size_tools=("llvm-size", "size")
        ),
        Toolchain("msvc++", ("cl",), ("c++17",), "msvc"),
    ),
}


def resolve(candidates: tuple[str, ...]) -> str | None:
    """Return the first of ``candidates`` found on PATH, else None."""
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def compile_command(
    toolchain: Toolchain, exe: str, std: str, source: str, output: str
) -> list[str]:
    """Build a strict compile-only command for ``toolchain`` at dialect ``std``."""
    if toolchain.style == "gnu":
        return [
            exe,
            *toolchain.extra_flags,
            f"-std={std}",
            "-pedantic-errors",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-c",
            source,
            "-o",
            output,
        ]
    if toolchain.style == "msvc":
        # Compilability only: MSVC's default warnings on MMIO headers are noisy.
        return [exe, "/nologo", f"/std:{std}", "/W3", "/c", source, f"/Fo{output}"]
    if toolchain.style == "armcc":
        # Arm Compiler 5: --c90/--c99, --cpu, --diag_error. UNVERIFIED.
        return [
            exe,
            *toolchain.extra_flags,
            f"--{std}",
            "--diag_error=warning",
            "-c",
            source,
            "-o",
            output,
        ]
    if toolchain.style == "iar":
        # IAR iccarm: standard flag (C11 is the default), --cpu, errors. UNVERIFIED.
        std_flag = [] if std == "c11" else [f"--{std}"]
        return [
            exe,
            source,
            *toolchain.extra_flags,
            *std_flag,
            "--warnings_are_errors",
            "-o",
            output,
        ]
    raise ValueError(f"unknown toolchain style: {toolchain.style}")


def cases() -> list[tuple[str, Toolchain, str]]:
    """Every (language, toolchain, standard) triple across the registry."""
    return [
        (language, toolchain, std)
        for language, toolchains in TOOLCHAINS.items()
        for toolchain in toolchains
        for std in toolchain.standards
    ]
