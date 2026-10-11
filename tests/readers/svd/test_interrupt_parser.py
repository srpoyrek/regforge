"""InterruptParser: reads an <interrupt> element."""

import xml.etree.ElementTree as ET

from regforge.readers.svd.interrupt import InterruptParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_an_interrupt_reads_name_vector_and_description():
    irq = InterruptParser().parse(
        _el("<i><name>U1</name><value>21</value><description>UART 1</description></i>")
    )
    assert (irq.name, irq.value, irq.description) == ("U1", 21, "UART 1")
