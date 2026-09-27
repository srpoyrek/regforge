# C

How the decisions in the rule pages are spelled as C. A second target would
replace this page and reuse the rules unchanged.

Code: `regforge/writers/c.py`, `regforge/writers/templates/c/`.

How a name chosen in [ir/naming.md](../naming.md) becomes an identifier in
the header, and what other identifiers point at it.

Code: `regforge/writers/c.py`, `regforge/writers/templates/c/header.h.j2`.

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
REGFORGE_MAYBE_UNUSED static dc_uart_t *const DC_UART0 = (dc_uart_t *)DC_UART0_BASE;
#define DC_UART0_DR (*(volatile uint32_t *)(DC_UART0_BASE + 0x00000000UL))
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
static wdt_t *const WDT = (wdt_t *)WDT_BASE;
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
static gpio_gcr_t *const GPIO = (gpio_gcr_t *)GPIO_BASE;
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

## Register members

Each register becomes one member at its own offset, with the offset in a
trailing comment:

```c
typedef struct {
    volatile uint32_t       MODER;           /* 0x00  Mode register */
    uint8_t                 RESERVED0[12];   /* 0x04  (reserved) */
    volatile const uint32_t IDR;             /* 0x10  Input data register */
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
zero within each struct:

```c
uint8_t RESERVED0[12];   /* 0x04  (reserved) */
```

Padding is `uint8_t` because it exists to occupy bytes, not to be accessed, and
a byte array divides any gap. It is not `volatile`: nothing should read or write
it.

## Buffer windows

A block with `usage="buffer"` becomes one array member named `BUFFER<n>`:

```c
volatile uint32_t BUFFER0[8];   /* 0x08  (buffer) */
```

The element type is the device's `<width>`, because that is the natural access
size. When the window is not a whole number of bus words the writer falls back
to `uint8_t`, so no bytes are dropped.

The name is generated. `<addressBlock>` has no `<name>` element in the schema,
so there is no vendor name to use, and `BUFFER0` follows the same numbering as
`RESERVED0` to make clear it was not taken from the source.

## Flat macros

Alongside the struct, each register also gets a direct macro, so the header is
usable without the struct:

```c
#define DC_GPIOA_IDR (*(volatile const uint32_t *)(DC_GPIOA_BASE + 0x00000010UL))
```

The qualifiers match the struct member, so a read-only register cannot be
written through either route.

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
one member sized for every element:

```c
volatile uint32_t CC[4];   /* 0x10  Capture/compare channel */
```

This form needs the stride to equal the element size (see
[ir/address-math.md](../address-math.md)); a larger stride gives flat members
instead, below. The flat macro takes the index, and a count is emitted for
loop bounds:

```c
#define DC_PWMA_CC_COUNT (4U)
#define DC_PWMA_CC(i) (*(volatile uint32_t *)(DC_PWMA_BASE + 0x00000010UL + (i) * 0x00000004UL))
```

One `offsetof` assert covers the whole array, and a `sizeof` assert on the
member checks it holds exactly its elements (`sizeof` is unevaluated, so the
null pointer is never dereferenced):

```c
REGFORGE_STATIC_ASSERT(sizeof(((dc_pwm_t *)0)->CC) == 0x10, DC_PWM_CC_size, "PWM.CC array size");
```

When the stride is larger than the element (`CH[%s]` 8 bytes apart for 32-bit
registers) no C array fits, so the struct gets one member per element with
padding between, `CH0`, `RESERVED0`, `CH1`, ..., while `CH_COUNT` and the
`CH(i)` macro stay, stepping by the true stride.

Reset and field macros are emitted once per array, not once per element. A
field array (`OD[%s]`) gets an indexed position and mask, and its enumerated
values once:

```c
#define DC_GPIOA_ODR_OD_COUNT (16U)
#define DC_GPIOA_ODR_OD_Pos(i) (0U + (i) * 1U)
#define DC_GPIOA_ODR_OD_Msk(i) (0x00000001UL << ((i) * 1U))
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
    volatile uint32_t CTRL;          /* 0x00  Channel control */
    volatile uint32_t SRC;           /* 0x04  Source address */
    uint8_t           RESERVED0[8];  /* 0x08  (reserved) */
} dc_dma_ch_t;
REGFORGE_STATIC_ASSERT(offsetof(dc_dma_ch_t, SRC) == 0x04, DC_DMA_CH_SRC_offset, "DMA.CH.SRC offset");
REGFORGE_STATIC_ASSERT(sizeof(dc_dma_ch_t) == 0x10, DC_DMA_CH_SIZE, "DMA.CH element size vs dimIncrement");

typedef struct {
    volatile uint32_t CFG;            /* 0x00 */
    uint8_t           RESERVED0[12];  /* 0x04  (reserved) */
    dc_dma_ch_t       CH[4];          /* 0x10  DMA channel */
} dc_dma_t;
```

The type is named `<prefix><family>_<cluster>_t`, the cluster's
`headerStructName` replacing its name when given, and a nested cluster appends
its own name (`dc_dma_ch_sub_t`); see [ir/naming.md](../naming.md). An array
cluster's element is padded to the stride and its size asserted, so the array
tiles the vendor's spacing exactly. A single cluster gets no size assert,
because the source declares no size for it.

## Indexed macros

A register inside a cluster is reached through the cluster's name, and every
array on the path adds one index, outermost first:

```c
#define DC_DMA0_CH_CTRL(i) (*(volatile uint32_t *)(DC_DMA0_BASE + 0x00000010UL + (i) * 0x00000010UL))
#define DC_DMA0_CH_BUF(i, j) (*(volatile uint32_t *)(DC_DMA0_BASE + 0x00000010UL + (i) * 0x00000010UL + (j) * 0x00000004UL))
```

The constant offsets along the path are folded into one literal. A cluster
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
REGFORGE_STATIC_ASSERT(offsetof(dc_gpioa_t, IDR) == 0x10, DC_GPIOA_IDR_offset, "GPIOA.IDR offset");
```

One per named member. Guards the struct layout against packing options, ABI
differences, and hand edits. If padding is ever computed wrongly, this fails at
compile time rather than reading the wrong register at run time.

Buffer windows get one too, so the window's position is checked as tightly as a
register's. So do array members and cluster members, and a cluster's own
members are asserted inside its type.

## Struct size

```c
REGFORGE_STATIC_ASSERT(sizeof(dc_uart_t) == 0x28, DC_UART_SIZE, "UART struct size vs addressBlock");
```

Guards the struct against the footprint the vendor declared. This is what makes
an array over instances correct: when the size matches the spacing between
instances, `((dc_uart_t *)DC_UART0_BASE)[1]` is `DC_UART1`.

Emitted only when the source supports it; see
[ir/address-blocks.md](../address-blocks.md) for when it is skipped. An
array cluster's element type is asserted against `dimIncrement` the same way,
so `CH[3]` lands where the third channel really is.

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

typedef struct {
    volatile uint32_t NCR;  /* 0x00 */
    volatile uint32_t NSR;  /* 0x04 */
} can_node_t;
REGFORGE_STATIC_ASSERT(offsetof(can_node_t, NCR) == 0x00, CAN_NODE_NCR_offset, "CAN_NODE.NCR offset");
REGFORGE_STATIC_ASSERT(offsetof(can_node_t, NSR) == 0x04, CAN_NODE_NSR_offset, "CAN_NODE.NSR offset");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking can_node_t * accepts any of them. */
typedef can_node_t can_node0_t;

/* CAN_NODE0 @ 0x48014000 */
#define CAN_NODE0_BASE (0x48014000UL)
REGFORGE_MAYBE_UNUSED static can_node_t *const CAN_NODE0 = (can_node_t *)CAN_NODE0_BASE;

/* CAN_NODE0.NCR */
#define CAN_NODE0_NCR (*(volatile uint32_t *)(CAN_NODE0_BASE + 0x00000000UL))

/* CAN_NODE0.NSR */
#define CAN_NODE0_NSR (*(volatile uint32_t *)(CAN_NODE0_BASE + 0x00000004UL))
```

### One group becoming two types

Demonstrates [naming.md](../naming.md#rule-2-naming-the-types-when-one-group-becomes-several). `FPU` and `FPU_CPACR` share `groupName=FPU` but have different registers, so two types are emitted and the peripheral called `FPU` takes the plain name.

From [this SVD](../formats/svd.md#one-group-becoming-two-types):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* FPU_CPACR */

typedef struct {
    volatile uint32_t CPACR;  /* 0x00 */
} fpu_cpacr_t;
REGFORGE_STATIC_ASSERT(offsetof(fpu_cpacr_t, CPACR) == 0x00, FPU_CPACR_CPACR_offset, "FPU_CPACR.CPACR offset");

/* FPU_CPACR @ 0xE000ED88 */
#define FPU_CPACR_BASE (0xE000ED88UL)
REGFORGE_MAYBE_UNUSED static fpu_cpacr_t *const FPU_CPACR = (fpu_cpacr_t *)FPU_CPACR_BASE;

/* FPU_CPACR.CPACR */
#define FPU_CPACR_CPACR (*(volatile uint32_t *)(FPU_CPACR_BASE + 0x00000000UL))


/* -------------------------------------------------------------------------- */
/* FPU */
/* family FPU: split 2 ways by layout (FPU_CPACR | FPU); first differs at CPACR */

typedef struct {
    volatile uint32_t FPCCR;  /* 0x00 */
    volatile uint32_t FPCAR;  /* 0x04 */
} fpu_t;
REGFORGE_STATIC_ASSERT(offsetof(fpu_t, FPCCR) == 0x00, FPU_FPCCR_offset, "FPU.FPCCR offset");
REGFORGE_STATIC_ASSERT(offsetof(fpu_t, FPCAR) == 0x04, FPU_FPCAR_offset, "FPU.FPCAR offset");

/* FPU @ 0xE000EF34 */
#define FPU_BASE (0xE000EF34UL)
REGFORGE_MAYBE_UNUSED static fpu_t *const FPU = (fpu_t *)FPU_BASE;

/* FPU.FPCCR */
#define FPU_FPCCR (*(volatile uint32_t *)(FPU_BASE + 0x00000000UL))

/* FPU.FPCAR */
#define FPU_FPCAR (*(volatile uint32_t *)(FPU_BASE + 0x00000004UL))
```

### Two peripherals sharing one type

Demonstrates [families.md](../families.md#rule-1-grouping-follows-derivedfrom-and-groupname). `UART1` derives from `UART0`, so one struct is emitted with two instance pointers.

From [this SVD](../formats/svd.md#two-peripherals-sharing-one-type):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* UART (family: UART0, UART1) */

typedef struct {
    volatile uint32_t       DR;  /* 0x00 */
    volatile const uint32_t SR;  /* 0x04 */
} uart_t;
REGFORGE_STATIC_ASSERT(offsetof(uart_t, DR) == 0x00, UART_DR_offset, "UART.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart_t, SR) == 0x04, UART_SR_offset, "UART.SR offset");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking uart_t * accepts any of them. */
typedef uart_t uart0_t;
typedef uart_t uart1_t;

/* UART0 @ 0x40004000 */
#define UART0_BASE (0x40004000UL)
REGFORGE_MAYBE_UNUSED static uart_t *const UART0 = (uart_t *)UART0_BASE;

/* UART0.DR */
#define UART0_DR (*(volatile uint32_t *)(UART0_BASE + 0x00000000UL))

/* UART0.SR */
#define UART0_SR (*(volatile const uint32_t *)(UART0_BASE + 0x00000004UL))

/* UART1 @ 0x40004400 */
#define UART1_BASE (0x40004400UL)
REGFORGE_MAYBE_UNUSED static uart_t *const UART1 = (uart_t *)UART1_BASE;

/* UART1.DR */
#define UART1_DR (*(volatile uint32_t *)(UART1_BASE + 0x00000000UL))

/* UART1.SR */
#define UART1_SR (*(volatile const uint32_t *)(UART1_BASE + 0x00000004UL))
```

### A registers block and a buffer block

Demonstrates [address-blocks.md](../address-blocks.md#rule-1-usage-decides-what-is-emitted). The buffer window becomes one array member, and the size assert covers both blocks.

From [this SVD](../formats/svd.md#a-registers-block-and-a-buffer-block):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* UART0 */

typedef struct {
    volatile uint32_t       DR;          /* 0x00 */
    volatile const uint32_t SR;          /* 0x04 */
    volatile uint32_t       BUFFER0[8];  /* 0x08  (buffer) */
} uart0_t;
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, DR) == 0x00, UART0_DR_offset, "UART0.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, SR) == 0x04, UART0_SR_offset, "UART0.SR offset");
REGFORGE_STATIC_ASSERT(offsetof(uart0_t, BUFFER0) == 0x08, UART0_BUFFER0_offset, "UART0.BUFFER0 offset");
REGFORGE_STATIC_ASSERT(sizeof(uart0_t) == 0x28, UART0_SIZE, "UART0 struct size vs addressBlock");

/* UART0 @ 0x40004000 */
#define UART0_BASE (0x40004000UL)
REGFORGE_MAYBE_UNUSED static uart0_t *const UART0 = (uart0_t *)UART0_BASE;

/* UART0.DR */
#define UART0_DR (*(volatile uint32_t *)(UART0_BASE + 0x00000000UL))

/* UART0.SR */
#define UART0_SR (*(volatile const uint32_t *)(UART0_BASE + 0x00000004UL))
```

### Inherited register properties

Demonstrates [defaults.md](../defaults.md#rule-1-the-inheritance-chain). Neither register declares a size; both take it from the device `<width>`, and `SR` overrides access.

From [this SVD](../formats/svd.md#inherited-register-properties):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* MISC */

typedef struct {
    volatile uint32_t       DR;  /* 0x00 */
    volatile const uint32_t SR;  /* 0x04 */
} misc_t;
REGFORGE_STATIC_ASSERT(offsetof(misc_t, DR) == 0x00, MISC_DR_offset, "MISC.DR offset");
REGFORGE_STATIC_ASSERT(offsetof(misc_t, SR) == 0x04, MISC_SR_offset, "MISC.SR offset");

/* MISC @ 0x40030000 */
#define MISC_BASE (0x40030000UL)
REGFORGE_MAYBE_UNUSED static misc_t *const MISC = (misc_t *)MISC_BASE;

/* MISC.DR */
#define MISC_DR (*(volatile uint32_t *)(MISC_BASE + 0x00000000UL))

/* MISC.SR */
#define MISC_SR (*(volatile const uint32_t *)(MISC_BASE + 0x00000004UL))
```

### A peripheral array with a register array

Demonstrates [arrays.md](../arrays.md#rule-2-names-is-copies-names-is-an-array). `PWM%s` becomes `PWMA` and `PWMB`, one family; `CC[%s]` is one packed array member with an indexed macro; `DT%s` is two separately placed registers.

From [this SVD](../formats/svd.md#a-peripheral-array-with-a-register-array):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* PWM (family: PWMA, PWMB) */

typedef struct {
    volatile uint32_t CTRL;           /* 0x00 */
    uint8_t           RESERVED0[12];  /* 0x04  (reserved) */
    volatile uint32_t CC[4];          /* 0x10 */
    volatile uint32_t DT0;            /* 0x20 */
    uint8_t           RESERVED1[4];   /* 0x24  (reserved) */
    volatile uint32_t DT1;            /* 0x28 */
    uint8_t           RESERVED2[4];   /* 0x2C  (reserved) */
} pwm_t;
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, CTRL) == 0x00, PWM_CTRL_offset, "PWM.CTRL offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, CC) == 0x10, PWM_CC_offset, "PWM.CC offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, DT0) == 0x20, PWM_DT0_offset, "PWM.DT0 offset");
REGFORGE_STATIC_ASSERT(offsetof(pwm_t, DT1) == 0x28, PWM_DT1_offset, "PWM.DT1 offset");
REGFORGE_STATIC_ASSERT(sizeof(((pwm_t *)0)->CC) == 0x10, PWM_CC_size, "PWM.CC array size");
REGFORGE_STATIC_ASSERT(sizeof(pwm_t) == 0x30, PWM_SIZE, "PWM struct size vs addressBlock");

/* Per-instance names for the shared type, so a signature never has to know
 * which instances share a layout. Aliases, not distinct types: a function
 * taking pwm_t * accepts any of them. */
typedef pwm_t pwma_t;
typedef pwm_t pwmb_t;

/* PWMA @ 0x40015000 */
#define PWMA_BASE (0x40015000UL)
REGFORGE_MAYBE_UNUSED static pwm_t *const PWMA = (pwm_t *)PWMA_BASE;

/* PWMA.CTRL */
#define PWMA_CTRL (*(volatile uint32_t *)(PWMA_BASE + 0x00000000UL))

/* PWMA.CC[4] */
#define PWMA_CC_COUNT (4U)
#define PWMA_CC(i) (*(volatile uint32_t *)(PWMA_BASE + 0x00000010UL + (i) * 0x00000004UL))

/* PWMA.DT0 */
#define PWMA_DT0 (*(volatile uint32_t *)(PWMA_BASE + 0x00000020UL))

/* PWMA.DT1 */
#define PWMA_DT1 (*(volatile uint32_t *)(PWMA_BASE + 0x00000028UL))

/* PWMB @ 0x40015100 */
#define PWMB_BASE (0x40015100UL)
REGFORGE_MAYBE_UNUSED static pwm_t *const PWMB = (pwm_t *)PWMB_BASE;

/* PWMB.CTRL */
#define PWMB_CTRL (*(volatile uint32_t *)(PWMB_BASE + 0x00000000UL))

/* PWMB.CC[4] */
#define PWMB_CC_COUNT (4U)
#define PWMB_CC(i) (*(volatile uint32_t *)(PWMB_BASE + 0x00000010UL + (i) * 0x00000004UL))

/* PWMB.DT0 */
#define PWMB_DT0 (*(volatile uint32_t *)(PWMB_BASE + 0x00000020UL))

/* PWMB.DT1 */
#define PWMB_DT1 (*(volatile uint32_t *)(PWMB_BASE + 0x00000028UL))
```

### A cluster array

Demonstrates [clusters.md](../clusters.md#rule-2-a-cluster-arrays-element-is-padded-to-the-stride). `CH[%s]` becomes one nested type, padded to the stride and size-asserted, used as `CH[4]`, with indexed macros for its registers.

From [this SVD](../formats/svd.md#a-cluster-array):

```c
/* Peripherals */

/* -------------------------------------------------------------------------- */
/* DMA */

/* DMA.CH (4 elements, 0x10 bytes apart) */
typedef struct {
    volatile uint32_t CTRL;          /* 0x00 */
    volatile uint32_t SRC;           /* 0x04 */
    uint8_t           RESERVED0[8];  /* 0x08  (reserved) */
} dma_ch_t;
REGFORGE_STATIC_ASSERT(offsetof(dma_ch_t, CTRL) == 0x00, DMA_CH_CTRL_offset, "DMA.CH.CTRL offset");
REGFORGE_STATIC_ASSERT(offsetof(dma_ch_t, SRC) == 0x04, DMA_CH_SRC_offset, "DMA.CH.SRC offset");
REGFORGE_STATIC_ASSERT(sizeof(dma_ch_t) == 0x10, DMA_CH_SIZE, "DMA.CH element size vs dimIncrement");

typedef struct {
    volatile uint32_t CFG;            /* 0x00 */
    uint8_t           RESERVED0[12];  /* 0x04  (reserved) */
    dma_ch_t          CH[4];          /* 0x10 */
} dma_t;
REGFORGE_STATIC_ASSERT(offsetof(dma_t, CFG) == 0x00, DMA_CFG_offset, "DMA.CFG offset");
REGFORGE_STATIC_ASSERT(offsetof(dma_t, CH) == 0x10, DMA_CH_offset, "DMA.CH offset");
REGFORGE_STATIC_ASSERT(sizeof(((dma_t *)0)->CH) == 0x40, DMA_CH_size, "DMA.CH array size");
REGFORGE_STATIC_ASSERT(sizeof(dma_t) == 0x50, DMA_SIZE, "DMA struct size vs addressBlock");

/* DMA @ 0x40016000 */
#define DMA_BASE (0x40016000UL)
REGFORGE_MAYBE_UNUSED static dma_t *const DMA = (dma_t *)DMA_BASE;

/* DMA.CFG */
#define DMA_CFG (*(volatile uint32_t *)(DMA_BASE + 0x00000000UL))

/* DMA.CH[4].CTRL */
#define DMA_CH_CTRL(i) (*(volatile uint32_t *)(DMA_BASE + 0x00000010UL + (i) * 0x00000010UL))

/* DMA.CH[4].SRC */
#define DMA_CH_SRC(i) (*(volatile uint32_t *)(DMA_BASE + 0x00000014UL + (i) * 0x00000010UL))
```
