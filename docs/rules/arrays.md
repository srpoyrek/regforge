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
Every copy remembers the template it came from, so a later report about one
copy can point at the one declaration behind all of them.

A template can also fail to be one:

| Written | Result |
|---|---|
| `<dim>` 1 | one copy, `UART0`; the placeholder is still substituted; no finding |
| `<dim>` 0 | nothing: the element is dropped; `WARNING` (it declares nothing) |
| `<dim>` without `<dimIncrement>` | the copies' addresses are unknown: one instance, `UART`, with the placeholder removed; `ERROR` |
| `<dimIncrement>` without `<dim>` | meaningless alone: ignored; `WARNING` from the reader |
| `<dimIncrement>` 0 | every copy on one address; `ERROR`, and the copies are still made so the overlap is reported where it lands |

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
| register `[%s]` | larger than the element | not a packed array, so each element becomes a member of its own (`CH0`..`CH3`) with the holes as padding, and the `CH(i)` macro steps by the true stride; `WARNING` |
| register, cluster or field, either spelling | smaller than one element | `ERROR` finding: the elements overlap; the layout refuses it too (`LayoutError`, exit 4) |
| cluster `[%s]` | larger than its contents | the element struct is padded to the stride and its size asserted |
| cluster `[%s]` | smaller than its contents | refused: `LayoutError`, and an `ERROR` finding |

Both the finding and the refusal fire on the overlap case: the check runs first
and names it, the writer refuses second. The comparison happens after defaults
resolution, once every register has a size; see
[address-math.md](address-math.md#rule-4-addressunitbits-and-width-must-agree).

## Rule 4: labels come from `dimIndex`, else from 0

`dimIndex` supplies the labels that replace `%s`, in the spellings the
[format page](formats/svd.md#arrays) lists. Absent, the copies are numbered
from 0. An array (`[%s]`) is indexed by the language, so a `dimIndex` on one
names nothing: it is ignored and reported.

A label ends an identifier in the output, and every copy must get a name of
its own, so the list is made usable before it is applied. `dim` is the
authority on the count:

| Case | Result |
|---|---|
| two `%s` in the name (`PORT%s_PIN%s`) | every occurrence takes the same label (`PORT0_PIN0`); `WARNING` |
| fewer labels than `dim` (`0,1,2` for 4) | missing labels take their index: `0,1,2,3`; `WARNING` |
| more labels than `dim` | the extra labels are dropped; `WARNING` |
| a reversed range (`3-0`) | read as `0-3`; `WARNING` from the reader |
| a label that is not an identifier tail (`1.5`, `a b`) | rewritten with underscores (`1_5`, `a_b`), or its index when nothing is left; `WARNING` |
| repeated labels (`0,0,1`) | two copies cannot share a name: `ERROR`, and the whole list falls back to `0..N-1` |

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

## Rule 6: `dimName` names the type, `dimArrayIndex` names the indices

`dimName` is a name for the type the copies share. It ranks below
`headerStructName` and above `groupName` in [naming.md](naming.md), for a
peripheral template and for a cluster, whether the cluster is copies (`CH%s`)
or kept as an array (`CH[%s]`). On a register or field it names nothing, since
neither has a type of its own.

`dimArrayIndex` gives each index of an array a name. A kept array (register or
cluster) emits them as constants beside its accessor -- see
[targets/c.md](targets/c.md#array-members):

```c
/* DMA.CH[2] index names (dimArrayIndex) */
#define DC_DMA_CH_RX (0U)  /* receive channel */
#define DC_DMA_CH_TX (1U)
```

On a `%s` template the names have nothing to attach to, since each copy already
carries its label, and they are ignored without a finding.

## Rule 7: copies are checked like anything written out, and reported as copies

After expansion a copy is an ordinary peripheral, cluster, register or field,
so every check in [address-blocks.md](address-blocks.md) and
[address-math.md](address-math.md) sees it. What changes is the report:

| Case | Report |
|---|---|
| copies running past the `addressBlock` (`DATA%s` sixteen times in a `0x20` block) | one finding: `FIFO.DATA%s: DATA8..DATA15 (8 of its 16 copies, from offset 0x20) lie outside ...` |
| two copies overlapping each other (stride smaller than the footprint) | `ERROR`, ending `both expanded from one <dim> declaration (UART%s): its dimIncrement is smaller than the footprint` |
| the last copy running into another peripheral | `ERROR`, ending `UART3 was expanded from UART%s`, since the base peripheral looks fine by eye |
| a copy past `0xFFFFFFFF` (`baseAddress` `0xFFFFF000`, stride `0x1000`) | `ERROR`: regforge assumes 32-bit addresses today, and the C writer refuses the device rather than wrap the literal |

`dimIncrement` is in address units, like `addressOffset`: on a 16-bit-unit
device an increment of 2 is 4 bytes. It is converted where offsets are, never
assumed to be bytes.

## Rule 8: `derivedFrom` and `dim` together

Expansion runs before `derivedFrom`, so a derived peripheral can name a copy,
and a derived peripheral that is itself a template is split into shells
before its base's registers are copied into each. The remaining cases:

| Case | Result |
|---|---|
| `derivedFrom="UART1"` where `UART1` is a copy of `UART%s` | resolves; no finding |
| `derivedFrom="UART%s"`, the template itself | the template is gone once expanded, so the reference means its copies: resolved to the first copy, `UART0`, and re-pointed at it; `WARNING` |
| `dim` on the derived peripheral | three shells, each then inheriting the base's registers |
| base has `dim`, derived declares its own | the derived's own `dim` is used; no finding |
| derived declares only `dimIncrement` (or `dimIndex`, `dimName`) | a partial `dim`: `dim` and whatever else is unsaid come from the base template, the derived stride wins; no finding. A base with no `dim` to give is an `ERROR`, and the derived peripheral stays one instance |
| `derivedFrom` on a register | not parsed today; the same ordering rule will apply inside a peripheral when it is |

## Corner cases

| Case | Result |
|---|---|
| `%s` in the description | Left as written. The spec substitutes in `name` (and `displayName`) only. |
| `%s` without `dim`, a negative `dim` | Refused when the file is read; see [formats/svd.md](formats/svd.md#arrays). |
| `dim` on a name without `%s` | Accepted with a warning. Every copy would be one identifier, so the index (or `dimIndex` label) is appended: `UART` with `dim` 4 becomes `UART0`..`UART3`. Put `%s` in the name to choose where it goes. |
| `derivedFrom` naming the template (`UART%s`) | Not found: the template is gone once expanded. Name a copy instead. |
| Running expansion twice | No change. Copies carry no `dim`, and a kept array's `dim` is flagged as one, so neither is a template any more. |
| A stem with a dangling underscore (`PORT_%s`) | `PORT`. |
