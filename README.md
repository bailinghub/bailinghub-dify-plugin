# BailingHub Tool Plugin for Dify

Use a Dify Agent or Workflow to submit business actions through a self-hosted
[BailingHub](https://github.com/bailinghub/bailinghub) control plane.

The plugin intentionally exposes only three control-plane tools:

- `submit_governed_job`: submit an action to an administrator-configured route;
- `get_job`: read the current state and terminal result of a job;
- `wait_for_job`: poll a job for a bounded period without waiting indefinitely.

It does not import governed business APIs into Dify and does not give Dify admin,
executor, or business-system credentials.

```text
Dify Agent or Workflow
  -> BailingHub Dify Plugin
     -> POST /run
     -> GET /jobs/{job_id}
        -> BailingHub control plane
           -> governed executor
              -> business system
```

[Simplified Chinese](readme/README_zh_Hans.md)

## Source and Support

- Marketplace: [Install BailingHub from Dify Marketplace](https://marketplace.dify.ai/plugin/bailinghub/bailinghub)
- Source: [github.com/bailinghub/bailinghub-dify-plugin](https://github.com/bailinghub/bailinghub-dify-plugin)
- Bug reports and support: [GitHub Issues](https://github.com/bailinghub/bailinghub-dify-plugin/issues)
- Security reports: use this repository's private Security Advisory channel as described in
  [SECURITY.md](https://github.com/bailinghub/bailinghub-dify-plugin/blob/main/SECURITY.md).

## Project Boundary

This repository is an independent integration adapter. It is not:

- part of the ACC normative specification;
- embedded in the BailingHub server distribution;
- versioned or released together with ACC or BailingHub;
- an official Dify partnership or certification.

The dependency is one-way: this plugin consumes BailingHub's public Client API.
See [Project Boundaries](docs/PROJECT_BOUNDARIES.md) and
[Compatibility](docs/COMPATIBILITY.md).

## Requirements

- Dify with Tool Plugin support;
- a reachable self-hosted BailingHub instance;
- a dedicated BailingHub Client Token restricted to the routes Dify needs;
- HTTPS between Dify and BailingHub, except for loopback development.

## Configure

1. In BailingHub, create a dedicated client for this Dify application.
2. Allow only the required routes and set an appropriate rate limit.
3. [Install BailingHub from Dify Marketplace](https://marketplace.dify.ai/plugin/bailinghub/bailinghub). For offline or pinned-package installation, use a versioned package from this repository's Releases.
4. Configure:
   - `BailingHub Base URL`: the BailingHub HTTPS origin;
   - `Dedicated Client Token`: the raw client token, without a `Bearer` prefix.

Never use an admin token, executor token, tool-provider secret, or business-system
credential as the Client Token.

## Workflow Pattern

1. Generate a deterministic `request_id` in the workflow, for example
   `dify:<conversation-id>:<workflow-run-id>:<step-id>`.
2. Call `submit_governed_job` with an administrator-provided route.
3. Save the returned `job_id`.
4. Call `wait_for_job` for a short bounded wait, or call `get_job` from a later step.
5. Treat `done` as success. Treat `error` and `rejected` as terminal failures.

`queued`, `running`, and `dispatched` are non-terminal. If a bounded wait times out,
query the same `job_id` later. Do not submit a replacement action. When retrying the
same business request, reuse the same `request_id` without changing its meaning or
arguments.

## First Success and Feedback

Use the [Dify integration path](https://www.bailinghub.com/en/integrations#dify) as the
canonical start page. The first integration is successful when a job submitted through
the configured route reaches a terminal state under the same `job_id`, BailingHub retains
its approval and audit state, and Dify never receives administrator or business-system
credentials.

Report a PASS, partial result, or failure through the
[BailingHub independent validation form](https://github.com/bailinghub/bailinghub/issues/new?template=independent_validation.yml)
and select the Dify track. Never include tokens, model keys, personal information, or
production business data.

## Security Model

- Route choice is constrained again by the BailingHub client allowlist.
- `project` and `profile` are not plugin inputs and cannot be overridden by a model.
- Responses are limited to 1 MiB and filtered to job state and result fields.
- Arbitrary upstream response bodies are not exposed as errors.
- Non-loopback HTTP base URLs are rejected.
- Final business authorization remains in the business system.

The plugin is an adapter to governance enforcement; it is not the final authorization
boundary and does not make model output trustworthy.

The plugin sends requests only to the BailingHub base URL configured by the Dify
administrator. See [PRIVACY.md](PRIVACY.md) for the complete data-flow disclosure.

## Development

Python 3.12 and [uv](https://docs.astral.sh/uv/) are recommended.

```bash
uv sync --dev
uv run ruff check .
uv run pytest
uv run python scripts/check_project.py
```

Package with a pinned Dify Plugin CLI as described in [Releasing](docs/RELEASING.md).

## Related Documentation

- [BailingHub Dify integration recipe](https://github.com/bailinghub/bailinghub/tree/main/docs/integrations/dify)
- [BailingHub HTTP contract](https://github.com/bailinghub/bailinghub/blob/main/docs/CONTRACT.en.md)
- [Dify Tool Plugin guide](https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin)

## License

Apache License 2.0. See [LICENSE](LICENSE).
