"""ChoiceParser: the base of the closed-vocabulary parsers."""

import xml.etree.ElementTree as ET

from regforge.ir import Access
from regforge.readers.svd.choice_parser import ChoiceParser


class _ModeParser(ChoiceParser[Access]):
    kind = Access
    tag = "mode"


def test_a_subclass_reads_the_tag_it_names():
    element = ET.fromstring("<x><mode>read-only</mode><access>write-only</access></x>")
    assert _ModeParser().parse(element) is Access.READ_ONLY


def test_a_subclass_reads_an_absent_or_unlisted_child_as_none():
    assert _ModeParser().parse(ET.fromstring("<x/>")) is None
    assert _ModeParser().parse(ET.fromstring("<x><mode>nope</mode></x>")) is None
