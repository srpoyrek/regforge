# Access rules

**Read from:** [`access`](formats/svd.md#register) &nbsp;·&nbsp; **Emitted as:** [`const` on a read-only member](targets/c.md#type-and-qualifiers), the access column of the HTML reference, and a finding on the command line

Add an input format or an output target and only those two links change;
the rule below is unchanged.


An access says what software may do with a register or a field: read it, write it, or both.
A file can state it at the device, peripheral, cluster, register and field level; the nearest
one wins, and a register that no level states is read-write with a warning (see
[defaults.md](defaults.md)). The rules about it live in one class, `AccessResolution`, which
knows only a field's access and the access of its register, as plain values: the
[field's class](fields.md) is given the register's, and asks for the check along with the rest
of its content.

Code: `regforge/resolution/access.py`, `regforge/resolution/field.py` (`access_findings`,
`content_findings`), `regforge/resolution/enum_usage.py` (`against`),
`regforge/readers/svd/choice_parser.py`, `regforge/ir/access.py`,
`regforge/writers/html/device/peripheral/register/access.py` (`AccessHtml`).
Tests: `tests/resolution/test_access_resolution.py`,
`tests/resolution/test_field_resolution.py`, `tests/resolution/test_enum_usage_resolution.py`,
`tests/readers/svd/test_choice_parser.py`, `tests/readers/svd/test_access_parser.py`.

## Reading: every value is kept or noted

The reader takes the schema's five words: `read-only`, `write-only`, `read-write`,
`writeOnce` and `read-writeOnce`. A value that differs from one of them only in case is read
as that word and noted. Any other value is ignored and noted, so an access is never dropped
without a trace. Every closed-vocabulary tag works this way, since the parsers of `access`,
`dataType`, `protection`, `modifiedWriteValues`, `readAction` and the enumerated `usage` share
one base.

Input — read as [CMSIS-SVD](formats/svd.md#register):

```xml
<register><name>DR</name><addressOffset>0x0</addressOffset><access>read-writeonce</access></register>
<register><name>CR</name><addressOffset>0x4</addressOffset><access>write</access></register>
```

Output — two notes on the command line:

```
warn: DR: <access>read-writeonce</access> read as read-writeOnce
warn: CR: <access>write</access> is not a CMSIS-SVD value -- ignored
```

`CR` then takes the access of the level above it, as if it had said nothing. Guessing that
`write` meant `write-only` would be inventing a value, so it is left to the person.

## Rule 1: a field cannot go beyond its register's access

A field can only be as accessible as the register that holds it. A field that can be written
in a read-only register, or read in a write-only one, contradicts it. The file disagrees with
itself, though the hardware could still be as it says, so a human decides: a `WARNING`.

Input — read as [CMSIS-SVD](formats/svd.md#field):

```xml
<register>
  <name>FSTR</name><addressOffset>0x0</addressOffset><size>8</size>
  <access>read-only</access>
  <fields>
    <field><name>ERR</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth>
      <access>read-write</access></field>
  </fields>
</register>
```

Output — a finding on the command line:

```
warn: FLASH_IF.FSTR.ERR: access is read-write, but its register is read-only
```

| Case | Result |
|---|---|
| a field that can be written, in a `read-only` register | reported |
| a field that can be read, in a `write-only` or `writeOnce` register | reported |
| a narrower field access than its register's (`read-only` in `read-write`) | nothing |
| a field with no access of its own | nothing: it takes its register's |
| an access that is still unresolved | nothing: it says nothing |
| copies of one `%s` template | each copy is judged |

## Rule 2: a set must not describe what the access forbids

A set of enumerated values that describes only writes (`<usage>write</usage>`) on a field that
cannot be written, or only reads on a field that cannot be read, contradicts the field: a
`WARNING`. A set with no usage describes both, which is the schema's default and says nothing,
so it is never reported.

```
warn: TIM.CTRL.F: the write set describes writes, but access is read-only
```

## Where access is written

The HTML reference writes it in four places: the peripheral's table of registers, the
register's header line, the register's row, and each field's row, as `RO`, `WO`, `RW`,
`WO (once)` or `RW (write once)`. The C header uses it to make a read-only register
`volatile const`.

## In your files

Across the 93 vendor files in the survey, the 240,401 `<access>` values are all kept or noted:
240,388 were the schema's own spelling, 9 were `read-writeonce` (Nordic nrf52833, nrf52840 and
nrf9160) and read as `read-writeOnce`, and 4 were `write` (GigaDevice GD32VF103), noted and
ignored. Before, those 13 were dropped silently.

Rule 1 reports 268 fields in 12 files: 243 read-write fields in read-only registers, 16
read-only fields in write-only registers, 7 read-write fields in write-only registers and 2
write-only fields in read-only registers. One Fujitsu file accounts for 199 of them
(`FLASH_IF.FSTR.ERR` is the usual one) and Espressif's esp32 for 36. Rule 2 reports nothing:
no set in the survey describes only what its field forbids. The clean fixture reports nothing.

## Not here yet

These stay in their present place until their own element is converted: handing an access
down the chain from the device to the register and the field, and the warning for a register
whose access no level states (21,748 registers in 20 files), both in the defaults rules
([defaults.md](defaults.md)).
