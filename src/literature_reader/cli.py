"""Command-line interface for Literature Reading Companion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import VALID_FORMATS, VALID_PROVIDERS, VALID_TRANSLATIONS, RunConfig
from .pipeline import annotate_document, write_outputs
from .providers.base import ProviderConfigurationError
from .quality import AnnotationQualityError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-reader",
        description="Create a source-linked annotated reading copy from a PDF, DOCX, or TXT paper.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    annotate = subparsers.add_parser("annotate", help="Create an annotated reading copy.")
    annotate.add_argument("input", type=Path, help="Text-based PDF, DOCX, or TXT input.")
    annotate.add_argument("--provider", choices=sorted(VALID_PROVIDERS), default="mock")
    annotate.add_argument("--model", help="Optional provider-specific model name.")
    annotate.add_argument("--translation", choices=sorted(VALID_TRANSLATIONS), default="none")
    annotate.add_argument("--depth", choices=("overview", "deep"), default="deep")
    annotate.add_argument("--format", choices=sorted(VALID_FORMATS), default="html")
    annotate.add_argument("--output-dir", type=Path, default=Path("output"))
    annotate.add_argument("--batch-size", type=int, default=4)
    annotate.add_argument(
        "--focus",
        default="research_question,methods,figures_tables,results",
        help="Comma-separated reading priorities.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "annotate":
        parser.error(f"Unknown command: {args.command}")

    focus = tuple(item.strip() for item in args.focus.split(",") if item.strip())
    config = RunConfig(
        provider=args.provider,
        model=args.model,
        translation=args.translation,
        annotation_depth=args.depth,
        focus=focus,
        batch_size=args.batch_size,
    )
    try:
        reading_copy = annotate_document(args.input, config)
        paths = write_outputs(reading_copy, args.output_dir, args.format)
    except (AnnotationQualityError, FileNotFoundError, ProviderConfigurationError, ValueError) as error:
        parser.exit(status=2, message=f"error: {error}\n")

    print(f"Reading copy created for: {reading_copy.source.title}")
    if paths.html:
        print(f"HTML: {paths.html}")
    if paths.docx:
        print(f"DOCX: {paths.docx}")
    if reading_copy.warnings:
        print("Warnings:")
        for warning in reading_copy.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main(sys.argv[1:])
