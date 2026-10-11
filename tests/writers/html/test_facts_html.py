"""FactsHtml: the block of a list of labelled facts."""

from regforge.writers.html.context import RenderContext
from regforge.writers.html.facts import FactsHtml


def test_it_shows_each_label_and_value_under_a_title():
    html = FactsHtml(RenderContext.default()).render("Device", [("Vendor", "DemoCorp")])
    assert "<caption>Device</caption>" in html
    assert "<th>Vendor</th><td>DemoCorp</td>" in html


def test_no_facts_give_no_table():
    assert FactsHtml(RenderContext.default()).render("Device", []) == ""
