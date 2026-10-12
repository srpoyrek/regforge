"""ChoiceParser: the base of the closed-vocabulary parsers, and what every one of them inherits."""

import xml.etree.ElementTree as ET

import pytest

from regforge.ir import (
    Access,
    DataType,
    EnumUsage,
    ModifiedWriteValues,
    Protection,
    ReadAction,
)
from regforge.readers.svd import SvdReader
from regforge.readers.svd.choice_parser import ChoiceParser
from regforge.readers.svd.device.access import AccessParser
from regforge.readers.svd.device.peripheral.register.data_type import DataTypeParser
from regforge.readers.svd.device.peripheral.register.field.enum_set.enum_usage import (
    EnumUsageParser,
)
from regforge.readers.svd.device.peripheral.register.modified_write_values import (
    ModifiedWriteValuesParser,
)
from regforge.readers.svd.device.peripheral.register.read_action import ReadActionParser
from regforge.readers.svd.device.protection import ProtectionParser
from regforge.readers.svd.element_parser import ParseContext

PARSERS = [
    AccessParser,
    DataTypeParser,
    EnumUsageParser,
    ModifiedWriteValuesParser,
    ProtectionParser,
    ReadActionParser,
]


class _ModeParser(ChoiceParser[Access]):
    kind = Access
    tag = "mode"


def test_a_subclass_reads_the_tag_it_names():
    element = ET.fromstring("<x><mode>read-only</mode><access>write-only</access></x>")
    assert _ModeParser().parse(element) is Access.READ_ONLY


def test_a_subclass_reads_an_absent_or_unlisted_child_as_none():
    assert _ModeParser().parse(ET.fromstring("<x/>")) is None
    assert _ModeParser().parse(ET.fromstring("<x><mode>nope</mode></x>")) is None


# --- what every closed-vocabulary parser inherits -----------------------------------------


def test_every_closed_vocabulary_parser_inherits_from_it():
    assert all(issubclass(parser, ChoiceParser) for parser in PARSERS)


@pytest.mark.parametrize("parser_class", PARSERS)
def test_every_parser_reads_a_spelling_that_differs_only_in_case(parser_class):
    tag = parser_class.tag
    for member in parser_class.kind:
        shouted = member.value.upper()
        context = ParseContext()
        element = ET.fromstring(f"<x><name>N</name><{tag}>{shouted}</{tag}></x>")
        assert parser_class(context).parse(element) is member
        assert context.warnings == [f"N: <{tag}>{shouted}</{tag}> read as {member.value}"]


@pytest.mark.parametrize("parser_class", PARSERS)
def test_every_parser_notes_a_value_it_cannot_read_and_ignores_it(parser_class):
    tag = parser_class.tag
    context = ParseContext()
    element = ET.fromstring(f"<x><name>N</name><{tag}>bogus</{tag}></x>")
    expected = EnumUsage.READ_WRITE if parser_class is EnumUsageParser else None
    assert parser_class(context).parse(element) is expected
    assert context.warnings == [f"N: <{tag}>bogus</{tag}> is not a CMSIS-SVD value -- ignored"]


@pytest.mark.parametrize("parser_class", PARSERS)
def test_the_schemas_own_spelling_is_read_without_a_note(parser_class):
    tag = parser_class.tag
    for member in parser_class.kind:
        context = ParseContext()
        element = ET.fromstring(f"<x><{tag}>{member.value}</{tag}></x>")
        assert parser_class(context).parse(element) is member
        assert context.warnings == []


def test_white_space_around_a_value_is_not_a_difference():
    context = ParseContext()
    element = ET.fromstring("<x><access>  read-write </access></x>")
    assert AccessParser(context).parse(element) is Access.READ_WRITE
    assert context.warnings == []


def test_a_parser_without_a_context_reads_the_same_and_says_nothing():
    corrected = ET.fromstring("<x><access>read-writeonce</access></x>")
    unknown = ET.fromstring("<x><access>write</access></x>")
    assert AccessParser().parse(corrected) is Access.READ_WRITE_ONCE
    assert AccessParser().parse(unknown) is None


def test_the_note_names_the_element_by_its_name_or_else_by_its_tag():
    context = ParseContext()
    AccessParser(context).parse(ET.fromstring("<register><access>write</access></register>"))
    assert context.warnings == [
        "register: <access>write</access> is not a CMSIS-SVD value -- ignored"
    ]


_EVERY_TAG_SHOUTED = (
    "<device><name>X</name><access>READ-WRITE</access><protection>N</protection>"
    "<peripherals><peripheral><name>P</name><baseAddress>0x0</baseAddress>"
    "<access>Read-Only</access><protection>S</protection>"
    "<addressBlock><offset>0x0</offset><size>0x10</size><usage>registers</usage>"
    "<protection>P</protection></addressBlock>"
    "<registers>"
    "<cluster><name>C</name><addressOffset>0x0</addressOffset>"
    "<access>WRITE-ONLY</access><protection>P</protection>"
    "<register><name>CR</name><addressOffset>0x0</addressOffset></register></cluster>"
    "<register><name>R</name><addressOffset>0x4</addressOffset>"
    "<access>read-writeonce</access><dataType>UINT32_T</dataType><protection>S</protection>"
    "<modifiedWriteValues>ONETOCLEAR</modifiedWriteValues><readAction>CLEAR</readAction>"
    "<fields><field><name>F</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth>"
    "<access>READ-ONLY</access>"
    "<enumeratedValues><usage>WRITE</usage>"
    "<enumeratedValue><name>A</name><value>0</value></enumeratedValue>"
    "</enumeratedValues></field></fields></register>"
    "</registers></peripheral></peripherals></device>"
)


def test_every_closed_vocabulary_tag_of_a_file_is_read_whatever_its_case(tmp_path):
    svd = tmp_path / "shouted.svd"
    svd.write_text(_EVERY_TAG_SHOUTED, encoding="utf-8")
    reader = SvdReader()
    device = reader.read(svd)
    peripheral = device.peripherals[0]
    cluster = peripheral.clusters[0]
    register = peripheral.registers[0]
    field = register.fields[0]
    assert (device.default_access, device.default_protection) == (
        Access.READ_WRITE,
        Protection.NON_SECURE,
    )
    assert (peripheral.default_access, peripheral.default_protection) == (
        Access.READ_ONLY,
        Protection.SECURE,
    )
    assert peripheral.address_blocks[0].protection is Protection.PRIVILEGED
    assert (cluster.default_access, cluster.default_protection) == (
        Access.WRITE_ONLY,
        Protection.PRIVILEGED,
    )
    assert register.access is Access.READ_WRITE_ONCE
    assert register.data_type is DataType.UINT32
    assert register.protection is Protection.SECURE
    assert register.modified_write_values is ModifiedWriteValues.ONE_TO_CLEAR
    assert register.read_action is ReadAction.CLEAR
    assert field.access is Access.READ_ONLY
    assert field.enum_sets[0].usage is EnumUsage.WRITE
    # one note for each of the fourteen tags, none of them silent
    assert len(reader.warnings) == 14
    assert all("read as" in warning for warning in reader.warnings)


def test_a_misspelt_access_is_corrected_or_noted_never_dropped_silently(tmp_path):
    svd = tmp_path / "vendor.svd"
    svd.write_text(
        "<device><name>X</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress><registers><register><name>R</name>"
        "<addressOffset>0x0</addressOffset><access>read-writeonce</access>"
        "<fields><field><name>F</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth>"
        "<access>write</access></field></fields></register></registers></peripheral>"
        "</peripherals></device>",
        encoding="utf-8",
    )
    reader = SvdReader()
    register = reader.read(svd).peripherals[0].registers[0]
    assert register.access is Access.READ_WRITE_ONCE
    assert register.fields[0].access is None
    assert reader.warnings == [
        "R: <access>read-writeonce</access> read as read-writeOnce",
        "F: <access>write</access> is not a CMSIS-SVD value -- ignored",
    ]
