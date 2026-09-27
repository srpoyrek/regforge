# Family rules

**Read from:** [`groupName`, `derivedFrom`](formats/svd.md#peripheral) &nbsp;·&nbsp; **Emitted as:** [one struct per family](targets/c.md#type-names)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


Which peripherals share one emitted type. Nothing here is specific to C: the
same grouping would decide a Rust or C++ struct.

Code: `regforge/families.py`.
Tests: `tests/core/test_families.py`, `tests/check/test_group_divergence.py`.

## Rule 1: grouping follows [`derivedFrom`](formats/svd.md#peripheral) and [`groupName`](formats/svd.md#peripheral)

A peripheral belongs to the family named by its `derivedFrom` chain root's
`groupName`, or by that root's name if it has no `groupName`. Peripherals linked
by `derivedFrom` and peripherals sharing a `groupName` both end up in one
candidate family.

### Example

Input:

```xml
<peripheral>
  <name>UART0</name><groupName>UART</groupName><baseAddress>0x40004000</baseAddress>
  <registers>
    <register><name>DR</name><addressOffset>0x0</addressOffset></register>
    <register><name>SR</name><addressOffset>0x4</addressOffset><access>read-only</access></register>
  </registers>
</peripheral>
<peripheral derivedFrom="UART0">
  <name>UART1</name><baseAddress>0x40004400</baseAddress>
</peripheral>
```

Output:

```c
typedef struct {
    volatile uint32_t       DR;  /* 0x00 */
    volatile const uint32_t SR;  /* 0x04 */
} uart_t;

typedef uart_t uart0_t;
typedef uart_t uart1_t;

REGFORGE_MAYBE_UNUSED static uart_t *const UART0 = (uart_t *)UART0_BASE;
REGFORGE_MAYBE_UNUSED static uart_t *const UART1 = (uart_t *)UART1_BASE;
```

Complete versions: [the whole SVD](formats/svd.md#two-peripherals-sharing-one-type)
and [the whole header](targets/c.md#two-peripherals-sharing-one-type).

### Corner cases

| Case | Result |
|---|---|
| `derivedFrom` chain more than one level deep | Works; the chain root decides the family. `check_derived_chains` warns, because other SVD tools handle chains inconsistently. |
| `derivedFrom` cycle | The walk stops instead of looping, and a warning is reported. |
| `derivedFrom` names a peripheral that does not exist | Warning; the peripheral is left empty. |
| Derived peripheral declares a different `groupName` | Ignored for grouping. The chain root's label is used. |

## Rule 2: members are compared before they are merged

`groupName` is a label, not a statement about layout. Vendors use one label for
peripherals with different registers: STM32's `TIM1` has `RCR` and `BDTR` that
`TIM2`–`TIM5` do not, and all four use `groupName=TIM`.

So members are compared, and members that do not match are split into separate
types. Two peripherals share a type when all of this matches:

- each register's name, offset, size, and access
- each addressBlock's offset, size, and usage

Access is included because it decides whether the member is `const`.
The blocks are included because they change the struct: a `buffer` block is a
member, a `reserved` block is padding, and the `registers` block sets the
asserted size.

### Example of why blocks are compared

Two peripherals with identical registers but different blocks:

```
UART0   addressBlock size 0x400
UART1   addressBlock size 0x100
```

If blocks were not compared, both would share one type sized 0x400, and `UART1`
would point at 1 KB when it owns 256 bytes. They are emitted as two types
instead, each sized from its own block.

### Corner cases

| Case | Result |
|---|---|
| Same registers, same blocks | One type. |
| Same registers, different blocks | Two types. The reported difference is [`addressBlock`](formats/svd.md#peripheral). |
| A `buffer` window on one instance only | Two types. The other instance must not get a member it did not declare. |
| `derivedFrom` override adds a register | Two types. No warning, because no `groupName` claimed they matched. |

## Rule 3: a split under a `groupName` is reported

When a `groupName` covers different layouts, a warning is emitted and the kept
family carries a note that appears in the header.

Warning:

```
warn: groupName 'TMR': members have differing layouts (first differs at RCR)
      -- the label is not one verified type; regforge emits separate types
```

Recorded in the output — see [targets/c.md](targets/c.md#type-names):

```c
/* family TMR: split 2 ways by layout (TMR0 | TIMER_ADV); first differs at RCR */
```

The reported difference is the first of:

1. a register present on one side only
2. the first register whose offset, size, or access differs
3. `addressBlock`

A split caused by a `derivedFrom` override is not reported, because no
`groupName` claimed the peripherals were one type.

## Rule 4: which peripheral defines the type

The type is built from the first member that has no `derivedFrom`. Its registers
and blocks define the struct; the other members are emitted as instances of it.
