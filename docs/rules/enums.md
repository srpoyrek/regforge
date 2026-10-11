# Enumerated value rules

**Read from:** [`enumeratedValues`, `enumeratedValue`, `usage`](formats/svd.md#field) &nbsp;·&nbsp; **Emitted as:** [field macros](targets/c.md#field-macros) (the constants), and a finding on the command line

Add an input format or an output target and only those two links change;
the rule below is unchanged.


A field can name what its bits mean: an enumerated set, a list of entries that each give a
number a name, with a `usage` saying whether the set describes what a read returns, what a
write accepts, or both. The rules live in three classes, one per element, each knowing its
own element and the level below it:

- `EnumeratedValueResolution` is one entry: the numbers it names (a plain number, or every
  number a `0b01xx` pattern matches, and none for a catch-all `isDefault` entry), and
  whether the field can hold them.
- `EnumUsageResolution` is the direction a set describes: reads, writes or both.
- `EnumSetResolution` is one set: its entries together, and how it compares with another
  set of the same field.

None of them knows the field. The [field's class](fields.md) is given the sets, passes
each its width and path, and compares its sets in pairs. Collisions use the shared rule of
[bits.md](bits.md): two claimants on one position of a space, here numbers and directions.

Code: `regforge/resolution/enumerated_value.py`, `regforge/resolution/enum_usage.py`,
`regforge/resolution/enum_set.py`, `regforge/resolution/placeholder.py`,
`regforge/resolution/field.py` (`sets`, `enum_findings`), `regforge/ir/enumerated_value.py`,
`regforge/ir/enum_set.py`.
Tests: `tests/resolution/test_enumerated_value_resolution.py`,
`tests/resolution/test_enum_usage_resolution.py`,
`tests/resolution/test_enum_set_resolution.py`, `tests/resolution/test_placeholder.py`,
`tests/resolution/test_field_resolution.py`.

## Rule 1: an entry the field cannot hold is an error

An entry names a number no value of the field can be, whatever the register around it
holds: an `ERROR`. The field's own width counts, not the register's.

Input — read as [CMSIS-SVD](formats/svd.md#field):

```xml
<field>
  <name>MODE</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth>
  <enumeratedValues>
    <enumeratedValue><name>BIG</name><value>9</value></enumeratedValue>
  </enumeratedValues>
</field>
```

Output — a finding on the command line:

```
error: TIM.CTRL.MODE: BIG = 0x9 does not fit the 2-bit field
```

A pattern is judged by its widest number, and written in binary with `x` for the
don't-care bits (`0b1000x`). A catch-all entry names the rest, so it always fits.

## Rule 2: two entries on one number are a warning

The file contradicts itself, but the hardware could still be as it says, so a human
decides: a `WARNING`, one finding per pair of entries and per run of numbers.

```
warn: GPT16E0.GTITC.IVTC: value 0x2 is claimed by 10 and 10
```

| Case | Result |
|---|---|
| two plain entries with one number | `value 0x1 is claimed by A and B` |
| three entries on one number | one finding per pair: `A and B`, `A and C`, `B and C` |
| a pattern `0b01xx` and an entry `5` | `value 0x5 is claimed by P and B`, whichever is declared first |
| two patterns that share numbers | `values 0x2..0x3 are claimed by P and Q`: one finding for the run |
| a catch-all and any number | nothing: a catch-all names only the rest |
| a pattern with more than 16 `x` bits | not compared: too many numbers to list one by one |

The numbers are written in hex, as the entries are, and a set is not compared pair by
pair: plain numbers are bucketed, so only patterns are compared with every entry.

## Rule 3: a name used by two entries is a warning

The constants made from the entries would repeat (`TIM_CTRL_MODE_FAST` twice), so the
repeat is reported with the numbers it names, one finding per name.

```
warn: SYSCON.SYSMEMREMAP.MAP: the name USER_FLASH_MODE_INT is used by 2 entries (0x2, 0x3)
```

A placeholder name is not a repeat. Vendors call every unused number of a set `Reserved`,
so one set holds the name many times, and that is not two entries sharing a name. A name
is a placeholder when it is `reserved` in any case, optionally followed by `_` or digits
(`Reserved`, `RESERVED_`, `reserved3`); `Reserved_BITS` is a real name. This is the test
the [field rules](fields.md) use for repeated field names. Placeholder entries are still
compared on their numbers (Rule 2). It decides only what is reported: the header still
defines the constant of every entry, repeated ones included.

## Rule 4: a set has at most one catch-all entry

An `isDefault` entry names every number the set does not. Two of them cannot both name
the rest: a `WARNING`.

```
warn: P.R.F: 2 catch-all entries (REST, OTHER); only one can name the rest
```

## Rule 5: two sets of one field must not describe one direction

A field returns one thing when read and accepts one thing when written, so two sets may
differ only in direction. A read set beside a write set is the intended use. A read-write
set beside a read set, or two sets of one direction, contradict each other: a `WARNING`
naming the direction. A set is named by its `<name>`, or `the read set` when it has none.

```
warn: P.R.F: the read-write set and the read set both describe reads
```

| Case | Result |
|---|---|
| a read set and a write set | nothing |
| two read sets, or two write sets | `A and B both describe reads` (or writes) |
| a read-write set and a read set | `both describe reads` |
| a read-write set and a write set | `both describe writes` |
| two read-write sets | `both describe reads and writes` |

## In your files

Across the 93 vendor files in the survey (149,100 fields with sets, 154,374 sets, 393,825
entries), the rules find 69 repeated names in 69 sets (4 files, names such as `ENABLED` and
`TRISTATED`), 15 entries that do not fit their field (3 files, for instance a 1-bit field
with entries named `10` and `11`) and 6 numbers named twice (1 file: two entries both
called `10`). A further 87 repeated names are placeholders (`Reserved`, `reserved`,
`RESERVED`, `RESERVED_`, in 3 files), which are not reported. Two catch-alls and clashing
usages do not occur, and no pattern collides with another entry. The clean fixture
reports nothing.

## Not here yet

These stay in their present place until their own element is converted: copying a derived
set from the set it names (`derivedFrom`, in the resolve pass), the numbers a set leaves
unnamed (`gaps`, `is_complete`), and a name repeated across the read and the write set of
one field. Copies of one `<dim>` template are each judged, since they are separate fields.
