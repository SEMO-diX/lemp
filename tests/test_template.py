from __future__ import annotations

import json
import re
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
