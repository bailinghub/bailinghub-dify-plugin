from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


def endpoint_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    endpoints = manifest.get("endpoints")
    if not isinstance(endpoints, list):
        raise AssertionError("manifest endpoints must be an array")
    out: dict[str, dict[str, Any]] = {}
    for endpoint in endpoints:
        if not isinstance(endpoint, dict) or not isinstance(endpoint.get("id"), str):
            raise AssertionError("every manifest endpoint must have an id")
        out[endpoint["id"]] = endpoint
    return out


def semantic_version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise AssertionError(f"invalid semantic version: {value}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def required_fields(schema: dict[str, Any]) -> set[str]:
    value = schema.get("required", [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError("schema required must be an array of strings")
    return set(value)


def property_fields(schema: dict[str, Any]) -> set[str]:
    value = schema.get("properties")
    if not isinstance(value, dict):
        raise AssertionError("schema properties must be an object")
    return set(value)


def property_max_length(schema: dict[str, Any], field: str) -> int:
    properties = schema.get("properties")
    value = properties.get(field) if isinstance(properties, dict) else None
    maximum = value.get("maxLength") if isinstance(value, dict) else None
    if not isinstance(maximum, int) or maximum < 1:
        raise AssertionError(f"{field} must declare a positive maxLength")
    return maximum


def manifest_version() -> str:
    text = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^version:\s*['\"]?([^'\"\s#]+)['\"]?\s*(?:#.*)?$", text)
    if not match:
        raise AssertionError("manifest.yaml must declare a top-level version")
    return match.group(1)


def check(contract_dir: Path) -> None:
    declaration = load_json(ROOT / "compatibility/client-api.json")
    manifest = load_json(contract_dir / "manifest.json")
    vectors = load_json(contract_dir / str(manifest.get("vectors") or "vectors.json"))

    if manifest.get("contract") != declaration.get("contract"):
        raise AssertionError("contract id does not match the adapter declaration")
    if manifest.get("major") != declaration.get("contract_major"):
        raise AssertionError("Client API major version is incompatible")
    current = semantic_version(str(manifest.get("version") or ""))
    tested = semantic_version(str(declaration.get("tested_contract_version") or ""))
    if current[0] != tested[0] or current < tested:
        raise AssertionError("current Client API version predates the adapter compatibility floor")

    if declaration.get("adapter_version") != manifest_version():
        raise AssertionError("adapter_version must match manifest.yaml")

    endpoints = endpoint_map(manifest)
    endpoint_contracts = declaration.get("endpoint_contracts")
    if not isinstance(endpoint_contracts, dict) or not endpoint_contracts:
        raise AssertionError("adapter must declare endpoint_contracts")
    for endpoint_id, claim in endpoint_contracts.items():
        if endpoint_id not in endpoints or not isinstance(claim, dict):
            raise AssertionError(f"missing required endpoint: {endpoint_id}")
        actual = endpoints[endpoint_id]
        for key in ("method", "path", "authentication"):
            if claim.get(key) != actual.get(key):
                raise AssertionError(
                    f"{endpoint_id}: {key} changed from {claim.get(key)!r} to {actual.get(key)!r}"
                )

    requests = declaration.get("requests", {})
    for endpoint_id, claim in requests.items():
        endpoint = endpoints[endpoint_id]
        schema = load_json(contract_dir / endpoint["request_schema"])
        sent = set(claim.get("fields_sent", []))
        missing = required_fields(schema) - sent
        unknown = sent - property_fields(schema)
        if missing:
            raise AssertionError(f"{endpoint_id}: adapter omits required fields {sorted(missing)}")
        if unknown:
            raise AssertionError(f"{endpoint_id}: adapter sends unknown fields {sorted(unknown)}")

    run_request = load_json(contract_dir / endpoints["run.submit"]["request_schema"])
    limits = declaration.get("limits")
    if not isinstance(limits, dict):
        raise AssertionError("adapter limits must be an object")
    for limit_name, field in (
        ("request_id_max_length", "request_id"),
        ("route_max_length", "route"),
        ("input_max_length", "input"),
    ):
        adapter_limit = limits.get(limit_name)
        contract_limit = property_max_length(run_request, field)
        if not isinstance(adapter_limit, int) or adapter_limit < 1:
            raise AssertionError(f"{limit_name} must be a positive integer")
        if adapter_limit > contract_limit:
            raise AssertionError(
                f"{limit_name} allows {adapter_limit}, above contract maximum {contract_limit}"
            )

    responses = declaration.get("responses", {})
    for endpoint_id, claim in responses.items():
        endpoint = endpoints[endpoint_id]
        schema = load_json(contract_dir / endpoint["response_schema"])
        consumed = set(claim.get("required_fields", []))
        missing_guarantees = consumed - required_fields(schema)
        if missing_guarantees:
            raise AssertionError(
                f"{endpoint_id}: contract no longer guarantees {sorted(missing_guarantees)}"
            )

    status_claim = manifest.get("job_statuses", {})
    if declaration.get("known_job_statuses") != status_claim.get("known"):
        raise AssertionError("adapter known statuses differ from the Client API contract")
    if declaration.get("terminal_job_statuses") != status_claim.get("terminal"):
        raise AssertionError("adapter terminal statuses differ from the Client API contract")

    contract_errors = {int(status) for status in manifest.get("http_errors", {})}
    handled_errors = set(declaration.get("handled_http_errors", []))
    if not contract_errors.issubset(handled_errors):
        raise AssertionError(
            f"adapter does not classify HTTP errors {sorted(contract_errors - handled_errors)}"
        )

    cases = vectors.get("cases")
    if not isinstance(cases, list) or not cases:
        raise AssertionError("Client API vectors must contain cases")
    for case in cases:
        schema_name = case.get("schema") if isinstance(case, dict) else None
        if not isinstance(schema_name, str) or not (contract_dir / schema_name).is_file():
            raise AssertionError(f"vector references missing schema: {schema_name}")

    print(
        f"PASS: {declaration['consumer']} {declaration['adapter_version']} "
        f"accepts {manifest['contract']} {manifest['version']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        check(args.contract_dir.resolve())
    except (AssertionError, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
