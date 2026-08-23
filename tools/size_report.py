"""Report generated-header code/data size per compiler and optimization level.

Object-level: compile a representative translation unit with ``-c`` and read the
``size`` tool, for each toolchain in the shared registry (``tools/toolchains.py``)
that provides one, at ``-O0/-O1/-Os/-O2`` -- making "the abstractions cost
nothing once optimized" empirical instead of asserted. Toolchains and languages
come from the same registry the compile matrix uses, so nothing is duplicated.

Foundation on purpose: link-level flags (``-ffunction-sections
-fdata-sections -Wl,--gc-sections``, ``-flto``) whose effect only shows in a
linked image are the planned next layer.

Run with ``nox -s sizes`` (or ``python -m tools.size_report``).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from tools.toolchains import SOURCE_EXTENSION, TOOLCHAINS, resolve

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "c" / "minimal.h"

#: Levels worth comparing: -O0 (debug worst case) through the firmware-relevant
#: -Os, plus -O2 to confirm size does not balloon versus -Os.
OPT_LEVELS = ("-O0", "-O1", "-Os", "-O2")

#: Representative translation units, formatted with the golden header path. The
#: baseline (no header) makes the header's marginal cost readable at a glance.
TRANSLATION_UNITS = {
    "baseline (no header)": "int main(void) {{ return 0; }}\n",
    "include-only": '#include "{header}"\nint main(void) {{ return 0; }}\n',
    "use-registers": (
        '#include "{header}"\n'
        "int main(void) {{ DC_GPIOA_MODER = 1u; return (int)demomcu_irq_prio(1); }}\n"
    ),
}


def object_sizes(cc, cc_flags, size_exe, source_text, opt, extension):
    """Compile ``source_text`` at ``opt`` and return (text, data, bss, dec), or None."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        source = directory / f"unit.{extension}"
        source.write_text(source_text.format(header=GOLDEN.as_posix()), encoding="utf-8")
        obj = directory / "unit.o"
        compiled = subprocess.run(
            [cc, *cc_flags, opt, "-c", str(source), "-o", str(obj)],
            capture_output=True,
            text=True,
        )
        if compiled.returncode != 0:
            return None
        measured = subprocess.run([size_exe, str(obj)], capture_output=True, text=True)
        if measured.returncode != 0:
            return None
        rows = measured.stdout.strip().splitlines()
        if len(rows) < 2:
            return None
        text, data, bss, dec = (int(value) for value in rows[1].split()[:4])
        return text, data, bss, dec


def report() -> None:
    """Print the size table for every size-capable toolchain found on PATH."""
    ran = False
    for language, toolchains in TOOLCHAINS.items():
        extension = SOURCE_EXTENSION[language]
        for toolchain in toolchains:
            if not toolchain.size_tools:
                continue  # language/toolchain has no notion of object size
            cc = resolve(toolchain.executables)
            size_exe = resolve(toolchain.size_tools)
            if not cc or not size_exe:
                continue
            ran = True
            print(f"\nsize report -- {language}/{toolchain.key} ({Path(cc).name})   bytes")
            print(f"  {'TU':<22}{'opt':>5}{'text':>8}{'data':>7}{'bss':>6}{'dec':>7}")
            for tu_name, tu_source in TRANSLATION_UNITS.items():
                for opt in OPT_LEVELS:
                    sizes = object_sizes(
                        cc, toolchain.extra_flags, size_exe, tu_source, opt, extension
                    )
                    if sizes is None:
                        print(f"  {tu_name:<22}{opt:>5}   (measurement failed)")
                        continue
                    text, data, bss, dec = sizes
                    print(f"  {tu_name:<22}{opt:>5}{text:>8}{data:>7}{bss:>6}{dec:>7}")
    if not ran:
        print("no compiler + size tool found; nothing to report")


if __name__ == "__main__":
    report()
