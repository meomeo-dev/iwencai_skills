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

## Codex-Assisted Contributions

Codex-assisted changes are allowed.

- Treat Codex as an implementation assistant, not as a substitute for human review.
- Keep `iwencai_cli.py`, `specs/*.SPEC.yaml`, and `tests/` in sync when behavior changes.
- Do not accept generated code or text blindly; verify help text, contracts, and runtime behavior yourself.
- Run the full local quality gate before pushing any Codex-assisted change.
