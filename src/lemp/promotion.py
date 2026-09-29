from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .attestation import (
    ACTIONS_BOT_EMAIL,
    PROMOTION_WORKFLOW,
    AttestationError,
    verify_attested_tag,
    workflow_run_attempt,
)

BOT_NAME = "github-actions[bot]"
CHECKPOINT_RE = re.compile(r"^CP\d{6}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PROMOTION_EVENTS = {"push", "workflow_dispatch"}


class PromotionError(RuntimeError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise PromotionError(result.stderr.strip() or result.stdout.strip())
    return result


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    raise PromotionError(f"invalid {field}: {value!r}")


def attestation_text(
    *,
    checkpoint: str,
    commit_sha: str,
    repository: str,
    run_id: int,
    run_attempt: int,
    event: str,
) -> str:
    return (
        "lemp_attestation_version: 1\n"
        f"checkpoint: {checkpoint}\n"
        f"commit_sha: {commit_sha}\n"
        f"repository: {repository}\n"
        f"workflow: {PROMOTION_WORKFLOW}\n"
        f"workflow_run_id: {run_id}\n"
        f"workflow_run_attempt: {run_attempt}\n"
        f"event: {event}\n"
    )


def _create_tag(
    root: Path,
    tag: str,
    commit_sha: str,
    message: str,
    *,
    force: bool,
) -> None:
    args = [
        "-c",
        f"user.name={BOT_NAME}",
        "-c",
        f"user.email={ACTIONS_BOT_EMAIL}",
        "tag",
    ]
    if force:
        args.append("-f")
    args.extend(["-a", tag, "-m", message, commit_sha])
    _git(root, *args)


def prepare_tag(
    root: Path,
    *,
    checkpoint: str,
    commit_sha: str,
    repository: str,
    run_id: int | str,
    run_attempt: int | str,
    event: str,
) -> dict[str, Any]:
    root = root.resolve()
    if CHECKPOINT_RE.fullmatch(checkpoint) is None:
        raise PromotionError(f"invalid checkpoint: {checkpoint!r}")
    if SHA_RE.fullmatch(commit_sha) is None:
        raise PromotionError(f"invalid commit SHA: {commit_sha!r}")
    if REPOSITORY_RE.fullmatch(repository) is None:
        raise PromotionError(f"invalid repository: {repository!r}")
    if event not in PROMOTION_EVENTS:
        raise PromotionError(f"invalid promotion event: {event!r}")

    run_id = _positive_int(run_id, "run id")
    run_attempt = _positive_int(run_attempt, "run attempt")

    manifest_result = _git(root, "show", f"{commit_sha}:MANIFEST.yaml")
    manifest = yaml.safe_load(manifest_result.stdout) or {}
    if not isinstance(manifest, dict) or manifest.get("checkpoint") != checkpoint:
        raise PromotionError(
            "target commit MANIFEST checkpoint does not match promotion checkpoint"
        )

    tag = f"lemp-valid/{checkpoint}"
    ref = f"refs/tags/{tag}"
    message = attestation_text(
        checkpoint=checkpoint,
        commit_sha=commit_sha,
        repository=repository,
        run_id=run_id,
        run_attempt=run_attempt,
        event=event,
    )

    exists = _git(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0
    if not exists:
        _create_tag(root, tag, commit_sha, message, force=False)
        verify_attested_tag(
            root,
            tag,
            checkpoint,
            commit_sha,
            verify_remote=False,
        )
        return {"action": "CREATE", "tag": tag, "expected_remote_ref": None}

    previous_ref = _git(root, "rev-parse", ref).stdout.strip()
    peeled = _git(root, "rev-list", "-n", "1", tag).stdout.strip()
    if peeled != commit_sha:
        raise PromotionError(
            f"refusing to move existing canonical tag {tag} from {peeled} to {commit_sha}"
        )

    try:
        previous = verify_attested_tag(
            root,
            tag,
            checkpoint,
            commit_sha,
            verify_remote=False,
        )
    except AttestationError as exc:
        raise PromotionError(f"existing canonical tag is malformed: {exc}") from exc

    if previous is None:
        raise PromotionError("existing canonical tag lacks an attestation")

    previous_repository = previous.get("repository")
    if previous_repository != repository:
        raise PromotionError("existing canonical tag repository does not match current repository")

    previous_run_id = _positive_int(previous.get("workflow_run_id"), "existing run id")
    previous_attempt = _positive_int(
        previous.get("workflow_run_attempt"),
        "existing run attempt",
    )
    previous_event = previous.get("event")
    if previous_event not in PROMOTION_EVENTS:
        raise PromotionError("existing canonical tag event is not a promotion event")

    run = workflow_run_attempt(
        repository,
        previous_run_id,
        previous_attempt,
        commit_sha,
        previous_event,
    )
    if run.get("conclusion") == "success":
        return {
            "action": "KEEP_VALID",
            "tag": tag,
            "expected_remote_ref": previous_ref,
        }
    if run.get("status") != "completed":
        raise PromotionError(
            "existing attested workflow attempt is not completed; refusing recovery"
        )

    _create_tag(root, tag, commit_sha, message, force=True)
    verify_attested_tag(
        root,
        tag,
        checkpoint,
        commit_sha,
        verify_remote=False,
    )
    return {
        "action": "RECOVER_FAILED",
        "tag": tag,
        "expected_remote_ref": previous_ref,
    }


def prepare_tag_from_environment(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = yaml.safe_load((root / "MANIFEST.yaml").read_text(encoding="utf-8")) or {}
    if not isinstance(manifest, dict):
        raise PromotionError("MANIFEST.yaml must be a mapping")
    return prepare_tag(
        root,
        checkpoint=str(manifest.get("checkpoint") or ""),
        commit_sha=os.environ.get("GITHUB_SHA", ""),
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", ""),
        run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        event=os.environ.get("GITHUB_EVENT_NAME", ""),
    )
