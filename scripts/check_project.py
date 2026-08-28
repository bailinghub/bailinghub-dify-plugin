from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AUTHOR = "bailinghub"
FORBIDDEN_CLIENT_PATHS = (
    "/admin/",
    "/approvals/",
    "/executor/",
    "/send",
    "/tools/",
)
WORKFLOW_EXAMPLE = "examples/workflows/bailinghub-governed-job.yml"
BAILINGHUB_PLUGIN_IDENTIFIER = (
    "bailinghub/bailinghub:0.1.2@"
    "649ec051eeec350fca9cad7a47f8c1aa3fda8a1253c901f6f56560c4afd5d4d4"
)


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain a YAML object")
    return value


def require_file(relative_path: str) -> Path:
    path = ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"missing required file: {relative_path}")
    return path


def check_versions() -> None:
    manifest = load_yaml(require_file("manifest.yaml"))
    pyproject = tomllib.loads(require_file("pyproject.toml").read_text(encoding="utf-8"))
    manifest_version = str(manifest.get("version") or "")
    project_version = str(pyproject.get("project", {}).get("version") or "")
    if manifest_version != project_version:
        raise AssertionError(
            f"manifest version {manifest_version!r} != project version {project_version!r}"
        )
    if manifest.get("author") != EXPECTED_AUTHOR:
        raise AssertionError("manifest author must match the publishing GitHub account")


def check_plugin_graph() -> None:
    manifest = load_yaml(require_file("manifest.yaml"))
    provider_paths = manifest.get("plugins", {}).get("tools", [])
    if not isinstance(provider_paths, list) or provider_paths != ["provider/bailinghub.yaml"]:
        raise AssertionError("manifest must expose only the BailingHub tool provider")

    provider = load_yaml(require_file(provider_paths[0]))
    if provider.get("identity", {}).get("author") != EXPECTED_AUTHOR:
        raise AssertionError("provider author must match manifest author")
    credentials = provider.get("credentials_for_provider", {})
    if set(credentials) != {"base_url", "client_token"}:
        raise AssertionError("provider may request only base_url and client_token")

    tool_paths = provider.get("tools", [])
    expected_tools = {
        "tools/get_job.yaml",
        "tools/submit_governed_job.yaml",
        "tools/wait_for_job.yaml",
    }
    if set(tool_paths) != expected_tools:
        raise AssertionError("provider must expose exactly the three governed-job tools")

    for tool_path in tool_paths:
        tool = load_yaml(require_file(tool_path))
        if tool.get("identity", {}).get("author") != EXPECTED_AUTHOR:
            raise AssertionError(f"{tool_path} author must match manifest author")
        source = tool.get("extra", {}).get("python", {}).get("source")
        if not isinstance(source, str):
            raise AssertionError(f"{tool_path} must declare a Python source")
        require_file(source)

    submit = load_yaml(require_file("tools/submit_governed_job.yaml"))
    parameters = {item["name"]: item for item in submit.get("parameters", [])}
    if parameters.get("route", {}).get("form") != "form":
        raise AssertionError("route must be configured by a human, not selected by the model")


def check_security_boundary() -> None:
    require_file("compatibility/client-api.json")
    require_file("scripts/check_client_api_contract.py")
    client_source = require_file("tools/_client.py").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_CLIENT_PATHS:
        if forbidden in client_source:
            raise AssertionError(f"HTTP client must not reference privileged path {forbidden}")
    for required in (
        '"path": "/health"',
        '"path": "/run"',
        '"path": "/jobs/{job_id}"',
    ):
        if required not in client_source:
            raise AssertionError(f"HTTP client is missing expected public surface {required}")

    boundaries = require_file("docs/PROJECT_BOUNDARIES.md").read_text(encoding="utf-8")
    for phrase in ("independent integration adapter", "ACC normative", "one-way"):
        if phrase not in boundaries:
            raise AssertionError(f"project boundary document is missing: {phrase}")


def check_workflow_example() -> None:
    example = load_yaml(require_file(WORKFLOW_EXAMPLE))
    if example.get("kind") != "app" or example.get("version") != "0.6.0":
        raise AssertionError("workflow example must use the current Dify app DSL envelope")
    if example.get("app", {}).get("mode") != "workflow":
        raise AssertionError("workflow example must be a deterministic Workflow app")

    dependencies = example.get("dependencies", [])
    if len(dependencies) != 1:
        raise AssertionError("workflow example must declare exactly one plugin dependency")
    dependency = dependencies[0]
    if dependency.get("type") != "marketplace":
        raise AssertionError("workflow example must use the Marketplace plugin dependency")
    identifier = dependency.get("value", {}).get("marketplace_plugin_unique_identifier")
    if identifier != BAILINGHUB_PLUGIN_IDENTIFIER:
        raise AssertionError("workflow example must pin the reviewed BailingHub plugin package")

    graph = example.get("workflow", {}).get("graph", {})
    nodes = {node.get("id"): node.get("data", {}) for node in graph.get("nodes", [])}
    if [nodes.get(node_id, {}).get("type") for node_id in ("start", "submit", "wait", "end")] != [
        "start",
        "tool",
        "tool",
        "end",
    ]:
        raise AssertionError("workflow example must keep the start-submit-wait-end chain")

    submit = nodes["submit"]
    wait = nodes["wait"]
    expected_provider = "bailinghub/bailinghub/bailinghub"
    for name, node in (("submit", submit), ("wait", wait)):
        if node.get("provider_id") != expected_provider:
            raise AssertionError(f"{name} node must use the BailingHub tool provider")
        if node.get("plugin_unique_identifier") != BAILINGHUB_PLUGIN_IDENTIFIER:
            raise AssertionError(f"{name} node must pin the reviewed plugin package")

    route = submit.get("tool_configurations", {}).get("route", {})
    if route != {"type": "constant", "value": "replace-with-a-client-allowed-route"}:
        raise AssertionError("workflow example route must remain an explicit harmless placeholder")
    request_id = submit.get("tool_parameters", {}).get("request_id", {}).get("value", "")
    if request_id != "dify:{{#sys.workflow_run_id#}}:submit":
        raise AssertionError("workflow example request_id must be deterministic within the run")
    job_id = wait.get("tool_parameters", {}).get("job_id", {}).get("value", "")
    if job_id != "{{#submit.job_id#}}":
        raise AssertionError("wait node must reuse the exact job_id returned by submit")

    serialized = require_file(WORKFLOW_EXAMPLE).read_text(encoding="utf-8")
    forbidden_patterns = (
        r"https?://",
        r"/Users/",
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"(?i)bearer\s+[a-z0-9._~-]{16,}",
    )
    for pattern in forbidden_patterns:
        if re.search(pattern, serialized, flags=re.IGNORECASE):
            raise AssertionError(
                "workflow example contains a URL, local path, or secret-like value"
            )


def main() -> int:
    checks = (check_versions, check_plugin_graph, check_security_boundary, check_workflow_example)
    try:
        for check in checks:
            check()
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: plugin structure, versioning, and project boundaries are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
