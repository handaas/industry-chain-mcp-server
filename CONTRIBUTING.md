# Contributing

Codex and other coding agents must read [AGENTS.md](AGENTS.md) before changing the tool contract, product registry, runtime configuration, or documentation.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Use placeholder credentials for unit tests. Real HandaaS credentials are only
required for manual integration tests and must never be committed.

## Checks

```bash
python -m unittest discover -s tests -v
python -m py_compile server/*.py
python -m build
```

## Tool contract

- Expose only wrappers around existing HandaaS products.
- Keep tool names stable and parameters compatible with the upstream product.
- Return structured, actionable errors without secrets or signatures.
- Add regression tests for parameter normalization and error handling.

## Pull requests

Keep changes focused. Include the HandaaS product name, product ID, parameter
contract, and test evidence when adding a tool.
