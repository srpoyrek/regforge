"""CpuParser: reads the <cpu> element."""

import xml.etree.ElementTree as ET

from regforge.readers.svd.cpu import CpuParser


def _el(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_the_cpu_block_reads_its_nine_facts():
    cpu = CpuParser().parse(
        _el(
            "<cpu><name>CM4</name><revision>r0p1</revision><endian>little</endian>"
            "<mpuPresent>1</mpuPresent><fpuPresent>false</fpuPresent>"
            "<vtorPresent>true</vtorPresent><nvicPrioBits>4</nvicPrioBits>"
            "<vendorSystickConfig>0</vendorSystickConfig>"
            "<deviceNumInterrupts>32</deviceNumInterrupts></cpu>"
        )
    )
    assert (cpu.name, cpu.revision, cpu.endian) == ("CM4", "r0p1", "little")
    assert (cpu.mpu_present, cpu.fpu_present, cpu.vtor_present) == (True, False, True)
    assert (cpu.nvic_prio_bits, cpu.vendor_systick, cpu.num_interrupts) == (4, False, 32)
