"""InterruptHtml: the block of one interrupt."""

from regforge.ir import Interrupt
from regforge.writers.html.context import RenderContext
from regforge.writers.html.interrupt import InterruptHtml


def test_it_shows_name_vector_and_description():
    html = InterruptHtml(RenderContext.default()).render(Interrupt("U1", 21, "UART 1"))
    assert "<td>U1</td>" in html and "<td>21</td>" in html and "UART 1" in html


def test_an_interrupt_without_a_description_has_an_empty_cell():
    html = InterruptHtml(RenderContext.default()).render(Interrupt("U1", 21))
    assert "<td></td>" in html
