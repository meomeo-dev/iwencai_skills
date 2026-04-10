# Contributing

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
pre-commit install
```

## Quality Gates

Run the full local gate before opening a pull request:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m pyright
pre-commit run --all-files
```

## Contribution Rules

- Keep the public CLI family-first: `query2data`, `search`, `trade`.
- Update specs and contract tests together when changing behavior.
- Prefer concise, explicit help text and examples.
- Do not commit secrets, `.env`, local account state, or generated build artifacts.
