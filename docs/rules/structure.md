# Output structure rules

**Read from:** [every element](formats/svd.md) &nbsp;·&nbsp; **Emitted as:** [the file, block by block](targets/c.md#file-order)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A generated file is read top to bottom by people and by compilers, so its
blocks come in one fixed order, each block holds one topic, and nothing is
used before it is defined. Every target follows this page; a target page says
only how each block is spelled.

Code: `regforge/writers/templates/c/header.h.j2`.
Tests: `tests/writers/c/test_structure.py`.

## Rule 1: one topic per block, in this order

| # | Block | Holds, in this order | Present when |
|---|---|---|---|
| 1 | Banner | what the file is: device name and description, version, source license, provenance (source, hash, command, tool), the MISRA statement | always |
| 2 | Guard and includes | the include guard, then the standard headers the file needs | always |
| 3 | Compiler compatibility | the tool's portability prelude, include-guarded on its own so several generated files share one copy | always |
| 4 | Device | identity, then geometry: `SVD_VERSION`, `SVD_SHA256`; `ADDRESS_UNIT_BITS` with its assert, `BUS_WIDTH` | always |
| 5 | CPU | identity, capabilities, build guards, counts: `CPU_CORE`, `CPU_REVISION`; `HAS_FPU`, `HAS_MPU`, `HAS_VTOR`, `HAS_NVIC`; the endianness and FPU `#error` guards; `NUM_IRQS` | a `<cpu>` element |
| 6 | Interrupts | the vector enum | any interrupt |
| 7 | NVIC | priority facts and the priority helper (`NVIC_PRIO_BITS`, `NVIC_PRIO_FIELD_BITS`, `NVIC_PRIO_FIELD_MASK`, `IRQ_PRIO_LEVELS`, `irq_prio`); then, Cortex-M only, the word geometry, the register banks, the helpers | `nvicPrioBits`, or a Cortex-M core with interrupts |
| 8 | Peripherals | one section per family, Rule 3 | any peripheral |
| 9 | End guard | | always |

A block that has nothing to hold is omitted entirely, banner and all; an
empty block is never emitted.

## Rule 2: identity before geometry, facts before guards, helpers after their constants

Inside a block the order is: what the thing *is* (names, versions, hashes),
then what it *measures* (widths, counts, bits), then what the build must
*not get wrong* (`#error` guards, static asserts), then code that uses the
constants above it. So a hash is never between two widths, an NVIC fact is
never in the CPU block, and a helper never precedes the constant it reads.

## Rule 3: a peripheral section

Each family ([families.md](families.md)) is one section, and within it:

1. The family banner: name, description, instances, and the split note when
   the group was divided ([families.md](families.md#rule-3-a-split-under-a-groupname-is-reported)).
2. Layout constants, in member order ([targets/c.md](targets/c.md#layout-constants)).
3. Cluster types, innermost first, each followed by its own asserts
   ([clusters.md](clusters.md)).
4. The family struct, then its asserts: member offsets, array element sizes,
   union sizes, the struct size
   ([targets/c.md](targets/c.md#what-is-not-asserted)).
5. Per-instance type aliases, when the family has several instances.
6. One sub-section per instance: base address, typed instance macro,
   interrupt links, then a macro group per register in layout order (the
   accessor, reset value and mask, fields and their enumerated values), and
   the `dimArrayIndex` constants of its arrays.

## Rule 4: nothing before what it references

The order above is also the dependency order the language needs: constants
before the asserts that compare against them, a cluster's type before the
struct that has a member of it, the struct before the pointer that is cast to
it, the pointer before the macros that go through it, the vector enum before
the helpers that take it. A new element is placed by the same test: after
everything it names, in the block of its topic.

## Corner cases

| Case | Result |
|---|---|
| No `<cpu>` | no CPU block; the NVIC block appears only with `nvicPrioBits` or a Cortex-M core |
| `nvicPrioBits` on a core that is not Cortex-M | the NVIC block holds the priority facts and `irq_prio` alone |
| No interrupts | no Interrupts block, and no Cortex-M helpers, which take the enum |
| `deviceNumInterrupts` absent | `IRQ_COUNT` from the highest vector opens the NVIC helpers, since `NUM_IRQS` cannot |
| No provenance (`--no-provenance`) | the Device block starts at `SVD_VERSION`, or at `ADDRESS_UNIT_BITS` when the source has no version |
| No peripherals | no Peripherals block and no `<stddef.h>` |
