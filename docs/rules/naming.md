# Naming rules

**Read from:** [`groupName`, `headerStructName`, `derivedFrom`](formats/svd.md#peripheral) &nbsp;·&nbsp; **Emitted as:** [type names and aliases](targets/c.md#type-names)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


Which name a type gets. The rule picks a name string; how that string becomes an
identifier, and the extra per-peripheral aliases, belong to the target.

Examples show C output so the effect is visible.

Code: `regforge/families.py` (`family_name`, `group_families`, `_uniquify`),
`regforge/writers/c.py` (`_type_aliases`, `_alias_map`).
Tests: `tests/core/test_header_struct_name.py`,
`tests/core/test_type_name_collisions.py`.

## Rule 1: type name precedence

The type name is taken from the first of these that is present:

1. [`headerStructName`](formats/svd.md#peripheral) on the chain root
2. [`dimName`](formats/svd.md#arrays) on the template the chain root was expanded from
3. [`groupName`](formats/svd.md#peripheral) on the chain root
4. the chain root's own name

`headerStructName` sets the type name only. Which peripherals share a type is decided
by layout (see [families.md](families.md)).

Peripherals expanded from a `<dim>` template (`UART%s`) take the pattern's stem,
`UART`, as their `groupName` when they have none, so the copies share one type
named after the stem; a declared `groupName` or `headerStructName` still wins.
See [arrays.md](arrays.md#rule-5-peripheral-copies-form-one-family).

### Example

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```xml
<peripheral>
  <name>CAN_NODE0</name>
  <groupName>CAN</groupName>
  <headerStructName>CAN_NODE</headerStructName>
```

Output:

```c
typedef struct {
    volatile uint32_t NCR;  /* 0x00 */
    volatile uint32_t NSR;  /* 0x04 */
} can_node_t;
```

Complete versions: [the whole SVD](formats/svd.md#naming-precedence) and
[the whole header](targets/c.md#naming-precedence).

Without the rule the type would be `can_t`, taken from `groupName`. In Infineon
XMC files, `CAN_NODE0` and `CAN_MO` both use `groupName=CAN` but are different
structs, so `groupName` is not specific enough to name either one.

### All combinations

| `groupName` | `headerStructName` | type name |
|---|---|---|
| absent | absent | `P0` |
| `GRP` | absent | `GRP` |
| absent | `HSN` | `HSN` |
| `GRP` | `HSN` | `HSN` |
| `""` | absent | `P0` |
| absent | `""` | `P0` |
| `GRP` | `""` | `GRP` |

`<headerStructName></headerStructName>` parses as `None`. A value of only
whitespace parses as `""`. Both are skipped.

### Corner cases

Each case below is the actual generated output.

**The base declares `headerStructName` and the derived peripheral does not.**
The derived one inherits it, so both instances are the same type. In nRF files only `SPIM0`
declares `headerStructName`; `SPIM1` and `SPIM2` use [`derivedFrom`](formats/svd.md#peripheral). Without
inheritance they would fall to their own names, `spim1_t` and `spim2_t`, and the
shared type would not be shared.

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```xml
<peripheral>
  <name>SPIM0</name><groupName>SPIM</groupName><baseAddress>0x40003000</baseAddress>
  <headerStructName>SPIM</headerStructName>
  <registers>
    <register><name>ENABLE</name><addressOffset>0x500</addressOffset></register>
  </registers>
</peripheral>
<peripheral derivedFrom="SPIM0">
  <name>SPIM1</name><groupName>SPIM</groupName><baseAddress>0x40004000</baseAddress>
</peripheral>
```

Output — emitted as [C](targets/c.md#aliases):

```c
} spim_t;
typedef spim_t spim0_t;
typedef spim_t spim1_t;
REGFORGE_MAYBE_UNUSED static spim_t *const SPIM0 = (spim_t *)(uintptr_t)SPIM0_BASE;
REGFORGE_MAYBE_UNUSED static spim_t *const SPIM1 = (spim_t *)(uintptr_t)SPIM1_BASE;
```

**The derived peripheral declares `headerStructName` and the base does not.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
A0            registers: R                       (no headerStructName)
A1  derivedFrom=A0                               headerStructName=LATE
```

`A1` takes `A0`'s registers, so their layouts match. But `A1` has named its own
struct, and a peripheral that names a struct gets one.

Output — emitted as [C](targets/c.md#type-names):

```c
} a0_t;                /* A0 */
} late_t;              /* A1 */
typedef late_t a1_t;
```

Two types, not one. `A0` keeps its own name because it asked for nothing, and
`A1` gets the name it asked for.

**Both peripherals declare one, and they differ.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
T0   groupName=T   registers: R   headerStructName=TEE
T1   groupName=T   registers: R   headerStructName=OTHER
```

Same group, same registers, but each names its own struct.

Output — emitted as [C](targets/c.md#type-names):

```c
} tee_t;               /* T0 */
typedef tee_t t0_t;

} other_t;             /* T1 */
typedef other_t t1_t;
```

Two structs, because the source asked for two. Matching registers are not enough
to merge them when the vendor has given each one a name.

**Two unrelated peripherals declare the same `headerStructName`.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
X   registers: R      headerStructName=SHARED
Y   registers: R, S   headerStructName=SHARED
```

Different registers, so they are different structs. Both ask for the name
`SHARED`, and only one type can have it.

Output — emitted as [C](targets/c.md#type-names):

```c
} shared_t;            /* X */
typedef shared_t x_t;

} y_t;                 /* Y -- SHARED was taken, so it uses its own name */
```

The first one gets the requested name; the second falls back under Rule 3.

## Rule 2: naming the types when one group becomes several

A `groupName` says several peripherals belong together. regforge checks whether
they actually have the same registers, and when they do not it emits a separate
struct for each different layout (see [families.md](families.md)). That leaves a
naming problem: there is one group label and now more than one type, so they
cannot all be called after the group.

The rule: if one of those peripherals has a `<name>` equal to the group label,
its type is called after the group. Every other type is called after its own
peripheral.

### Example

STM32F7 has two peripherals, both `groupName=FPU`, with different registers:

```
FPU         registers: FPCCR, FPCAR, FPDSCR
FPU_CPACR   register:  CPACR
```

Output:

```c
typedef struct {
    volatile uint32_t CPACR;  /* 0x00 */
} fpu_cpacr_t;

typedef struct {
    volatile uint32_t FPCCR;  /* 0x00 */
    volatile uint32_t FPCAR;  /* 0x04 */
} fpu_t;
```

Complete versions: [the whole SVD](formats/svd.md#one-group-becoming-two-types)
and [the whole header](targets/c.md#one-group-becoming-two-types).

Without the rule, `FPU_CPACR` takes the group label and `FPU` is named after
itself, which is also `FPU` — two types called `fpu_t`, which the compiler
rejects as a redefinition.

### Corner cases

**No peripheral is named after the group.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
TIM1   groupName=TIM   registers: CR1, ARR, RCR
TIM2   groupName=TIM   registers: CR1, ARR
TIM3   groupName=TIM   registers: CR1, ARR
```

`TIM2` and `TIM3` have the same registers. `TIM1` has an extra one, so it cannot
share their struct. No peripheral is called `TIM`.

Output — emitted as [C](targets/c.md#type-names):

```c
} tim_t;               /* TIM2 and TIM3 */
typedef tim_t tim2_t;
typedef tim_t tim3_t;

} tim1_t;              /* TIM1 */
```

Nothing matches the label `TIM`, so it goes to the larger set, and `TIM1` is
named after itself.

**A peripheral is named after the group, but it is in the smaller set.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
CAN_MO0   groupName=CAN   registers: MOFCR, MOFGPR
CAN_MO1   groupName=CAN   registers: MOFCR, MOFGPR
CAN_MO2   groupName=CAN   registers: MOFCR, MOFGPR
CAN       groupName=CAN   register:  CLC
```

Three peripherals share one layout; `CAN` has a different one. A peripheral
*is* called `CAN`.

Output — emitted as [C](targets/c.md#type-names):

```c
} can_mo0_t;           /* CAN_MO0, CAN_MO1, CAN_MO2 */
typedef can_mo0_t can_mo1_t;
typedef can_mo0_t can_mo2_t;

} can_t;               /* CAN */
```

The label `CAN` goes to the peripheral called `CAN`, even though it is alone
against three. Size is only used when nothing matches the label.

**Nothing matches the label and the sets are the same size.**

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```
AAA   groupName=GRP   registers: R
BBB   groupName=GRP   registers: R, S
```

No peripheral is called `GRP`, and neither set is larger, so neither rule
decides. The label goes to whichever peripheral appears first in the file:

```
AAA declared first  ->  GRP is AAA's type, BBB's type is bbb_t
BBB declared first  ->  GRP is BBB's type, AAA's type is aaa_t
```

Reordering the peripherals in the source therefore changes which type is called
`grp_t`. Every other case is decided by the peripheral names, so this is the
only one where declaration order is used.

## Rule 3: every emitted type name is unique

Each family becomes one typedef. Two typedefs with the same name is a
redefinition error. Names are compared without case, because the writer
lowercases them.

If two families want one name, the second falls back to its root instance's
name, then to a numeric suffix. The family records the rename in its note, which
is printed in the header.

## Rule 4: a cluster's type is named inside its family

A cluster becomes a struct type of its own. Its name is the family's name, then
the cluster's [`headerStructName`](formats/svd.md#cluster) or, when absent, the
cluster's own name; a nested cluster appends its name to its parent's:

```
DMA  cluster CH                            ->  dma_ch_t
DMA  cluster CH  headerStructName=CHANNEL  ->  dma_channel_t
DMA  cluster CH  nested cluster SUB        ->  dma_ch_sub_t
```

The family prefix keeps the vendor habit of calling every channel block `CH`
from colliding across peripherals. Two clusters of one family asking for the
same name fall back to the cluster's own name, then to a numeric suffix, as in
Rule 3. Copies expanded from a `CH%s` template share one type named after the
stem, `dma_ch_t`, with members `CH0`, `CH1`, ... The member itself always keeps
the cluster's own name; only the type is renamed. Spelled as C in
[targets/c.md](targets/c.md#cluster-members).
