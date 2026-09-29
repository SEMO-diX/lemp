from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from lemp.promotion import prepare_tag
from lemp.runtime import checkpoint, init_memory, status, sync


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def prepare_cp2(root: Path) -> None:
    manifest_path = root / "MANIFEST.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["memory_version"] = 2
    manifest["checkpoint"] = "CP000002"
    manifest["latest_session"] = "S000002"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    state_path = root / "STATE.md"
    text = state_path.read_text(encoding="utf-8")
    text = text.replace("Checkpoint: CP000001", "Checkpoint: CP000002", 1)
    text = text.replace(
        "MANIFEST checkpoint expected: `CP000001`",
        "MANIFEST checkpoint expected: `CP000002`",
    )
    text = text.replace(
        "This file Checkpoint: `CP000001`",
        "This file Checkpoint: `CP000002`",
    )
    state_path.write_text(text, encoding="utf-8")

    current_path = root / "state" / "CURRENT.yaml"
    current = yaml.safe_load(current_path.read_text(encoding="utf-8"))
    current["checkpoint"] = "CP000002"
    current_path.write_text(
        yaml.safe_dump(current, sort_keys=False),
        encoding="utf-8",
    )

    (root / "sessions" / "S000002.md").write_text(
        "---\nid: S000002\ndate: 2026-09-29\nprevious: S000001\n"
        "checkpoint_after: CP000002\nstate_version_after: 1\n---\n\n"
        "# Session S000002\n\nSynthetic lifecycle checkpoint.\n",
        encoding="utf-8",
    )
    (root / "archive" / "S000002-source.md").write_text(
        "# Source Recovery — S000002\n\nSynthetic lifecycle source.\n",
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
    archive_path.write_text(
        yaml.safe_dump(archive, sort_keys=False),
        encoding="utf-8",
    )


def test_full_two_checkpoint_lifecycle(tmp_path: Path) -> None:
    root = tmp_path / "memory"
    init_memory(root)
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Lifecycle Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "cp1")

    cp1_sha = git(root, "rev-parse", "HEAD")
    first = prepare_tag(
        root,
        checkpoint="CP000001",
        commit_sha=cp1_sha,
        repository="example/memory",
        run_id=1,
        run_attempt=1,
        event="push",
    )
    assert first["action"] == "CREATE"
    assert sync(root, fetch_tags=False, offline_attestation=True)["canonical"]["checkpoint"] == "CP000001"

    git(root, "switch", "-c", "candidate/cp000002")
    prepare_cp2(root)
    candidate = checkpoint(
        root,
        fetch_tags=False,
        offline_attestation=True,
    )
    assert candidate["result"] == "CANDIDATE_COMMITTED"
    assert candidate["previous_generation"]["result"] == "PASS"

    candidate_sha = candidate["candidate_sha"]
    git(root, "switch", "main")
    git(root, "merge", "--ff-only", "candidate/cp000002")
    assert git(root, "rev-parse", "HEAD") == candidate_sha

    second = prepare_tag(
        root,
        checkpoint="CP000002",
        commit_sha=candidate_sha,
        repository="example/memory",
        run_id=2,
        run_attempt=1,
        event="push",
    )
    assert second["action"] == "CREATE"

    synced = sync(root, fetch_tags=False, offline_attestation=True)
    assert synced["integrity"] == "PASS"
    assert synced["canonical"]["checkpoint"] == "CP000002"
    assert synced["canonical"]["sha"] == candidate_sha

    state = status(root, fetch_tags=False, offline_attestation=True)
    assert state["integrity"] == "PASS"
    assert state["candidate"]["relation"] == "CURRENT"
    assert state["canonical"]["checkpoint"] == "CP000002"
