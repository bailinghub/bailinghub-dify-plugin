from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

from scripts.check_package import check_package

ROOT = Path(__file__).resolve().parents[1]


def test_tool_yaml_files_have_unique_names_and_existing_sources() -> None:
    names: set[str] = set()
    for path in sorted((ROOT / "tools").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        name = data["identity"]["name"]
        assert name not in names
        names.add(name)
        assert (ROOT / data["extra"]["python"]["source"]).is_file()
        assert data["parameters"]
        assert data["output_schema"]["type"] == "object"
    assert names == {"submit_governed_job", "get_job", "wait_for_job"}


def test_route_is_a_human_configured_parameter() -> None:
    data = yaml.safe_load((ROOT / "tools" / "submit_governed_job.yaml").read_text(encoding="utf-8"))
    parameters = {item["name"]: item for item in data["parameters"]}
    assert parameters["route"]["form"] == "form"


def test_project_boundary_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_project.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("PASS:")


def test_public_workflow_example_is_deterministic_and_secret_free() -> None:
    workflow = yaml.safe_load(
        (ROOT / "examples" / "workflows" / "bailinghub-governed-job.yml").read_text(
            encoding="utf-8"
        )
    )
    nodes = {node["id"]: node["data"] for node in workflow["workflow"]["graph"]["nodes"]}
    assert [nodes[node_id]["type"] for node_id in ("start", "submit", "wait", "end")] == [
        "start",
        "tool",
        "tool",
        "end",
    ]
    assert nodes["submit"]["tool_parameters"]["request_id"]["value"] == (
        "dify:{{#sys.workflow_run_id#}}:submit"
    )
    assert nodes["wait"]["tool_parameters"]["job_id"]["value"] == "{{#submit.job_id#}}"
    assert nodes["submit"]["tool_configurations"]["route"]["value"] == (
        "replace-with-a-client-allowed-route"
    )


def test_package_audit_rejects_environment_files(tmp_path: Path) -> None:
    package = tmp_path / "invalid.difypkg"
    with zipfile.ZipFile(package, "w") as archive:
        for required in (
            "PRIVACY.md",
            "README.md",
            "_assets/icon.svg",
            "main.py",
            "manifest.yaml",
            "provider/bailinghub.py",
            "provider/bailinghub.yaml",
            "requirements.txt",
        ):
            archive.writestr(required, "placeholder")
        archive.writestr(".env.example", "SECRET=placeholder")

    try:
        check_package(package)
    except AssertionError as exc:
        assert "forbidden package file" in str(exc)
    else:
        raise AssertionError("package audit accepted an environment file")
