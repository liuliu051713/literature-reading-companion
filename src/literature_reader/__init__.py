"""Local-first academic literature reading companion."""

from .config import RunConfig
from .pipeline import annotate_document

__all__ = ["RunConfig", "annotate_document"]
__version__ = "0.1.0"
