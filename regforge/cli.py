"""Command-line interface.

Drives the conversion pipeline: a reader parses the input into the
intermediate representation and a writer renders it to the chosen target,
with optional post-processing of the generated source.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from enum import IntEnum
from pathlib import Path

from . import __version__
from .postprocess import FormatterNotAvailable, uncrustify
from .provenance import build_provenance
from .readers import available_readers, get_reader, reader_for_path
from .writers import EmitError, Writer, available_writers, get_writer, writer_for_path


class ExitCode(IntEnum):
    """Process exit codes returned by :func:`main`."""

    OK = 0
    USAGE_ERROR = 2  # unknown input format or output target
    FORMATTER_ERROR = 3  # uncrustify unavailable or failed
    EMIT_ERROR = 4  # the writer refused to emit the device


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="regforge",
        description="Convert register descriptions between formats "
        "(for example, CMSIS-SVD to C).",
    )
    parser.add_argument("input", help="path to the input device description")
    parser.add_argument(
        "-o",
        "--output",
        help="output file (default: standard output)",
    )
    parser.add_argument(
        "-f",
        "--from",
        dest="from_format",
        metavar="FORMAT",
        help="input format; inferred from the input extension if omitted "
        f"(available: {', '.join(available_readers())})",
    )
    parser.add_argument(
        "-t",
        "--to",
        dest="to_target",
        metavar="TARGET",
        help="output target; defaults to 'c', or inferred from the output "
        f"extension (available: {', '.join(available_writers())})",
    )
    parser.add_argument(
        "--no-provenance",
        action="store_true",
        help="omit the provenance banner and audit constants (source hash, "
        "command) from the output",
    )
    parser.add_argument(
        "--uncrustify",
        action="store_true",
        help="format generated C/C++ output with uncrustify",
    )
    parser.add_argument(
        "--uncrustify-config",
        metavar="PATH",
        help="uncrustify configuration file (implies --uncrustify)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"regforge {__version__}",
    )
    return parser


def _select_writer(args: argparse.Namespace) -> Writer:
    """Choose the output writer from the parsed arguments."""
    if args.to_target:
        return get_writer(args.to_target)
    if args.output:
        try:
            return writer_for_path(args.output)
        except ValueError:
            pass
    return get_writer("c")


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    raw_args = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw_args)

    try:
        reader = get_reader(args.from_format) if args.from_format else reader_for_path(args.input)
        writer = _select_writer(args)
    except ValueError as error:
        print(f"regforge: error: {error}", file=sys.stderr)
        return ExitCode.USAGE_ERROR

    device = reader.read(args.input)

    provenance = None
    if not args.no_provenance:
        command = "regforge " + " ".join(raw_args)
        provenance = build_provenance(args.input, tool_version=__version__, command=command)

    try:
        output = writer.render(device, provenance)
    except EmitError as error:
        print(f"regforge: error: {error}", file=sys.stderr)
        return ExitCode.EMIT_ERROR

    if args.uncrustify or args.uncrustify_config:
        try:
            output = uncrustify(
                output,
                language=writer.language,
                config=args.uncrustify_config,
            )
        except (FormatterNotAvailable, ValueError) as error:
            print(f"regforge: error: {error}", file=sys.stderr)
            return ExitCode.FORMATTER_ERROR
        except subprocess.CalledProcessError as error:
            print(f"regforge: error: uncrustify failed: {error.stderr}", file=sys.stderr)
            return ExitCode.FORMATTER_ERROR

    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(output)
    else:
        sys.stdout.write(output)
    return ExitCode.OK
