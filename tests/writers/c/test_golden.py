"""Full C output must match the committed golden, byte for byte.

The golden is generated (with provenance on) by the canonical command below;
regenerate it with ``nox -s goldens``. The provenance is reconstructed here
with the same command and the real source hash so the comparison is
deterministic. When the regforge version changes, regenerate the golden.
"""

from regforge import __version__
from regforge.provenance import Provenance, sha256_file
from regforge.writers.c import CWriter

GOLDEN_COMMAND = "regforge tests/fixtures/svd/minimal.svd -o tests/golden/c/minimal.h"


def test_full_output_matches_golden(demo_device, minimal_svd_path, golden_header_path):
    provenance = Provenance(
        source_path="tests/fixtures/svd/minimal.svd",
        source_sha256=sha256_file(minimal_svd_path),
        tool_version=__version__,
        command=GOLDEN_COMMAND,
    )
    generated = CWriter().render(demo_device, provenance)
    assert generated == golden_header_path.read_text(encoding="utf-8")
