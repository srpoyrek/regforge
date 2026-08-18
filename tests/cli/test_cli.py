"""Command-line interface behavior."""

from regforge.cli import ExitCode, main
from regforge.provenance import sha256_file


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
