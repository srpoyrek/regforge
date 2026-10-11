"""Full HTML output must match the committed goldens, byte for byte.

The goldens are generated (with provenance on) by the canonical commands below;
regenerate them with ``nox -s goldens``. The provenance is reconstructed here with
the same command and the real source hash, so the comparison is deterministic. When
the regforge version changes, regenerate the goldens.
"""

from pathlib import Path

from regforge import __version__
from regforge.provenance import Provenance, sha256_file
from regforge.writers.html import HtmlWriter

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "golden" / "html"


def _provenance(svd_path, name):
    return Provenance(
        source_path=f"tests/fixtures/svd/{name}.svd",
        source_sha256=sha256_file(svd_path),
        tool_version=__version__,
        command=f"regforge tests/fixtures/svd/{name}.svd -o tests/golden/html/{name}.html",
    )


def test_the_clean_chip_matches_its_golden(demo_device, minimal_svd_path):
    generated = HtmlWriter().render(demo_device, _provenance(minimal_svd_path, "minimal"))
    assert generated == (GOLDEN_DIR / "minimal.html").read_text(encoding="utf-8")


def test_the_flawed_chip_matches_its_golden(lint_demo_device, lint_demo_svd_path):
    generated = HtmlWriter().render(lint_demo_device, _provenance(lint_demo_svd_path, "lint_demo"))
    assert generated == (GOLDEN_DIR / "lint_demo.html").read_text(encoding="utf-8")


def test_the_goldens_have_no_trailing_whitespace_and_one_final_newline():
    # The repository's pre-commit hooks rewrite a golden that breaks either rule.
    for golden in GOLDEN_DIR.glob("*.html"):
        text = golden.read_text(encoding="utf-8")
        assert text.endswith("</html>\n"), golden.name
        assert all(line == line.rstrip() for line in text.splitlines()), golden.name
