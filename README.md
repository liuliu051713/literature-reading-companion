# Literature Reading Companion

**A local-first, model-agnostic tool for turning an academic paper into an annotated reading copy.**

[中文说明](README.zh-CN.md)

Literature Reading Companion does not treat a paper as a translation task. It first builds a paper-level reading map and then adds source-linked annotations that explain what a passage is doing, how it connects to the surrounding argument, and what the reader should take away.

The project is designed to work with more than one model provider. The first release includes adapters for OpenAI and Gemini, plus an offline `mock` provider for testing the workflow without sending a document to any model.

It also includes a private **ChatGPT App / MCP developer-mode route**. In that route, ChatGPT performs the reading work in its own conversation and the local MCP service only receives the authorized file, validates paragraph anchors, and renders HTML/DOCX. It does not use this repository's OpenAI API provider or require `OPENAI_API_KEY`.

## What the first release does

- Reads text-based PDF, DOCX, or TXT files locally.
- Preserves stable paragraph anchors such as `P001` and source page numbers when available.
- Supports two reading modes: original text with Chinese annotations, or original text with full Chinese translation and annotations.
- Makes the substantive, beginner-friendly passage explanation the leading part of every annotation rather than a page-role summary.
- Renders model-marked formulae as browser-native MathML in HTML and editable Office Math in DOCX.
- Produces an HTML reading copy with a source column and a corresponding annotation column.
- Can also produce a DOCX reading copy.
- Checks that every rendered annotation has a valid source anchor and that no expected anchor is missing.
- Can be connected to ChatGPT developer mode so a user can upload a paper in ChatGPT and receive downloadable HTML/DOCX output without using this project's OpenAI API integration.

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

## Use from ChatGPT on the web (no model API key)

For a private developer-mode test, install the MCP extra and run the local server:

```bash
pip install -e ".[chatgpt-app]"
python -m literature_reader.chatgpt_mcp
```

ChatGPT needs a public HTTPS MCP endpoint, so a temporary HTTPS tunnel or a hosted deployment is still required. The detailed Chinese guide explains the exact Windows steps, privacy boundaries, the developer-mode connection, and the upload prompt: [docs/chatgpt-app.md](docs/chatgpt-app.md).

## Design principles

- **Context before commentary.** Each note must explain the passage itself for a reader new to the field, then relate it to the paper's overall argument and its immediate neighbours.
- **Traceability.** In v0.1, notes are rendered only against a stable paragraph anchor; the tool does not output detached commentary. Figure, table, and formula anchors are planned extensions.
- **Clear separation of claims.** The model must distinguish an author's claim from a reading aid or a caveat.
- **Local-first privacy.** The repository does not operate a document-storage service. A selected provider receives text only when the user explicitly runs that provider.
- **Provider independence.** The paper model, annotation schema, quality checks, and renderers are not tied to a single AI vendor.
- **No hidden model call in the ChatGPT App route.** The MCP server does not contain an OpenAI API key; ChatGPT writes the reading map and notes through its active conversation.

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
