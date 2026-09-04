# Project Boundaries

## Ownership

`bailinghub-dify-plugin` is an independent integration adapter with its own repository,
version, changelog, tests, packages, issues, and release process.

## What Belongs Here

- Dify Tool Plugin manifests and tool schemas;
- the minimal HTTP client for BailingHub's public Client API;
- Dify-specific setup, workflow guidance, packaging, and compatibility tests;
- adapter-specific security and privacy documentation.

## What Does Not Belong Here

| Concern | Owning project or layer |
| --- | --- |
| ACC normative fields and conformance | ACC repository |
| BailingHub server routes and runtime behavior | BailingHub repository |
| Business API implementation and final authorization | Business system |
| Dify runtime behavior and plugin SDK | Dify |
| Private deployment configuration or credentials | Deploying organization |

## Asset Placement Matrix

Keep every change in the layer that owns its semantics and lifecycle.

| Asset | Location | Visibility | Release lifecycle |
| --- | --- | --- | --- |
| Portable governance semantics and conformance | ACC repository | Public | ACC only |
| Control-plane APIs, runtime enforcement, and server behavior | BailingHub repository | Public | BailingHub only |
| Dify manifests, tools, packaging, and adapter tests | This repository | Public | This adapter only |
| Generic Dify workflow templates containing only placeholders | This repository | Public | Adapter-managed |
| Deployer-configured workflows, test routes, credentials, request IDs, and E2E evidence | Deploying organization's operations store | Private | Organization-managed |

Public templates must use placeholders and harmless routes, must not embed model credentials,
and must preserve the adapter's documented job lifecycle. A working internal workflow is
evidence that the adapter can be operated; it is not itself a distributable artifact. Do not
copy private workflow exports, deployment URLs, tokens, account identifiers, or raw run evidence
into this repository.

## Dependency Direction

The dependency direction is deliberately one-way.

```text
bailinghub-dify-plugin -> BailingHub public Client API
BailingHub may consume ACC declarations
ACC has no dependency on either implementation
```

The adapter must not require ACC to name or privilege Dify, and ACC must not contain
plugin installation instructions. The BailingHub server may link to this adapter as an
optional integration, but the adapter is not part of the BailingHub server release.

## Versioning Rule

- Plugin versions describe this adapter only.
- BailingHub versions describe the control plane only.
- ACC versions describe the contract only.
- Compatibility is documented explicitly; version numbers are never synchronized for
  appearance.

## Change Routing

- A Dify manifest, UX, packaging, or SDK issue is fixed here.
- A `/run` or `/jobs/{job_id}` contract issue is fixed in BailingHub first, then reflected
  in this adapter's compatibility matrix.
- A governance field or portable semantic proposal is discussed in ACC, not here.
- An internal workflow, route, credential, or verification-record change stays in the
  deploying organization's private operations store and is never released with the plugin.
