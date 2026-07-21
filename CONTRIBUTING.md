# Contributing

Contributions are welcome when they preserve the adapter boundary described in
`docs/PROJECT_BOUNDARIES.md`.

Before proposing a change:

1. Decide whether it belongs to the Dify adapter, BailingHub server, ACC specification, or
   the business system.
2. Add or update tests for any observable behavior.
3. Do not include tokens, private URLs, customer data, or production request bodies.
4. Run `uv run ruff check .`, `uv run pytest`, and `uv run python scripts/check_project.py`.

Features that require administrator, executor, tool-provider, or business-system credentials
will not be accepted into this adapter.
