# Compatibility

## Stable API Surface

The plugin intentionally consumes only:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Verify that the configured origin is BailingHub-like |
| `POST` | `/run` | Submit a governed job |
| `GET` | `/jobs/{job_id}` | Read client-owned job state and result |

No admin, executor, approval-decision, tool-proxy, configuration, or direct business API
endpoint is used.

## Current Adapter Contract

| Adapter version | BailingHub requirement | Dify runtime | Python |
| --- | --- | --- | --- |
| `0.1.x` | Client API with `/run` and `/jobs/{job_id}` | Tool Plugin support | `3.12` |

This matrix records protocol compatibility, not release coupling. A BailingHub release is
compatible when the documented request and response semantics remain valid, regardless of
whether its version number resembles the plugin version.

## Job Semantics

- Non-terminal: `queued`, `running`, `dispatched`.
- Successful terminal: `done`.
- Failed terminal: `error`, `rejected`.
- `request_id` is a client-scoped idempotency key.
- Job lookup must enforce client ownership.

Unknown status values are rejected rather than guessed. A future BailingHub status must be
reviewed and covered by adapter tests before this plugin claims compatibility with it.

## Change Policy

- Additive BailingHub response fields are ignored unless explicitly exposed by this plugin.
- A new required request field, changed authentication method, or changed terminal-state
  meaning requires a compatibility review and usually a plugin release.
- Dify SDK or manifest changes are handled in this adapter without changing BailingHub or
  ACC versions.
