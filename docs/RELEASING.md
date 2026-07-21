# Releasing

The plugin has an independent release train. Releasing BailingHub or ACC does not release
this adapter, and releasing this adapter does not change either upstream project.

## Release Checklist

1. Update `manifest.yaml`, `pyproject.toml`, and `CHANGELOG.md` with the same plugin version.
2. Review `docs/COMPATIBILITY.md` against the current BailingHub Client API.
3. Run:

   ```bash
   uv sync --dev
   uv run ruff check .
   uv run pytest
   uv run python scripts/check_project.py
   ```

4. Package with the pinned Dify Plugin CLI version used by CI.
5. Run `uv run python scripts/check_package.py dist/bailinghub.difypkg`.
6. Install the generated `.difypkg` into a test Dify workspace.
7. Validate credentials with a dedicated test client.
8. Run one harmless route through `queued -> done` and preserve a sanitized result.
9. Publish the plugin package and release notes in this repository only.
10. Update any optional link in BailingHub documentation after the adapter release exists.

## Distribution Stages

1. Local `.difypkg` for maintainer verification.
2. Independent GitHub repository for versioned community use.
3. Dify Marketplace submission after maintainer E2E, privacy review, package-content audit,
   and Marketplace pre-flight checks pass.

Independent installation remains the next adoption milestone after distribution and must
not be inferred from maintainer or Marketplace validation.

Marketplace publication is a distribution decision, not a claim of Dify certification or
partnership.
