# Data type rules

**Read from:** [`dataType`](formats/svd.md#register) &nbsp;·&nbsp; **Emitted as:** a `Type` entry in the register's header in the HTML reference, and a finding on the command line (the [C header](targets/c.md#register-members) chooses a member's type from the register's size and does not use it)

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A register can say which C type it is meant to be accessed as: one of `uint8_t`, `uint16_t`,
`uint32_t`, `uint64_t`, `int8_t`, `int16_t`, `int32_t`, `int64_t`, or a pointer to any of them.
The rule about it lives in one class, `DataTypeResolution`, which knows only the type and the
register's size as a number; the collector hands it both for each register.

Code: `regforge/resolution/data_type.py`, `regforge/resolution/collector.py` (`_effects`),
`regforge/ir/device/peripheral/register/data_type.py`, `regforge/readers/svd/device/peripheral/register/data_type.py`,
`regforge/writers/html/device/peripheral/register/data_type.py` (`DataTypeHtml`),
`regforge/writers/html/device/peripheral/register/register.py`.
Tests: `tests/resolution/test_data_type_resolution.py`, `tests/resolution/test_collect.py`,
`tests/readers/svd/device/peripheral/register/test_data_type_parser.py`,
`tests/writers/html/device/peripheral/register/test_data_type_html.py`,
`tests/writers/html/device/peripheral/register/test_register_html.py`.

## Rule 1: a data type must be as wide as its register

A data type names an integer of a fixed width: `uint16_t` is 16 bits. It contradicts a register
of another size. The file disagrees with itself, though the hardware could still be as it says,
so a human decides: a `WARNING`.

Input — read as [CMSIS-SVD](formats/svd.md#register):

```xml
<register>
  <name>CTRL</name><addressOffset>0x0</addressOffset><size>32</size>
  <dataType>uint16_t</dataType>
</register>
```

Output — a finding on the command line:

```
warn: TIM.CTRL: dataType uint16_t is 16 bits wide, but the register is 32 bits
```

| Case | Result |
|---|---|
| an integer type of the register's width, signed or not | nothing |
| an integer type of another width | reported |
| a pointer type (`uint8_t *`) | nothing: an address's width depends on the processor |
| a register whose size is still unresolved | nothing: the width is unknown |

## Where the data type is written

The HTML reference writes it in the register's header line, beside the size and the access:
`Type int32_t`. A value the schema does not list is ignored and noted by the reader, as every
closed-vocabulary tag is (see [access.md](access.md#reading-every-value-is-kept-or-noted)).

## In your files

Across the 93 vendor files in the survey, 16 registers state a data type, all `int32_t`, in
four Nordic files (nrf51, nrf52810, nrf52833 and nrf52840). Every one sits in a 32-bit
register, so the rule reports nothing, and no file uses a pointer type. The clean fixture
reports nothing.

## Not here yet

The C header does not use the data type: a member's type follows the register's size. Letting
a stated type decide it would change the generated headers, and is left for its own step.
