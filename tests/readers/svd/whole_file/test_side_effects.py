"""SVD side-effect attributes: protection, data type, read action, write behaviour."""

from regforge.ir import (
    DataType,
    ModifiedWriteValues,
    Protection,
    ReadAction,
)
from regforge.readers.svd import SvdReader


def _read(tmp_path, *, device="", peripheral="", cluster="", register="", field="", enum=""):
    svd = tmp_path / "x.svd"
    svd.write_text(
        f"<device><name>X</name>{device}<peripherals><peripheral><name>P</name>"
        f"<baseAddress>0x0</baseAddress>{peripheral}<registers>{cluster}<register><name>R</name>"
        f"<addressOffset>0x0</addressOffset>{register}<fields><field><name>F</name>"
        f"<bitOffset>0</bitOffset><bitWidth>2</bitWidth>{field}{enum}</field></fields>"
        "</register></registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    return SvdReader().read(svd)


def _register(device):
    return device.peripherals[0].registers[0]


def test_a_register_reads_its_name_type_protection_and_side_effects(tmp_path):
    device = _read(
        tmp_path,
        register="<displayName>Control</displayName><dataType>uint32_t</dataType>"
        "<protection>s</protection><modifiedWriteValues>oneToClear</modifiedWriteValues>"
        "<readAction>clear</readAction>",
    )
    register = _register(device)
    assert register.display_name == "Control"
    assert register.data_type is DataType.UINT32
    assert register.protection is Protection.SECURE
    assert register.modified_write_values is ModifiedWriteValues.ONE_TO_CLEAR
    assert register.read_action is ReadAction.CLEAR


def test_a_pointer_data_type_keeps_its_spelling(tmp_path):
    device = _read(tmp_path, register="<dataType>uint8_t *</dataType>")
    assert _register(device).data_type is DataType.UINT8_PTR


def test_a_range_write_constraint(tmp_path):
    device = _read(
        tmp_path,
        register="<writeConstraint><range><minimum>1</minimum>"
        "<maximum>0x0A</maximum></range></writeConstraint>",
    )
    constraint = _register(device).write_constraint
    assert constraint is not None
    assert (constraint.minimum, constraint.maximum) == (1, 10)
    assert constraint.has_range


def test_flag_write_constraints_accept_true_and_one(tmp_path):
    device = _read(
        tmp_path,
        register="<writeConstraint><writeAsRead>true</writeAsRead>"
        "<useEnumeratedValues>1</useEnumeratedValues></writeConstraint>",
    )
    constraint = _register(device).write_constraint
    assert constraint is not None
    assert constraint.write_as_read is True
    assert constraint.use_enumerated_values is True


def test_anything_not_in_the_schema_list_is_read_as_absent(tmp_path):
    device = _read(
        tmp_path,
        register="<dataType>float</dataType><protection>x</protection>"
        "<readAction>bogus</readAction><modifiedWriteValues>never</modifiedWriteValues>",
    )
    register = _register(device)
    assert register.data_type is None and register.protection is None
    assert register.read_action is None and register.modified_write_values is None


def test_a_register_that_says_nothing_has_nothing(tmp_path):
    register = _register(_read(tmp_path))
    assert register.display_name is None and register.data_type is None
    assert register.protection is None and register.write_constraint is None


def test_a_field_reads_its_side_effects(tmp_path):
    device = _read(
        tmp_path,
        field="<modifiedWriteValues>zeroToSet</modifiedWriteValues>"
        "<readAction>modifyExternal</readAction>"
        "<writeConstraint><useEnumeratedValues>true</useEnumeratedValues></writeConstraint>",
    )
    field = _register(device).fields[0]
    assert field.modified_write_values is ModifiedWriteValues.ZERO_TO_SET
    assert field.read_action is ReadAction.MODIFY_EXTERNAL
    assert field.write_constraint is not None and field.write_constraint.use_enumerated_values


def test_protection_is_read_everywhere_the_schema_allows_it(tmp_path):
    # The schema allows it in the register properties group (device, peripheral, cluster and
    # register) and in an address block; every one is read.
    device = _read(
        tmp_path,
        device="<protection>n</protection>",
        peripheral="<protection>s</protection><addressBlock><offset>0x0</offset>"
        "<size>0x10</size><usage>registers</usage><protection>p</protection></addressBlock>",
        cluster="<cluster><name>C</name><addressOffset>0x0</addressOffset>"
        "<protection>p</protection></cluster>",
        register="<protection>n</protection>",
    )
    peripheral = device.peripherals[0]
    assert device.default_protection is Protection.NON_SECURE
    assert peripheral.default_protection is Protection.SECURE
    assert peripheral.address_blocks[0].protection is Protection.PRIVILEGED
    assert peripheral.clusters[0].default_protection is Protection.PRIVILEGED
    assert _register(device).protection is Protection.NON_SECURE


def test_a_device_level_protection_is_read_as_the_real_renesas_files_write_it(tmp_path):
    # Five SVDs in the public collections carry exactly this: one <protection>n</protection>
    # on the device, and nothing below it.
    device = _read(tmp_path, device="<protection>n</protection>")
    assert device.default_protection is Protection.NON_SECURE
    assert device.peripherals[0].default_protection is None
    assert _register(device).protection is None


def test_is_default_marks_the_catch_all_enumerated_value(tmp_path):
    device = _read(
        tmp_path,
        enum="<enumeratedValues>"
        "<enumeratedValue><name>OTHER</name><value>0</value>"
        "<isDefault>true</isDefault></enumeratedValue>"
        "<enumeratedValue><name>A</name><value>1</value></enumeratedValue>"
        "</enumeratedValues>",
    )
    values = _register(device).fields[0].enum_sets[0].values
    assert [v.is_default for v in values] == [True, False]
