# Installation and first run

## 1. Create a local environment

Python 3.10 or newer is required.

macOS or Linux:

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

Windows PowerShell:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .

## 2. Verify the local pipeline

The mock provider does not contact an AI provider. Use it to verify extraction,
stable anchors, and output layout:

    paper-reader annotate examples/sample-paper.txt --provider mock --format all --output-dir output

Open the HTML file in a browser. The source and its matching note should share
the same anchor, for example P002.

## 3. Configure one model provider

Install only the adapter you intend to use.

    pip install -e ".[openai]"
    # or
    pip install -e ".[gemini]"

Set a key only in your local shell. Do not place a real key in .env.example,
source code, test fixtures, GitHub issues, or screenshots.

    export OPENAI_API_KEY="your-key"
    paper-reader annotate paper.pdf --provider openai --translation full --format html

    export GEMINI_API_KEY="your-key"
    paper-reader annotate paper.pdf --provider gemini --translation none --format docx

The provider-specific model can be changed without editing source code:

    paper-reader annotate paper.pdf --provider openai --model your-model-name

## Input limits in v0.1

- PDF must contain extractable text. Run OCR separately for a scanned paper.
- DOCX paragraphs are preserved directly.
- TXT support exists for tests and plain-text preprints.
- Complex multi-column PDF reconstruction is not yet guaranteed. Inspect the
  generated reading copy before relying on it.

## Privacy and copyright

The command-line tool does not upload files to a project-owned server. When an
OpenAI or Gemini provider is selected, the extracted text is sent to the
provider selected by the user. Use only documents you are permitted to process,
and do not commit papers, keys, or generated reading copies unless you have the
right to share them.
