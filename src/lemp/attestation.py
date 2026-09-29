from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ACTIONS_BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
PROMOTION_WORKFLOW = ".github/workflows/lemp-canonical.yml"
ATTESTATION_VERSION = 1
ATTESTATION_REQUIRED_FROM = 17
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class AttestationError(RuntimeError):
    pass


class RemoteVerificationUnavailable(AttestationError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AttestationError(result.stderr.strip() or result.stdout.strip())
    return result


def _tag_object(root: Path, tag: str) -> tuple[dict[str, str], dict[str, Any]]:
    ref = f"refs/tags/{tag}"
    kind = _git(root, "cat-file", "-t", ref, check=False)
    if kind.returncode != 0 or kind.stdout.strip() != "tag":
        raise AttestationError(f"{tag} must be an annotated tag")

    raw = _git(root, "cat-file", "-p", ref).stdout
    header, separator, body = raw.partition("\n\n")
    if not separator:
        raise AttestationError(f"{tag} has no attestation body")

    fields: dict[str, str] = {}
    for line in header.splitlines():
        key, sep, value = line.partition(" ")
        if sep:
            fields[key] = value

    try:
        data = yaml.safe_load(body) or {}
    except Exception as exc:
        raise AttestationError(f"invalid attestation YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise AttestationError("canonical attestation must be a YAML mapping")
    return fields, data


def _origin_repository(root: Path) -> str | None:
    result = _git(root, "remote", "get-url", "origin", check=False)
    if result.returncode != 0:
        return None
    match = re.search(
        r"github\.com[/:]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
        result.stdout.strip(),
    )
    return match.group(1) if match else None


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    raise AttestationError(f"invalid attestation {field}: {value!r}")


def _github_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = None
    if result is not None and result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    raise RemoteVerificationUnavailable(
        "remote attestation verification requires GH_TOKEN/GITHUB_TOKEN "
        "or an authenticated GitHub CLI; use --offline-attestation only for diagnostics"
    )


def _github_json(repository: str, path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{path.lstrip('/')}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {_github_token()}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "LEMP-canonical-verifier",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise RemoteVerificationUnavailable(
                f"GitHub attestation lookup is not authorized: HTTP {exc.code}"
            ) from exc
        raise AttestationError(f"GitHub attestation lookup failed: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RemoteVerificationUnavailable(
            f"GitHub attestation verification is unavailable: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise AttestationError("GitHub Actions response must be an object")
    return data


def workflow_run_attempt(
    repository: str,
    run_id: int,
    run_attempt: int,
    sha: str,
    event: str,
) -> dict[str, Any]:
    data = _github_json(
        repository,
        f"actions/runs/{run_id}/attempts/{run_attempt}",
    )
    expected = {
        "name": "LEMP Canonical Gate",
        "path": PROMOTION_WORKFLOW,
        "head_sha": sha,
        "head_branch": "main",
        "event": event,
        "run_attempt": run_attempt,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise AttestationError(
                f"attested workflow run {key} mismatch: {data.get(key)!r} != {value!r}"
            )
    return data


def verify_workflow_run(
    repository: str,
    run_id: int,
    run_attempt: int,
    sha: str,
    event: str,
) -> None:
    data = workflow_run_attempt(repository, run_id, run_attempt, sha, event)
    if data.get("conclusion") != "success":
        raise AttestationError("attested workflow run did not complete successfully")


def verify_attested_tag(
    root: Path,
    tag: str,
    checkpoint: str,
    sha: str,
    *,
    verify_remote: bool = True,
) -> dict[str, Any] | None:
    number = int(checkpoint[2:])
    if number < ATTESTATION_REQUIRED_FROM:
        return None

    fields, attestation = _tag_object(root, tag)
    if fields.get("object") != sha or fields.get("type") != "commit":
        raise AttestationError(f"{tag} does not annotate the selected commit")
    if fields.get("tag") != tag:
        raise AttestationError(f"{tag} annotated header mismatch")

    tagger = fields.get("tagger", "")
    email = re.search(r"<([^>]+)>", tagger)
    if email is None or email.group(1) != ACTIONS_BOT_EMAIL:
        raise AttestationError(f"{tag} tagger is not the GitHub Actions bot")

    expected = {
        "lemp_attestation_version": ATTESTATION_VERSION,
        "checkpoint": checkpoint,
        "commit_sha": sha,
        "workflow": PROMOTION_WORKFLOW,
    }
    for key, value in expected.items():
        if attestation.get(key) != value:
            raise AttestationError(
                f"{tag} attestation {key} mismatch: {attestation.get(key)!r} != {value!r}"
            )

    repository = attestation.get("repository")
    if not isinstance(repository, str) or REPOSITORY_RE.fullmatch(repository) is None:
        raise AttestationError(f"{tag} attestation repository is invalid")

    origin_repository = _origin_repository(root)
    if origin_repository is not None and origin_repository != repository:
        raise AttestationError(
            f"{tag} attestation repository does not match origin: "
            f"{repository!r} != {origin_repository!r}"
        )

    run_id = _positive_int(attestation.get("workflow_run_id"), "workflow_run_id")
    attempt = _positive_int(
        attestation.get("workflow_run_attempt"),
        "workflow_run_attempt",
    )
    event = attestation.get("event")
    if event not in {"push", "workflow_dispatch"}:
        raise AttestationError(f"{tag} attestation event is not a promotion event")

    if verify_remote:
        verify_workflow_run(repository, run_id, attempt, sha, event)
    return attestation
