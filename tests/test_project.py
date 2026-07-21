from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

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
