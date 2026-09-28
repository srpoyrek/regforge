# addressBlock rules

**Read from:** [`addressBlock`](formats/svd.md#peripheral) &nbsp;·&nbsp; **Emitted as:** [members, padding and the size assert](targets/c.md#buffer-windows)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


`<addressBlock>` declares how much address space a peripheral occupies and what
that space holds. regforge uses it to set the struct's size, its padding, and a
`sizeof` static assert.

How blocks are spelled in C -- the member types, the padding names, the
asserts -- is in [targets/c.md](targets/c.md#register-members) and
[targets/c.md](targets/c.md#struct-size).

Code: `regforge/layout.py`.
Tests: `tests/core/test_layout.py`, `tests/check/test_address_blocks.py`,
`tests/check/test_unowned_gaps.py`.

## Rule 1: `usage` decides what is emitted

SVD defines three values. A block with no `usage` is treated as `registers`.

| `usage` | Emitted |
|---|---|
| `registers`, or absent | Named struct members, and the `sizeof` assert |
| `buffer` | One array member |
| `reserved` | Padding only |

### Example

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```xml
<addressBlock><offset>0</offset><size>0x8</size><usage>registers</usage></addressBlock>
<addressBlock><offset>0x8</offset><size>0x20</size><usage>buffer</usage></addressBlock>
```

Output — emitted as [C](targets/c.md#register-members):

```c
typedef struct {
    volatile uint32_t       DR;                              /* 0x00 */
    volatile const uint32_t SR;                              /* 0x04 */
    volatile uint32_t       BUFFER0[DC_UART_BUFFER0_COUNT];  /* 0x08  (buffer) */
} dc_uart_t;
REGFORGE_STATIC_ASSERT(offsetof(dc_uart_t, BUFFER0) == DC_UART_BUFFER0_OFFSET, DC_UART_BUFFER0_OFFSET_CHECK, "UART.BUFFER0 offset");
REGFORGE_STATIC_ASSERT(sizeof(dc_uart_t) == DC_UART_SIZE, DC_UART_SIZE_CHECK, "UART struct size vs addressBlock");
```

### Corner cases

| Case | Result |
|---|---|
| Naming the buffer member | `<addressBlock>` has no `<name>` element. In 79 vendor files, 0 of 6,832 blocks carry one. The member is named `BUFFER0`, `BUFFER1`, matching the `RESERVED0` scheme. |
| Element type of the buffer | Taken from `<device><width>`. A 32-bit bus gives `uint32_t`. |
| Window size not a multiple of the bus width | Falls back to `uint8_t`, so no bytes are lost. |
| A buffer block overlapping a register | `LayoutError`, naming the block. |
| `usage` value outside the three | Not a register window, so the peripheral gets no size assert. TI ships `FLASH Memory`, `SRAM`, `ROM Boot Loader` on 99 blocks; Espressif ships `TX FIFO`. Not yet reported as a finding. |
| `usage="buffer"` in vendor files | Does not occur. 0 of about 51,000 blocks tested. The rule is only exercised by a written fixture. |

## Rule 2: the `sizeof` assert

A peripheral gets a `sizeof` assert when exactly one block with `registers`
usage starts at offset 0 and has a non-zero size. `buffer` and `reserved` blocks
do not prevent it, because both are emitted.

The asserted size is the largest of:

- the register block's size
- the end of the last register
- the end of every other declared block

### Why the struct is padded to the block

```
UART0 at 0x40004000, UART1 at 0x40004400   -> 0x400 apart
sizeof(dc_uart_t) == 0x400                 -> ((dc_uart_t *)UART0_BASE)[1] is UART1
```

The struct size matches the hardware spacing, so an array over the instances
lands on the right addresses. The assert checks this at compile time.

### Corner cases

| Case | Result |
|---|---|
| Block smaller than the registers | The assert uses the register-derived size. `check_address_blocks` warns about the block. |
| Block size 0 | No assert. `sizeof(t) == 0` is not valid C. Espressif ships such blocks. |
| More than one `registers` block | No assert. |
| A `registers` block at a non-zero offset | No assert. |
| No block at all | No assert. This is 1,424 of 4,125 peripherals tested. |

## Rule 3: padding over space no block claims is reported

A struct cannot have holes, so space between registers becomes `RESERVED`
padding. When a block covers that space, the padding matches what the vendor
declared. When no block covers it, regforge reports it:

```
warn: UART2: [0x80, 0x200c0000) is padded into the struct but 537656320 byte(s)
      of it lie outside every declared addressBlock -- the peripheral never
      claimed that space
```

The padding is still emitted and the member offsets are still correct. Only the
report is added.

### Corner cases

| Case | Result |
|---|---|
| Up to 2 uncovered bytes | Not reported. The median gap across 2,499 measured gaps is 2 bytes. |
| Gap covered by two blocks between them | Not reported. No single block has to span it. |
| Gap partly covered | Reported, counting only the uncovered bytes. |
| Large gap fully inside one block | Not reported. A sifive PLIC declares one 64 MB block covering its whole span. |

The peripheral is not split into separate structs. Of the peripherals with the
largest spans, all but two declare a block covering the span, so splitting them
would contradict the source.

## Rule 4: blocks are inherited through [`derivedFrom`](formats/svd.md#peripheral)

The footprint belongs to the type, so a derived peripheral with no block of its
own copies its base's. Interrupts are not inherited; see
[interrupts.md](interrupts.md).

## Rule 5: two peripherals cannot occupy the same addresses

Overlapping extents are reported as an error. A peripheral's extent is its
blocks' ranges `[base+offset, base+offset+size)`, or the span of its registers
when it declares no block. When a peripheral involved was expanded from a
`<dim>` template the report says so, since the template is what needs fixing;
see [arrays.md](arrays.md#rule-7-copies-are-checked-like-anything-written-out-and-reported-as-copies).

`alternatePeripheral` is not parsed yet, so peripherals that legitimately share
an address, such as SPI and TWI on nRF parts, are currently reported too.
