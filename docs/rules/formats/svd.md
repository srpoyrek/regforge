# CMSIS-SVD

How an SVD file is read: which elements become which values, and how those
values are parsed. The rules that act on them are in the rule pages, linked
from each section.

Code: `regforge/readers/svd.py`. Tests: `tests/readers/svd/`.

Code: `regforge/readers/svd.py`.
Tests: `tests/readers/svd/`.

## Device

| Element | Becomes | Default when absent |
|---|---|---|
| `<name>` | device name | `"device"` |
| `<vendor>`, `<series>`, `<version>`, `<description>` | metadata for the output banner | absent |
| `<licenseText>` | copied into the banner | absent |
| `<headerDefinitionsPrefix>` | prefix for emitted identifiers | none |
| `<addressUnitBits>` | bits per address step | `8` |
| `<width>` | data bus width in bits | `32` |
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | device-level register defaults | absent |
| `<cpu>` | the processor description | absent |
| `<vendorExtensions>` | kept verbatim as text, never interpreted | absent |

## CPU

Every field is optional, and several apply only to Arm Cortex-M. A reader for
another architecture leaves them absent rather than guessing.

| Element | Becomes |
|---|---|
| `<name>`, `<revision>`, `<endian>` | core identity |
| `<mpuPresent>`, `<fpuPresent>`, `<vtorPresent>` | capability flags |
| `<nvicPrioBits>` | implemented priority bits |
| `<vendorSystickConfig>` | flag |
| `<deviceNumInterrupts>` | vector count, used to bounds-check the NVIC helpers |

## Peripheral

| Element | Becomes | Notes |
|---|---|---|
| `<name>` | peripheral name | |
| `<baseAddress>` | absolute base | defaults to `0` |
| `<description>` | comment text | |
| `derivedFrom` | the base it copies from | an **XML attribute**, not a child element |
| `<groupName>` | family label | see [ir/families.md](../families.md) |
| `<headerStructName>` | requested struct name | see [ir/naming.md](../naming.md) |
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | peripheral-level defaults | see [ir/defaults.md](../defaults.md) |
| `<addressBlock>` | declared footprint, repeatable | see [ir/address-blocks.md](../address-blocks.md) |
| `<interrupt>` | a vector, repeatable | see [ir/interrupts.md](../interrupts.md) |
| `<registers><register>` | the registers | |

## Register

| Element | Becomes | Default |
|---|---|---|
| `<name>` | register name | `""` |
| `<addressOffset>` | offset from the base, in address units | `0` |
| `<size>`, `<resetValue>`, `<resetMask>`, `<access>` | resolved through the defaults chain | absent |
| `<description>` | comment text | absent |
| `<fields><field>` | the bit fields | none |

## Field

The bit range can be written three ways, and all three are accepted:

| Form | Example |
|---|---|
| `<bitRange>` | `[7:4]` |
| `<bitOffset>` + `<bitWidth>` | `4` and `4` |
| `<lsb>` + `<msb>` | `4` and `7` |

`<enumeratedValues><enumeratedValue>` becomes the field's named constants. A
value with no `<value>` child is skipped, because there is nothing to name.

## Not read

These are in the SVD schema but do not affect output today:

| Element | Status |
|---|---|
| `<cluster>` | not walked; a register group inside a peripheral |
| `<dim>`, `<dimIncrement>` | register arrays are not modelled |
| `alternatePeripheral`, `alternateRegister` | not parsed; see [ir/address-blocks.md](../address-blocks.md) |
| `<protection>` | not parsed |
| `<prependToName>`, `<appendToName>` | not applied |
| `<headerSystemFilename>`, `<headerStructName>` on clusters | not applied |
| `<writeConstraint>`, `<readAction>`, `<modifiedWriteValues>` | not parsed |

`<vendorExtensions>` is kept as text so nothing is lost, but its contents are
never interpreted.


Code: `regforge/readers/svd.py`.
Tests: `tests/readers/svd/`.

## Integers

The schema allows three notations, and all are accepted:

| Written | Value |
|---|---|
| `42` | 42 |
| `0x1F` | 31 |
| `0b1010` | 10 |
| `#1010` | 10 |

`#` is the SVD spelling for binary and appears in real vendor files.

## Booleans

The schema says `true` / `false`, but vendors also write `1` / `0`. Both are
accepted:

| Written | Value |
|---|---|
| `true`, `1` | true |
| `false`, `0` | false |
| anything else | absent |

An unrecognised value is treated as absent rather than as false, so a typo does
not silently assert that a feature is missing.

## Text

Text is stripped of surrounding whitespace. Line breaks inside the text are
kept, because descriptions and licence text are multi-line.

| In the file | Value |
|---|---|
| `<groupName>UART</groupName>` | `UART` |
| `<groupName>  UART  </groupName>` | `UART` |
| `<groupName>   </groupName>` | `""` — empty, so rules skip it |
| `<groupName></groupName>` | absent |
| element not present | absent |

The last two differ in the model but behave the same in every rule, because both
an empty string and an absent value are skipped.

## Missing values

A missing element becomes an absent value, never a guess. Where the schema
defines a default, that default is used and is listed in
[above](#device); where it does not, the value stays absent and any
rule that needs it reports that it is missing.

## Worked examples

The complete input for each rule example. The C each one produces is on the
[C target page](../targets/c.md#worked-examples), and the rule it demonstrates
is linked from its heading.

### Naming precedence

Demonstrates [naming.md](../naming.md#rule-1-type-name-precedence). A peripheral declaring `headerStructName`, so the type is named `can_node_t` rather than `can_t` from its `groupName`.

```xml
<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>DEMO</name>
  <addressUnitBits>8</addressUnitBits>
  <width>32</width>
  <size>32</size>
  <access>read-write</access>
  <peripherals>
    <peripheral>
      <name>CAN_NODE0</name>
      <groupName>CAN</groupName>
      <headerStructName>CAN_NODE</headerStructName>
      <baseAddress>0x48014000</baseAddress>
      <registers>
        <register><name>NCR</name><addressOffset>0x0</addressOffset></register>
        <register><name>NSR</name><addressOffset>0x4</addressOffset></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#naming-precedence).

### One group becoming two types

Demonstrates [naming.md](../naming.md#rule-2-naming-the-types-when-one-group-becomes-several). `FPU` and `FPU_CPACR` share `groupName=FPU` but have different registers, so two types are emitted and the peripheral called `FPU` takes the plain name.

```xml
<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>DEMO</name>
  <addressUnitBits>8</addressUnitBits>
  <width>32</width>
  <size>32</size>
  <access>read-write</access>
  <peripherals>
    <peripheral>
      <name>FPU_CPACR</name><groupName>FPU</groupName><baseAddress>0xE000ED88</baseAddress>
      <registers><register><name>CPACR</name><addressOffset>0x0</addressOffset></register></registers>
    </peripheral>
    <peripheral>
      <name>FPU</name><groupName>FPU</groupName><baseAddress>0xE000EF34</baseAddress>
      <registers>
        <register><name>FPCCR</name><addressOffset>0x0</addressOffset></register>
        <register><name>FPCAR</name><addressOffset>0x4</addressOffset></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#one-group-becoming-two-types).

### Two peripherals sharing one type

Demonstrates [families.md](../families.md#rule-1-grouping-follows-derivedfrom-and-groupname). `UART1` derives from `UART0`, so one struct is emitted with two instance pointers.

```xml
<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>DEMO</name>
  <addressUnitBits>8</addressUnitBits>
  <width>32</width>
  <size>32</size>
  <access>read-write</access>
  <peripherals>
    <peripheral>
      <name>UART0</name><groupName>UART</groupName><baseAddress>0x40004000</baseAddress>
      <registers>
        <register><name>DR</name><addressOffset>0x0</addressOffset></register>
        <register><name>SR</name><addressOffset>0x4</addressOffset><access>read-only</access></register>
      </registers>
    </peripheral>
    <peripheral derivedFrom="UART0">
      <name>UART1</name><baseAddress>0x40004400</baseAddress>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#two-peripherals-sharing-one-type).

### A registers block and a buffer block

Demonstrates [address-blocks.md](../address-blocks.md#rule-1-usage-decides-what-is-emitted). The buffer window becomes one array member, and the size assert covers both blocks.

```xml
<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>DEMO</name>
  <addressUnitBits>8</addressUnitBits>
  <width>32</width>
  <size>32</size>
  <access>read-write</access>
  <peripherals>
    <peripheral>
      <name>UART0</name><baseAddress>0x40004000</baseAddress>
      <addressBlock><offset>0</offset><size>0x8</size><usage>registers</usage></addressBlock>
      <addressBlock><offset>0x8</offset><size>0x20</size><usage>buffer</usage></addressBlock>
      <registers>
        <register><name>DR</name><addressOffset>0x0</addressOffset></register>
        <register><name>SR</name><addressOffset>0x4</addressOffset><access>read-only</access></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#a-registers-block-and-a-buffer-block).

### Inherited register properties

Demonstrates [defaults.md](../defaults.md#rule-1-the-inheritance-chain). Neither register declares a size; both take it from the device `<width>`, and `SR` overrides access.

```xml
<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.3">
  <name>DEMO</name>
  <addressUnitBits>8</addressUnitBits>
  <width>32</width>
  <size>32</size>
  <access>read-write</access>
  <peripherals>
    <peripheral>
      <name>MISC</name><baseAddress>0x40030000</baseAddress>
      <registers>
        <register><name>DR</name><addressOffset>0x0</addressOffset></register>
        <register><name>SR</name><addressOffset>0x4</addressOffset><access>read-only</access></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#inherited-register-properties).
