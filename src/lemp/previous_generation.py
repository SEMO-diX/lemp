from __future__ import annotations

import io
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .attestation import (
    AttestationError,
    RemoteVerificationUnavailable,
    verify_attested_tag,
)


class PreviousGenerationError(RuntimeError):
    pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise PreviousGenerationError(result.stderr.strip() or result.stdout.strip())
    return result


def _yaml_file(root: Path, rel: str) -> dict[str, Any]:
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise PreviousGenerationError(f"path escapes repository: {rel}") from exc
    if not path.is_file():
        raise PreviousGenerationError(f"missing required file: {rel}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise PreviousGenerationError(f"expected YAML mapping: {rel}")
    return data


def _extract(root: Path, sha: str, destination: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", sha],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise PreviousGenerationError(
            result.stderr.decode("utf-8", "replace").strip() or "git archive failed"
        )
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        archive.extractall(destination, filter="data")


def _checkpoint_number(value: object) -> int:
    if not isinstance(value, str) or len(value) != 8 or not value.startswith("CP"):
        raise PreviousGenerationError(f"invalid checkpoint: {value!r}")
    digits = value[2:]
    if not digits.isdigit():
        raise PreviousGenerationError(f"invalid checkpoint: {value!r}")
    return int(digits)


def _candidate_invariants(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    control = manifest.get("control_plane") or {}
    index_rel = control.get("invariant_index", "invariants/INDEX.yaml")
    if not isinstance(index_rel, str):
        raise PreviousGenerationError("candidate invariant index path is invalid")
    index = _yaml_file(root, index_rel)
    result: dict[str, dict[str, Any]] = {}
    for entry in index.get("invariants") or []:
        if not isinstance(entry, dict):
            continue
        iid, rel = entry.get("id"), entry.get("path")
        if not isinstance(iid, str) or not isinstance(rel, str):
            continue
        invariant = _yaml_file(root, rel)
        result[iid] = invariant
    return result


def validate_against_previous(
    root: Path,
    *,
    fetch_tags: bool = True,
    offline_attestation: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    candidate_manifest = _yaml_file(root, "MANIFEST.yaml")
    candidate_checkpoint = candidate_manifest.get("checkpoint")
    candidate_number = _checkpoint_number(candidate_checkpoint)
    if candidate_number <= 1:
        raise PreviousGenerationError(
            "previous-generation validation requires checkpoint greater than CP000001"
        )

    previous_checkpoint = f"CP{candidate_number - 1:06d}"
    previous_tag = f"lemp-valid/{previous_checkpoint}"

    if fetch_tags:
        fetched = _git(
            root,
            "fetch",
            "--force",
            "--prune",
            "--prune-tags",
            "--tags",
            "origin",
            check=False,
        )
        if fetched.returncode != 0:
            raise PreviousGenerationError(
                "failed to refresh canonical tags: "
                + (fetched.stderr.strip() or fetched.stdout.strip())
            )

    exists = _git(
        root,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/tags/{previous_tag}",
        check=False,
    )
    if exists.returncode != 0:
        raise PreviousGenerationError(
            f"required previous canonical tag is missing: {previous_tag}"
        )

    previous_sha = _git(root, "rev-list", "-n", "1", previous_tag).stdout.strip()
    candidate_sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    ancestor = _git(
        root,
        "merge-base",
        "--is-ancestor",
        previous_sha,
        candidate_sha,
        check=False,
    )
    if ancestor.returncode != 0:
        raise PreviousGenerationError(
            "candidate HEAD does not descend from the previous canonical snapshot"
        )

    previous_manifest_raw = _git(
        root,
        "show",
        f"{previous_sha}:MANIFEST.yaml",
    ).stdout
    previous_manifest = yaml.safe_load(previous_manifest_raw) or {}
    if (
        not isinstance(previous_manifest, dict)
        or previous_manifest.get("checkpoint") != previous_checkpoint
    ):
        raise PreviousGenerationError(
            "previous canonical MANIFEST does not match expected checkpoint"
        )

    try:
        verify_attested_tag(
            root,
            previous_tag,
            previous_checkpoint,
            previous_sha,
            verify_remote=not offline_attestation,
        )
    except RemoteVerificationUnavailable as exc:
        raise PreviousGenerationError(str(exc)) from exc
    except AttestationError as exc:
        raise PreviousGenerationError(
            f"previous canonical attestation rejected: {exc}"
        ) from exc

    with tempfile.TemporaryDirectory(prefix="lemp-previous-") as raw:
        previous_root = Path(raw)
        _extract(root, previous_sha, previous_root)

        previous_required = previous_manifest.get("required_context") or []
        previous_critical = previous_manifest.get("critical_memories") or []
        for rel in [*previous_required, *previous_critical]:
            if not isinstance(rel, str):
                raise PreviousGenerationError(
                    f"previous canonical contains invalid required path: {rel!r}"
                )
            if not (root / rel).is_file():
                raise PreviousGenerationError(
                    f"candidate removed previous required memory: {rel}"
                )

        previous_control = previous_manifest.get("control_plane") or {}
        candidate_control = candidate_manifest.get("control_plane") or {}
        if not isinstance(previous_control, dict) or not isinstance(candidate_control, dict):
            raise PreviousGenerationError("control_plane must remain a mapping")

        previous_fail = set(
            ((previous_control.get("integrity_gate") or {}).get("fail_closed_on") or [])
        )
        candidate_fail = set(
            ((candidate_control.get("integrity_gate") or {}).get("fail_closed_on") or [])
        )
        missing_fail = sorted(previous_fail - candidate_fail)
        if missing_fail:
            raise PreviousGenerationError(
                "candidate weakened fail-closed conditions: " + ", ".join(missing_fail)
            )

        previous_global = previous_control.get(
            "global_contract",
            "contracts/GLOBAL.yaml",
        )
        previous_active = previous_control.get("active_contracts") or []
        contract_paths = []
        for rel in [previous_global, *previous_active]:
            if isinstance(rel, str) and rel not in contract_paths:
                contract_paths.append(rel)

        candidate_invariants = _candidate_invariants(root, candidate_manifest)
        required_invariant_ids: set[str] = set()

        for rel in contract_paths:
            if not (root / rel).is_file():
                raise PreviousGenerationError(
                    f"candidate removed previous active contract: {rel}"
                )
            previous_contract = _yaml_file(previous_root, rel)
            candidate_contract = _yaml_file(root, rel)
            if candidate_contract.get("status") != "active":
                raise PreviousGenerationError(
                    f"candidate deactivated previous active contract: {rel}"
                )

            for required_path in previous_contract.get("required") or []:
                if not isinstance(required_path, str) or not (root / required_path).is_file():
                    raise PreviousGenerationError(
                        f"candidate no longer satisfies previous contract {rel}: "
                        f"{required_path!r}"
                    )

            for iid in previous_contract.get("required_invariants") or []:
                if isinstance(iid, str):
                    required_invariant_ids.add(iid)

            previous_gate = previous_contract.get("integrity_gate") or {}
            candidate_gate = candidate_contract.get("integrity_gate") or {}
            if isinstance(previous_gate, dict) and previous_gate.get("fail_closed") is True:
                if not isinstance(candidate_gate, dict) or candidate_gate.get("fail_closed") is not True:
                    raise PreviousGenerationError(
                        f"candidate weakened fail_closed on contract: {rel}"
                    )
                prev_fail_on = set(previous_gate.get("fail_on") or [])
                cand_fail_on = set(candidate_gate.get("fail_on") or [])
                removed = sorted(prev_fail_on - cand_fail_on)
                if removed:
                    raise PreviousGenerationError(
                        f"candidate removed contract fail_on conditions from {rel}: "
                        + ", ".join(removed)
                    )

        for iid in sorted(required_invariant_ids):
            invariant = candidate_invariants.get(iid)
            if invariant is None:
                raise PreviousGenerationError(
                    f"candidate removed previous required invariant: {iid}"
                )
            if invariant.get("status") != "active":
                raise PreviousGenerationError(
                    f"candidate deactivated previous required invariant: {iid}"
                )
            if invariant.get("severity") != "critical":
                raise PreviousGenerationError(
                    f"candidate weakened previous invariant severity: {iid}"
                )

    return {
        "result": "PASS",
        "previous_canonical": {
            "checkpoint": previous_checkpoint,
            "tag": previous_tag,
            "sha": previous_sha,
        },
        "candidate": {
            "checkpoint": candidate_checkpoint,
            "sha": candidate_sha,
        },
        "compatibility": {
            "required_context_preserved": True,
            "active_contracts_preserved": True,
            "critical_invariants_preserved": True,
            "fail_closed_conditions_not_weakened": True,
        },
    }
