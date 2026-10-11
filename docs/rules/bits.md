# Bit rules

**Read from:** [`bitOffset`, `bitWidth`, `bitRange`](formats/svd.md#field) &nbsp;·&nbsp; **Emitted as:** [field macros](targets/c.md#field-macros), and a finding on the command line

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register is a row of bits, and a field names a run of them. A bit has no
attributes of its own: it is a position, the field that claims it, and its value
after reset. The rules about bits live in one class, `BitResolution`, which says
what is wrong in words. It knows nothing above a bit: it is handed the register's
width and, for each bit position, the labels of whoever claims it. `collect` is the
one place that knows the whole device; it builds that data from the registers and
fields, gathers what every element's class finds, and the command line prints it.
The other elements still keep their rules in the checks; they move to a class of their
own one at a time.

Code: `regforge/ir/bit.py` (`Bit`, `bits`, `claims`), `regforge/resolution/bit.py`
(`BitResolution`), `regforge/resolution/collector.py` (`collect`),
`regforge/check.py` (`check_element_rules`).
Tests: `tests/core/test_bit.py`, `tests/resolution/test_bit_resolution.py`,
`tests/resolution/test_collect.py`.

## Rule 1: the first declared field keeps a contested bit

The bit map gives each bit to one field. When two fields cover a bit, the one
declared first keeps it and the other gets the rest of its range. Both fields still
get their own macros, since a mask is what a field covers, not what it owns.

Input — read as [CMSIS-SVD](formats/svd.md#field):

```xml
<register>
  <name>CTRL</name><addressOffset>0x0</addressOffset><size>8</size>
  <fields>
    <field><name>MODE</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>
    <field><name>STATE</name><bitOffset>1</bitOffset><bitWidth>2</bitWidth></field>
  </fields>
</register>
```

Output — emitted as [C](targets/c.md#field-macros), each field with its own mask:

```c
#define TIM_CTRL_MODE_Pos (0U)
#define TIM_CTRL_MODE_Msk (0x00000003UL)
#define TIM_CTRL_STATE_Pos (1U)
#define TIM_CTRL_STATE_Msk (0x00000006UL)
```

In the HTML register reference, bit 1 reads `MODE` and `STATE` has bit 2 alone.

## Rule 2: two fields on one bit are a warning

The file contradicts itself, but the hardware could still be as it says, so a human
decides: a `WARNING`, one finding per run of shared bits, naming every field in the
order they were declared.

```
warn: TIM.CTRL: bit 1 is claimed by MODE and STATE
```

| Case | Result |
|---|---|
| `A` at bits 0..7 and `B` at bits 4..11 of a 16-bit register | `bits 4..7 are claimed by A and B`: one finding for the run |
| `A` at 0..7, `B` at 0, `C` at 6..7 | two findings: `bit 0 ... A and B`, `bits 6..7 ... A and C` |
| three fields on one bit | all three named, `A and B and C` |
| a field array and a field | the array is named with its count, `OD[4] and X` |
| fields that only touch (`A` at 0..1, `B` at 2..3) | nothing |

Not reported here, because something else already reports it. The collector hands the
bit class one claimant for each of the first two, since only it knows about fields:

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
`check_address_math` still reports it; it moves to the field's class when that one is
converted.

```
error: P.R.F: bits 30..33 run past the 32-bit register
error: P.R.A[9]: bits 0..35 run past the 32-bit register
error: P.R.M%s: M8..M8 (1 of its 9 copies) run past the 32-bit register
```

## Corner cases

| # | Input | Result |
|---|---|---|
| 1 | a field exactly reaching the last bit | fits; nothing |
| 2 | two fields both past the width | Rule 3 for each (from `check_address_math`); no collision, since the bits do not exist |
| 3 | a copy of a template and a plain field on one bit | Rule 2, the copy named by its own name |
| 4 | an unresolved register size | silent: both rules need the width |
| 5 | a vendor file with a `Reserved` field over a real one | Rule 2; in the corpus 108 of 109,520 registers, in 13 of 88 files |
