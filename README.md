# regforge

**reg** (registers) + **forge** (it forges / generates code).

regforge converts a device's register map from an input format into source
code or documentation for a target. It reads a description such as
[CMSIS-SVD](https://open-cmsis-pack.github.io/svd-spec/main/index.html) into a
format-independent intermediate representation, then renders that model to a
target: a C header, or an HTML register reference. Readers and writers are
pluggable, so new input formats and output targets are added independently
without changing the core.

```
input format ──reader──▶ intermediate representation ──writer──▶ target
   (SVD, …)               Device ▸ Peripheral ▸ Cluster ▸          (C header,
                          AlternateSet ▸ Register ▸ Field ▸        HTML reference,
                          EnumSet ▸ EnumeratedValue                more to follow)
```

Between the reader and the writer, the same passes run for every target:

1. **Expand `<dim>`** templates into their copies (`UART%s` into `UART0`,
   `UART1`, …), or keep a `[%s]` array as one element.
2. **Resolve `derivedFrom`** for peripherals, for registers (a name or a path such
   as `PORT.PMUX0_%s`) and for enumerated-value sets, copying what the derived
   element leaves unsaid from its base.
3. **Group alternate views** of one word into an `AlternateSet`: a register with
   no alternates is a set of one view, registers declared as alternates of one
   another (`alternateRegister`, or a name reused in another `alternateGroup`)
   are a set of several, emitted as one C union.
4. **Fill inherited defaults** (`size`, `access`, `resetValue`, `resetMask`).
5. **Run the consistency checks.** Findings are printed to stderr; none is
   dropped silently.

## Installation

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
regforge device.svd -o device.h                 # SVD in, C header out
regforge device.svd -o device.html              # SVD in, HTML register reference out
regforge device.svd                             # C header to standard output
regforge device.svd -o device.h --uncrustify    # format the generated C
regforge device.svd -o device.h --no-provenance # leave out the source hash and command
```

Options:

| Option | Description |
| --- | --- |
| `-o, --output PATH` | Output file (default: standard output). |
| `-f, --from FORMAT` | Input format; inferred from the input extension if omitted (`svd`). |
| `-t, --to TARGET` | Output target, `c` or `html`; defaults to `c`, or inferred from the output extension (`.h`, `.html`). |
| `--no-provenance` | Omit the provenance banner and audit constants (source hash, command, tool version) from the output. |
| `--uncrustify` | Format generated C/C++ output with uncrustify. |
| `--uncrustify-config PATH` | Use a specific uncrustify configuration (implies `--uncrustify`). |
| `-v, --verbose` | Log pipeline stages and per-stage timing to stderr (`-vv` for detail). |
| `--version` | Print the version and exit. |

`--uncrustify` runs the [uncrustify](https://github.com/uncrustify/uncrustify)
formatter on the *generated* C/C++ output only; it must be installed
separately and does not affect regforge's own sources.

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Written. Warnings and errors found in the description are logged to stderr but do not change the code. |
| `2` | Unknown input format or output target, or a usage error. |
| `3` | `--uncrustify` was requested but uncrustify is unavailable or failed. |
| `4` | The writer refused to emit the device, for example two registers overlapping without a declared `alternateRegister`, or an `addressUnitBits` the C writer cannot honour. |

## Output targets

**C header** (`-t c`, the default). Typed structs per peripheral, `offsetof` and
`sizeof` static asserts against the vendor's offsets and address blocks, one
union per set of alternate registers, field masks and enumerated-value
constants, an interrupt enum and, for Cortex-M, NVIC helpers. See
[Compiler support](#compiler-support) and
[the C target rules](docs/rules/targets/c.md).

**HTML register reference** (`-t html`). One self-contained file for people to
read: a contents table, then a section per peripheral with its address blocks,
interrupts, a register table, and for every register its offset and address,
size, access, reset value and mask, bit map, fields and enumerated values
(including catch-all entries and don't-care patterns such as `0b01xx`), the
registers that share its address, and notes on what reading or writing it does.
There is no script and no external file, and the page prints one peripheral to a
page, so a browser's "save as PDF" makes the PDF. The same input gives the same
bytes.

## Compiler support

Generated C headers target C89, C99, C11, and C23, and also compile as C++.
Portability lives in a small self-contained `REGFORGE_*` prelude
([compat.h.j2](regforge/writers/templates/c/compat.h.j2)) that adapts
`static_assert` and `inline` per compiler and standard.
Every generated header also satisfies the required rules of MISRA C:2012;
`nox -s misra` runs cppcheck's MISRA addon over the goldens in CI, with the
advisory deviations listed in
[the C target rules](docs/rules/targets/c.md#misra-c2012).

| Compiler | Status |
| --- | --- |
| GCC, Clang | Verified — compile matrix (C89 / C99 / C11) and C++ (C++11 / C++17); local + CI. |
| GNU Arm Embedded (`arm-none-eabi-gcc`) | Covered in CI — the free bare-metal Cortex-M cross-compiler. |
| MSVC | Covered in CI (Windows) — compilability. |
| Arm Compiler 6 (armclang) | Supported (Clang-based, same code path); exercised where installed. |
| Arm Compiler 5, IAR | In the matrix but commercially licensed — run only on a self-hosted runner with the toolchain. |
| Pre-8 IAR, Arm Compiler <5, other | Not officially supported — headers still compile, but unreferenced peripheral handles may warn. |

The compile matrix
([tests/writers/c/test_compiles.py](tests/writers/c/test_compiles.py)) exercises
every compiler it finds on `PATH` across the standards it supports and skips
those that are absent — run it in isolation with `nox -s compilers`. A companion
size report ([tools/size_report.py](tools/size_report.py), `nox -s sizes`) prints
code/data size per compiler and optimization level, and a
[zero-cost test](tests/writers/c/test_sizes.py) asserts an included-but-unused
header adds no bytes at `-Os`.

## Documentation

**https://srpoyrek.github.io/regforge/** — built from [docs/](docs/) and
published on every push to `main`.

What regforge does with each part of an SVD file is in
[docs/rules/](docs/rules/): each rule states what it does, shows input and
output, lists the corner cases, and links to the input format it reads and the
output target it emits. Among them, [derived.md](docs/rules/derived.md) covers
how `derivedFrom` is resolved for registers and enumerated-value sets,
[alternates.md](docs/rules/alternates.md) how alternate registers and
`alternateGroup` become one union, and [arrays.md](docs/rules/arrays.md) how
`<dim>` is expanded. To view it locally:

```bash
mkdocs serve        # live at http://127.0.0.1:8000, reloads on save
nox -s docs         # strict build to site/
```

## Extending

**Add an input format:** subclass `Reader` in a new module under
[regforge/readers/](regforge/readers/), set `format_name` and
`file_extensions`, and register it with `register_reader`.

**Add an output target:** subclass `Writer` in a new module under
[regforge/writers/](regforge/writers/), set `target_name`, `file_extension`,
and `language`, provide a template under `writers/templates/`, and register it
with `register_writer`.

Nothing else changes: the CLI discovers the new format or target through the
registry automatically.

The SVD reader ([regforge/readers/svd/](regforge/readers/svd/)) and the HTML
writer ([regforge/writers/html/](regforge/writers/html/)) show the shape to
follow for anything larger than a single module: one class per element, each
with its own test file, composed recursively (the device asks its peripherals,
each peripheral its registers, each register its fields, and so on).

## Development

```bash
pytest                    # run the tests
nox                       # run tests and lint
nox -s compilers          # compile the golden header on every compiler on PATH
nox -s sizes              # size per compiler / optimization level
nox -s format             # apply ruff + black
pre-commit install        # enable hooks on commit
```

Output is verified three ways:

- **Golden tests** — the suite parses
  [tests/fixtures/svd/minimal.svd](tests/fixtures/svd/minimal.svd) (the clean
  reference chip, which reports no findings) and
  [lint_demo.svd](tests/fixtures/svd/lint_demo.svd) (the catalogue of flaws the
  checks report) and compares the generated C header and HTML page
  byte-for-byte against [tests/golden/c/](tests/golden/c/) and
  [tests/golden/html/](tests/golden/html/). Regenerate them after an
  intentional change with `nox -s goldens`; the goldens record the command that
  made them, so do not add flags or change the output path by hand.
- **Compile matrix** — the C header must build cleanly under every C/C++ compiler
  present (see [Compiler support](#compiler-support)); GNU-family compilers are
  held to `-Wextra -Werror`.
- **Zero-cost check** — an included-but-unused header must add no code or data at
  `-Os`, so the abstractions stay free in optimized firmware.

All three run in CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) on
Linux and Windows.

## License

Apache-2.0 — see [LICENSE](LICENSE).

Source generated by regforge carries no license obligation. Output may be used
in proprietary firmware with no attribution requirement.
