# regforge rules

regforge reads a register description in one format and writes source code in
another. The rules that decide *what* the output must contain are the same
whatever the pair is; only the reading and the spelling change.

So each rule has its own page, and every rule page links to the format it is
read from and the target it is emitted as.

```
    input format          rules            output target
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │ formats/svd  │──►│  naming      │──►│  targets/c   │
  │ (others)     │   │  families    │   │  (others)    │
  └──────────────┘   │  ...         │   └──────────────┘
                     └──────────────┘
```

Today there is one of each: CMSIS-SVD in, C out. Adding a target means writing
`targets/<language>.md` and updating one link per rule. Adding an input format
means writing `formats/<format>.md` and doing the same. No rule page is
rewritten.

## Rules

| Rule | Decides |
|---|---|
| [structure.md](structure.md) | The order of blocks in a generated file |
| [naming.md](naming.md) | What a type is called |
| [families.md](families.md) | Which peripherals share one type |
| [address-blocks.md](address-blocks.md) | Declared footprint, size contract, padding |
| [interrupts.md](interrupts.md) | Vectors, and what `derivedFrom` does not carry |
| [defaults.md](defaults.md) | Inherited `size` / `access` / `reset*` |
| [address-math.md](address-math.md) | Address units, bus width, member offsets |
| [arrays.md](arrays.md) | `dim`: copies, arrays, strides |
| [clusters.md](clusters.md) | Register groups as nested types |
| [alternates.md](alternates.md) | Two layouts of one word: `alternateRegister` as a union |

## Input formats

| Format | Page |
|---|---|
| CMSIS-SVD | [formats/svd.md](formats/svd.md) |

## Output targets

| Target | Page |
|---|---|
| C | [targets/c.md](targets/c.md) |

## Findings

A check reports either a warning or an error. Checks belong to the rules, not to
a format or a target: they read the model, so they run whatever the pair is.

| Severity | Used for |
|---|---|
| `WARNING` | The source may be wrong, or regforge cannot verify it |
| `ERROR` | The source contradicts itself; no hardware could match it |

Example of each:

- `WARNING`: a register is wider than the bus. This can be a multi-access
  register or a mistake, so a person decides.
- `ERROR`: the bus is narrower than one address unit. This cannot be built.

Checks live in `regforge/check.py`. Adding a function to the `ALL_CHECKS` tuple
is all the wiring needed; the CLI picks it up from there.
