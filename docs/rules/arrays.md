# Array rules

**Read from:** [`dim`, `dimIncrement`, `dimIndex`](formats/svd.md#arrays) &nbsp;·&nbsp; **Emitted as:** [array members and indexed macros](targets/c.md#array-members)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


An element that exists several times over is written once, as a template, with
`dim` saying how many copies, `dimIncrement` how far apart, and `%s` in the
name where each copy's label goes. The three values mean the same thing on a
peripheral, a cluster, a register and a field.

Code: `regforge/resolve.py` (`expand_dim`), `regforge/layout.py`,
`regforge/check.py` (`check_address_math`).
Tests: `tests/resolve/test_dim.py`, `tests/core/test_layout.py`,
`tests/check/test_address_math.py`, `tests/writers/c/test_arrays.py`.

## Rule 1: expansion runs first and only copies

Templates are expanded straight after parsing, before `derivedFrom` and before
defaults, so a `derivedFrom="UART1"` can name a copy of `UART%s`, and a derived
peripheral that is itself a template is split into shells before its base's
registers are copied into each.

Expansion copies and renames; it never judges a stride. A register may still
have no `size` at that point (it arrives from the device `<width>` in defaults
resolution), so whether the stride fits is left to the checks and the layout,
which run later.

### Example

Input — read as [CMSIS-SVD](formats/svd.md#arrays):

```xml
<peripheral>
  <dim>4</dim><dimIncrement>0x400</dimIncrement>
  <name>UART%s</name><baseAddress>0x40000000</baseAddress>
```

Result, in the model:

| copy | name | baseAddress |
|---|---|---|
| 0 | `UART0` | `0x40000000` |
| 1 | `UART1` | `0x40000400` |
| 2 | `UART2` | `0x40000800` |
| 3 | `UART3` | `0x40000C00` |

Each copy gets its own deep copy of the registers, clusters, address blocks and
interrupts, and the copies replace the template at its position in the list.

## Rule 2: `NAME%s` is copies, `NAME[%s]` is an array

The spelling of the placeholder decides the shape:

| Written | Becomes | Emitted as [C](targets/c.md#array-members) |
|---|---|---|
| `DATA%s` | eight registers `DATA0`..`DATA7`, `dimIncrement` apart | eight ordinary members and macros |
| `DATA[%s]` | one register `DATA` that keeps its `dim` | `volatile uint32_t DATA[8];` and `DATA(i)` |
| `CH%s` (cluster) | eight clusters `CH0`..`CH7` sharing one type | eight members of `dma_ch_t` |
| `CH[%s]` (cluster) | one cluster `CH` that keeps its `dim` | `dma_ch_t CH[8];` and `CH_CTRL(i)` |
| `MODE%s` (field) | sixteen fields, `dimIncrement` **bits** apart | sixteen `_Pos` / `_Msk` pairs |
| `MODE[%s]` (field) | one field `MODE` that keeps its `dim` | `MODE_Pos(i)` / `MODE_Msk(i)` |
| `UART[%s]` (peripheral) | treated as `UART%s`, with a warning | separate instances |

A peripheral is an instance, not an array (`UART[0]` is not an identifier), so
array notation on one means copies.

### Example

Input — read as [CMSIS-SVD](formats/svd.md#register):

```xml
<register><dim>8</dim><dimIncrement>4</dimIncrement><name>DATA[%s]</name><addressOffset>0x10</addressOffset></register>
```

Output — emitted as [C](targets/c.md#array-members):

```c
volatile uint32_t DATA[8];   /* 0x10 */
#define FIFO_DATA_COUNT (8U)
#define FIFO_DATA(i) (*(volatile uint32_t *)(FIFO_BASE + 0x00000010UL + (i) * 0x00000004UL))
```

Complete versions: [the whole SVD](formats/svd.md#a-peripheral-array-with-a-register-array)
and [the whole header](targets/c.md#a-peripheral-array-with-a-register-array).

## Rule 3: an array's stride must fit its element

| Array | Stride | Result |
|---|---|---|
| register `[%s]` | equal to the element size | one packed array member |
| register `[%s]` | larger or smaller | refused: `LayoutError`, CLI exit 4, naming the register. A C array cannot hold space between elements; write `NAME%s` instead. |
| register, cluster or field, either spelling | smaller than one element | `ERROR` finding: the elements overlap |
| cluster `[%s]` | larger than its contents | the element struct is padded to the stride and its size asserted |
| cluster `[%s]` | smaller than its contents | refused: `LayoutError`, and an `ERROR` finding |

Both the finding and the refusal fire on the overlap case: the check runs first
and names it, the writer refuses second. The comparison happens after defaults
resolution, once every register has a size; see
[address-math.md](address-math.md#rule-4-addressunitbits-and-width-must-agree).

## Rule 4: labels come from `dimIndex`, else from 0

`dimIndex` supplies the labels that replace `%s`, in the three spellings the
[format page](formats/svd.md#arrays) lists. Absent, the copies are numbered
from 0. An array (`[%s]`) is indexed by the language, so a `dimIndex` on one
names nothing: it is ignored and reported.

```xml
<dim>3</dim><dimIncrement>0x1000</dimIncrement><dimIndex>A,B,C</dimIndex>
<name>GPIO%s</name><baseAddress>0x50000000</baseAddress>
```

gives `GPIOA` at `0x50000000`, `GPIOB` at `0x50001000`, `GPIOC` at `0x50002000`.

## Rule 5: peripheral copies form one family

Copies of `UART%s` take the pattern's stem, `UART`, as their `groupName` when
the template declares none, so [families.md](families.md) merges them into one
type with four instances instead of emitting four identical structs. A declared
`groupName` or `headerStructName` still wins, as in [naming.md](naming.md).

Interrupts are copied to every instance, `%s` substituted in their names. `dim`
cannot shift a vector number, so the copies share it; expansion reports that,
and the shared vector shows at each instance as in
[interrupts.md](interrupts.md#rule-3-one-vector-used-by-several-peripherals-appears-once).

## Corner cases

| Case | Result |
|---|---|
| `%s` in the description | Left as written. The spec substitutes in `name` (and `displayName`) only. |
| `dim` without `dimIncrement`, `dim` without `%s`, `%s` without `dim`, wrong label count, `dim` of 0 | Refused when the file is read; see [formats/svd.md](formats/svd.md#arrays). |
| `derivedFrom` naming the template (`UART%s`) | Not found: the template is gone once expanded. Name a copy instead. |
| Running expansion twice | No change. Copies carry no `dim`, and an array's bare name has no `%s`. |
| A stem with a dangling underscore (`PORT_%s`) | `PORT`. |
| `dimName`, `dimArrayIndex` | Not read. |
