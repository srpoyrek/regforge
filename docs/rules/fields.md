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
(`CollisionResolution`), with bits as its space.

Code: `regforge/resolution/field.py` (`FieldResolution`), `regforge/ir/field.py`
(`Field`, `runs`, `fits_in`), `regforge/resolution/collector.py` (`collect`),
`regforge/check.py` (`check_element_rules`).
Tests: `tests/resolution/test_field_resolution.py`, `tests/resolution/test_collect.py`,
`tests/core/test_field.py`.

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

## Not here yet

These field matters stay in their present place until their own element is converted:
the stride of a field array against its width and the expansion of `%s` fields (the `dim`
rules), a field's inherited `access` (the defaults), and enumerated values that do not
fit the field (the enumerated-value rules).
