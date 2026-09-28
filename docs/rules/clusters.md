# Cluster rules

**Read from:** [`cluster`](formats/svd.md#cluster) &nbsp;·&nbsp; **Emitted as:** [cluster members](targets/c.md#cluster-members)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A cluster is a named group of registers inside a peripheral, at an offset of
its own: a DMA channel's control block, a timer's capture unit. It may nest,
and it may be an array. It is the only container inside a peripheral; it holds
registers and clusters, never interrupts, address blocks or fields.

Code: `regforge/ir.py` (`Cluster`), `regforge/layout.py` (`cluster_layout`),
`regforge/writers/c.py` (`_cluster_types`).
Tests: `tests/readers/svd/test_clusters.py`, `tests/core/test_layout.py`,
`tests/writers/c/test_clusters.py`.

## Rule 1: a cluster is one member of its own type

Its registers are laid out inside it exactly as a peripheral's are: offsets
relative to the cluster, gaps padded, overlaps refused. The cluster then takes
one slot in its parent at its own offset, sized to its extent rounded up to
the type's alignment, and that size is asserted so the inner struct is checked
on its own terms. The emitted type is defined before the struct that uses it.

### Example

Input — read as [CMSIS-SVD](formats/svd.md#cluster):

```xml
<cluster>
  <name>STAT</name><addressOffset>0x50</addressOffset>
  <register><name>FLAGS</name><addressOffset>0x0</addressOffset><access>read-only</access></register>
  <register><name>ERR</name><addressOffset>0x4</addressOffset><access>read-only</access></register>
</cluster>
```

Output — emitted as [C](targets/c.md#cluster-members):

```c
typedef struct {
    volatile const uint32_t FLAGS;  /* 0x00 */
    volatile const uint32_t ERR;    /* 0x04 */
} dc_dma_stat_t;
REGFORGE_STATIC_ASSERT(sizeof(dc_dma_stat_t) == DC_DMA_STAT_SIZE, DC_DMA_STAT_SIZE_CHECK, "DMA.STAT size vs its last register");

    dc_dma_stat_t     STAT;            /* 0x50 */
```

## Rule 2: a cluster array's element is padded to the stride

With `dim`, the cluster's type is one element: its contents, padded out to
`dimIncrement`, so that `count` of them tile the array exactly. The element's
size is asserted against the stride, and the member becomes an array whose
bound is the cluster's `_COUNT` constant; the padding's length is a named
constant too.

Input — read as [CMSIS-SVD](formats/svd.md#cluster):

```xml
<cluster>
  <dim>4</dim><dimIncrement>0x10</dimIncrement><name>CH[%s]</name><addressOffset>0x10</addressOffset>
  <register><name>CTRL</name><addressOffset>0x0</addressOffset></register>
  <register><name>SRC</name><addressOffset>0x4</addressOffset></register>
</cluster>
```

Output — emitted as [C](targets/c.md#cluster-members):

```c
typedef struct {
    volatile uint32_t CTRL;                              /* 0x00 */
    volatile uint32_t SRC;                               /* 0x04 */
    uint8_t           RESERVED0[DMA_CH_RESERVED0_SIZE];  /* 0x08  (reserved) */
} dma_ch_t;
REGFORGE_STATIC_ASSERT(sizeof(dma_ch_t) == DMA_CH_STRIDE, DMA_CH_SIZE_CHECK, "DMA.CH element size vs dimIncrement");

    dma_ch_t          CH[DMA_CH_COUNT];  /* 0x10 */
```

Complete versions: [the whole SVD](formats/svd.md#a-cluster-array) and
[the whole header](targets/c.md#a-cluster-array).

A single cluster is asserted against its extent instead of a stride; see Rule 1.

## Rule 3: the type is named inside the family

`<family>_<cluster>`, the cluster's `headerStructName` replacing its name when
given, nested clusters appending theirs. Clusters with the same wanted name and
the same contents share one type. The full rule is
[naming.md](naming.md#rule-4-a-clusters-type-is-named-inside-its-family).

## Rule 4: the inheritance chain gains a rung

A cluster may declare `size`, `access`, `resetValue` and `resetMask`; its
registers take them before the peripheral's, and a nested cluster adds a rung
of its own. See [defaults.md](defaults.md).

## Rule 5: checks see through clusters

A register inside a cluster is checked at its offset from the peripheral. For
block containment and peripheral overlap, a cluster counts as one extent that
reaches its last element. Two peripherals share a type only when their
clusters match too: name, offset, shape and contents
([families.md](families.md)).

## Corner cases

| Case | Result |
|---|---|
| Stride smaller than the contents | `LayoutError` (exit 4) and an `ERROR` finding; the elements overlap. |
| Empty cluster | `LayoutError`. There is no element to lay out. |
| `derivedFrom` on a cluster | Parsed, reported as a warning, not resolved. The cluster is emitted as written, so it needs registers of its own. |
| `dimIndex` on `CH[%s]` | Ignored with a warning; array elements are indexed by the language. |
| `CH%s` | Copies `CH0`, `CH1`, ... `dimIncrement` apart, one shared type named after the stem. |
| A register array inside a cluster array | Both indices in the flat macro, outermost first, each named for its array: `DMA_CH_BUF(ch_index, buf_index)`. |
| A single cluster ending mid-word | Its C type is padded to its alignment, so the slot and `_SIZE` are the padded extent; a register placed in that padding is a `LayoutError`. |
| An `alternateRegister` pair inside a cluster | One union member of the cluster's type, exactly as in a peripheral ([alternates.md](alternates.md)). |
| `alternateCluster` | Not read. |
| Interrupts, address blocks or fields written inside a cluster | Ignored: the schema puts them on the peripheral and the register. |
