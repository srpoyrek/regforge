"""Generation provenance: an audit trail for generated output.

Where most register-header generators discard everything about *how* a header
was produced, regforge records it. A :class:`Provenance` value captures the
source description, its content hash, any patches applied, the tool version,
and the exact command that ran. Writers embed this into the generated output
(a header banner plus compile-time constants) so that, months later, any file
can be traced back to the precise inputs and tool run that created it.

The hash is content-based rather than timestamp-based on purpose: the same
inputs always yield byte-identical output, which is what reproducible and
auditable builds require.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

#: Default number of leading hash characters shown in short form.
DEFAULT_SHORT_SHA_LENGTH = 16


@dataclass
class PatchRef:
    """A reference to a patch applied to the source, by name and content hash."""

    name: str
    sha256: str


@dataclass
class Provenance:
    """Record of the inputs and command that produced a generated artifact.

    Attributes:
        source_path: Path to the source description that was read.
        source_sha256: SHA-256 hex digest of the source description's bytes.
        tool_version: Version of regforge that produced the output.
        command: The command line that was run, for reproduction.
        patches: Patches applied to the source, in application order.
    """

    source_path: str
    source_sha256: str
    tool_version: str
    command: str
    patches: list[PatchRef] = field(default_factory=list)

    @property
    def source_name(self) -> str:
        """The bare file name of the source description."""
        return Path(self.source_path).name

    def short_sha(self, length: int = DEFAULT_SHORT_SHA_LENGTH) -> str:
        """The leading ``length`` characters of the source hash, for banners."""
        return self.source_sha256[:length]


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of the file at ``path``."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_provenance(
    source_path: str | Path,
    tool_version: str,
    command: str,
    patches: list[PatchRef] | None = None,
) -> Provenance:
    """Assemble a :class:`Provenance` for a generation run.

    Hashes the source file at ``source_path`` and records it alongside the
    tool version and command.
    """
    return Provenance(
        source_path=str(source_path),
        source_sha256=sha256_file(source_path),
        tool_version=tool_version,
        command=command,
        patches=list(patches or []),
    )
