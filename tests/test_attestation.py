from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

import lemp.attestation as attestation


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )


def cp1_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    (root / "MANIFEST.yaml").write_text(
        yaml.safe_dump({"protocol": "LEMP", "protocol_version": "1.1", "checkpoint": "CP000001"}),
        encoding="utf-8",
    )
    git(root, "add", "MANIFEST.yaml")
    git(root, "commit", "-m", "cp1")
    sha = git(root, "rev-parse", "HEAD").stdout.strip()
    return root, sha


def test_cp1_annotated_attestation_passes_offline(tmp_path: Path) -> None:
    root, sha = cp1_repo(tmp_path)
    message = (
        "lemp_attestation_version: 1\n"
        "checkpoint: CP000001\n"
        f"commit_sha: {sha}\n"
        "repository: example/memory\n"
        "workflow: .github/workflows/lemp-canonical.yml\n"
        "workflow_run_id: 12345\n"
        "workflow_run_attempt: 1\n"
        "event: push\n"
    )
    git(
        root,
        "-c",
        "user.name=github-actions[bot]",
        "-c",
        f"user.email={attestation.ACTIONS_BOT_EMAIL}",
        "tag",
        "-a",
        "lemp-valid/CP000001",
        "-m",
        message,
    )
    data = attestation.verify_attested_tag(
        root,
        "lemp-valid/CP000001",
        "CP000001",
        sha,
        verify_remote=False,
    )
    assert data is not None
    assert data["workflow_run_id"] == 12345


def test_cp1_lightweight_tag_is_rejected(tmp_path: Path) -> None:
    root, sha = cp1_repo(tmp_path)
    git(root, "tag", "lemp-valid/CP000001")
    with pytest.raises(attestation.AttestationError):
        attestation.verify_attested_tag(
            root,
            "lemp-valid/CP000001",
            "CP000001",
            sha,
            verify_remote=False,
        )


def test_exact_workflow_run_fields_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        attestation,
        "_github_json",
        lambda repository, path: {
            "name": "LEMP Canonical Gate",
            "path": ".github/workflows/lemp-canonical.yml",
            "head_sha": "a" * 40,
            "head_branch": "main",
            "event": "push",
            "run_attempt": 2,
            "conclusion": "success",
        },
    )
    attestation.verify_workflow_run(
        "example/memory",
        99,
        2,
        "a" * 40,
        "push",
    )

    with pytest.raises(attestation.AttestationError):
        attestation.verify_workflow_run(
            "example/memory",
            99,
            1,
            "a" * 40,
            "push",
        )


def test_invalid_checkpoint_is_reported_as_attestation_error(tmp_path: Path) -> None:
    root, sha = cp1_repo(tmp_path)
    with pytest.raises(attestation.AttestationError, match="invalid canonical checkpoint"):
        attestation.verify_attested_tag(
            root,
            "lemp-valid/not-a-checkpoint",
            "not-a-checkpoint",
            sha,
            verify_remote=False,
        )
