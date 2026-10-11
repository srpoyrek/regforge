"""LicenseHtml: the block of the licence notice."""

from regforge.writers.html.context import RenderContext
from regforge.writers.html.license_notice import LicenseHtml


def test_it_shows_the_notice_in_a_collapsed_block():
    html = LicenseHtml(RenderContext.default()).render("Apache-2.0 <demo>")
    assert "<details>" in html and "Apache-2.0 &lt;demo&gt;" in html


def test_no_notice_gives_no_block():
    renderer = LicenseHtml(RenderContext.default())
    assert renderer.render(None) == "" and renderer.render("  \n ") == ""
