# Side-effect rules

**Read from:** [`modifiedWriteValues`, `readAction`, `protection`](formats/svd.md#kept-not-yet-acted-on) &nbsp;·&nbsp; **Emitted as:** a finding on the command line (the [C header](targets/c.md) does not use these settings yet)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register or a field can say what a write does to it (`modifiedWriteValues`: a write of 1
clears the bit, any write sets the field) and what a read does besides returning the value
(`readAction`: a read clears it, a read pops a FIFO). Each setting is its own element with
its own class. A class knows only the setting and the access written beside it, not what
carries them: the [field's class](fields.md) hands each its own access, and the collector
does the same for a register.

- `ModifiedWriteValuesResolution` is a write behaviour.
- `ReadActionResolution` is a read action.

Code: `regforge/resolution/modified_write_values.py`, `regforge/resolution/read_action.py`,
`regforge/resolution/field.py` (`effects`, `effect_findings`),
`regforge/resolution/collector.py`, `regforge/ir/device/peripheral/register/modified_write_values.py`,
`regforge/ir/device/peripheral/register/read_action.py`, `regforge/ir/device/access.py`.
Tests: `tests/resolution/test_modified_write_values_resolution.py`,
`tests/resolution/test_read_action_resolution.py`,
`tests/resolution/test_field_resolution.py`, `tests/resolution/test_collect.py`.

## Rule 1: a write behaviour needs an access that can write

A write behaviour says what a write does, so it contradicts an access that forbids writing.
The file disagrees with itself, though the hardware could still be as it says, so a human
decides: a `WARNING`.

Input — read as [CMSIS-SVD](formats/svd.md#kept-not-yet-acted-on):

```xml
<register>
  <name>CTRL</name><addressOffset>0x0</addressOffset><size>8</size>
  <access>read-only</access>
  <fields>
    <field><name>DONE</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth>
      <modifiedWriteValues>oneToClear</modifiedWriteValues></field>
  </fields>
</register>
```

The field has no access of its own, so it takes the register's, `read-only`.

Output — a finding on the command line:

```
warn: TIM.CTRL.DONE: modifiedWriteValues oneToClear describes a write, but access is read-only
```

| Case | Result |
|---|---|
| any write behaviour beside `read-only` | `modifiedWriteValues oneToClear describes a write, but access is read-only` |
| `modify`, the schema's default, beside `read-only` | reported too: it is spelled out beside an access that cannot write |
| `read-write`, `write-only`, `writeOnce`, `read-writeOnce` | nothing |
| an access that is still unresolved | nothing: it counts as read-write |
| a field that says `read-only` in a read-write register | judged against the field's own access |
| copies of one `%s` template | each copy is judged |

A register's own write behaviour is judged against the register's own access in the same
way.

## Rule 2: a read action needs an access that can read

A read action says what a read does, so it contradicts an access that cannot be read:
`write-only`, or `writeOnce`, which cannot be read back. A `WARNING`, for the same reason.

```
warn: USBD.EPSTALL: readAction modifyExternal describes a read, but access is write-only
```

| Case | Result |
|---|---|
| any read action beside `write-only` | `readAction clear describes a read, but access is write-only` |
| any read action beside `writeOnce` | reported, naming `writeOnce` |
| `read-only`, `read-write`, `read-writeOnce` | nothing |
| an access that is still unresolved | nothing: it counts as read-write |
| a flag that clears when read and also on a write of 1 | nothing: a normal flag |

## Not reported

The survey says these are normal, so no rule flags them:

| Case | In the survey |
|---|---|
| `modifyExternal` on a writable register (the schema only recommends read-only) | 405 of the 495 registers that have it |
| a per-bit write behaviour (`oneToClear` and kin) on a field wider than one bit | 200 fields |
| a field and its register both giving a write behaviour, or both a read action | 24 each |
| a field with both a write behaviour and a read action | 895 |

## Protection

`<protection>` says which accesses may reach an element: `s` needs secure permission, `n`
accepts a non-secure access (and a secure one), `p` needs privileged permission. It came
with CMSIS-SVD 1.3 as a register property, a default at device, peripheral and cluster level
and a value on a register, and with 1.3.2 for an address block. The schema uses the same
values for the CPU's SAU configuration (`protectionWhenDisabled`), which regforge does not
read. Every other place is read ([the SVD page](formats/svd.md#kept-not-yet-acted-on)), and
the HTML reference shows a register's own protection.

No class judges it. The schema lets any register override the protection it would inherit,
so no combination of values contradicts itself, and the data has nothing to flag: 5 of the
93 survey files carry one, each a single device-level `n` (Renesas RA2E1, RA2E2, RA2L1, RA4E1
and RA4M2) that nothing below it overrides. They are the only files with a `<protection>`
element among the 2,474 SVD files of four public collections (cmsis-svd-data, NXP's
mcux-soc-svd, ST's STM32 set and ARM's own device files). The address-block form and the SAU
configuration occur in none of the 2,459 files of the first three. A register shows only a
protection it states itself; handing the default down the chain belongs with the defaults
rules.

## In your files

Across the 93 vendor files in the survey (116,583 registers, 508,281 fields), 3,322 fields
and 109 registers give a write behaviour, and 2,118 fields and 498 registers a read action.
The rules report 18 findings in 5 files: 16 write behaviours beside a read-only access (in
3 files, 8 of them `modify`, for instance `OCOTP.HW_OCOTP_CTRL_CLR.BUSY` and the
`UA_MSR.DCTSF` flag of the Nuvoton UARTs) and 2 read actions beside a write-only access (the
`USBD.EPSTALL` register of two Nordic files). The clean fixture reports nothing.

## Not here yet

These stay in their present place until their own element is converted: a write
constraint against the access and the enumerated values, the register as a class of its
own, and handing `protection` down the chain with the other defaults.
