"""Command-line interface.

Drives the conversion pipeline: a reader parses the input into the
intermediate representation and a writer renders it to the chosen target,
with optional post-processing of the generated source.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from enum import IntEnum
from pathlib import Path

from . import __version__
from .check import ALL_CHECKS, Severity, run_checks
from .postprocess import FormatterNotAvailable, uncrustify
from .provenance import build_provenance
from .readers import available_readers, get_reader, reader_for_path
from .resolve import expand_dim, resolve_alternates, resolve_defaults, resolve_derived
from .writers import EmitError, Writer, available_writers, get_writer, writer_for_path

logger = logging.getLogger("regforge")

#: Short labels shown in place of logging's uppercase level names.
_LEVEL_LABEL = {"DEBUG": "debug", "INFO": "info", "WARNING": "warn", "ERROR": "error"}

#: ANSI color codes, used only when stderr is a terminal.
_RESET = "\033[0m"
_COLOR = {
    "red": "\033[31m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "dim": "\033[2m",
}
#: Default line color per level; a record may override via a ``color`` extra.
_LEVEL_COLOR = {"error": "red", "warn": "yellow", "info": "cyan", "debug": "dim"}


def _enable_ansi() -> None:
    """Best-effort enable of ANSI escape processing on a Windows console."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-12)  # STD_ERROR_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # VT processing
    except Exception:  # pragma: no cover - colouring is best-effort only
        pass


class _Formatter(logging.Formatter):
    """Format a line as ``[<elapsed>] <level>: <message>`` -- time first.

    The elapsed time (ms since the run started) rides on each record as the
    ``elapsed_ms`` extra; a record without it omits the stamp. When ``use_color``
    is set, each line is colored by level (warn=yellow, error=red, info=cyan),
    unless the record carries a ``color`` extra that overrides it.
    """

    def __init__(self, use_color: bool) -> None:
        super().__init__()
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        label = _LEVEL_LABEL.get(record.levelname, record.levelname.lower())
        elapsed = getattr(record, "elapsed_ms", None)
        stamp = f"[{elapsed:>7.1f} ms] " if elapsed is not None else ""
        line = f"{stamp}{label}: {record.getMessage()}"
        if not self._use_color:
            return line
        code = _COLOR.get(getattr(record, "color", None) or _LEVEL_COLOR.get(label, ""))
        return f"{code}{line}{_RESET}" if code else line


class ExitCode(IntEnum):
    """Process exit codes returned by :func:`main`."""

    OK = 0
    USAGE_ERROR = 2  # unknown input format or output target
    FORMATTER_ERROR = 3  # uncrustify unavailable or failed
    EMIT_ERROR = 4  # the writer refused to emit the device


def _configure_logging(verbosity: int) -> None:
    """Configure the regforge logger on stderr.

    Warnings and errors always show; ``-v`` adds INFO progress + timing and
    ``-vv`` adds DEBUG detail.
    """
    logger.handlers.clear()
    logger.propagate = False
    use_color = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
    if use_color:
        _enable_ansi()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_Formatter(use_color))
    logger.addHandler(handler)
    if verbosity >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbosity == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


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
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="log pipeline stages and timing to stderr (repeat -vv for detail)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"regforge {__version__}",
    )
    return parser


def _provenance_command(args: argparse.Namespace) -> str:
    """Reconstruct a normalized command for the provenance banner.

    Built from the parsed *output-affecting* options, not raw argv, so cosmetic
    flags (``-v``/``--verbose``) and argument order never change the recorded
    command -- and therefore never change the generated file. Running with or
    without ``-v`` produces byte-identical output.
    """
    parts = ["regforge", args.input]
    if args.from_format:
        parts += ["-f", args.from_format]
    if args.to_target:
        parts += ["-t", args.to_target]
    if args.output:
        parts += ["-o", args.output]
    if args.uncrustify_config:
        parts += ["--uncrustify-config", args.uncrustify_config]
    elif args.uncrustify:
        parts.append("--uncrustify")
    return " ".join(parts)


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
    _configure_logging(args.verbose)
    started = time.perf_counter()

    def log(level: int, msg: str, *msg_args: object, color: str | None = None) -> None:
        elapsed = (time.perf_counter() - started) * 1000
        logger.log(level, msg, *msg_args, extra={"elapsed_ms": elapsed, "color": color})

    try:
        reader = get_reader(args.from_format) if args.from_format else reader_for_path(args.input)
        writer = _select_writer(args)
    except ValueError as error:
        log(logging.ERROR, "%s", error)
        return ExitCode.USAGE_ERROR

    device = reader.read(args.input)
    log(
        logging.INFO,
        "parsed %s via '%s': %d peripheral(s), %d warning(s)",
        args.input,
        reader.format_name,
        len(device.peripherals),
        len(reader.warnings),
    )
    for warning in reader.warnings:
        log(logging.WARNING, "%s", warning)
    log(
        logging.DEBUG,
        "%d register(s), %d field(s)",
        sum(len(p.registers) for p in device.peripherals),
        sum(len(r.fields) for p in device.peripherals for r in p.registers),
    )

    # The passes run in a fixed order: dim expansion first, so derivedFrom
    # can name a copy; derivedFrom before defaults, so copied registers
    # resolve under the derived peripheral's own chain.
    dim_findings = expand_dim(device)
    dim_errors = sum(1 for finding in dim_findings if finding.severity is Severity.ERROR)
    log(
        logging.INFO,
        "expanded dim templates: %d peripheral(s), %d warning(s), %d error(s)",
        len(device.peripherals),
        len(dim_findings) - dim_errors,
        dim_errors,
    )
    for finding in dim_findings:
        level = logging.ERROR if finding.severity is Severity.ERROR else logging.WARNING
        log(level, "%s", finding.message)

    derived_count = sum(1 for p in device.peripherals if p.derived_from is not None)
    derived_warnings = resolve_derived(device)
    log(
        logging.INFO,
        "resolved derivedFrom: %d peripheral(s), %d warning(s)",
        derived_count,
        len(derived_warnings),
    )
    for warning in derived_warnings:
        log(logging.WARNING, "%s", warning)

    alternate_findings = resolve_alternates(device)
    log(logging.INFO, "resolved alternateRegister: %d finding(s)", len(alternate_findings))
    for finding in alternate_findings:
        level = logging.ERROR if finding.severity is Severity.ERROR else logging.WARNING
        log(level, "%s", finding.message)

    warnings = resolve_defaults(device)
    log(logging.INFO, "resolved defaults: %d warning(s)", len(warnings))
    for warning in warnings:
        log(logging.WARNING, "%s", warning)

    # Consistency checks are advisory here (findings are logged, not fatal); the
    # dedicated `regforge check` subcommand will add non-zero exit on ERROR.
    findings = run_checks(device)
    warning_count = sum(1 for finding in findings if finding.severity is Severity.WARNING)
    error_count = sum(1 for finding in findings if finding.severity is Severity.ERROR)
    log(
        logging.INFO,
        "ran %d consistency check(s): %d warning(s), %d error(s)",
        len(ALL_CHECKS),
        warning_count,
        error_count,
        color="red" if error_count else "blue",
    )
    for finding in findings:
        level = logging.ERROR if finding.severity is Severity.ERROR else logging.WARNING
        log(level, "%s", finding.message)

    provenance = None
    if not args.no_provenance:
        provenance = build_provenance(
            args.input, tool_version=__version__, command=_provenance_command(args)
        )

    try:
        output = writer.render(device, provenance)
    except EmitError as error:
        log(logging.ERROR, "%s", error)
        return ExitCode.EMIT_ERROR
    log(logging.INFO, "rendered target '%s'", writer.target_name)

    if args.uncrustify or args.uncrustify_config:
        try:
            output = uncrustify(output, language=writer.language, config=args.uncrustify_config)
        except (FormatterNotAvailable, ValueError) as error:
            log(logging.ERROR, "%s", error)
            return ExitCode.FORMATTER_ERROR
        except subprocess.CalledProcessError as error:
            log(logging.ERROR, "uncrustify failed: %s", error.stderr)
            return ExitCode.FORMATTER_ERROR
        log(logging.INFO, "formatted with uncrustify")

    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(output)
        log(logging.INFO, "wrote %s (%d bytes)", args.output, len(output))
    else:
        sys.stdout.write(output)

    log(logging.INFO, "done", color="green")
    return ExitCode.OK
