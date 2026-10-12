# CMSIS-SVD

How an SVD file is read: which elements become which values, and how those
values are parsed. The rules that act on them are in the rule pages, linked
from each section.

Code: `regforge/readers/svd/` (one parser class per element, in a folder tree that mirrors the
IR: `device/`, `device/peripheral/`, and so on down to `enum_set/`).
Tests: `tests/readers/svd/` (the same tree, one test file per parser; the tests that read a
whole file are in `whole_file/`).

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
| `<groupName>` | family label | see [families.md](../device/peripheral/families.md) |
| `<headerStructName>` | requested struct name | see [naming.md](../device/peripheral/naming.md) |
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | peripheral-level defaults | see [defaults.md](../device/defaults.md) |
| `<addressBlock>` | declared footprint, repeatable | see [address-blocks.md](../device/peripheral/address-blocks.md) |
| `<interrupt>` | a vector, repeatable | see [interrupts.md](../device/peripheral/interrupts.md) |
| `<registers><register>` | the registers | |
| `<registers><cluster>` | a register group, see [Cluster](#cluster) | see [clusters.md](../device/peripheral/cluster/clusters.md) |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [arrays.md](../device/peripheral/arrays.md) |

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
| `<size>`, `<access>`, `<resetValue>`, `<resetMask>` | cluster-level defaults, one rung below the peripheral's | see [defaults.md](../device/defaults.md) |
| `<register>` | the registers, as direct children | |
| `<cluster>` | nested clusters, as direct children | |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [arrays.md](../device/peripheral/arrays.md) |

## Register

| Element | Becomes | Default |
|---|---|---|
| `<name>` | register name | `""` |
| `<addressOffset>` | offset from the base, in address units | `0` |
| `<size>`, `<resetValue>`, `<resetMask>`, `<access>` | resolved through the defaults chain | absent |
| `<description>` | comment text | absent |
| `<fields><field>` | the bit fields | none |
| `<dim>`, `<dimIncrement>`, `<dimIndex>` | a template for several copies, see [Arrays](#arrays) | see [arrays.md](../device/peripheral/arrays.md) |
| `<alternateRegister>`, `<alternateGroup>` | another view of the register named, see [Alternate registers](#alternate-registers) | see [alternates.md](../device/peripheral/alternates.md) |
| `derivedFrom` | the register it copies from, see [Derived registers](#derived-registers) | an **XML attribute**; none |

## Derived registers

`derivedFrom` on a `<register>` names the register it takes what it leaves unsaid
from: a name in the same peripheral or cluster, or a path from the peripheral down
(`PORT.PMUX0_%s`, `CH.CTRL`). The attribute is kept as written; the resolve pass
copies the base's `size`, `resetValue`, `resetMask`, `access`, `description`,
`displayName`, `dataType`, `protection`, side-effect settings and fields into the
register wherever it states none of its own. A field of the same name replaces the
base's field in place and any other field it writes is added. Its own name, offset,
`<dim>` and `<alternateRegister>` stay. The rules, including what happens to a
`%s` template, are in [derived.md](../device/peripheral/derived.md#registers).

## Alternate registers

`<alternateRegister>` names another register of the same peripheral or
cluster that describes the same word with a different layout. Both are read
as registers; the name is kept as written and matched after expansion, so it
may name a `%s` template or a `[%s]` array.

```xml
<register><name>CCMR1_Output</name><addressOffset>0x18</addressOffset></register>
<register>
  <name>CCMR1_Input</name><alternateRegister>CCMR1_Output</alternateRegister>
  <addressOffset>0x18</addressOffset>
</register>
```

`<alternateGroup>` names the mode or function a register serves. It is kept on
the register as a label and links nothing by itself. The schema also lets a name
be reused in another group: when another register of the block has the same name,
the grouped one is renamed `NAME_GROUP` and, if the two sit at one offset, is a view
of `NAME`. A group on a name nothing else uses changes nothing. What the pair
becomes is decided by [alternates.md](../device/peripheral/alternates.md#rule-7-alternategroup-is-a-label-only-a-shared-name-renames).

## Field

The bit range can be written three ways, and all three are accepted:

| Form | Example |
|---|---|
| `<bitRange>` | `[7:4]` |
| `<bitOffset>` + `<bitWidth>` | `4` and `4` |
| `<lsb>` + `<msb>` | `4` and `7` |

Each `<enumeratedValues>` block becomes one set on the field, since a field may
carry a read set and a write set. The set keeps its `<name>`, `<headerEnumName>`,
`<usage>` (`read-write` when absent) and `derivedFrom`, which makes the set a copy of
another (see [derived.md](../device/peripheral/derived.md#rule-6-a-derived-set-is-a-copy)); its
`<enumeratedValue>` entries become the field's named constants. The schema gives an entry a `<value>`
or `<isDefault>`, never both. A catch-all `<isDefault>` entry has no number and is
kept as the entry for all other values. A `<value>` may write some bits as `x`
(`#01xx`, or `0b01xx`): the bits read as 0 in the value and are recorded as
don't-care. An entry with neither is skipped, because there is nothing to name.
The C writer reads the values of all sets together and writes a constant for each
plain number, none for a catch-all or a pattern; it does not yet act on `<usage>`.
A `derivedFrom` set already holds its base's entries by then.

`<dim>`, `<dimIncrement>` and `<dimIndex>` are read on a field too, with the
increment in bits; see [Arrays](#arrays).

## Arrays

`<dim>`, `<dimIncrement>` and `<dimIndex>` may appear on a peripheral, a
cluster, a register or a field, and mean the same on each: the element is a
template, `<dim>` copies of it exist, `<dimIncrement>` apart, and `%s` in the
name is replaced by each copy's label. The reader stores the three values as
read and leaves the template in place; a later pass expands it. The rules that
act on them are in [arrays.md](../device/peripheral/arrays.md).

| Element | Becomes |
|---|---|
| `<dim>` | the number of copies; at least 1 |
| `<dimIncrement>` | the distance between two neighbouring copies: address units on a peripheral, cluster or register, bits on a field |
| `<dimIndex>` | the labels that replace `%s`; absent means `0`, `1`, `2`, ... |
| `<dimName>` | a name for the type the copies share; see [naming.md](../device/peripheral/naming.md) |
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
[arrays.md](../device/peripheral/arrays.md#rule-4-labels-come-from-dimindex-else-from-0).

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
[arrays.md](../device/peripheral/arrays.md#rule-1-expansion-runs-first-and-only-copies).

The stride is not judged here. Whether `<dimIncrement>` fits the element needs
the resolved register size, which exists only after defaults resolution.

## Kept, not yet acted on

These are read into the IR, but the C header does not use them yet. (The HTML reference
shows a register's protection and the side effects of registers and fields, and the
[side-effect rules](../device/peripheral/register/side-effects.md) check them against the access.) On a register:
`<displayName>`, `<dataType>`, `<protection>`, `<modifiedWriteValues>`, `<readAction>` and
`<writeConstraint>` (`writeAsRead`, `useEnumeratedValues`, `range`). On a field: the last
three. On an address block: `<protection>`. At device, peripheral and cluster level:
`<protection>`, as the default for the registers below. That is every place the schema
allows `<protection>`, except the CPU's SAU configuration (see below). A spelling that
differs from the schema's only in case is read as the schema's word, and any other value
outside its list is read as absent; both are noted, for every tag with a closed list (see
[access.md](../device/access.md#reading-every-value-is-kept-or-noted)).

## Not read

These are in the SVD schema but do not affect output today:

| Element | Status |
|---|---|
| `alternateCluster` | not parsed |
| `alternatePeripheral` | not parsed; see [address-blocks.md](../device/peripheral/address-blocks.md) |
| `<prependToName>`, `<appendToName>` | not applied |
| `<headerSystemFilename>` | not applied |
| `<sauRegionsConfig>` (the CPU's SAU regions, with `protectionWhenDisabled`) | not parsed; none of the 2,459 SVD files in three public collections uses it |

`<vendorExtensions>` is kept as text so nothing is lost, but its contents are
never interpreted.


Code: `regforge/readers/svd/` (one parser class per element).
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

Demonstrates [naming.md](../device/peripheral/naming.md#rule-1-type-name-precedence). A peripheral declaring `headerStructName`, so the type is named `can_node_t` rather than `can_t` from its `groupName`.

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

Demonstrates [naming.md](../device/peripheral/naming.md#rule-2-naming-the-types-when-one-group-becomes-several). `FPU` and `FPU_CPACR` share `groupName=FPU` but have different registers, so two types are emitted and the peripheral called `FPU` takes the plain name.

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

Demonstrates [families.md](../device/peripheral/families.md#rule-1-grouping-follows-derivedfrom-and-groupname). `UART1` derives from `UART0`, so one struct is emitted with two instance pointers.

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

Demonstrates [address-blocks.md](../device/peripheral/address-blocks.md#rule-1-usage-decides-what-is-emitted). The buffer window becomes one array member, and the size assert covers both blocks.

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

Demonstrates [defaults.md](../device/defaults.md#rule-1-the-inheritance-chain). Neither register declares a size; both take it from the device `<width>`, and `SR` overrides access.

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

Demonstrates [arrays.md](../device/peripheral/arrays.md#rule-2-names-is-copies-names-is-an-array). `PWM%s` becomes `PWMA` and `PWMB`, one family; `CC[%s]` is one packed array member with an indexed macro; `DT%s` is two separately placed registers.

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

Demonstrates [clusters.md](../device/peripheral/cluster/clusters.md#rule-2-a-cluster-arrays-element-is-padded-to-the-stride). `CH[%s]` becomes one nested type, padded to the stride and size-asserted, used as `CH[DMA_CH_COUNT]`, with indexed macros for its registers.

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

### An alternate register pair

Demonstrates [alternates.md](../device/peripheral/alternates.md). `CCMR1_Input` names `CCMR1_Output` as its `alternateRegister`, so the word at `0x0C` is one union `CCMR1` with a member per view, asserted for offset and size, and each view keeps its own field macros.

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
      <name>TIM1</name><baseAddress>0x40010000</baseAddress>
      <addressBlock><offset>0</offset><size>0x10</size><usage>registers</usage></addressBlock>
      <registers>
        <register><name>CR1</name><addressOffset>0x0</addressOffset></register>
        <register>
          <name>CCMR1_Output</name><addressOffset>0xC</addressOffset>
          <fields><field><name>OC1M</name><bitOffset>4</bitOffset><bitWidth>3</bitWidth></field></fields>
        </register>
        <register>
          <name>CCMR1_Input</name><alternateRegister>CCMR1_Output</alternateRegister><addressOffset>0xC</addressOffset>
          <fields><field><name>IC1F</name><bitOffset>4</bitOffset><bitWidth>4</bitWidth></field></fields>
        </register>
      </registers>
    </peripheral>
  </peripherals>
</device>
```

Produces [this C](../targets/c.md#an-alternate-register-pair).
