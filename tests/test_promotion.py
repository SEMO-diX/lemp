from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

import lemp.promotion as promotion


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )


def repo_at_cp17(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "LEMP Test")
    git(root, "config", "user.email", "lemp@example.invalid")
    (root / "MANIFEST.yaml").write_text(
        yaml.safe_dump(
            {
                "protocol": "LEMP",
                "protocol_version": "1.1",
                "checkpoint": "CP000017",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    git(root, "add", "MANIFEST.yaml")
    git(root, "commit", "-m", "cp17")
    sha = git(root, "rev-parse", "HEAD").stdout.strip()
    return root, sha


def test_prepare_tag_creates_annotated_attestation(tmp_path: Path) -> None:
    root, sha = repo_at_cp17(tmp_path)
    result = promotion.prepare_tag(
        root,
        checkpoint="CP000017",
        commit_sha=sha,
        repository="example/memory",
        run_id=123,
        run_attempt=1,
        event="push",
    )
    assert result["action"] == "CREATE"
    assert result["tag"] == "lemp-valid/CP000017"
    assert git(root, "cat-file", "-t", "refs/tags/lemp-valid/CP000017").stdout.strip() == "tag"


def test_successful_existing_attestation_is_kept(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, sha = repo_at_cp17(tmp_path)
    promotion.prepare_tag(
        root,
        checkpoint="CP000017",
        commit_sha=sha,
        repository="example/memory",
        run_id=123,
        run_attempt=1,
        event="push",
    )
    monkeypatch.setattr(
        promotion,
        "workflow_run_attempt",
        lambda *args, **kwargs: {"status": "completed", "conclusion": "success"},
    )
    result = promotion.prepare_tag(
        root,
        checkpoint="CP000017",
        commit_sha=sha,
        repository="example/memory",
        run_id=124,
        run_attempt=1,
        event="push",
    )
    assert result["action"] == "KEEP_VALID"


def test_existing_tag_never_moves_to_another_commit(tmp_path: Path) -> None:
    root, sha = repo_at_cp17(tmp_path)
    promotion.prepare_tag(
        root,
        checkpoint="CP000017",
        commit_sha=sha,
        repository="example/memory",
        run_id=123,
        run_attempt=1,
        event="push",
    )
    (root / "note.txt").write_text("new commit", encoding="utf-8")
    git(root, "add", "note.txt")
    git(root, "commit", "-m", "new commit")
    new_sha = git(root, "rev-parse", "HEAD").stdout.strip()

    with pytest.raises(promotion.PromotionError):
        promotion.prepare_tag(
            root,
            checkpoint="CP000017",
            commit_sha=new_sha,
            repository="example/memory",
            run_id=124,
            run_attempt=1,
            event="push",
        )
