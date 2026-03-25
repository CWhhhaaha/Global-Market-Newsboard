# Contributing

Thanks for contributing.

## Scope

Good pull requests for this project usually improve one of these areas:

- source quality
- deduplication
- retail-facing signal quality
- deployment
- docs
- UI scan speed

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.market_stream.app:app --reload
```

## Guidelines

- Prefer public, stable, low-friction sources.
- Do not add sources that require redistributing full copyrighted articles.
- Keep changes small and easy to review.
- Preserve the trader-first UI and fast scan flow.
- If you add a source, update source metadata and filtering rules together.
- If you change deployment behavior, update the README in the same PR.

## Before Opening a PR

- Run `python3 -m compileall src`
- Verify `/health`
- Verify the homepage still loads and updates
- Note any new source limitations or legal constraints in the PR description
