"""Command-line interface behavior."""

from regforge.cli import main
from regforge.provenance import sha256_file


def test_writes_header_to_file(tmp_path, minimal_svd_path):
    output = tmp_path / "demo.h"
    assert main([str(minimal_svd_path), "-o", str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    assert "#ifndef REGFORGE_DEMOMCU_H" in text
    # Provenance is on by default: the real source hash appears.
    assert f'DEMOMCU_SVD_SHA256 "{sha256_file(minimal_svd_path)}"' in text


def test_writes_header_to_stdout(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path)]) == 0
    assert "#ifndef REGFORGE_DEMOMCU_H" in capsys.readouterr().out


def test_no_provenance_flag_omits_audit_trail(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path), "--no-provenance"]) == 0
    output = capsys.readouterr().out
    assert "SVD_SHA256" not in output
    assert "Command:" not in output


def test_creates_missing_output_directory(tmp_path, minimal_svd_path):
    output = tmp_path / "nested" / "dir" / "demo.h"
    assert main([str(minimal_svd_path), "-o", str(output)]) == 0
    assert output.exists()


def test_unknown_input_format_reports_error(capsys, minimal_svd_path):
    assert main([str(minimal_svd_path), "--from", "does-not-exist"]) == 2
    assert "unknown input format" in capsys.readouterr().err
