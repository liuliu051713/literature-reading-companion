"""Output renderers for aligned reading copies."""

from .docx import render_docx
from .html import render_html

__all__ = ["render_docx", "render_html"]
