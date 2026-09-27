# Defaults resolution rules

**Read from:** [`size`, `access`, `resetValue`, `resetMask`](formats/svd.md#register) &nbsp;·&nbsp; **Emitted as:** [member qualifiers and reset macros](targets/c.md#type-and-qualifiers)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register can omit `size`, `access`, `resetValue`, and `resetMask` and take
them from an enclosing element. regforge resolves this once before emission, so
writers read finished values.

Code: `regforge/resolve.py`. Tests: `tests/resolve/test_defaults.py`.

## Rule 1 — the inheritance chain

Each property is taken from the first level that declares it:

```
register  ->  peripheral  ->  device
```

`size` has one more step, falling back to the data bus width:

```
register <size>  ->  peripheral <size>  ->  device <size>  ->  device <width>
```

### Example

Input — read as [CMSIS-SVD](formats/svd.md#register):

```xml
<device>
  <width>32</width>
  <access>read-write</access>
  <peripherals><peripheral>
    <registers>
      <register><name>DR</name><addressOffset>0x0</addressOffset></register>
      <register><name>SR</name><addressOffset>0x4</addressOffset>
                <access>read-only</access></register>
```

Output — emitted as [C](targets/c.md#type-and-qualifiers):

```c
volatile uint32_t       DR;   /* size from <width>, access from <device> */
volatile const uint32_t SR;   /* its own access is used */
```

## Rule 2 — fields inherit from their register

A field with no `access` takes the register's resolved access. This runs after
the register is resolved, so the field never copies an unresolved value.

## Rule 3 — access missing at every level is reported

If no level declares `access`, regforge uses read-write and reports it:

```
warn: MISC.REG: access unspecified at every level -- defaulting to read-write (unverified)
```

Access decides whether the member is `const`. A read-only register is emitted as
`volatile const`, so writing it is a compile error.

## Rule 4 — [`resetMask`](formats/svd.md#register) is emitted only when partial

A mask covering the register's full width adds nothing to the width already
declared.

| Declared | Emitted |
|---|---|
| No [`resetValue`](formats/svd.md#register) | Nothing |
| `resetValue`, no mask | `..._RESET_VALUE` |
| Mask `0x0000FFFF` on a 32-bit register | `..._RESET_VALUE` and `..._RESET_MASK` |
| Mask `0xFFFFFFFF` on a 32-bit register | `..._RESET_VALUE` only |

## Corner cases

| Case | Result |
|---|---|
| A property absent at every level | Stays absent. No value is invented. |
| Register inheritance across peripherals | Handled by `resolve_derived`, not this pass. Both run before emission. |
| Running resolution twice | No change. Each step only fills values that are still unset. |
