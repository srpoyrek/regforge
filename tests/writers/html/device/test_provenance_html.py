"""ProvenanceHtml: the block saying where the document came from."""

from regforge.provenance import Provenance
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device.provenance import ProvenanceHtml


def test_it_names_the_source_the_hash_the_version_and_the_command():
    provenance = Provenance("some/dir/chip.svd", "ab" * 32, "0.0.1", "regforge chip.svd -o c.html")
    html = ProvenanceHtml(RenderContext.default()).render(provenance)
    assert "<b>chip.svd</b>" in html and "0.0.1" in html
    assert "abababababababab" in html and "ab" * 32 in html
    assert "regforge chip.svd -o c.html" in html


def test_no_provenance_gives_no_footer():
    assert ProvenanceHtml(RenderContext.default()).render(None) == ""
