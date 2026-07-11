# Repository guidance

Keep this project local-first and provider-neutral.

- Do not add real API keys, user papers, or copyrighted articles to the repository.
- Preserve the public annotation schema when changing model adapters or renderers.
- Every annotation must keep a valid source anchor. Do not make the renderer silently drop unmatched notes.
- Test all changes with `PYTHONPATH=src python -m unittest discover -s tests -v`.
- Keep the default `mock` provider fully offline so contributors can validate the pipeline without credentials.
- Treat OCR, web hosting, authentication, and cloud storage as separate future features, not hidden defaults.

