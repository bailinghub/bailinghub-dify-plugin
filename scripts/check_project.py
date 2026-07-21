from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AUTHOR = "niejingchuan"
FORBIDDEN_CLIENT_PATHS = (
    "/admin/",
    "/approvals/",
    "/executor/",
    "/send",
    "/tools/",
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
    client_source = require_file("tools/_client.py").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_CLIENT_PATHS:
        if forbidden in client_source:
            raise AssertionError(f"HTTP client must not reference privileged path {forbidden}")
    for required in ('"/health"', '"/run"', 'f"/jobs/{'):
        if required not in client_source:
            raise AssertionError(f"HTTP client is missing expected public surface {required}")

    boundaries = require_file("docs/PROJECT_BOUNDARIES.md").read_text(encoding="utf-8")
    for phrase in ("independent integration adapter", "ACC normative", "one-way"):
        if phrase not in boundaries:
            raise AssertionError(f"project boundary document is missing: {phrase}")


def main() -> int:
    checks = (check_versions, check_plugin_graph, check_security_boundary)
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
