"""Core provenance data model (hashing and assembly)."""

import hashlib

from regforge.provenance import Provenance, build_provenance, sha256_file


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"hello regforge")
    assert sha256_file(path) == hashlib.sha256(b"hello regforge").hexdigest()


def test_source_name_and_short_sha():
    provenance = Provenance(
        source_path="some/dir/chip.svd",
        source_sha256="abcdef" + "0" * 58,
        tool_version="1.0",
        command="regforge chip.svd",
    )
    assert provenance.source_name == "chip.svd"
    assert provenance.short_sha(6) == "abcdef"


def test_build_provenance_hashes_source(tmp_path):
    path = tmp_path / "chip.svd"
    path.write_bytes(b"<device/>")
    provenance = build_provenance(path, tool_version="0.0.1", command="regforge chip.svd")
    assert provenance.source_sha256 == sha256_file(path)
    assert provenance.tool_version == "0.0.1"
    assert provenance.command == "regforge chip.svd"
    assert provenance.patches == []
