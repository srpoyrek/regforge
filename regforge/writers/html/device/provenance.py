"""The HTML block saying where the document came from."""

from __future__ import annotations

from markupsafe import Markup

from regforge.provenance import Provenance
from regforge.writers.html.context import ElementHtml


class ProvenanceHtml(ElementHtml):
    """Renders the audit trail as the page footer."""

    def render(self, provenance: Provenance | None) -> Markup:
        """The footer, or nothing when the run recorded no provenance."""
        if provenance is None:
            return Markup("")
        return self._fill(
            "provenance.html.j2",
            source_name=provenance.source_name,
            sha=provenance.short_sha(),
            full_sha=provenance.source_sha256,
            tool_version=provenance.tool_version,
            command=provenance.command,
        )
