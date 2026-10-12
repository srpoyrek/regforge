"""DeviceHtml: the block of the whole device, the document."""

from regforge.ir import Cpu, Device, Peripheral, Register
from regforge.provenance import Provenance
from regforge.writers.html.context import RenderContext
from regforge.writers.html.device.device import DeviceHtml


def _render(device, provenance=None):
    return DeviceHtml(RenderContext.default()).render(device, provenance)


def test_it_is_a_complete_page_with_a_title():
    html = _render(Device(name="Chip"))
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Chip register reference</title>" in html and html.rstrip().endswith("</html>")


def test_it_shows_the_description_facts_and_core():
    device = Device(
        name="Chip",
        description="A demo chip",
        vendor="DemoCorp",
        cpu=Cpu(name="CM4"),
        license_text="Apache-2.0",
    )
    html = _render(device)
    for text in ("A demo chip", "<th>Vendor</th><td>DemoCorp</td>", "<th>Core</th><td>CM4</td>"):
        assert text in html
    assert "<details>" in html


def test_it_lists_every_peripheral_in_the_contents_and_as_a_section():
    device = Device(
        name="Chip",
        peripherals=[
            Peripheral("A", 0x0, registers=[Register("R", 0x0, size=32)]),
            Peripheral("B", 0x100),
        ],
    )
    html = _render(device)
    assert 'href="#A"' in html and 'href="#B"' in html
    assert 'id="A"' in html and 'id="B"' in html and 'id="A.R"' in html


def test_it_escapes_everything_it_is_given():
    html = _render(Device(name="Chip", description="<script>alert(1)</script>"))
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_it_adds_the_provenance_footer_when_given_one():
    provenance = Provenance("chip.svd", "cd" * 32, "0.0.1", "regforge chip.svd")
    assert "<footer>" in _render(Device(name="Chip"), provenance)
    assert "<footer>" not in _render(Device(name="Chip"))


def test_the_fixture_renders_every_register_of_every_peripheral(demo_device):
    html = str(_render(demo_device))
    for peripheral in demo_device.peripherals:
        assert f'id="{peripheral.name}"' in html
        for register in peripheral.registers:
            assert f'id="{peripheral.name}.{register.name}"' in html
