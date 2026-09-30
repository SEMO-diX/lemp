from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

from lemp.runtime import init_memory


def test_generated_template_contains_valid_control_files(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)

    for rel in (
        "MANIFEST.yaml",
        "STATE.md",
        "schemas/applicability.schema.json",
        "schemas/context-contract.schema.json",
        ".github/workflows/lemp-canonical.yml",
    ):
        assert (root / rel).is_file(), rel

    json.loads(
        (root / "schemas" / "applicability.schema.json").read_text(encoding="utf-8")
    )
    json.loads(
        (root / "schemas" / "context-contract.schema.json").read_text(encoding="utf-8")
    )


def test_generated_canonical_workflow_is_sha_pinned(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)
    workflow_path = root / ".github" / "workflows" / "lemp-canonical.yml"
    workflow = yaml.load(
        workflow_path.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert workflow["name"] == "LEMP Canonical Gate"
    assert "gate" in workflow["jobs"]
    assert "promote" in workflow["jobs"]

    spec = workflow["env"]["LEMP_RUNTIME_SPEC"]
    match = re.search(r"@([0-9a-f]{40})$", spec)
    assert match is not None
    assert not spec.endswith("@main")


def test_runtime_source_can_be_overridden(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    custom = "git+https://github.com/example/lemp.git@0123456789abcdef0123456789abcdef01234567"
    init_memory(root, runtime_spec=custom)
    workflow = yaml.load(
        (root / ".github" / "workflows" / "lemp-canonical.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    assert workflow["env"]["LEMP_RUNTIME_SPEC"] == custom


def test_generated_memory_requires_attestation_from_cp1(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)

    manifest = yaml.safe_load(
        (root / "MANIFEST.yaml").read_text(encoding="utf-8")
    )
    assert manifest["canonical"]["attestation_required_from"] == "CP000001"

    bootstrap = (root / "BOOTSTRAP.md").read_text(encoding="utf-8")
    assert "including CP000001" in bootstrap
    assert "CP000017" not in bootstrap
    assert "local tag object only" not in bootstrap


def test_generated_canonical_workflow_shell_is_syntax_valid(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)

    workflow = yaml.load(
        (root / ".github" / "workflows" / "lemp-canonical.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["gate"]["steps"]
    sequence = next(
        step for step in steps if step.get("name") == "Validate checkpoint sequence"
    )
    script = sequence["run"]

    result = subprocess.run(
        ["bash", "-n"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
