# Literature Reading Companion

**A local-first, model-agnostic tool for turning an academic paper into an annotated reading copy.**

[中文说明](README.zh-CN.md)

Literature Reading Companion does not treat a paper as a translation task. It first builds a paper-level reading map and then adds source-linked annotations that explain what a passage is doing, how it connects to the surrounding argument, and what the reader should take away.

The project is designed to work with more than one model provider. The first release includes adapters for OpenAI and Gemini, plus an offline `mock` provider for testing the workflow without sending a document to any model.

## What the first release does

- Reads text-based PDF, DOCX, or TXT files locally.
- Preserves stable paragraph anchors such as `P001` and source page numbers when available.
- Supports two reading modes: original text with Chinese annotations, or original text with full Chinese translation and annotations.
- Produces an HTML reading copy with a source column and a corresponding annotation column.
- Can also produce a DOCX reading copy.
- Checks that every rendered annotation has a valid source anchor and that no expected anchor is missing.

> Scanned PDFs, OCR correction, complex multi-column reconstruction, batch processing, and collaborative reading are intentionally outside v0.1.

## Quick start

```bash
git clone https://github.com/liuliu051713/literature-reading-companion.git
cd literature-reading-companion
python -m venv .venv
```

Activate the environment, then install the package:

```bash
pip install -e .
```

Run the complete local workflow without an API key:

```bash
paper-reader annotate examples/sample-paper.txt \
  --provider mock \
  --format all \
  --output-dir output
```

This produces `output/sample-paper.reading.html` and `output/sample-paper.reading.docx`.

## Use OpenAI or Gemini

Install exactly the provider you need:

```bash
pip install -e ".[openai]"
# or
pip install -e ".[gemini]"
```

Set one local environment variable; never add API keys to a file that will be committed:

```bash
export OPENAI_API_KEY="..."
# or
export GEMINI_API_KEY="..."
```

Examples:

```bash
paper-reader annotate paper.pdf --provider openai --translation full --format html
paper-reader annotate paper.docx --provider gemini --translation none --format docx
```

See [docs/installation.md](docs/installation.md) for Windows instructions and [docs/annotation-standard.md](docs/annotation-standard.md) for the annotation contract.

## Design principles

- **Context before commentary.** Each note must relate a passage to the paper's overall argument and its immediate neighbours.
- **Traceability.** In v0.1, notes are rendered only against a stable paragraph anchor; the tool does not output detached commentary. Figure, table, and formula anchors are planned extensions.
- **Clear separation of claims.** The model must distinguish an author's claim from a reading aid or a caveat.
- **Local-first privacy.** The repository does not operate a document-storage service. A selected provider receives text only when the user explicitly runs that provider.
- **Provider independence.** The paper model, annotation schema, quality checks, and renderers are not tied to a single AI vendor.

## Repository layout

```text
src/literature_reader/     Python package and command-line interface
schemas/                   Public JSON schemas for structured model output
docs/                      Installation, annotation, and privacy guidance
examples/                  Small original example only; no copyrighted papers
tests/                     Offline regression tests
```

## License

Released under the [MIT License](LICENSE).
