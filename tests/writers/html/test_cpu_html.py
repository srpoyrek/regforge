"""CpuHtml: the block of the processor core."""

from regforge.ir import Cpu
from regforge.writers.html.context import RenderContext
from regforge.writers.html.cpu import CpuHtml


def test_it_shows_the_facts_the_file_states():
    cpu = Cpu(name="CM4", fpu_present=False, nvic_prio_bits=4)
    html = CpuHtml(RenderContext.default()).render(cpu)
    assert "<th>Core</th><td>CM4</td>" in html
    assert "<th>FPU</th><td>no</td>" in html
    assert "<th>NVIC priority bits</th><td>4</td>" in html


def test_it_leaves_out_what_the_file_does_not_say():
    html = CpuHtml(RenderContext.default()).render(Cpu(name="CM0"))
    assert "Revision" not in html and "MPU" not in html


def test_a_core_that_says_nothing_gives_no_table():
    assert CpuHtml(RenderContext.default()).render(Cpu()) == ""
