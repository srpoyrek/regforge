# Field rules

**Read from:** [`bitOffset`, `bitWidth`, `bitRange`](formats/svd.md#field) &nbsp;·&nbsp; **Emitted as:** [field macros](targets/c.md#field-macros), and a finding on the command line

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A field is a named run of a register's bits. The rules about a field live in one class,
`FieldResolution`, which says what is wrong in words. It knows its own element and the
level below it, the [bit](bits.md): it is given the register's width as a number and the
register's path, and knows nothing of the register itself. Which pairs of fields to
compare is for the level above, the register, which will take that walk over from
`collect`. A field is also a participant in the shared collision rule
(`CollisionResolution`), with bits as its space. It also holds the field's enumerated
sets, which it hands to the set class one by one and in pairs; see [enums.md](enums.md).
Two fields compared with each other are judged for the name they share as well as the
bits. Its write behaviour and read action go to their own classes, with the field's own
access; see [side-effects.md](side-effects.md).

Code: `regforge/resolution/field.py` (`FieldResolution`), `regforge/resolution/placeholder.py`
(`is_placeholder_name`), `regforge/ir/field.py` (`Field`, `runs`, `fits_in`),
`regforge/resolution/collector.py` (`collect`), `regforge/check.py` (`check_element_rules`).
Tests: `tests/resolution/test_field_resolution.py`, `tests/resolution/test_placeholder.py`,
`tests/resolution/test_collect.py`, `tests/core/test_field.py`.

## Rule 1: a field past the register's width is an error

A bit beyond the width has no storage: an `ERROR`. An array is measured to its last
copy, and copies of one `<dim>` template are reported together, since the template is what
needs fixing.

Input — read as [CMSIS-SVD](formats/svd.md#field):

```xml
<register>
  <name>R</name><addressOffset>0x0</addressOffset><size>32</size>
  <fields>
    <field><name>F</name><bitOffset>30</bitOffset><bitWidth>4</bitWidth></field>
  </fields>
</register>
```

Output — a finding on the command line:

```
error: P.R.F: bits 30..33 run past the 32-bit register
```

| Case | Result |
|---|---|
| a plain field at bits 30..33 of a 32-bit register | `P.R.F: bits 30..33 run past the 32-bit register` |
| an array `A[9]` of 4-bit copies from bit 0 | `P.R.A[9]: bits 0..35 run past the 32-bit register`, to the last copy |
| copies `M0`..`M8` of `M%s`, only `M8` past the width | `P.R.M%s: M8..M8 (1 of its 9 copies) run past the 32-bit register` |
| a field reaching exactly the last bit | fits; nothing |
| a register whose size is still unresolved | silent: the width is unknown |

The C writer refuses such a register with its own error; this finding is what the checks
report for every target.

## Rule 2: two fields on one bit are a warning

Two fields are compared by the bits they share, and the [bit class](bits.md) judges them:
a `WARNING`, one finding per run of shared bits and per pair of fields. Nothing is
reported for fields that only touch, or lie apart.

```
warn: TIM.CTRL: bit 1 is claimed by MODE and STATE
```

Not compared with each other, because something else already reports it:

| Case | Reported by |
|---|---|
| copies of one `%s` template overlapping each other | `expand_dim`, as an `ERROR` |
| a field array overlapping itself (a stride smaller than the field) | `check_address_math`, as an `ERROR` |

## Rule 3: two fields with one name are a warning

Each field becomes constants named after it (`TIM_CTRL_MODE_Pos`, `TIM_CTRL_MODE_Msk`), so
two fields of one register with one name make the same constant twice, with two different
values: the generated header defines `TIM_CTRL_MODE_Pos` as `(0U)` and again as `(4U)`. The
file contradicts itself, but the hardware could still be as it says, so a human decides: a
`WARNING`, one finding per pair of fields, saying where each sits. The two need not touch;
they are compared wherever they are in the register.

Input — read as [CMSIS-SVD](formats/svd.md#field):

```xml
<register>
  <name>CTRL</name><addressOffset>0x0</addressOffset><size>8</size>
  <fields>
    <field><name>MODE</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>
    <field><name>MODE</name><bitOffset>4</bitOffset><bitWidth>2</bitWidth></field>
  </fields>
</register>
```

Output — a finding on the command line:

```
warn: TIM.CTRL: the name MODE is used by two fields (bits 0..1 and bits 4..5)
```

| Case | Result |
|---|---|
| two fields with one name | `the name MODE is used by two fields (bits 0..1 and bits 4..5)` |
| three fields with one name | one finding per pair: first and second, first and third, second and third |
| a one-bit field | placed as `bit 7`, not `bits 7..7` |
| a field array | placed from its first bit to the last bit of its last copy: `bits 0..6` |
| one name on overlapping bits | two findings, the name first, then Rule 2: `bits 2..3 are claimed by X and X` |
| `Reserved`, `RESERVED_`, `reserved3` | nothing: a placeholder name, below |
| `Mode` and `MODE` | nothing: names are compared as written |
| copies of one `%s` template | nothing: the copies are not compared with each other |

### Placeholder names

Vendors call every unused run of bits `Reserved`, so one register often holds the name
many times. That is not two fields sharing a name, so it is not reported. A name is a
placeholder when it is `reserved` in any case, optionally followed by `_` or digits
(`Reserved`, `RESERVED_`, `reserved3`); `Reserved_BITS` is a real name. Two placeholder
fields on one bit are still two claimants (Rule 2). The same test exempts a repeated entry
name in an [enumerated set](enums.md). It decides only what is reported: the header
still defines the constants of every placeholder field, repeated ones included (see
[field macros](targets/c.md#field-macros)).

## In your files

Across the 93 vendor files in the survey, a register holds one field name more than once
1,574 times (3,621 fields beyond the first), and the name is always `Reserved` (3,468) or
`RESERVED` (153). So Rule 3 reports nothing in any of them. Two of the 43 headers the C
writer produces for the survey, NXP LPC1102 and LPC13xx, repeat the constants of their
placeholder fields (`I2C_CONSET_RESERVED_Pos` among them), which Rule 3 does not mention.

## Not here yet

These field matters stay in their present place until their own element is converted:
the stride of a field array against its width and the expansion of `%s` fields (the `dim`
rules), and a field's inherited `access` (the defaults). Enumerated values that do not
fit the field are reported now, by the set class (see [enums.md](enums.md)).
