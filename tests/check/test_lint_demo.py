"""The lint-demo device: a deliberately-flawed chip the linter must flag.

`lint_demo.svd` trips the addressBlock/overlap checks (and a resolve warning) on
purpose. These tests lock the exact findings -- the whole point of the fixture --
and confirm regforge still emits valid, byte-stable C for a flawed footprint.
"""

from regforge import __version__
from regforge.check import Severity, run_checks
from regforge.provenance import Provenance, sha256_file
from regforge.readers.svd import SvdReader
from regforge.resolve import resolve_defaults
from regforge.writers.c import CWriter

GOLDEN_COMMAND = "regforge tests/fixtures/svd/lint_demo.svd -o tests/golden/c/lint_demo.h"


def test_cross_peripheral_overlap_is_an_error(lint_demo_device):
    errors = [f for f in run_checks(lint_demo_device) if f.severity is Severity.ERROR]
    assert len(errors) == 1
    message = errors[0].message
    assert "UART" in message and "TIMER" in message and "overlapping" in message


def test_addressblock_warnings_are_flagged(lint_demo_device):
    messages = " ".join(
        f.message for f in run_checks(lint_demo_device) if f.severity is Severity.WARNING
    )
    assert "FLASH.FAR" in messages and "outside" in messages  # register outside its block
    assert "DMA: addressBlocks" in messages and "overlap" in messages  # intra-peripheral overlap


def test_resolve_warns_on_unspecified_access(lint_demo_svd_path):
    # Read fresh: the resolved fixture has already consumed the warnings.
    device = SvdReader().read(lint_demo_svd_path)
    warnings = resolve_defaults(device)
    assert any("MISC.REG" in w and "access unspecified" in w for w in warnings)


def test_header_matches_golden(lint_demo_device, lint_demo_svd_path, lint_demo_golden_path):
    provenance = Provenance(
        source_path="tests/fixtures/svd/lint_demo.svd",
        source_sha256=sha256_file(lint_demo_svd_path),
        tool_version=__version__,
        command=GOLDEN_COMMAND,
    )
    generated = CWriter().render(lint_demo_device, provenance)
    assert generated == lint_demo_golden_path.read_text(encoding="utf-8")

    # Note: the demo header is compiled across the full toolchain matrix by
    # tests/writers/c/test_compiles.py::test_lint_demo_header_compiles.
