# Derived register rules

**Read from:** [`derivedFrom`](formats/svd.md#derived-registers) &nbsp;·&nbsp; **Emitted as:** [register members](targets/c.md#register-members) and [field macros](targets/c.md#field-macros)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register can say that it is another register with a different name and
offset, and write only what differs. regforge copies the rest in once, before
defaults are resolved, so writers read a register that is complete. A
peripheral's `derivedFrom` works the same way for whole peripherals; see
[interrupts.md](interrupts.md) for what it does not carry.

Code: `regforge/resolve.py` (`resolve_derived`, `_resolve_register_bases`).
Tests: `tests/resolve/test_derived_registers.py`,
`tests/readers/svd/test_register_parser.py`.

## Registers

### Rule 1: what is inherited

Wherever the derived register states nothing, it takes the base's `size`,
`resetValue`, `resetMask`, `access`, `description`, `displayName`, `dataType`,
`protection`, `modifiedWriteValues`, `readAction` and `writeConstraint`, and its
fields. A value the base left to its own defaults is taken as unset, so it
resolves under the derived register's chain; see [defaults.md](defaults.md).

Its name and `addressOffset` are its own. Its `<dim>` is its own too, and so is
its `alternateRegister`: a view of another word is a fact about that register,
not about the one it was copied from. Fields are copies; changing the derived
register's field leaves the base's alone.

Input — read as [CMSIS-SVD](formats/svd.md#derived-registers):

```xml
<register>
  <name>CTRL1</name><addressOffset>0x0</addressOffset><size>32</size>
  <fields>
    <field><name>EN</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth></field>
    <field><name>MODE</name><bitOffset>1</bitOffset><bitWidth>2</bitWidth></field>
  </fields>
</register>
<register derivedFrom="CTRL1">
  <name>CTRL2</name><addressOffset>0x4</addressOffset>
</register>
```

Output — emitted as [C](targets/c.md#field-macros):

```c
/* TIM.CTRL2 */
#define TIM_CTRL2 (TIM->CTRL2)
#define TIM_CTRL2_EN_Pos (0U)
#define TIM_CTRL2_EN_Msk (0x00000001UL)
#define TIM_CTRL2_MODE_Pos (1U)
#define TIM_CTRL2_MODE_Msk (0x00000006UL)
```

### Rule 2: fields written on the derived register

A field with the name of one the base has replaces it, in the base's place. A
field the base lacks is added after the base's. Nothing the derived register
writes is lost.

### Rule 3: where the base is looked for

`derivedFrom` is a register name or a dotted path. It is read from the
peripheral or cluster that holds the derived register, then from the root of
its peripheral, then as `PERIPHERAL.REGISTER` or `PERIPHERAL.CLUSTER.REGISTER`
from the device.

| Written | Means |
|---|---|
| `CTRL1` | the register of that name beside it, else in its peripheral |
| `CH.CTRL` | the register `CTRL` of the cluster `CH` |
| `UART0.CTRL` | the register `CTRL` of the peripheral `UART0` |
| `PORT.PMUX0_%s` | the copies of the template `PMUX0_%s` in `PORT` |
| `CC[%s]` or `CC` | the array kept as `CC` |

### Rule 4: a base that is a template

Arrays are expanded first, so a template's name is gone by the time a
`derivedFrom` is read and the reference means its copies.

| Case | Result |
|---|---|
| a copy of a template derived from a template with the same number of copies (`PMUX1_%s` from `PMUX0_%s`) | each copy takes the copy of the same index; no finding |
| any other register naming a template | the first copy, and the reference is re-pointed at it; `WARNING` |
| the two templates have different numbers of copies | the first copy for all; `WARNING` |

### Rule 5: chains, and what cannot be resolved

The base is resolved first, so a chain `C` from `B` from `A` inherits a complete
set whatever order the file lists them in.

| Case | Result |
|---|---|
| no register of that name | nothing is inherited; `WARNING` |
| the register names itself | nothing is inherited; `WARNING` |
| a cycle (`A` from `B`, `B` from `A`) | reported once, each register keeps what it has; `WARNING` |
