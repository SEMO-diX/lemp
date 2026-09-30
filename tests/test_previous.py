from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from lemp.promotion import prepare_tag
from lemp.runtime import LEMPError, checkpoint, init_memory


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_prior_required_condition_is_preserved(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "cp1")
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    prepare_tag(
        root,
        checkpoint="CP000001",
        commit_sha=sha,
        repository="example/memory",
        run_id=1,
        run_attempt=1,
        event="push",
    )
    git(root, "switch", "-c", "candidate/cp000002")

    manifest_path = root / "MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["memory_version"] = 2
    manifest["checkpoint"] = "CP000002"
    manifest["latest_session"] = "S000002"
    manifest["control_plane"]["integrity_gate"]["fail_closed_on"].remove(
        "missing_critical_invariant"
    )
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    state_path = root / "STATE.md"
    text = state_path.read_text(encoding="utf-8")
    text = text.replace("Checkpoint: CP000001", "Checkpoint: CP000002", 1)
    text = text.replace("MANIFEST checkpoint expected: `CP000001`", "MANIFEST checkpoint expected: `CP000002`")
    text = text.replace("This file Checkpoint: `CP000001`", "This file Checkpoint: `CP000002`")
    state_path.write_text(text, encoding="utf-8")

    current_path = root / "state" / "CURRENT.yaml"
    current = yaml.safe_load(current_path.read_text(encoding="utf-8"))
    current["checkpoint"] = "CP000002"
    current_path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")

    (root / "sessions" / "S000002.md").write_text(
        "---\nid: S000002\ndate: 2026-09-29\nprevious: S000001\n"
        "checkpoint_after: CP000002\nstate_version_after: 1\n---\n\n"
        "# Session S000002\n\nSynthetic test session.\n",
        encoding="utf-8",
    )
    (root / "archive" / "S000002-source.md").write_text(
        "# Source Recovery — S000002\n\nSynthetic source.\n",
        encoding="utf-8",
    )
    archive_path = root / "archive" / "INDEX.yaml"
    archive = yaml.safe_load(archive_path.read_text(encoding="utf-8"))
    archive["records"].append(
        {
            "session": "S000002",
            "path": "archive/S000002-source.md",
            "record_type": "source-recovery",
            "status": "immutable-preferred",
        }
    )
    archive_path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")

    with pytest.raises(LEMPError, match="previous-generation validation failed"):
        checkpoint(root, fetch_tags=False, offline_attestation=True)
