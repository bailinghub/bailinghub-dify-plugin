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
