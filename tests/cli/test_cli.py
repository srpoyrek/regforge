"""Command-line interface behavior."""

import logging

from regforge.cli import ExitCode, _Formatter, main
from regforge.provenance import sha256_file


def _record(level: int, message: str, color: str | None = None) -> logging.LogRecord:
    record = logging.LogRecord("regforge", level, "", 0, message, (), None)
    record.color = color
    return record


def test_formatter_colors_by_level():
    fmt = _Formatter(use_color=True)
    assert "\033[33m" in fmt.format(_record(logging.WARNING, "oops"))  # warn -> yellow
    assert "\033[31m" in fmt.format(_record(logging.ERROR, "bad"))  # error -> red
    assert "\033[36m" in fmt.format(_record(logging.INFO, "step"))  # info -> cyan
    assert fmt.format(_record(logging.WARNING, "x")).endswith("\033[0m")  # reset


def test_formatter_color_override_and_disabled():
    fmt = _Formatter(use_color=True)
    assert "\033[32m" in fmt.format(_record(logging.INFO, "done", color="green"))  # override
    assert "\033[34m" in fmt.format(_record(logging.INFO, "checks", color="blue"))
    plain = _Formatter(use_color=False)
    assert "\033[" not in plain.format(_record(logging.WARNING, "oops"))  # no codes off-tty


def test_writes_header_to_file(tmp_path, minimal_svd_path):
    output = tmp_path / "demo.h"
    assert main([str(minimal_svd_path), "-o", str(output)]) == ExitCode.OK
    text = output.read_text(encoding="utf-8")
    assert "#ifndef REGFORGE_DEMOMCU_H" in text
    # Provenance is on by default: the real source hash appears.
    assert f'DEMOMCU_SVD_SHA256 "{sha256_file(minimal_svd_path)}"' in text


def test_writes_header_to_stdout(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path)]) == ExitCode.OK
    assert "#ifndef REGFORGE_DEMOMCU_H" in capsys.readouterr().out


def test_no_provenance_flag_omits_audit_trail(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path), "--no-provenance"]) == ExitCode.OK
    output = capsys.readouterr().out
    assert "SVD_SHA256" not in output
    assert "Command:" not in output


def test_creates_missing_output_directory(tmp_path, minimal_svd_path):
    output = tmp_path / "nested" / "dir" / "demo.h"
    assert main([str(minimal_svd_path), "-o", str(output)]) == ExitCode.OK
    assert output.exists()


def test_unknown_input_format_reports_error(capsys, minimal_svd_path):
    # exit code, message on stderr, and NOTHING on stdout (no partial output).
    assert main([str(minimal_svd_path), "--from", "does-not-exist"]) == ExitCode.USAGE_ERROR
    captured = capsys.readouterr()
    assert "unknown input format" in captured.err
    assert captured.out == ""


def test_word_addressable_device_is_refused(tmp_path, capsys):
    svd = tmp_path / "word.svd"
    svd.write_text(
        "<device><name>C2000</name><addressUnitBits>16</addressUnitBits></device>",
        encoding="utf-8",
    )
    assert main([str(svd)]) == ExitCode.EMIT_ERROR
    captured = capsys.readouterr()
    assert "addressUnitBits=16" in captured.err
    assert captured.out == ""  # refused before any header was written


def test_uncrustify_missing_reports_error(monkeypatch, capsys, minimal_svd_path):
    from regforge import postprocess

    monkeypatch.setattr(postprocess.shutil, "which", lambda name: None)
    assert main([str(minimal_svd_path), "--uncrustify"]) == ExitCode.FORMATTER_ERROR
    captured = capsys.readouterr()
    assert "uncrustify" in captured.err
    assert captured.out == ""


def test_verbose_logs_stages_and_timing(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path), "--no-provenance", "-v"]) == ExitCode.OK
    captured = capsys.readouterr()
    for stage in ("parsed", "resolved defaults", "rendered", "done"):
        assert stage in captured.err
    assert "ms" in captured.err  # timing is shown
    assert captured.out.startswith("/*")  # header still on stdout, logs on stderr


def _clean_svd(tmp_path):
    # A well-formed device that produces no resolve warnings and no check findings.
    svd = tmp_path / "clean.svd"
    svd.write_text(
        "<device><name>C</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress><registers><register><name>R</name>"
        "<addressOffset>0x0</addressOffset><size>32</size><access>read-write</access>"
        "</register></registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    return svd


def test_quiet_by_default(tmp_path, capsys):
    # A clean device: no INFO progress and no warnings -> nothing on stderr.
    assert main([str(_clean_svd(tmp_path)), "--no-provenance"]) == ExitCode.OK
    captured = capsys.readouterr()
    assert captured.err == ""  # no INFO progress, no timing, no warnings


def test_verbosity_flag_does_not_change_output(tmp_path, minimal_svd_path):
    # -v is cosmetic (logging only); it must never leak into the provenance
    # banner or otherwise change the generated file.
    out = tmp_path / "h.h"
    assert main([str(minimal_svd_path), "-o", str(out)]) == ExitCode.OK
    without_v = out.read_text(encoding="utf-8")
    assert main([str(minimal_svd_path), "-o", str(out), "-v"]) == ExitCode.OK
    with_v = out.read_text(encoding="utf-8")
    assert with_v == without_v


def test_check_findings_surface(capsys, tmp_path, lint_demo_svd_path):
    # The consistency checks run during emit; their findings show as warnings
    # even without -v (they are logged at WARNING level).
    out = tmp_path / "out.h"
    main([str(lint_demo_svd_path), "-o", str(out), "--no-provenance"])
    err = capsys.readouterr().err
    assert "ADCB" in err  # derived peripheral omitted its own vector
    assert "differing layouts" in err  # group divergence (FPU, TMR)
    assert "parsed" not in err  # but INFO progress stays suppressed without -v


def test_clean_fixture_reports_nothing(capsys, minimal_svd_path):
    # The clean chip is the contract: every check silent, both severities zero.
    assert main([str(minimal_svd_path), "--no-provenance"]) == ExitCode.OK
    err = capsys.readouterr().err
    assert "warn:" not in err and "error:" not in err


def test_check_summary_shown_with_verbose(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path), "--no-provenance", "-v"]) == ExitCode.OK
    err = capsys.readouterr().err
    # Nothing to report on the clean fixture, and the summary says so.
    assert "consistency check(s): 0 warning(s), 0 error(s)" in err
    assert err.count("warn:") == 0


def test_warnings_show_without_verbose(tmp_path, capsys):
    # A device with no access anywhere warns -- and warnings ignore -v entirely.
    svd = tmp_path / "noaccess.svd"
    svd.write_text(
        "<device><name>C</name><peripherals><peripheral><name>P</name>"
        "<baseAddress>0x0</baseAddress><registers><register><name>R</name>"
        "<addressOffset>0x0</addressOffset><size>32</size></register>"
        "</registers></peripheral></peripherals></device>",
        encoding="utf-8",
    )
    assert main([str(svd), "--no-provenance"]) == ExitCode.OK  # note: no -v
    captured = capsys.readouterr()
    assert "warn:" in captured.err
    assert "access unspecified" in captured.err
    assert "parsed" not in captured.err  # but INFO progress still suppressed


def test_verbose_logs_every_pass_in_pipeline_order(capsys, minimal_svd_path):
    # dim expansion -> derivedFrom -> defaults -> checks -> render, each on its own line.
    assert main([str(minimal_svd_path), "-v"]) == ExitCode.OK
    err = capsys.readouterr().err
    order = [err.index(marker) for marker in ("expanded dim", "derivedFrom", "defaults", "check")]
    assert order == sorted(order)
