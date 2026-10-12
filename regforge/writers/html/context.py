"""What every HTML renderer shares: the template environment and how a block is filled."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "html"


@dataclass
class RenderContext:
    """The template environment one render uses.

    Attributes:
        env: The Jinja environment; it escapes every value, so only a child block
            (already ``Markup``) is inserted as markup.
    """

    env: Environment

    @classmethod
    def default(cls) -> RenderContext:
        """A context that reads the templates shipped with regforge."""
        return cls(
            Environment(
                loader=FileSystemLoader(str(_TEMPLATE_DIR)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
                undefined=StrictUndefined,
                autoescape=True,
            )
        )


class ElementHtml:
    """Base of the renderers: one class per element, each producing its own HTML block.

    A renderer fills its own template and asks the renderers of its children for
    theirs, so the document is built by recursive calls from the device down.
    """

    def __init__(self, context: RenderContext) -> None:
        self.context = context

    def _fill(self, template: str, **values: object) -> Markup:
        return Markup(self.context.env.get_template(template).render(**values))


class LeafHtml:
    """Base of the renderers of the small elements that read as a phrase, not as a block.

    An access reads ``RW``, a data type ``int32_t``, a write behaviour "writing 1 clears the
    bit": there is no template to fill, so a leaf needs no environment and is built on its
    own. A block renderer (:class:`ElementHtml`) calls the leaves of the element it renders.
    """
