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
| `derivedFrom` | the base it copies from | an **XML attribute**, not a child element; may name a `<dim>` copy, or the template itself (then its first copy) |
| `<groupName>` | family label | see [ir/families.md](../families.md) |
| `<headerStructName>` | requested struct name | see [ir/naming.md](../naming.md) |
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | peripheral-level defaults | see [ir/defaults.md](../defaults.md) |
| `<addressBlock>` | declared footprint, repeatable | see [ir/address-blocks.md](../address-blocks.md) |
| `<interrupt>` | a vector, repeatable | see [ir/interrupts.md](../interrupts.md) |
| `<registers><register>` | the registers | |
| `<registers><cluster>` | a register group, see [Cluster](#cluster) | see [ir/clusters.md](../clusters.md) |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [ir/arrays.md](../arrays.md) |

## Cluster

A `<cluster>` groups registers inside a peripheral at an offset of its own. Its
registers and nested clusters are read the same way as a peripheral's, with
offsets relative to the cluster.

| Element | Becomes | Notes |
|---|---|---|
| `<name>` | cluster name | |
| `<addressOffset>` | offset from the enclosing peripheral or cluster, in address units | defaults to `0` |
| `<description>` | comment text | |
| `derivedFrom` | the cluster it copies from | an **XML attribute**; parsed and reported, not resolved yet |
| `<headerStructName>` | the vendor's name for the cluster's struct type | |
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | cluster-level defaults, one rung below the peripheral's | see [ir/defaults.md](../defaults.md) |
| `<register>` | the registers, as direct children | |
| `<cluster>` | nested clusters, as direct children | |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [ir/arrays.md](../arrays.md) |

## Register

| Element | Becomes | Default |
|---|---|---|
| `<name>` | register name | `""` |
| `<addressOffset>` | offset from the base, in address units | `0` |
| `<size>`, `<resetValue>`, `<resetMask>`, `<access>` | resolved through the defaults chain | absent |
| `<description>` | comment text | absent |
| `<fields><field>` | the bit fields | none |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [ir/arrays.md](../arrays.md) |

## Field

The bit range can be written three ways, and all three are accepted:

| Form | Example |
|---|---|
| `<bitRange>` | `[7:4]` |
| `<bitOffset>` + `<bitWidth>` | `4` and `4` |
| `<lsb>` + `<msb>` | `4` and `7` |

`<enumeratedValues><enumeratedValue>` becomes the field's named constants. A
value with no `<value>` child is skipped, because there is nothing to name.

`<dim>`, `<dimIncrement>` and `<dimIndex>` are read on a field too, with the
increment in bits; see [Arrays](#arrays).

## Arrays

`<dim>`, `<dimIncrement>` and `<dimIndex>` may appear on a peripheral, a
cluster, a register or a field, and mean the same on each: the element is a
template, `<dim>` copies of it exist, `<dimIncrement>` apart, and `%s` in the
name is replaced by each copy's label. The reader stores the three values as
read and leaves the template in place; a later pass expands it. The rules that
act on them are in [ir/arrays.md](../arrays.md).

| Element | Becomes |
|---|---|
| `<dim>` | the number of copies; at least 1 |
| `<dimIncrement>` | the distance between two neighbouring copies: address units on a peripheral, cluster or register, bits on a field |
| `<dimIndex>` | the labels that replace `%s`; absent means `0`, `1`, `2`, ... |
| `<dimName>` | a name for the type the copies share; see [ir/naming.md](../naming.md) |
| `<dimArrayIndex>` | names for an array's indices, each an `<enumeratedValue>` with a `<value>` |

`<dimIndex>` is a comma-separated list; any entry may be a range:

| Written | Labels |
|---|---|
| `A,B,C` | `A`, `B`, `C` |
| `0-3` | `0`, `1`, `2`, `3` |
| `A-D` | `A`, `B`, `C`, `D` |
| `0-3,7` | `0`, `1`, `2`, `3`, `7` |
| `3-0` | `0`, `1`, `2`, `3`, and the reader reports the reversed range |

The reader only turns the text into labels. How many there are, and whether
they can end an identifier, is judged when the template is expanded; see
[ir/arrays.md](../arrays.md#rule-4-labels-come-from-dimindex-else-from-0).

A file that cannot be expanded is refused when it is read, the way a field
with no bit range is:

| Case | Result |
|---|---|
| `%s` in a name without `<dim>` | error |
| a negative `<dim>` | error |

A `<dim>` on a name without `%s` is not refused. Every copy would be the same
identifier, so expansion appends the index (`UART` with `<dim>` 4 gives `UART0`
to `UART3`) and reports it; put `%s` in the name to choose where the index goes.
Nor is a `<dim>` of 0 or a `<dim>` without `<dimIncrement>`: both are stored as
read and judged by expansion (dropped, or kept as one instance), and a
`<dimIncrement>` with no `<dim>` is noted by the reader and ignored; see
[ir/arrays.md](../arrays.md#rule-1-expansion-runs-first-and-only-copies).

The stride is not judged here. Whether `<dimIncrement>` fits the element needs
the resolved register size, which exists only after defaults resolution.

## Not read

These are in the SVD schema but do not affect output today:

| Element | Status |
|---|---|
| `alternateCluster` | not parsed |
| `alternatePeripheral`, `alternateRegister` | not parsed; see [ir/address-blocks.md](../address-blocks.md) |
| `<protection>` | not parsed |
| `<prependToName>`, `<appendToName>` | not applied |
| `<headerSystemFilename>` | not applied |
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

### A peripheral array with a register array

Demonstrates [arrays.md](../arrays.md#rule-2-names-is-copies-names-is-an-array). `PWM%s` becomes `PWMA` and `PWMB`, one family; `CC[%s]` is one packed array member with an indexed macro; `DT%s` is two separately placed registers.

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
      <dim>2</dim><dimIncrement>0x100</dimIncrement><dimIndex>A,B</dimIndex>
      <name>PWM%s</name><baseAddress>0x40015000</baseAddress>
      <addressBlock><offset>0</offset><size>0x30</size><usage>registers</usage></addressBlock>
      <registers>
        <register><name>CTRL</name><addressOffset>0x0</addressOffset></register>
        <register><dim>4</dim><dimIncrement>4</dimIncrement><name>CC[%s]</name><addressOffset>0x10</addressOffset></register>
        <register><dim>2</dim><dimIncrement>8</dimIncrement><name>DT%s</name><addressOffset>0x20</addressOffset></register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#a-peripheral-array-with-a-register-array).

### A cluster array

Demonstrates [clusters.md](../clusters.md#rule-2-a-cluster-arrays-element-is-padded-to-the-stride). `CH[%s]` becomes one nested type, padded to the stride and size-asserted, used as `CH[4]`, with indexed macros for its registers.

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
      <name>DMA</name><baseAddress>0x40016000</baseAddress>
      <addressBlock><offset>0</offset><size>0x50</size><usage>registers</usage></addressBlock>
      <registers>
        <register><name>CFG</name><addressOffset>0x0</addressOffset></register>
        <cluster>
          <dim>4</dim><dimIncrement>0x10</dimIncrement><name>CH[%s]</name><addressOffset>0x10</addressOffset>
          <register><name>CTRL</name><addressOffset>0x0</addressOffset></register>
          <register><name>SRC</name><addressOffset>0x4</addressOffset></register>
        </cluster>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#a-cluster-array).
