# C

How the decisions in the rule pages are spelled as C. A second target would
replace this page and reuse the rules unchanged.

Code: `regforge/writers/c.py`, `regforge/writers/templates/c/`.

How a name chosen in [ir/naming.md](../naming.md) becomes an identifier in
the header, and what other identifiers point at it.

Code: `regforge/writers/c.py`, `regforge/writers/templates/c/header.h.j2`.

## File order

The header's blocks come in the order [ir/structure.md](../structure.md)
fixes, each under a banner comment: the file banner, the include guard and
includes, `Compiler compatibility`, `Device`, `CPU`, `Interrupts`, `NVIC`,
`Peripherals`, the end guard. Within `Peripherals`, one section per family
in the order of that page's Rule 3. The MISRA statement is a paragraph of
the file banner, because it describes the file.

## Type names

The model supplies a name string. The C writer lowercases it, prefixes the
device's `headerDefinitionsPrefix`, and appends `_t`:

```
name from the model:  GPIO
headerDefinitionsPrefix absent:  gpio_t
headerDefinitionsPrefix = DC_:   dc_gpio_t
```

So the vendor's casing never reaches the output. `GPIO`, `Gpio`, and `gpio` all
produce the same identifier, and the header reads consistently whatever the
source looked like.

Enum types end in `_e`, not `_t`:

```c
typedef enum { ... } dc_irqn_e;
```

## Instance names

A peripheral produces three things, all upper-case with the same prefix:

```c
#define DC_UART0_BASE (0x40004000UL)
REGFORGE_MAYBE_UNUSED static dc_uart_t *const DC_UART0 = (dc_uart_t *)(uintptr_t)DC_UART0_BASE;
#define DC_UART0_DR (DC_UART0->DR)
```

`REGFORGE_MAYBE_UNUSED` keeps the pointer from warning when a translation unit
includes the header but does not use that peripheral.

## Aliases

A peripheral that shares a type gets a second name for it:

```c
typedef dc_tim_t dc_tim2_t;
typedef dc_tim_t dc_tim3_t;
```

Same type, different spelling. A function taking `dc_tim_t *` accepts a pointer
to either instance. This lets a signature be written `dc_tim2_t *` without the
author knowing that TIM2 shares its layout with TIM3.

### When no alias is emitted

**The peripheral's name already spells the type name.**

```
WDT   groupName=WDT   registers: CR
```
```c
} wdt_t;
static wdt_t *const WDT = (wdt_t *)(uintptr_t)WDT_BASE;
```

The alias would read `typedef wdt_t wdt_t;`, declaring the same typedef name
twice. C11 permits this when the target type is identical; C89 and C99 do not,
and these headers are compiled as C89:

```
$ gcc -std=c89 -pedantic-errors -c t.c
t.c: error: redefinition of typedef 'wdt_t'
$ gcc -std=c99 -pedantic-errors -c t.c
t.c: error: redefinition of typedef 'wdt_t'
$ gcc -std=c11 -pedantic-errors -c t.c
$
```

Nothing is lost: `wdt_t` is already spelled after this peripheral.

**Another type already uses that name.**

```
GP0    groupName=GPIO       registers: PMD
GP1    groupName=GPIO       registers: PMD
GPIO   groupName=GPIO_GCR   registers: DBNCECON, OTHER
```
```c
} gpio_t;              /* GP0 and GP1 */
typedef gpio_t gp0_t;
typedef gpio_t gp1_t;

} gpio_gcr_t;          /* GPIO -- no gpio_t alias */
static gpio_gcr_t *const GPIO = (gpio_gcr_t *)(uintptr_t)GPIO_BASE;
```

The alias would be `typedef gpio_gcr_t gpio_t;`, declaring `gpio_t` a second
time as a different type. The alias is dropped, not the peripheral: `GPIO` keeps
its base macro, its pointer, and its register macros. This shape is in Nuvoton's
M051 file.

**Two peripherals in different types have the same name.** The first processed
takes the alias; the second is skipped for the same reason.

How the member list decided in [ir/address-blocks.md](../address-blocks.md)
and [ir/address-math.md](../address-math.md) is written as C.

Code: `regforge/writers/c.py` (`_c_layout`), the header template.

## Layout constants

Every number the layout produces is named once, per type, and referenced from
there: each member's byte offset from the instance base, for an array its
stride and count, for a padding gap its byte size (`_RESERVED<n>_SIZE`) and
for a buffer window its element count (`_BUFFER<n>_COUNT`). A cluster's own
offset is named after the cluster; its members are named after the cluster's
type and are relative to one element.

```c
#define DC_DMA_CFG_OFFSET        (0x00000000UL)
#define DC_DMA_RESERVED0_SIZE    (0x0000000CUL)
#define DC_DMA_CH_OFFSET         (0x00000010UL)
#define DC_DMA_CH_STRIDE         (0x00000010UL)
#define DC_DMA_CH_COUNT          (4U)
#define DC_DMA_CH_CTRL_OFFSET    (0x00000000UL)
#define DC_DMA_CH_RESERVED0_SIZE (0x00000008UL)
#define DC_DMA_SIZE              (0x00000100UL)
```

Every array bound in the struct and every assert below refers to these, so no
number is written twice and the struct carries no literal; the register macros
go through the typed instance and repeat none of them. User code has the
constants for address tables, DMA descriptors and startup assembly, where an
address must be a constant expression. `_SIZE` appears when the struct has a
size contract (see [ir/address-blocks.md](../address-blocks.md)) and on a
single cluster's type, whose contract is its own extent. An instance that shares a type
gets its own `_COUNT` name as an alias of the family's, `DC_PWMA_CC_COUNT` for
`DC_PWM_CC_COUNT`, so a loop can be written against the instance.

## Register members

Each register becomes one member at its own offset, with the offset and the
description in a trailing comment. A description longer than 40 characters
is cut at a word and marked `...` there; the register's macro comment always
carries the whole text:

```c
typedef struct {
    volatile uint32_t       MODER;                               /* 0x00  Mode register */
    uint8_t                 RESERVED0[DC_GPIOA_RESERVED0_SIZE];  /* 0x04  (reserved) */
    volatile const uint32_t IDR;                                 /* 0x10  Input data register */
} dc_gpioa_t;
```

## Type and qualifiers

The base type comes from the register's resolved size:

| Size in bits | Type |
|---|---|
| 8 | `uint8_t` |
| 16 | `uint16_t` |
| 32 | `uint32_t` |
| 64 | `uint64_t` |
| anything else | refused, CLI exit 4 |

Every register member is `volatile`. A read-only register is additionally
`const`, so writing it is a compile error:

| Resolved access | Emitted |
|---|---|
| `read-only` | `volatile const uint32_t` |
| `read-write`, `write-only`, `writeOnce`, `read-writeOnce` | `volatile uint32_t` |

C has no qualifier for "write-only" or "write-once", so those are plain
`volatile`. CMSIS spells the read-only case `__IM`; this is the same thing
without the macro.

## Padding members

Space between registers becomes a byte array named `RESERVED<n>`, numbered from
zero within each struct. Its length is the type's `_RESERVED<n>_SIZE` constant,
in bytes, emitted with the other layout constants in member order:

```c
#define DC_GPIOA_RESERVED0_SIZE (0x0000000CUL)

uint8_t RESERVED0[DC_GPIOA_RESERVED0_SIZE];   /* 0x04  (reserved) */
```

Padding is `uint8_t` because it exists to occupy bytes, not to be accessed, and
a byte array divides any gap. It is not `volatile`: nothing should read or write
it.

## Buffer windows

A block with `usage="buffer"` becomes one array member named `BUFFER<n>`, its
bound the type's `_BUFFER<n>_COUNT` constant:

```c
#define DC_UART_BUFFER0_OFFSET (0x00000008UL)
#define DC_UART_BUFFER0_COUNT  (8U)

volatile uint32_t BUFFER0[DC_UART_BUFFER0_COUNT];   /* 0x08  (buffer) */
```

The element type is the device's `<width>`, because that is the natural access
size, and `_COUNT` counts those elements. When the window is not a whole number
of bus words the writer falls back to `uint8_t`, so no bytes are dropped.

The name is generated. `<addressBlock>` has no `<name>` element in the schema,
so there is no vendor name to use, and `BUFFER0` follows the same numbering as
`RESERVED0` to make clear it was not taken from the source.

## Flat macros

Alongside the struct, each register also gets a macro that names it directly.
The macro is the register's path through the typed instance pointer:

```c
#define DC_GPIOA_IDR (DC_GPIOA->IDR)
#define DC_DMA_STAT_FLAGS (DC_DMA->STAT.FLAGS)
#define DC_DMA_CH_CTRL(ch_index) (DC_DMA->CH[(ch_index)].CTRL)
```

A view of an alternate register set is reached through its union,
`DC_TIM1->CCMR1.Input` (see [Union members](#union-members)).
Because the macro is the member, its type and qualifiers are the member's own:
a read-only register cannot be written through either route, and the offsets
live in one place, the struct, where the asserts check them. Only an array the
struct cannot hold as an array (see [Array members](#array-members)) is
addressed arithmetically, from the layout constants:

```c
#define DC_PWMX_CH(ch_index) (*(volatile uint32_t *)(DC_PWMX_BASE + DC_PWMX_CH_OFFSET + (ch_index) * DC_PWMX_CH_STRIDE))
```

## Field macros

Each field emits a position and a mask, and each enumerated value a constant:

```c
#define DC_GPIOA_MODER_MODE0_Pos (0U)
#define DC_GPIOA_MODER_MODE0_Msk (0x00000003UL)
#define DC_GPIOA_MODER_MODE0_INPUT (0U)
```

The `_Pos` / `_Msk` suffixes follow CMSIS, so existing field-manipulation code
reads the same.

## Array members

A register that kept its `dim` through expansion (`CC[%s]` in the source) is
one member, its bound the family's `_COUNT` constant:

```c
volatile uint32_t CC[DC_PWM_CC_COUNT];   /* 0x10  Capture/compare channel */
```

This form needs the stride to equal the element size (see
[ir/address-math.md](../address-math.md)); a larger stride gives flat members
instead, below. The flat macro takes the index, named after the array it
steps through, and a count is emitted for loop bounds:

```c
#define DC_PWMA_CC_COUNT DC_PWM_CC_COUNT
#define DC_PWMA_CC(cc_index) (DC_PWMA->CC[(cc_index)])
```

Three asserts pin the array. One `offsetof` covers its start; a `sizeof` on the
member checks it holds exactly its elements (`sizeof` is unevaluated, so the
null pointer is never dereferenced); and the last element is placed outright,
so `CC[k]` reaching `OFFSET + k * STRIDE` is stated rather than inferred. That
last one is spelled as the start plus `k` element sizes, not as
`offsetof(dc_pwm_t, CC[k])`, because MSVC's C front end does not accept an
array subscript inside `offsetof` as a constant expression:

```c
REGFORGE_STATIC_ASSERT(sizeof(((dc_pwm_t *)0)->CC) == DC_PWM_CC_COUNT * DC_PWM_CC_STRIDE, DC_PWM_CC_ARRAY_CHECK, "PWM.CC array size");
REGFORGE_STATIC_ASSERT(offsetof(dc_pwm_t, CC) + (DC_PWM_CC_COUNT - 1U) * sizeof(((dc_pwm_t *)0)->CC[0]) == DC_PWM_CC_OFFSET + (DC_PWM_CC_COUNT - 1U) * DC_PWM_CC_STRIDE, DC_PWM_CC_LAST_CHECK, "PWM.CC[3] offset via the struct");
```

When the stride is larger than the element (`CH[%s]` 8 bytes apart for 32-bit
registers) no C array fits, so the struct gets one member per element with
padding between, `CH0`, `RESERVED0`, `CH1`, ..., while `CH_COUNT` and the
`CH(ch_index)` macro stay. With no array member to index, that macro is the
one place the address is summed from the layout constants, stepping by the
true stride.

Reset and field macros are emitted once per array, not once per element. A
field array (`OD[%s]`) gets an indexed position and mask, and its enumerated
values once:

```c
#define DC_GPIOA_ODR_OD_COUNT (16U)
#define DC_GPIOA_ODR_OD_Pos(od_index) (0U + (od_index) * 1U)
#define DC_GPIOA_ODR_OD_Msk(od_index) (0x00000001UL << ((od_index) * 1U))
```

An array whose source names its indices (`dimArrayIndex`) gets one constant per
name, so a caller can write `DC_DMA_CH(DC_DMA_CH_RX)`:

```c
/* DMA.CH[2] index names (dimArrayIndex) */
#define DC_DMA_CH_RX (0U)  /* receive channel */
#define DC_DMA_CH_TX (1U)
```

Copies expanded from a `NAME%s` template are ordinary registers, fields or
peripherals and are spelled exactly as if the vendor had written each out.

## Cluster members

A cluster becomes a struct type of its own, emitted before the peripheral's
struct that uses it, and one member of that type -- an array of it when the
cluster carries `dim`:

```c
/* DMA.CH -- DMA channel (4 elements, 0x10 bytes apart) */
typedef struct {
    volatile uint32_t CTRL;                                 /* 0x00  Channel control */
    volatile uint32_t SRC;                                  /* 0x04  Source address */
    uint8_t           RESERVED0[DC_DMA_CH_RESERVED0_SIZE];  /* 0x08  (reserved) */
} dc_dma_ch_t;
REGFORGE_STATIC_ASSERT(offsetof(dc_dma_ch_t, SRC) == DC_DMA_CH_SRC_OFFSET, DC_DMA_CH_SRC_OFFSET_CHECK, "DMA.CH.SRC offset");
REGFORGE_STATIC_ASSERT(sizeof(dc_dma_ch_t) == DC_DMA_CH_STRIDE, DC_DMA_CH_SIZE_CHECK, "DMA.CH element size vs dimIncrement");

/* DMA.STAT -- Status block */
typedef struct {
    volatile const uint32_t FLAGS;  /* 0x00 */
    volatile const uint32_t ERR;    /* 0x04 */
} dc_dma_stat_t;
REGFORGE_STATIC_ASSERT(sizeof(dc_dma_stat_t) == DC_DMA_STAT_SIZE, DC_DMA_STAT_SIZE_CHECK, "DMA.STAT size vs its last register");

typedef struct {
    volatile uint32_t CFG;                               /* 0x00 */
    uint8_t           RESERVED0[DC_DMA_RESERVED0_SIZE];  /* 0x04  (reserved) */
    dc_dma_ch_t       CH[DC_DMA_CH_COUNT];               /* 0x10  DMA channel */
} dc_dma_t;
```

The type is named `<prefix><family>_<cluster>_t`, the cluster's
`headerStructName` replacing its name when given, and a nested cluster appends
its own name (`dc_dma_ch_sub_t`); see [ir/naming.md](../naming.md). An array
cluster's element is padded to the stride and its size asserted, so the array
tiles the vendor's spacing exactly, and its last element is placed by an
`offsetof` assert of its own. A single cluster's type is asserted against its
extent, the end of its last register rounded up to the type's alignment, so
the inner struct is checked on its own terms rather than only through the
padding its parent computes after it.

## Union members

Two registers the source declares at one offset as views of one word
(`alternateRegister`, see [ir/alternates.md](../alternates.md)) become one
named union member, as wide as the widest view. Its name comes from the
views' common prefix when that is a usable identifier, else from the primary
view. The union carries the layout constants and is asserted for offset and
size; every view is asserted at that offset by name, and each view's macro
reaches it through the union:

```c
#define DC_TIM1_CCMR1_OFFSET (0x0000000CUL)
#define DC_TIM1_CCMR1_SIZE   (0x00000004UL)

    union {
        volatile uint32_t Output;  /* 0x0C  Capture/compare mode (output) */
        volatile uint32_t Input;   /* 0x0C  Capture/compare mode (input) */
    } CCMR1;  /* 0x0C  one register, 2 views */
REGFORGE_STATIC_ASSERT(offsetof(dc_tim1_t, CCMR1) == DC_TIM1_CCMR1_OFFSET, DC_TIM1_CCMR1_OFFSET_CHECK, "TIM1.CCMR1 offset");
REGFORGE_STATIC_ASSERT(sizeof(((dc_tim1_t *)0)->CCMR1) == DC_TIM1_CCMR1_SIZE, DC_TIM1_CCMR1_SIZE_CHECK, "TIM1.CCMR1 union size");
REGFORGE_STATIC_ASSERT(offsetof(dc_tim1_t, CCMR1.Output) == DC_TIM1_CCMR1_OFFSET, DC_TIM1_CCMR1_OUTPUT_OFFSET_CHECK, "TIM1.CCMR1.Output offset");

/* TIM1.CCMR1_Output - Capture/compare mode (output)  [alternate: CCMR1_Input] */
#define DC_TIM1_CCMR1_OUTPUT (DC_TIM1->CCMR1.Output)
#define DC_TIM1_CCMR1_OUTPUT_OC1M_Pos (4U)
```

The union is named, never anonymous, so the header stays C89. Each view keeps
its own type and qualifiers (`volatile const uint32_t RXD;` beside
`volatile uint32_t DR;`), its own field and reset macros, and a comment naming
the other views. An array of unions (`CCI[%s]` alternate `CC[%s]`) is an
array member `CC[DC_PWM_CC_COUNT]` with the usual stride, count, array and
last-element asserts, plus `sizeof(CC[0]) == _STRIDE`; the macros index it,
`DC_PWMA_CCI(cc_index)` being `DC_PWMA->CC[(cc_index)].CCI`. Two registers at
one offset that are not declared alternates are refused (`LayoutError`).

## Indexed macros

A register inside a cluster is reached through the cluster's name, and every
array on the path adds one parameter, outermost first, named after the array
it indexes:

```c
#define DC_DMA0_CH_CTRL(ch_index) (DC_DMA0->CH[(ch_index)].CTRL)
#define DC_DMA0_CH_BUF(ch_index, buf_index) (DC_DMA0->CH[(ch_index)].BUF[(buf_index)])
```

A call site therefore reads against a signature that says what each number
is. Two arrays of one name on a path get `ch_index` and `ch2_index`. A cluster
without `dim` adds no index, so `DC_DMA0_STAT_FLAGS` is an ordinary macro. No
bounds are checked; the `_COUNT` macros are there for the caller's loops.

The generated header checks its own assumptions when it is compiled. Each assert
guards something the generator cannot verify on its own.

Code: `regforge/writers/templates/c/header.h.j2`, `compat.h.j2`.

## The macro

`REGFORGE_STATIC_ASSERT` resolves to `static_assert` in C++, `_Static_assert` in
C11 and later, and a negative-array-size trick otherwise, so the asserts work
back to C89.

## Byte width

```c
#define DEMOMCU_ADDRESS_UNIT_BITS 8
REGFORGE_STATIC_ASSERT(CHAR_BIT == DEMOMCU_ADDRESS_UNIT_BITS, ...);
```

Guards a byte-addressed header being compiled by a toolchain whose `CHAR_BIT` is
not 8. The generator cannot see the compiler, so the header checks it.

## Member offsets

```c
REGFORGE_STATIC_ASSERT(offsetof(dc_gpioa_t, IDR) == DC_GPIOA_IDR_OFFSET, DC_GPIOA_IDR_OFFSET_CHECK, "GPIOA.IDR offset");
```

One per named member, against the layout constant. Guards the struct layout against packing options, ABI
differences, and hand edits. If padding is ever computed wrongly, this fails at
compile time rather than reading the wrong register at run time.

Buffer windows get one too, so the window's position is checked as tightly as a
register's. So do array members and cluster members, and a cluster's own
members are asserted inside its type. An array member gets a second one on
its last element, the start plus `COUNT - 1` element sizes, so element
addressing is checked outright rather than inferred from the array size.

## Struct size

```c
REGFORGE_STATIC_ASSERT(sizeof(dc_uart_t) == DC_UART_SIZE, DC_UART_SIZE_CHECK, "UART struct size vs addressBlock");
```

Guards the struct against the footprint the vendor declared. This is what makes
an array over instances correct: when the size matches the spacing between
instances, `((dc_uart_t *)DC_UART0_BASE)[1]` is `DC_UART1`.

Emitted only when the source supports it; see
[ir/address-blocks.md](../address-blocks.md) for when it is skipped. An
array cluster's element type is asserted against `dimIncrement` the same way,
so `CH[3]` lands where the third channel really is, and a single cluster's
type against its own extent, `DC_DMA_STAT_SIZE`.

## Endianness and FPU

```c
#if defined(__BYTE_ORDER__) && (__BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__)
#error "DemoMCU is little-endian, but the compiler targets a different byte order."
#endif

#if defined(__ARM_FP) && !DEMOMCU_HAS_FPU
#error "Building with FPU codegen for DemoMCU, which has no FPU (check -mfloat-abi / -mfpu)."
#endif
```

These are `#error` rather than static asserts, because they test preprocessor
state, and they are guarded by `defined(...)` so a compiler that does not define
those macros is not affected.

## MISRA C:2012

The generated header satisfies every required rule of MISRA C:2012, and CI
proves it on every push: `nox -s misra` runs cppcheck's MISRA addon over both
golden headers with `--std=c99 --platform=unix32` (a 32-bit MCU ABI for the
essential-type rules) and fails on any finding. Locally it needs cppcheck on
PATH, or `REGFORGE_CPPCHECK` pointing at one.

Six advisory rules are deviated from, each the case its own guideline names,
and the header says so in its preamble:

| Rule | Deviation |
|---|---|
| 11.4 | Integer to pointer: memory-mapped registers have no other spelling. Every such cast is a `_BASE` constant or an architecturally fixed NVIC address, through `uintptr_t`. |
| 19.2 | A union only where the source declares two layouts of one word ([alternates.md](../alternates.md)). |
| 2.3, 2.4, 2.5, 8.9 | Unused types, tags, macros and file-scope objects are judged per translation unit; a definitions header is used piecemeal by design. |

Everything else is spelled to the rules: unsigned literals carry `U`, device
macros that meet unsigned operands are unsigned (`DEMOMCU_NUM_IRQS (32U)`),
macro parameters are parenthesised, shifts are by named unsigned constants,
and a helper that only reads takes a pointer to `const`.

## Worked examples

The complete output for each rule example, generated by regforge. The SVD that
produced each one is on the [SVD format page](../formats/svd.md#worked-examples).
These are emitted with no `headerDefinitionsPrefix`, so identifiers carry no prefix.

### Naming precedence

Demonstrates [naming.md](../naming.md#rule-1-type-name-precedence). A peripheral declaring `headerStructName`, so the type is named `can_node_t` rather than `can_t` from its `groupName`.

From [this SVD](../formats/svd.md#naming-precedence):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* CAN_NODE */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define CAN_NODE_NCR_OFFSET (0x00000000UL)
#define CAN_NODE_NSR_OFFSET (0x00000004UL)

typedef struct {
    volatile uint32_t NCR;  /* 0x00 */
    volatile uint32_t NSR;  /* 0x04 */
} can_node_t;
REGFORGE_STATIC_ASSERT(offsetof(can_node_t, NCR) == CAN_NODE_NCR_OFFSET, CAN_NODE_NCR_OFFSET_CHECK, "CAN_NODE.NCR offset");
REGFORGE_STATIC_ASSERT(offsetof(can_node_t, NSR) == CAN_NODE_NSR_OFFSET, CAN_NODE_NSR_OFFSET_CHECK, "CAN_NODE.NSR offset");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking can_node_t * accepts any of them. */
typedef can_node_t can_node0_t;

/* CAN_NODE0 @ 0x48014000 */
#define CAN_NODE0_BASE (0x48014000UL)
REGFORGE_MAYBE_UNUSED static can_node_t *const CAN_NODE0 = (can_node_t *)(uintptr_t)CAN_NODE0_BASE;

/* CAN_NODE0.NCR */
#define CAN_NODE0_NCR (CAN_NODE0->NCR)

/* CAN_NODE0.NSR */
#define CAN_NODE0_NSR (CAN_NODE0->NSR)
```

### One group becoming two types

Demonstrates [naming.md](../naming.md#rule-2-naming-the-types-when-one-group-becomes-several). `FPU` and `FPU_CPACR` share `groupName=FPU` but have different registers, so two types are emitted and the peripheral called `FPU` takes the plain name.

From [this SVD](../formats/svd.md#one-group-becoming-two-types):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* FPU_CPACR */
/* family FPU: split 2 ways by layout (FPU_CPACR | FPU); FPU_CPACR first differs from FPU at CPACR */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define FPU_CPACR_CPACR_OFFSET (0x00000000UL)

typedef struct {
    volatile uint32_t CPACR;  /* 0x00 */
} fpu_cpacr_t;
REGFORGE_STATIC_ASSERT(offsetof(fpu_cpacr_t, CPACR) == FPU_CPACR_CPACR_OFFSET, FPU_CPACR_CPACR_OFFSET_CHECK, "FPU_CPACR.CPACR offset");

/* FPU_CPACR @ 0xE000ED88 */
#define FPU_CPACR_BASE (0xE000ED88UL)
REGFORGE_MAYBE_UNUSED static fpu_cpacr_t *const FPU_CPACR = (fpu_cpacr_t *)(uintptr_t)FPU_CPACR_BASE;

/* FPU_CPACR.CPACR */
#define FPU_CPACR_CPACR (FPU_CPACR->CPACR)


/* -------------------------------------------------------------------------- */
/* FPU */
/* family FPU: split 2 ways by layout (FPU_CPACR | FPU); first differs at CPACR */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define FPU_FPCCR_OFFSET (0x00000000UL)
#define FPU_FPCAR_OFFSET (0x00000004UL)

typedef struct {
    volatile uint32_t FPCCR;  /* 0x00 */
    volatile uint32_t FPCAR;  /* 0x04 */
} fpu_t;
REGFORGE_STATIC_ASSERT(offsetof(fpu_t, FPCCR) == FPU_FPCCR_OFFSET, FPU_FPCCR_OFFSET_CHECK, "FPU.FPCCR offset");
REGFORGE_STATIC_ASSERT(offsetof(fpu_t, FPCAR) == FPU_FPCAR_OFFSET, FPU_FPCAR_OFFSET_CHECK, "FPU.FPCAR offset");

/* FPU @ 0xE000EF34 */
#define FPU_BASE (0xE000EF34UL)
REGFORGE_MAYBE_UNUSED static fpu_t *const FPU = (fpu_t *)(uintptr_t)FPU_BASE;

/* FPU.FPCCR */
#define FPU_FPCCR (FPU->FPCCR)

/* FPU.FPCAR */
#define FPU_FPCAR (FPU->FPCAR)
```

### Two peripherals sharing one type

Demonstrates [families.md](../families.md#rule-1-grouping-follows-derivedfrom-and-groupname). `UART1` derives from `UART0`, so one struct is emitted with two instance pointers.

From [this SVD](../formats/svd.md#two-peripherals-sharing-one-type):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* UART (family: UART0, UART1) */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define UART_DR_OFFSET (0x00000000UL)
#define UART_SR_OFFSET (0x00000004UL)

typedef struct {
    volatile uint32_t       DR;  /* 0x00 */
    volatile const uint32_t SR;  /* 0x04 */
} uart_t;
REGFORGE_STATIC_ASSERT(offsetof(uart_t, DR) == UART_DR_OFFSET, UART_DR_OFFSET_CHECK, "UART.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart_t, SR) == UART_SR_OFFSET, UART_SR_OFFSET_CHECK, "UART.SR offset");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking uart_t * accepts any of them. */
typedef uart_t uart0_t;
typedef uart_t uart1_t;

/* UART0 @ 0x40004000 */
#define UART0_BASE (0x40004000UL)
REGFORGE_MAYBE_UNUSED static uart_t *const UART0 = (uart_t *)(uintptr_t)UART0_BASE;

/* UART0.DR */
#define UART0_DR (UART0->DR)

/* UART0.SR */
#define UART0_SR (UART0->SR)

/* UART1 @ 0x40004400 */
#define UART1_BASE (0x40004400UL)
REGFORGE_MAYBE_UNUSED static uart_t *const UART1 = (uart_t *)(uintptr_t)UART1_BASE;

/* UART1.DR */
#define UART1_DR (UART1->DR)

/* UART1.SR */
#define UART1_SR (UART1->SR)
```

### A registers block and a buffer block

Demonstrates [address-blocks.md](../address-blocks.md#rule-1-usage-decides-what-is-emitted). The buffer window becomes one array member, and the size assert covers both blocks.

From [this SVD](../formats/svd.md#a-registers-block-and-a-buffer-block):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* UART0 */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define UART0_DR_OFFSET      (0x00000000UL)
#define UART0_SR_OFFSET      (0x00000004UL)
#define UART0_BUFFER0_OFFSET (0x00000008UL)
#define UART0_BUFFER0_COUNT  (8U)
#define UART0_SIZE           (0x00000028UL)

typedef struct {
    volatile uint32_t       DR;                            /* 0x00 */
    volatile const uint32_t SR;                            /* 0x04 */
    volatile uint32_t       BUFFER0[UART0_BUFFER0_COUNT];  /* 0x08  (buffer) */
} uart0_t;
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, DR) == UART0_DR_OFFSET, UART0_DR_OFFSET_CHECK, "UART0.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, SR) == UART0_SR_OFFSET, UART0_SR_OFFSET_CHECK, "UART0.SR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, BUFFER0) == UART0_BUFFER0_OFFSET, UART0_BUFFER0_OFFSET_CHECK, "UART0.BUFFER0 offset");
REGFORGE_STATIC_ASSERT(sizeof(uart0_t) == UART0_SIZE, UART0_SIZE_CHECK, "UART0 struct size vs addressBlock");

/* UART0 @ 0x40004000 */
#define UART0_BASE (0x40004000UL)
REGFORGE_MAYBE_UNUSED static uart0_t *const UART0 = (uart0_t *)(uintptr_t)UART0_BASE;

/* UART0.DR */
#define UART0_DR (UART0->DR)

/* UART0.SR */
#define UART0_SR (UART0->SR)
```

### Inherited register properties

Demonstrates [defaults.md](../defaults.md#rule-1-the-inheritance-chain). Neither register declares a size; both take it from the device `<width>`, and `SR` overrides access.

From [this SVD](../formats/svd.md#inherited-register-properties):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* MISC */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define MISC_DR_OFFSET (0x00000000UL)
#define MISC_SR_OFFSET (0x00000004UL)

typedef struct {
    volatile uint32_t       DR;  /* 0x00 */
    volatile const uint32_t SR;  /* 0x04 */
} misc_t;
REGFORGE_STATIC_ASSERT(offsetof(misc_t, DR) == MISC_DR_OFFSET, MISC_DR_OFFSET_CHECK, "MISC.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(misc_t, SR) == MISC_SR_OFFSET, MISC_SR_OFFSET_CHECK, "MISC.SR offset");

/* MISC @ 0x40030000 */
#define MISC_BASE (0x40030000UL)
REGFORGE_MAYBE_UNUSED static misc_t *const MISC = (misc_t *)(uintptr_t)MISC_BASE;

/* MISC.DR */
#define MISC_DR (MISC->DR)

/* MISC.SR */
#define MISC_SR (MISC->SR)
```

### A peripheral array with a register array

Demonstrates [arrays.md](../arrays.md#rule-2-names-is-copies-names-is-an-array). `PWM%s` becomes `PWMA` and `PWMB`, one family; `CC[%s]` is one packed array member with an indexed macro; `DT%s` is two separately placed registers.

From [this SVD](../formats/svd.md#a-peripheral-array-with-a-register-array):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* PWM (family: PWMA, PWMB) */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define PWM_CTRL_OFFSET    (0x00000000UL)
#define PWM_RESERVED0_SIZE (0x0000000CUL)
#define PWM_CC_OFFSET      (0x00000010UL)
#define PWM_CC_STRIDE      (0x00000004UL)
#define PWM_CC_COUNT       (4U)
#define PWM_DT0_OFFSET     (0x00000020UL)
#define PWM_RESERVED1_SIZE (0x00000004UL)
#define PWM_DT1_OFFSET     (0x00000028UL)
#define PWM_RESERVED2_SIZE (0x00000004UL)
#define PWM_SIZE           (0x00000030UL)

typedef struct {
    volatile uint32_t CTRL;                           /* 0x00 */
    uint8_t           RESERVED0[PWM_RESERVED0_SIZE];  /* 0x04  (reserved) */
    volatile uint32_t CC[PWM_CC_COUNT];               /* 0x10 */
    volatile uint32_t DT0;                            /* 0x20 */
    uint8_t           RESERVED1[PWM_RESERVED1_SIZE];  /* 0x24  (reserved) */
    volatile uint32_t DT1;                            /* 0x28 */
    uint8_t           RESERVED2[PWM_RESERVED2_SIZE];  /* 0x2C  (reserved) */
} pwm_t;
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, CTRL) == PWM_CTRL_OFFSET, PWM_CTRL_OFFSET_CHECK, "PWM.CTRL offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, CC) == PWM_CC_OFFSET, PWM_CC_OFFSET_CHECK, "PWM.CC offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, DT0) == PWM_DT0_OFFSET, PWM_DT0_OFFSET_CHECK, "PWM.DT0 offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, DT1) == PWM_DT1_OFFSET, PWM_DT1_OFFSET_CHECK, "PWM.DT1 offset");
REGFORGE_STATIC_ASSERT(sizeof(((pwm_t *)0)->CC) == PWM_CC_COUNT * PWM_CC_STRIDE, PWM_CC_ARRAY_CHECK, "PWM.CC array size");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, CC) + (PWM_CC_COUNT - 1U) * sizeof(((pwm_t *)0)->CC[0]) == PWM_CC_OFFSET + (PWM_CC_COUNT - 1U) * PWM_CC_STRIDE, PWM_CC_LAST_CHECK, "PWM.CC[3] offset via the struct");
REGFORGE_STATIC_ASSERT(sizeof(pwm_t) == PWM_SIZE, PWM_SIZE_CHECK, "PWM struct size vs addressBlock");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking pwm_t * accepts any of them. */
typedef pwm_t pwma_t;
typedef pwm_t pwmb_t;

/* PWMA @ 0x40015000 */
#define PWMA_BASE (0x40015000UL)
REGFORGE_MAYBE_UNUSED static pwm_t *const PWMA = (pwm_t *)(uintptr_t)PWMA_BASE;

/* PWMA.CTRL */
#define PWMA_CTRL (PWMA->CTRL)

/* PWMA.CC[4] */
#define PWMA_CC_COUNT PWM_CC_COUNT
#define PWMA_CC(cc_index) (PWMA->CC[(cc_index)])

/* PWMA.DT0 */
#define PWMA_DT0 (PWMA->DT0)

/* PWMA.DT1 */
#define PWMA_DT1 (PWMA->DT1)

/* PWMB @ 0x40015100 */
#define PWMB_BASE (0x40015100UL)
REGFORGE_MAYBE_UNUSED static pwm_t *const PWMB = (pwm_t *)(uintptr_t)PWMB_BASE;

/* PWMB.CTRL */
#define PWMB_CTRL (PWMB->CTRL)

/* PWMB.CC[4] */
#define PWMB_CC_COUNT PWM_CC_COUNT
#define PWMB_CC(cc_index) (PWMB->CC[(cc_index)])

/* PWMB.DT0 */
#define PWMB_DT0 (PWMB->DT0)

/* PWMB.DT1 */
#define PWMB_DT1 (PWMB->DT1)
```

### A cluster array

Demonstrates [clusters.md](../clusters.md#rule-2-a-cluster-arrays-element-is-padded-to-the-stride). `CH[%s]` becomes one nested type, padded to the stride and size-asserted, used as `CH[DMA_CH_COUNT]`, with indexed macros for its registers.

From [this SVD](../formats/svd.md#a-cluster-array):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* DMA */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define DMA_CFG_OFFSET        (0x00000000UL)
#define DMA_RESERVED0_SIZE    (0x0000000CUL)
#define DMA_CH_OFFSET         (0x00000010UL)
#define DMA_CH_STRIDE         (0x00000010UL)
#define DMA_CH_COUNT          (4U)
#define DMA_CH_CTRL_OFFSET    (0x00000000UL)
#define DMA_CH_SRC_OFFSET     (0x00000004UL)
#define DMA_CH_RESERVED0_SIZE (0x00000008UL)
#define DMA_SIZE              (0x00000050UL)

/* DMA.CH (4 elements, 0x10 bytes apart) */
typedef struct {
    volatile uint32_t CTRL;                              /* 0x00 */
    volatile uint32_t SRC;                               /* 0x04 */
    uint8_t           RESERVED0[DMA_CH_RESERVED0_SIZE];  /* 0x08  (reserved) */
} dma_ch_t;
REGFORGE_STATIC_ASSERT(offsetof(dma_ch_t, CTRL) == DMA_CH_CTRL_OFFSET, DMA_CH_CTRL_OFFSET_CHECK, "DMA.CH.CTRL offset");
REGFORGE_STATIC_ASSERT(offsetof(dma_ch_t, SRC) == DMA_CH_SRC_OFFSET, DMA_CH_SRC_OFFSET_CHECK, "DMA.CH.SRC offset");
REGFORGE_STATIC_ASSERT(sizeof(dma_ch_t) == DMA_CH_STRIDE, DMA_CH_SIZE_CHECK, "DMA.CH element size vs dimIncrement");

typedef struct {
    volatile uint32_t CFG;                            /* 0x00 */
    uint8_t           RESERVED0[DMA_RESERVED0_SIZE];  /* 0x04  (reserved) */
    dma_ch_t          CH[DMA_CH_COUNT];               /* 0x10 */
} dma_t;
REGFORGE_STATIC_ASSERT(offsetof(dma_t, CFG) == DMA_CFG_OFFSET, DMA_CFG_OFFSET_CHECK, "DMA.CFG offset");
REGFORGE_STATIC_ASSERT(offsetof(dma_t, CH) == DMA_CH_OFFSET, DMA_CH_OFFSET_CHECK, "DMA.CH offset");
REGFORGE_STATIC_ASSERT(sizeof(((dma_t *)0)->CH) == DMA_CH_COUNT * DMA_CH_STRIDE, DMA_CH_ARRAY_CHECK, "DMA.CH array size");
REGFORGE_STATIC_ASSERT(offsetof(dma_t, CH) + (DMA_CH_COUNT - 1U) * sizeof(((dma_t *)0)->CH[0]) == DMA_CH_OFFSET + (DMA_CH_COUNT - 1U) * DMA_CH_STRIDE, DMA_CH_LAST_CHECK, "DMA.CH[3] offset via the struct");
REGFORGE_STATIC_ASSERT(sizeof(dma_t) == DMA_SIZE, DMA_SIZE_CHECK, "DMA struct size vs addressBlock");

/* DMA @ 0x40016000 */
#define DMA_BASE (0x40016000UL)
REGFORGE_MAYBE_UNUSED static dma_t *const DMA = (dma_t *)(uintptr_t)DMA_BASE;

/* DMA.CFG */
#define DMA_CFG (DMA->CFG)

/* DMA.CH[4].CTRL */
#define DMA_CH_CTRL(ch_index) (DMA->CH[(ch_index)].CTRL)

/* DMA.CH[4].SRC */
#define DMA_CH_SRC(ch_index) (DMA->CH[(ch_index)].SRC)
```

### An alternate register pair

Demonstrates [alternates.md](../alternates.md). `CCMR1_Input` names `CCMR1_Output` as its `alternateRegister`, so the word at `0x0C` is one union `CCMR1` with a member per view, asserted for offset and size, and each view keeps its own field macros.

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* TIM1 */

/* Layout constants: byte offsets from an instance's base; a cluster's members
 * are relative to one element of that cluster. Every assert below refers to
 * these, so each number is written once; the register macros go through the
 * typed instance and repeat none of them. */
#define TIM1_CR1_OFFSET     (0x00000000UL)
#define TIM1_RESERVED0_SIZE (0x00000008UL)
#define TIM1_CCMR1_OFFSET   (0x0000000CUL)
#define TIM1_CCMR1_SIZE     (0x00000004UL)
#define TIM1_SIZE           (0x00000010UL)

typedef struct {
    volatile uint32_t CR1;                             /* 0x00 */
    uint8_t           RESERVED0[TIM1_RESERVED0_SIZE];  /* 0x04  (reserved) */
    union {
        volatile uint32_t Output;  /* 0x0C */
        volatile uint32_t Input;   /* 0x0C */
    } CCMR1;  /* 0x0C  one register, 2 views */
} tim1_t;
REGFORGE_STATIC_ASSERT(offsetof(tim1_t, CR1) == TIM1_CR1_OFFSET, TIM1_CR1_OFFSET_CHECK, "TIM1.CR1 offset");
REGFORGE_STATIC_ASSERT(offsetof(tim1_t, CCMR1) == TIM1_CCMR1_OFFSET, TIM1_CCMR1_OFFSET_CHECK, "TIM1.CCMR1 offset");
REGFORGE_STATIC_ASSERT(sizeof(((tim1_t *)0)->CCMR1) == TIM1_CCMR1_SIZE, TIM1_CCMR1_SIZE_CHECK, "TIM1.CCMR1 union size");
REGFORGE_STATIC_ASSERT(offsetof(tim1_t, CCMR1.Output) == TIM1_CCMR1_OFFSET, TIM1_CCMR1_OUTPUT_OFFSET_CHECK, "TIM1.CCMR1.Output offset");
REGFORGE_STATIC_ASSERT(offsetof(tim1_t, CCMR1.Input) == TIM1_CCMR1_OFFSET, TIM1_CCMR1_INPUT_OFFSET_CHECK, "TIM1.CCMR1.Input offset");
REGFORGE_STATIC_ASSERT(sizeof(tim1_t) == TIM1_SIZE, TIM1_SIZE_CHECK, "TIM1 struct size vs addressBlock");

/* TIM1 @ 0x40010000 */
#define TIM1_BASE (0x40010000UL)
REGFORGE_MAYBE_UNUSED static tim1_t *const TIM1 = (tim1_t *)(uintptr_t)TIM1_BASE;

/* TIM1.CR1 */
#define TIM1_CR1 (TIM1->CR1)

/* TIM1.CCMR1_Output  [alternate: CCMR1_Input] */
#define TIM1_CCMR1_OUTPUT (TIM1->CCMR1.Output)
#define TIM1_CCMR1_OUTPUT_OC1M_Pos (4U)
#define TIM1_CCMR1_OUTPUT_OC1M_Msk (0x00000070UL)

/* TIM1.CCMR1_Input  [alternate: CCMR1_Output] */
#define TIM1_CCMR1_INPUT (TIM1->CCMR1.Input)
#define TIM1_CCMR1_INPUT_IC1F_Pos (4U)
#define TIM1_CCMR1_INPUT_IC1F_Msk (0x000000F0UL)
```
