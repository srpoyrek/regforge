"""Tests for the command-line interface."""

from regforge.cli import main


def test_writes_header_to_file(tmp_path, minimal_svd_path, golden_header_path):
    output = tmp_path / "demo.h"
    exit_code = main([str(minimal_svd_path), "-o", str(output)])
    assert exit_code == 0
    assert output.read_text(encoding="utf-8") == golden_header_path.read_text(encoding="utf-8")


def test_writes_header_to_stdout(capsys, minimal_svd_path, golden_header_path):
    exit_code = main([str(minimal_svd_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == golden_header_path.read_text(encoding="utf-8")


def test_creates_missing_output_directory(tmp_path, minimal_svd_path):
    output = tmp_path / "nested" / "dir" / "demo.h"
    exit_code = main([str(minimal_svd_path), "-o", str(output)])
    assert exit_code == 0
    assert output.exists()


def test_unknown_input_format_reports_error(capsys, minimal_svd_path):
    exit_code = main([str(minimal_svd_path), "--from", "does-not-exist"])
    assert exit_code == 2
    assert "unknown input format" in capsys.readouterr().err
