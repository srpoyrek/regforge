# Interrupt rules

**Read from:** [`interrupt`, `cpu`](formats/svd.md#peripheral) &nbsp;·&nbsp; **Emitted as:** [the vector enum and NVIC helpers](targets/c.md)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


The enum and the NVIC helpers below are shown as C because that is the only
writer today; the vector rules themselves are not C-specific.

Code: `regforge/interrupts.py`, `regforge/arch.py`, `regforge/resolve.py`.
Tests: `tests/core/test_interrupts.py`,
`tests/check/test_derived_interrupts.py`, `tests/writers/c/test_interrupts.py`.

## Rule 1: interrupts are not inherited through [`derivedFrom`](formats/svd.md#peripheral)

A derived peripheral copies its base's registers and address blocks, but not its
interrupts. Each instance has its own vector.

### Example

Input — read as [CMSIS-SVD](formats/svd.md#peripheral):

```xml
<peripheral><name>UART0</name>
  <interrupt><name>UART0</name><value>20</value></interrupt>
<peripheral derivedFrom="UART0"><name>UART1</name>
  <interrupt><name>UART1</name><value>21</value></interrupt>
```

Both instances get their own `_IRQ` constant.

If the derived peripheral declares no interrupt, the SVD spec says it inherits
the base's. That puts two peripherals on one vector under the base's name.
regforge does not inherit, and reports it:

```
warn: ADCB: derivedFrom 'ADCA' but declares no interrupt of its own; per SVD
      spec it would inherit the base's vector(s) (40) -- two peripherals on one
      vector. regforge treats interrupts as per-instance and does not inherit,
      so ADCB has no vector; declare its own <interrupt>.
```

### Corner cases

| Case | Result |
|---|---|
| Derived declares a vector equal to the base's | Warning. A separate instance normally needs a separate vector. |
| Base has no interrupt either | No finding. Nothing was lost. |
| Base has several vectors | All are listed in the warning. |

## Rule 2: one device-wide enum, sorted by vector number

Every distinct interrupt becomes one enumerator, named after the interrupt, not
the peripheral.

Emitted as [C](targets/c.md):

```c
typedef enum {
    DC_UART0_IRQn    = 20,  /* UART0 global interrupt */
    DC_TIM1_UP_IRQn  = 25,  /* TIM1 update */
    DC_TIM1_BRK_IRQn = 26,  /* TIM1 break */
    DC_SPI1_IRQn     = 30   /* SPI1 interrupt */
} dc_irqn_e;
```

### Corner cases

| Case | Result |
|---|---|
| A peripheral with several vectors | One enumerator each, named after the interrupt. `TIM1_UP` and `TIM1_BRK` would collide if named after the peripheral. |
| Interrupt name differs from peripheral name | The interrupt's name is used. |
| Last enumerator | No trailing comma. C89 with `-pedantic-errors` rejects it. |
| Enum type name | Ends in `_e`, not `_t`. |

## Rule 3: one vector used by several peripherals appears once

Some packages combine interrupts, so two peripherals declare different interrupt
names with the same value. The enum lists the vector once. Each peripheral's
`_IRQ` constant points at it, and the comment names the others.

Emitted as [C](targets/c.md#instance-names):

```c
#define DC_SPI0_IRQ DC_SPI0_IRQn  /* SPI0 interrupt, vector 30 -- shared with DC_SPI1; demux in ISR */
```

This is a shared vector: same number, different addresses. It is not
`alternatePeripheral`, which is the same address.

Copies expanded from a `<dim>` peripheral template share the template's vector
when the interrupt is named per copy (`UART%s_IRQ`), because `dim` cannot shift
a number; the copies are listed at each instance like any other shared vector.
An interrupt named without `%s` stays on the first copy alone, and the others
are reported as having no vector of their own; see
[arrays.md](arrays.md#rule-5-peripheral-copies-form-one-family).

## Rule 4: NVIC helpers are emitted only for Cortex-M

The interrupt controller depends on the core, so `regforge/arch.py` reads
`<cpu><name>`. Cortex-M cores get the NVIC register banks at the addresses ARM
fixes for all vendors, plus helpers.

Emitted as [C](targets/c.md):

```c
REGFORGE_INLINE void dc_nvic_enable(dc_irqn_e irq)
```

The helpers take `dc_irqn_e`, so a plain `int` does not compile. In debug builds
they bounds-check against [`deviceNumInterrupts`](formats/svd.md#cpu), or against the highest declared
vector plus one when the device omits that element. With `NDEBUG` each helper
compiles to the register access alone.

Other cores get the enum but no helpers. RISC-V PLIC and CLIC, and Cortex-A/R
GIC, are not implemented.
