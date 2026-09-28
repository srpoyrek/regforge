# Address math rules

**Read from:** [`addressUnitBits`, `width`, `addressOffset`](formats/svd.md#device) &nbsp;·&nbsp; **Emitted as:** [member types and offsets](targets/c.md#type-and-qualifiers)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


How an offset in the source becomes a byte offset in the output.

How the resulting members are spelled is in [targets/c.md](targets/c.md#register-members).

Code: `regforge/layout.py`, `regforge/check.py` (`check_address_math`).
Tests: `tests/core/test_layout.py`, `tests/check/test_address_math.py`,
`tests/readers/svd/test_address_units.py`.

## Rule 1: offsets are stored in address units and converted at the end

`<addressUnitBits>` gives the number of bits one address step covers. It is 8 on
byte-addressable parts and 16 on word-addressable ones such as TI C2000. The IR
keeps offsets in address units. Conversion happens only where a byte-addressable
writer needs it:

```
bytes = units * addressUnitBits / 8
```

At 8 bits this changes nothing. It is a function rather than a fixed value
because other writers convert differently.

### Example

```
addressUnitBits = 16, register at unit offset 0x2  ->  byte offset 0x4
```

## Rule 2: the C writer rejects word-addressable devices

Rather than emit byte offsets that would be wrong, the C writer stops:

```
DemoMCU: addressUnitBits=16 (word-addressable, e.g. TI C2000) is not supported
by the C emitter yet -- offsets would be wrong if emitted as bytes.
```

The header also checks the assumption when it is compiled — see
[targets/c.md](targets/c.md#byte-width):

```c
#define DEMOMCU_ADDRESS_UNIT_BITS 8
REGFORGE_STATIC_ASSERT(CHAR_BIT == DEMOMCU_ADDRESS_UNIT_BITS, DEMOMCU_ADDRESS_UNIT_BITS_CHECK,
    "regforge: this header targets 8-bit address units; the compiler's CHAR_BIT disagrees.");
```

This catches a byte-addressed header built by a toolchain where `CHAR_BIT` is
16, which the generator cannot detect.

## Rule 3: the register type comes from its resolved size

| Size in bits | Type |
|---|---|
| 8 | `uint8_t` |
| 16 | `uint16_t` |
| 32 | `uint32_t` |
| 64 | `uint64_t` |
| anything else | `EmitError`, CLI exit 4 |

A 24-bit register stops generation by name instead of being rounded to 32.

## Rule 4: [`addressUnitBits`](formats/svd.md#device) and [`width`](formats/svd.md#device) must agree

| Condition | Severity |
|---|---|
| `addressUnitBits` is not a power of two | `WARNING` |
| `width` < `addressUnitBits` | `ERROR` |
| `width` is not a multiple of `addressUnitBits` | `ERROR` |
| Register size > bus width | `WARNING` |
| Register size is not a whole number of address units | `WARNING` |
| Register offset misaligned for its size | `WARNING` |
| Register array stride smaller than the element | `ERROR` |
| Cluster array stride smaller than the cluster's contents | `ERROR` |
| Field array increment smaller than the field width | `ERROR` |
| Field reaching past the register width | `ERROR` |
| Register array (`NAME[%s]`) stride larger than the element | `WARNING` |
| A peripheral reaching past the 32-bit address space | `ERROR` |

The power-of-two test is used instead of a fixed list of valid widths, so wider
buses stay correct without editing the check.

The `ERROR` rows describe hardware that cannot exist: a bus narrower than one
address step, or array elements that overlap each other. The `WARNING` rows
describe hardware that is unusual but possible, such as a register read in two
bus accesses. The array rows are checked only after defaults resolution, once
every register has a size to compare the stride against. A register inside a
cluster is checked at its offset from the peripheral.

## Rule 5: registers are placed in offset order with explicit padding

Registers are sorted by offset, and the space between them becomes `RESERVED`
padding, its length a named constant, so each member lands at its declared
offset. Each member's position is
checked at compile time — see [targets/c.md](targets/c.md#member-offsets):

```c
typedef struct {
    volatile uint32_t MODER;                               /* 0x00 */
    uint8_t           RESERVED0[DC_GPIOA_RESERVED0_SIZE];  /* 0x04  (reserved) */
    volatile uint32_t IDR;                                 /* 0x10 */
} dc_gpioa_t;
REGFORGE_STATIC_ASSERT(offsetof(dc_gpioa_t, IDR) == DC_GPIOA_IDR_OFFSET, DC_GPIOA_IDR_OFFSET_CHECK, "GPIOA.IDR offset");
```

### Corner cases

| Case | Result |
|---|---|
| Two registers overlap | `LayoutError` naming the register. Union and `alternateRegister` layouts are not implemented. |
| Register array (`NAME[%s]`) | One member spanning every element when the stride equals the element size. A larger stride leaves holes no C array can hold, so each element becomes a member of its own with the holes as padding (`WARNING`); the indexed macro still steps by the stride. A smaller stride means the elements overlap: an `ERROR` finding and a `LayoutError` (exit 4). |
| Addresses past `0xFFFFFFFF` | regforge assumes 32-bit addresses today. A peripheral reaching beyond is an `ERROR` finding, and the C writer refuses the device rather than wrap a literal. |
| Cluster | One member of its own struct type, laid out inside the same way. An array cluster's element is padded to the stride, so the array tiles exactly; a stride smaller than the contents is a `LayoutError` and an `ERROR` finding. |
| Empty cluster | `LayoutError`. There is no element to lay out (a cluster `derivedFrom` is not resolved yet). |
