# Deterministic governed-job workflow

`bailinghub-governed-job.yml` is a portable Dify Workflow template with no LLM node and no
embedded credential, deployment URL, account identifier, or production route.

## Import and configure

1. Install BailingHub `0.1.2` from Dify Marketplace.
2. Configure the plugin with a self-hosted BailingHub HTTPS origin and a dedicated Client Token.
3. Import `bailinghub-governed-job.yml` into Dify Studio.
4. Open the `Submit governed job` node and replace
   `replace-with-a-client-allowed-route` with one route allowed by that Client Token.
5. Run the workflow with a harmless test instruction before using business data.

The workflow creates `request_id` as `dify:<workflow_run_id>:submit`. A retry of the tool node
inside the same workflow run therefore preserves the idempotency key. A new workflow run is a
new request. If the bounded wait returns `wait_timed_out: true`, keep the returned `job_id` and
query it later; do not submit a replacement job.

The template returns `job_id`, `request_id`, `status`, `terminal`, `wait_timed_out`, `result`, and
`error`. `done` is success. `error` and `rejected` are terminal failures. `queued`, `running`, and
`dispatched` are non-terminal states.

This file is a generic adapter example, not a copy of a deployed workflow. Keep configured
routes, credentials, private URLs, request identifiers, and E2E evidence in the deploying
organization's private operations store.
