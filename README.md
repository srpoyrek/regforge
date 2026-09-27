# regforge

**reg** (registers) + **forge** (it forges / generates code).

regforge converts a device's register map from an input format into source
code for a target language. It reads a description such as
[CMSIS-SVD](https://open-cmsis-pack.github.io/svd-spec/main/index.html) into a
format-independent intermediate representation, then renders that model to a
target such as C. Readers and writers are pluggable, so new input formats and
output languages are added independently without changing the core.

```
input format ──reader──▶ intermediate representation ──writer──▶ target language
   (SVD, …)                    (Device / Peripheral /              (C, and more
                                Register / Field)                   to follow)
```

## Installation

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
regforge device.svd -o device.h                 # SVD in, C header out
regforge device.svd                             # write to standard output
regforge device.svd -o device.h --uncrustify    # format the generated C
```

Options:

| Option | Description |
| --- | --- |
| `-o, --output PATH` | Output file (default: standard output). |
| `-f, --from FORMAT` | Input format; inferred from the input extension if omitted. |
| `-t, --to TARGET` | Output target; defaults to `c`, or inferred from the output extension. |
| `--uncrustify` | Format generated C/C++ output with uncrustify. |
| `--uncrustify-config PATH` | Use a specific uncrustify configuration. |
| `-v, --verbose` | Log pipeline stages and per-stage timing to stderr (`-vv` for detail). |

`--uncrustify` runs the [uncrustify](https://github.com/uncrustify/uncrustify)
formatter on the *generated* C/C++ output only; it must be installed
separately and does not affect regforge's own sources.

## Compiler support

Generated C headers target C89, C99, C11, and C23, and also compile as C++.
Portability lives in a small self-contained `REGFORGE_*` prelude
([compat.h.j2](regforge/writers/templates/c/compat.h.j2)) that adapts
`static_assert`, `inline`, and unused-suppression per compiler and standard.

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
output target it emits. To view it locally:

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

- **Golden test** — the suite parses
  [tests/fixtures/svd/minimal.svd](tests/fixtures/svd/minimal.svd) and compares
  the generated header byte-for-byte against
  [tests/golden/c/minimal.h](tests/golden/c/minimal.h). Regenerate it after an
  intentional template change with `nox -s goldens`.
- **Compile matrix** — the header must build cleanly under every C/C++ compiler
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
