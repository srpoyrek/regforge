# regforge

Converts a register description in one format into source code in another.
Today that is CMSIS-SVD in and a C header out.

## Where to start

- **[Rules](rules/README.md)** — every decision regforge makes about the
  output, with input, output, and corner cases for each.
- **[CMSIS-SVD](rules/formats/svd.md)** — what is read from the file, and what
  is not.
- **[C](rules/targets/c.md)** — how the output is spelled.

## Install and run

```
pip install regforge
regforge device.svd -o device.h
```

The full command reference and compiler support table are in the
[project README](https://github.com/srpoyrek/regforge#readme).
