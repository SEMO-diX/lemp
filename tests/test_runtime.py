from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from lemp.promotion import prepare_tag
from lemp.runtime import LEMPError, checkpoint, init_memory, status, sync, validate


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)


def fixture(tmp_path: Path) -> Path:
    root = tmp_path / "memory"
    init_memory(root)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic canonical")
    sha = git(root, "rev-parse", "HEAD").stdout.strip()
    prepare_tag(
        root,
        checkpoint="CP000001",
        commit_sha=sha,
        repository="example/memory",
        run_id=1,
        run_attempt=1,
        event="push",
    )
    return root


def test_template_validates(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    result = validate(root)
    assert result.integrity == "PASS"


def test_sync_materializes_canonical_context(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    payload = sync(root, fetch_tags=False, offline_attestation=True)
    assert payload["integrity"] == "PASS"
    assert payload["canonical"]["checkpoint"] == "CP000001"
    paths = {item["path"] for item in payload["working_context"]}
    assert "STATE.md" in paths
    assert "decisions/D000001.md" in paths
    assert "invariants/INV000003.yaml" in paths


def test_unvalidated_head_does_not_replace_canonical(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    state = root / "STATE.md"
    state.write_text(state.read_text(encoding="utf-8") + "\nCandidate-only note.\n", encoding="utf-8")
    git(root, "add", "STATE.md")
    git(root, "commit", "-m", "unvalidated candidate")
    s = status(root, fetch_tags=False, offline_attestation=True)
    assert s["candidate"]["relation"] == "NEWER_UNVALIDATED"
    payload = sync(root, fetch_tags=False, offline_attestation=True)
    canonical_state = next(x["content"] for x in payload["working_context"] if x["path"] == "STATE.md")
    assert "Candidate-only note" not in canonical_state


def test_checkpoint_finalizes_managed_candidate(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    git(root, "switch", "-c", "candidate/cp000002")

    manifest = root / "MANIFEST.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        .replace("memory_version: 1", "memory_version: 2")
        .replace("checkpoint: CP000001", "checkpoint: CP000002", 1)
        .replace("latest_session: S000001", "latest_session: S000002"),
        encoding="utf-8",
    )

    state = root / "STATE.md"
    state.write_text(
        state.read_text(encoding="utf-8")
        .replace("Checkpoint: CP000001", "Checkpoint: CP000002", 1)
        .replace("MANIFEST checkpoint expected: `CP000001`", "MANIFEST checkpoint expected: `CP000002`")
        .replace("This file Checkpoint: `CP000001`", "This file Checkpoint: `CP000002`"),
        encoding="utf-8",
    )

    current = root / "state" / "CURRENT.yaml"
    current.write_text(
        current.read_text(encoding="utf-8").replace(
            "checkpoint: CP000001", "checkpoint: CP000002"
        ),
        encoding="utf-8",
    )

    session = root / "sessions" / "S000002.md"
    session.write_text(
        """---
id: S000002
date: 2026-09-29
previous: S000001
checkpoint_after: CP000002
state_version_after: 1
---

# Session S000002

Synthetic checkpoint progression test.
""",
        encoding="utf-8",
    )

    archive_record = root / "archive" / "S000002-source.md"
    archive_record.write_text(
        "# Source Recovery — S000002\n\nSynthetic checkpoint progression source.\n",
        encoding="utf-8",
    )
    archive_index_path = root / "archive" / "INDEX.yaml"
    archive_index = yaml.safe_load(archive_index_path.read_text(encoding="utf-8"))
    archive_index["records"].append(
        {
            "session": "S000002",
            "path": "archive/S000002-source.md",
            "record_type": "source-recovery",
            "status": "immutable-preferred",
        }
    )
    archive_index_path.write_text(
        yaml.safe_dump(archive_index, sort_keys=False),
        encoding="utf-8",
    )

    result = checkpoint(root, fetch_tags=False, offline_attestation=True)
    assert result["result"] == "CANDIDATE_COMMITTED"
    assert result["candidate_checkpoint"] == "CP000002"
    assert result["promotion"] == "PENDING_CANONICAL_GATE"
    assert result["previous_generation"]["result"] == "PASS"


def test_lightweight_cp1_tag_is_not_canonical(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "synthetic cp1")
    git(root, "tag", "lemp-valid/CP000001")

    with pytest.raises(LEMPError, match="no valid canonical tag"):
        sync(root, fetch_tags=False, offline_attestation=True)
