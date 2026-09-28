# Alternate register rules

**Read from:** [`alternateRegister`, `alternateGroup`](formats/svd.md#alternate-registers) &nbsp;·&nbsp; **Emitted as:** [union members](targets/c.md#union-members)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


One word, two layouts. A timer's capture/compare mode register means one
thing in output-compare mode and another in input-capture mode, so the file
describes the same offset twice, the second register naming the first as its
`alternateRegister`. STM32 timers do this on every `TIM`. The two are one
register: regforge keeps both descriptions and emits one union for the word.

Code: `regforge/resolve.py` (`resolve_alternates`), `regforge/layout.py`
(`union_naming`, the union slot), `regforge/check.py`
(`check_alternate_registers`), `regforge/writers/c.py`.
Tests: `tests/resolve/test_alternates.py`, `tests/core/test_alternates_layout.py`,
`tests/check/test_alternates.py`, `tests/writers/c/test_alternates.py`.

## Rule 1: views are linked by final name, within their own block

`resolve_alternates` runs after `expand_dim` and `resolve_derived`, so the
name an `alternateRegister` carries is matched against registers as they
finally exist, in the same peripheral or the same cluster:

| Declared | Pairs with |
|---|---|
| `CCMR1_Input` alternate `CCMR1_Output` | the register of that name in the block |
| `DTR%s` alternate `DT%s` | copy with copy: `DTR0` with `DT0`, `DTR1` with `DT1` |
| `CCI[%s]` alternate `CC[%s]` | the array `CC`, when `dim` and `dimIncrement` match |
| `RAW` alternate `DT%s` | the template's first copy, `DT0`, with a `WARNING` |
| `DR` with `alternateGroup` `Cal` | the register `DR`; the view is named `DR_Cal` |

A derived peripheral inherits its base's pairs with the base's registers. A
declaration is not inherited across a register-level `derivedFrom`, which
regforge does not resolve.

The result on every register of a set is `alternates`: all the views' names,
the primary first. The primary is the view nothing points away from; a cycle
(`A` alternate `B`, `B` alternate `A`) has none, and file order decides. A
chain `A` alternate `B`, `B` alternate `C` is one set of three, `C` first.

## Rule 2: one set is one union, as wide as its widest view

The layout gives the set one slot at the shared offset, sized to the widest
view, so a byte view and a half-word view of a word cost nothing extra and the
padding after the union is computed from the word. Two registers at one
offset that are *not* declared alternates are still refused (`LayoutError`,
exit 4) with the hint to add `alternateRegister`: regforge never infers a
union.

### Example

Input — read as [CMSIS-SVD](formats/svd.md#alternate-registers):

```xml
<register><name>CCMR1_Output</name><addressOffset>0x0C</addressOffset></register>
<register>
  <name>CCMR1_Input</name><alternateRegister>CCMR1_Output</alternateRegister>
  <addressOffset>0x0C</addressOffset>
</register>
```

Output — emitted as [C](targets/c.md#union-members):

```c
#define DC_TIM1_CCMR1_OFFSET (0x0000000CUL)
#define DC_TIM1_CCMR1_SIZE   (0x00000004UL)

    union {
        volatile uint32_t Output;  /* 0x0C */
        volatile uint32_t Input;   /* 0x0C */
    } CCMR1;  /* 0x0C  one register, 2 views */
REGFORGE_STATIC_ASSERT(offsetof(dc_tim1_t, CCMR1) == DC_TIM1_CCMR1_OFFSET, DC_TIM1_CCMR1_OFFSET_CHECK, "TIM1.CCMR1 offset");
REGFORGE_STATIC_ASSERT(sizeof(((dc_tim1_t *)0)->CCMR1) == DC_TIM1_CCMR1_SIZE, DC_TIM1_CCMR1_SIZE_CHECK, "TIM1.CCMR1 union size");
REGFORGE_STATIC_ASSERT(offsetof(dc_tim1_t, CCMR1.Input) == DC_TIM1_CCMR1_OFFSET, DC_TIM1_CCMR1_INPUT_OFFSET_CHECK, "TIM1.CCMR1.Input offset");

#define DC_TIM1_CCMR1_OUTPUT (DC_TIM1->CCMR1.Output)
#define DC_TIM1_CCMR1_INPUT (DC_TIM1->CCMR1.Input)
```

Complete versions: [the whole SVD](formats/svd.md#an-alternate-register-pair)
and [the whole header](targets/c.md#an-alternate-register-pair).

## Rule 3: the union is named by the views' common prefix, else after the primary

| Views | Union | Members | Why |
|---|---|---|---|
| `CCMR1_Output`, `CCMR1_Input` | `CCMR1` | `Output`, `Input` | the common prefix, `_` trimmed, is an identifier no sibling uses and every remainder is one |
| `XFER_Mem`, `XFER_Periph` | `XFER` | `Mem`, `Periph` | same |
| `DR`, `RXD` | `DR` | `DR`, `RXD` | no common prefix: the primary's name, full member names |
| `DR`, `DR8`, `DR16` | `DR` | `DR`, `DR8`, `DR16` | the remainders `8` and `16` are not identifiers |
| `DT0`, `DTR0` | `DT0` | `DT0`, `DTR0` | the remainder `0` is not an identifier |
| `CCR_X`, `CCR_Y` beside a register `CCR` | `CCR_X` | `CCR_X`, `CCR_Y` | the prefix would collide with the sibling: fallback plus a `WARNING` |

The union's name is what the layout constants, the asserts and the struct
member use; each view's flat macro keeps the register's own name.

## Rule 4: every view keeps its own type, qualifiers, fields and reset

The views differ on purpose, so nothing is merged: a read-only view is
`const` beside a writable one, a byte view is `uint8_t`, and the field and
reset macros are emitted per view under the register's name
(`DC_TIM1_CCMR1_INPUT_IC1F_Pos`). Each view's comment names the others.

## Rule 5: what the header asserts

| Assert | Proves |
|---|---|
| `offsetof(t, CCMR1) == _OFFSET` | the union is where the vendor put the word |
| `sizeof(t.CCMR1) == _SIZE` | the union is as wide as the widest view, so the padding after it is right |
| `offsetof(t, CCMR1.Input) == _OFFSET` | every view, by name, sits at that offset |

An array of unions (`CCI[%s]` alternate `CC[%s]`) gets the array asserts
instead: `_STRIDE`, `_COUNT`, the array size, the last element, and the
element size against `dimIncrement`. An array whose stride is wider than the
widest view is unpacked into `CC0`, `CC1`, ... like a register array, and its
macro is then the address sum.

## Rule 6: findings

| Case | Severity |
|---|---|
| target named does not exist in the block | `ERROR`; the register is ordinary |
| target at another offset | `WARNING`; unrelated (a real overlap then raises `LayoutError`) |
| target of another `dim` shape, or copy counts differ | `WARNING`; unrelated |
| a register naming itself | `WARNING`; ignored |
| a plain register naming a `%s` template | `WARNING`; the first copy |
| views with differing `resetValue` | `WARNING` from `check_alternate_registers`; each view keeps its own |
| the common prefix collides with a sibling | `WARNING`; fallback naming |

## Corner cases

| # | Input | Result |
|---|---|---|
| 1 | `A` alt `B`, `B` alt `A` | one union |
| 2 | chain `A` alt `B`, `B` alt `C` | one union of three, `C` first |
| 3 | self-alternate | `WARNING`, ignored |
| 4 | target missing | `ERROR`, ordinary register |
| 5 | target in another peripheral or cluster | `ERROR` (it must be in the same block) |
| 6 | different offsets | `WARNING`, unrelated; an undeclared overlap raises `LayoutError` as always |
| 7 | different sizes (32 vs 16) | union of 4 bytes, `_SIZE` 4, padding computed from 4 |
| 8 | different access (RW vs RO) | members carry their own `const`; no finding |
| 9 | different reset values | `WARNING` |
| 10 | no usable common prefix | union named after the primary, full member names |
| 11 | common prefix equals a sibling register's name | rule 2 naming plus `WARNING` |
| 12 | undeclared same-offset overlap | `LayoutError` with the `alternateRegister` hint; never inferred |
| 13 | `alternateGroup` (same name, another group) | read as the view `NAME_GROUP`, alternate of `NAME` |
| 14 | alternate inside a `[%s]` array | equal `dim` and `dimIncrement` required; the union is the element |
| 15 | alternate inside a cluster | identical path, a union member of the cluster's type |
| 16 | register-level `derivedFrom` | not supported; nothing to copy down |
| 17 | one view has fields, the other none | fine; the field-less view is a plain word access |
| 18 | three views, two of them byte-sized | one union, size 4 |
| 19 | families | the alternate set is part of the layout signature |
| 20 | word-addressable device | offsets compared in address units, no change |
| 21 | `DTR%s` alternate `DT%s` | copy pairs with copy of the same index; differing counts are a `WARNING` |
