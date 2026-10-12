# Bit rules

**Read from:** [`bitOffset`, `bitWidth`, `bitRange`](../../../formats/svd.md#field) &nbsp;·&nbsp; **Emitted as:** [field macros](../../../targets/c.md#field-macros), and a finding on the command line

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register is a row of bits, and a field names a run of them. A bit has no
attributes of its own: it is a position, the field that claims it, and its value
after reset. The rules about bits live in one class, `BitResolution`, which stands for
one bit and says what is wrong in words. It knows nothing above a bit: it is given the
bit's position and the label of whoever claims it. A rule that needs two bits is a
`compare` of two of them, and `compare_all` does it for two lists of bits at once.

`compare` is not specific to bits. It comes from `CollisionResolution`
(`regforge/resolution/collision.py`), the one rule every level that has collisions
shares: two claimants on one position of some space, whether a bit, an address, an
enumerated value's number or an interrupt vector. A class names its space (`unit`),
how serious a collision is there (`severity`) and the positions it occupies, and gets
the comparison, the joining of a run of positions into one finding and the message.
Positions are integers and claimants are labels, so the shared rule knows no element.

The levels above build on that, each knowing only itself and the level below: a field
compares its bits with another field's by calling the bit class, a register decides
which pairs of fields to compare, and so on up. Today the bit and the field exist, so
`collect`, the one place that knows the whole device, does the walk of the register
level: it picks the pairs of fields, gathers what every element's class finds, and the
command line prints it. The other elements still keep
their rules in the checks; they move to a class of their own one at a time.

Code: `regforge/ir/device/peripheral/register/bit.py` (`Bit`, `bits`, `claims`), `regforge/resolution/device/peripheral/register/bit.py`
(`BitResolution`), `regforge/resolution/collision.py` (`CollisionResolution`),
`regforge/resolution/collector.py` (`collect`), `regforge/check.py`
(`check_element_rules`).
Tests: `tests/ir/device/peripheral/register/test_bit.py`, `tests/resolution/device/peripheral/register/test_bit_resolution.py`,
`tests/resolution/test_collision.py`, `tests/resolution/test_collector.py`.

## Rule 1: the first declared field keeps a contested bit

The bit map gives each bit to one field. When two fields cover a bit, the one
declared first keeps it and the other gets the rest of its range. Both fields still
get their own macros, since a mask is what a field covers, not what it owns.

Input — read as [CMSIS-SVD](../../../formats/svd.md#field):

```xml
<register>
  <name>CTRL</name><addressOffset>0x0</addressOffset><size>8</size>
  <fields>
    <field><name>MODE</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>
    <field><name>STATE</name><bitOffset>1</bitOffset><bitWidth>2</bitWidth></field>
  </fields>
</register>
```

Output — emitted as [C](../../../targets/c.md#field-macros), each field with its own mask:

```c
#define TIM_CTRL_MODE_Pos (0U)
#define TIM_CTRL_MODE_Msk (0x00000003UL)
#define TIM_CTRL_STATE_Pos (1U)
#define TIM_CTRL_STATE_Msk (0x00000006UL)
```

In the HTML register reference, bit 1 reads `MODE` and `STATE` has bit 2 alone.

## Rule 2: two fields on one bit are a warning

The file contradicts itself, but the hardware could still be as it says, so a human
decides: a `WARNING`. Two bits are compared at a time, so the finding is per pair of
fields: one finding per run of consecutive shared bits, naming the two fields in the
order they were declared.

```
warn: TIM.CTRL: bit 1 is claimed by MODE and STATE
```

| Case | Result |
|---|---|
| `A` at bits 0..7 and `B` at bits 4..11 of a 16-bit register | `bits 4..7 are claimed by A and B`: one finding for the run |
| `A` at 0..7, `B` at 0, `C` at 6..7 | two findings: `bit 0 ... A and B`, `bits 6..7 ... A and C` |
| three fields on one bit | one finding per pair: `A and B`, `A and C`, `B and C` |
| two different fields with the same name | still two claimants on the bit: `Reserved and Reserved`; the shared name is the [field's](field/fields.md) own rule |
| a field array and a field | the array is named with its count, `OD[4] and X` |
| fields that only touch (`A` at 0..1, `B` at 2..3) | nothing |

Not reported here, because something else already reports it. The collector does not
compare those with each other, since only it knows about fields:

| Case | Reported by |
|---|---|
| copies of one `%s` template overlapping each other | `expand_dim`, as an `ERROR` |
| a field array overlapping itself (a stride smaller than the field) | `check_address_math`, as an `ERROR` |
| bits beyond the register's width | Rule 3 |
| a register whose size is still unresolved | nothing: the width is unknown |

## Rule 3: a field past the register's width is an error

A bit beyond the width has no storage: an `ERROR`. Copies of one `<dim>` template are
reported together, since the template is what needs fixing, and an array is measured
to its last element. This compares a field with its register, which is above a bit, so
it is the [field's](field/fields.md) rule, reported by `FieldResolution`.

```
error: P.R.F: bits 30..33 run past the 32-bit register
error: P.R.A[9]: bits 0..35 run past the 32-bit register
error: P.R.M%s: M8..M8 (1 of its 9 copies) run past the 32-bit register
```

## Corner cases

| # | Input | Result |
|---|---|---|
| 1 | a field exactly reaching the last bit | fits; nothing |
| 2 | two fields both past the width | Rule 3 for each (from the field class); no collision, since the bits do not exist |
| 3 | a copy of a template and a plain field on one bit | Rule 2, the copy named by its own name |
| 4 | an unresolved register size | silent: both rules need the width |
| 5 | a vendor file with overlapping fields | Rule 2; in the survey 108 of 116,583 registers, in 13 of 93 files (a `Reserved` field over a real one in 11 of them, in 2 files) |
