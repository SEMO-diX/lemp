from __future__ import annotations

import io
import json
import re
import subprocess
import tarfile
import tempfile

from .archive_validation import validate_archive
from .attestation import AttestationError, RemoteVerificationUnavailable, verify_attested_tag
from .control_plane import validate_control_plane
from .path_rules import allowed_memory_path
from .provenance import validate_provenance
from .previous_generation import PreviousGenerationError, validate_against_previous
from .template_data import DEFAULT_RUNTIME_SPEC, RUNTIME_SPEC_PLACEHOLDER, TEMPLATE_FILES
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CHECKPOINT_RE = re.compile(r"^CP(\d{6})$")
TAG_RE = re.compile(r"^lemp-valid/(CP\d{6})$")
STATE_CP_RE = re.compile(r"^Checkpoint:\s*(CP\d{6})\s*$", re.MULTILINE)
STATE_VER_RE = re.compile(r"^State-Version:\s*(\d+)\s*$", re.MULTILINE)


class LEMPError(RuntimeError):
    pass


def _run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(args),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise LEMPError(proc.stderr.strip() or proc.stdout.strip() or f"command failed: {args}")
    return proc


def _yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise LEMPError(f"cannot read YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LEMPError(f"expected YAML mapping: {path}")
    return data


def _safe(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise LEMPError(f"unsafe repository path: {rel!r}")
    target = (root / rel).resolve()
    base = root.resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise LEMPError(f"path escapes repository: {rel}") from exc
    return target


@dataclass
class Validation:
    integrity: str
    checkpoint: str | None
    state_version: int | None
    missing_optional: list[str]
    errors: list[str]
    required_context: list[str]
    required_invariant_paths: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "integrity": self.integrity,
            "checkpoint": self.checkpoint,
            "state_version": self.state_version,
            "missing_optional": self.missing_optional,
            "errors": self.errors,
            "required_context": self.required_context,
            "required_invariant_paths": self.required_invariant_paths,
        }


def _list_value(value: Any, field: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return []
    return value


def _extend_validation_layer(
    errors: list[str],
    label: str,
    validator: Any,
) -> None:
    try:
        layer_errors = validator()
    except Exception as exc:
        errors.append(
            f"{label} validation failed: {type(exc).__name__}: {exc}"
        )
        return
    if not isinstance(layer_errors, list) or any(
        not isinstance(item, str) for item in layer_errors
    ):
        errors.append(f"{label} validator returned an invalid error list")
        return
    errors.extend(layer_errors)


def validate(root: Path) -> Validation:
    root = root.resolve()
    errors: list[str] = []
    missing_optional: list[str] = []
    required_context: list[str] = []
    required_invariant_paths: list[str] = []

    try:
        manifest = _yaml(root / "MANIFEST.yaml")
    except LEMPError as exc:
        return Validation("FAIL", None, None, [], [str(exc)], [], [])

    checkpoint = manifest.get("checkpoint")
    state_version = manifest.get("state_version")
    checkpoint_valid = (
        isinstance(checkpoint, str) and CHECKPOINT_RE.fullmatch(checkpoint) is not None
    )
    state_version_valid = (
        isinstance(state_version, int)
        and not isinstance(state_version, bool)
        and state_version >= 1
    )

    if manifest.get("protocol") != "LEMP":
        errors.append("MANIFEST.protocol must be LEMP")
    if str(manifest.get("protocol_version")) != "1.1":
        errors.append("MANIFEST.protocol_version must be 1.1")
    if not checkpoint_valid:
        errors.append("MANIFEST.checkpoint must match CPxxxxxx")
    if not state_version_valid:
        errors.append("MANIFEST.state_version must be a positive integer")

    state_path = root / "STATE.md"
    if not state_path.is_file():
        errors.append("missing STATE.md")
    else:
        try:
            text = state_path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"cannot read STATE.md: {type(exc).__name__}: {exc}")
        else:
            state_cp = STATE_CP_RE.search(text)
            state_ver = STATE_VER_RE.search(text)
            if checkpoint_valid and (
                state_cp is None or state_cp.group(1) != checkpoint
            ):
                errors.append("STATE checkpoint does not match MANIFEST")
            if state_version_valid and (
                state_ver is None or int(state_ver.group(1)) != state_version
            ):
                errors.append("STATE State-Version does not match MANIFEST")

    raw_required = manifest.get("required_context")
    if isinstance(raw_required, list):
        if any(not isinstance(item, str) for item in raw_required):
            errors.append("MANIFEST.required_context must contain only paths")
        else:
            required_context = list(dict.fromkeys(raw_required))
            for rel in required_context:
                try:
                    if not _safe(root, rel).is_file():
                        errors.append(f"missing required context: {rel}")
                except LEMPError as exc:
                    errors.append(str(exc))
    else:
        errors.append("MANIFEST.required_context must be a list of paths")

    critical_memories = _list_value(
        manifest.get("critical_memories"),
        "MANIFEST.critical_memories",
        errors,
    )
    for rel in critical_memories:
        if not isinstance(rel, str):
            errors.append(f"invalid critical memory path: {rel!r}")
            continue
        try:
            if not _safe(root, rel).is_file():
                errors.append(f"missing critical memory: {rel}")
        except LEMPError as exc:
            errors.append(str(exc))

    control = manifest.get("control_plane")
    if not isinstance(control, dict):
        errors.append("MANIFEST.control_plane must be a mapping")
        control = {}

    contract_paths: list[str] = []
    global_contract = control.get("global_contract", "contracts/GLOBAL.yaml")
    if not isinstance(global_contract, str):
        errors.append("MANIFEST.control_plane.global_contract must be a path")
    else:
        contract_paths.append(global_contract)

    active_contracts = _list_value(
        control.get("active_contracts"),
        "MANIFEST.control_plane.active_contracts",
        errors,
    )
    for rel in active_contracts:
        if not isinstance(rel, str):
            errors.append(f"invalid active contract path: {rel!r}")
            continue
        if rel not in contract_paths:
            contract_paths.append(rel)

    required_invariants: list[str] = []
    for rel in contract_paths:
        try:
            path = _safe(root, rel)
            if not path.is_file():
                errors.append(f"missing active contract: {rel}")
                continue
            contract = _yaml(path)
        except LEMPError as exc:
            errors.append(str(exc))
            continue

        if contract.get("protocol") != manifest.get("protocol"):
            errors.append(f"{rel}: protocol mismatch")
        if str(contract.get("protocol_version")) != str(
            manifest.get("protocol_version")
        ):
            errors.append(f"{rel}: protocol_version mismatch")
        if contract.get("status") != "active":
            errors.append(f"{rel}: contract is not active")

        for req in _list_value(contract.get("required"), f"{rel}.required", errors):
            if not isinstance(req, str):
                errors.append(f"{rel}: invalid required path: {req!r}")
                continue
            if req not in required_context:
                required_context.append(req)
            try:
                if not _safe(root, req).is_file():
                    errors.append(f"{rel}: missing required path: {req}")
            except LEMPError as exc:
                errors.append(str(exc))

        optional = contract.get("optional", [])
        for opt in _list_value(optional, f"{rel}.optional", errors):
            if not isinstance(opt, str):
                errors.append(f"{rel}: invalid optional path: {opt!r}")
                continue
            try:
                if not _safe(root, opt).is_file():
                    missing_optional.append(opt)
            except LEMPError as exc:
                errors.append(str(exc))

        for iid in _list_value(
            contract.get("required_invariants"),
            f"{rel}.required_invariants",
            errors,
        ):
            if not isinstance(iid, str):
                errors.append(f"{rel}: invalid required invariant id: {iid!r}")
                continue
            if iid not in required_invariants:
                required_invariants.append(iid)

    invariant_index_path = control.get("invariant_index", "invariants/INDEX.yaml")
    known_invariants: dict[str, tuple[str, dict[str, Any]]] = {}
    if not isinstance(invariant_index_path, str):
        errors.append("MANIFEST.control_plane.invariant_index must be a path")
    else:
        try:
            index = _yaml(_safe(root, invariant_index_path))
            invariant_entries = _list_value(
                index.get("invariants"),
                f"{invariant_index_path}.invariants",
                errors,
            )
            for item in invariant_entries:
                if not isinstance(item, dict):
                    errors.append("invalid invariant index entry")
                    continue
                iid, rel = item.get("id"), item.get("path")
                if not isinstance(iid, str) or not isinstance(rel, str):
                    errors.append("invalid invariant index entry")
                    continue
                try:
                    inv = _yaml(_safe(root, rel))
                except LEMPError as exc:
                    errors.append(str(exc))
                    continue
                if inv.get("id") != iid:
                    errors.append(f"invariant id mismatch: {iid}")
                known_invariants[iid] = (rel, inv)
        except LEMPError as exc:
            errors.append(str(exc))

    for iid in required_invariants:
        item = known_invariants.get(iid)
        if item is None:
            errors.append(f"missing required invariant: {iid}")
            continue
        rel, inv = item
        required_invariant_paths.append(rel)
        if inv.get("status") != "active":
            errors.append(f"required invariant is not active: {iid}")
        if inv.get("severity") != "critical":
            errors.append(f"required invariant is not critical: {iid}")

    current_path = control.get("current_state", "state/CURRENT.yaml")
    if not isinstance(current_path, str):
        errors.append("MANIFEST.control_plane.current_state must be a path")
    else:
        try:
            current = _yaml(_safe(root, current_path))
            if checkpoint_valid and current.get("checkpoint") != checkpoint:
                errors.append("current state checkpoint does not match MANIFEST")
        except LEMPError as exc:
            errors.append(str(exc))

    conflict_path = control.get("conflict_index", "conflicts/INDEX.yaml")
    if not isinstance(conflict_path, str):
        errors.append("MANIFEST.control_plane.conflict_index must be a path")
    else:
        try:
            conflicts = _yaml(_safe(root, conflict_path))
            conflict_entries = _list_value(
                conflicts.get("conflicts"),
                f"{conflict_path}.conflicts",
                errors,
            )
            for item in conflict_entries:
                if not isinstance(item, dict):
                    errors.append(f"invalid conflict index entry: {item!r}")
                    continue
                if (
                    item.get("status") == "unresolved"
                    and item.get("severity") == "critical"
                ):
                    errors.append(
                        f"unresolved critical conflict: {item.get('id')}"
                    )
        except LEMPError as exc:
            errors.append(str(exc))

    archive_policy = manifest.get("archive_policy")
    if not isinstance(archive_policy, dict):
        errors.append("MANIFEST.archive_policy must be a mapping")
    elif archive_policy.get("checkpointed_session_archive_required"):
        latest_session = manifest.get("latest_session")
        index_rel = archive_policy.get("index", "archive/INDEX.yaml")
        if not isinstance(latest_session, str):
            errors.append("MANIFEST.latest_session must be a session id")
        if not isinstance(index_rel, str):
            errors.append("MANIFEST.archive_policy.index must be a path")
        if isinstance(latest_session, str) and isinstance(index_rel, str):
            try:
                archive_index = _yaml(_safe(root, index_rel))
                records = _list_value(
                    archive_index.get("records"),
                    f"{index_rel}.records",
                    errors,
                )
                if not any(
                    isinstance(item, dict)
                    and item.get("session") == latest_session
                    for item in records
                ):
                    errors.append(
                        "latest session has no source-recovery archive record"
                    )
            except LEMPError as exc:
                errors.append(str(exc))

    _extend_validation_layer(
        errors,
        "control-plane",
        lambda: validate_control_plane(root, manifest),
    )
    _extend_validation_layer(
        errors,
        "provenance",
        lambda: validate_provenance(root, manifest),
    )
    _extend_validation_layer(
        errors,
        "archive",
        lambda: validate_archive(root, manifest),
    )

    integrity = "FAIL" if errors else ("PARTIAL" if missing_optional else "PASS")
    return Validation(
        integrity,
        checkpoint if checkpoint_valid else None,
        state_version if state_version_valid else None,
        sorted(set(missing_optional)),
        errors,
        required_context,
        sorted(set(required_invariant_paths)),
    )

def init_memory(
    destination: Path,
    *,
    runtime_spec: str = DEFAULT_RUNTIME_SPEC,
) -> Path:
    destination = destination.resolve()
    if not isinstance(runtime_spec, str) or not runtime_spec.strip():
        raise LEMPError("runtime_spec must be a non-empty string")
    if "\n" in runtime_spec or "\r" in runtime_spec:
        raise LEMPError("runtime_spec must be a single line")
    if destination.exists() and any(destination.iterdir()):
        raise LEMPError(f"destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    encoded_runtime_spec = json.dumps(runtime_spec)
    for rel, content in TEMPLATE_FILES.items():
        target = _safe(destination, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        rendered = content.replace(RUNTIME_SPEC_PLACEHOLDER, encoded_runtime_spec)
        target.write_text(rendered, encoding="utf-8")
    return destination


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(root, "git", *args, check=check)


def _refresh_tags(root: Path) -> None:
    remote = _git(root, "remote", "get-url", "origin", check=False)
    if remote.returncode == 0 and remote.stdout.strip():
        _git(root, "fetch", "--force", "--prune", "--prune-tags", "--tags", "origin")


def _tag_message(root: Path, tag: str) -> str:
    kind = _git(root, "cat-file", "-t", f"refs/tags/{tag}", check=False)
    if kind.returncode != 0 or kind.stdout.strip() != "tag":
        raise LEMPError(f"{tag} requires an annotated attestation")
    out = _git(root, "for-each-ref", "--format=%(contents)", f"refs/tags/{tag}")
    return out.stdout


def _local_attestation(root: Path, tag: str, checkpoint: str, sha: str) -> None:
    number = int(checkpoint[2:])
    if number < 17:
        return
    message = _tag_message(root, tag)
    fields: dict[str, str] = {}
    for line in message.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    required = {
        "lemp_attestation_version",
        "checkpoint",
        "commit_sha",
        "repository",
        "workflow",
        "workflow_run_id",
        "workflow_run_attempt",
        "event",
    }
    missing = sorted(required - fields.keys())
    if missing:
        raise LEMPError(f"{tag} attestation missing fields: {', '.join(missing)}")
    if fields["checkpoint"] != checkpoint or fields["commit_sha"] != sha:
        raise LEMPError(f"{tag} attestation does not bind the selected checkpoint/SHA")
    if fields["workflow"] != ".github/workflows/lemp-canonical.yml":
        raise LEMPError(f"{tag} attestation workflow mismatch")


def resolve_canonical(
    root: Path,
    *,
    fetch_tags: bool = True,
    offline_attestation: bool = False,
) -> tuple[str, str, str]:
    root = root.resolve()
    if fetch_tags:
        _refresh_tags(root)
    result = _git(root, "tag", "--list", "lemp-valid/CP??????")
    tags = []
    for raw in result.stdout.splitlines():
        m = TAG_RE.fullmatch(raw.strip())
        if m:
            tags.append((int(m.group(1)[2:]), raw.strip(), m.group(1)))
    if not tags:
        raise LEMPError("no validated canonical tag found")

    for _, tag, checkpoint in sorted(tags, reverse=True):
        sha_r = _git(root, "rev-list", "-n", "1", tag, check=False)
        if sha_r.returncode != 0:
            continue
        sha = sha_r.stdout.strip()
        show = _git(root, "show", f"{sha}:MANIFEST.yaml", check=False)
        if show.returncode != 0:
            continue
        try:
            manifest = yaml.safe_load(show.stdout) or {}
        except Exception:
            continue
        if not isinstance(manifest, dict) or manifest.get("checkpoint") != checkpoint:
            continue
        try:
            verify_attested_tag(
                root,
                tag,
                checkpoint,
                sha,
                verify_remote=not offline_attestation,
            )
        except RemoteVerificationUnavailable as exc:
            raise LEMPError(str(exc)) from exc
        except AttestationError:
            continue
        return tag, checkpoint, sha
    raise LEMPError("no valid canonical tag survived attestation verification")


def _extract_snapshot(root: Path, sha: str, destination: Path) -> None:
    proc = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", sha],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise LEMPError(proc.stderr.decode("utf-8", "replace"))
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:") as archive:
        archive.extractall(destination, filter="data")


def sync(
    root: Path,
    *,
    fetch_tags: bool = True,
    offline_attestation: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    tag, checkpoint, sha = resolve_canonical(
        root,
        fetch_tags=fetch_tags,
        offline_attestation=offline_attestation,
    )
    with tempfile.TemporaryDirectory(prefix="lemp-sync-") as raw:
        snapshot = Path(raw)
        _extract_snapshot(root, sha, snapshot)
        result = validate(snapshot)
        if result.integrity == "FAIL":
            raise LEMPError("canonical snapshot failed integrity: " + "; ".join(result.errors))
        context_paths = list(dict.fromkeys(result.required_context + result.required_invariant_paths))
        working_context = []
        for rel in context_paths:
            target = _safe(snapshot, rel)
            if target.is_file():
                working_context.append({"path": rel, "content": target.read_text(encoding="utf-8")})
        return {
            "integrity": result.integrity,
            "canonical": {"tag": tag, "checkpoint": checkpoint, "sha": sha},
            "missing_optional": result.missing_optional,
            "required_context": result.required_context,
            "required_invariant_paths": result.required_invariant_paths,
            "working_context": working_context,
            "attestation_scope": ("offline-local-only" if offline_attestation else "remote-workflow-verified"),
        }


def status(
    root: Path,
    *,
    fetch_tags: bool = True,
    offline_attestation: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    tag, checkpoint, sha = resolve_canonical(
        root,
        fetch_tags=fetch_tags,
        offline_attestation=offline_attestation,
    )
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if head == sha:
        relation = "CURRENT"
    else:
        ancestor = _git(root, "merge-base", "--is-ancestor", sha, head, check=False)
        relation = "NEWER_UNVALIDATED" if ancestor.returncode == 0 else "DIVERGED_UNVALIDATED"

    with tempfile.TemporaryDirectory(prefix="lemp-status-") as raw:
        snapshot = Path(raw)
        _extract_snapshot(root, sha, snapshot)
        result = validate(snapshot)
        if result.integrity == "FAIL":
            raise LEMPError(
                "canonical snapshot failed integrity: " + "; ".join(result.errors)
            )

    return {
        "integrity": result.integrity,
        "canonical": {
            "tag": tag,
            "checkpoint": checkpoint,
            "sha": sha,
            "state_version": result.state_version,
        },
        "candidate": {"sha": head, "relation": relation},
        "missing_optional": result.missing_optional,
        "attestation_scope": (
            "offline-local-only" if offline_attestation else "remote-workflow-verified"
        ),
    }


def _checkpoint_paths(root: Path, canonical_sha: str) -> list[str]:
    paths: set[str] = set()
    commands = [
        ("diff", "--name-only", f"{canonical_sha}..HEAD"),
        ("diff", "--name-only"),
        ("diff", "--name-only", "--cached"),
        ("ls-files", "--others", "--exclude-standard"),
    ]
    for args in commands:
        result = _git(root, *args, check=False)
        if result.returncode == 0:
            paths.update(line.strip() for line in result.stdout.splitlines() if line.strip())
    return sorted(paths)


def _managed_memory_path(rel: str) -> bool:
    return allowed_memory_path(rel)


def checkpoint(
    root: Path,
    *,
    fetch_tags: bool = True,
    allow_main: bool = False,
    check_only: bool = False,
    commit_message: str | None = None,
    offline_attestation: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    tag, canonical_checkpoint, canonical_sha = resolve_canonical(
        root,
        fetch_tags=fetch_tags,
        offline_attestation=offline_attestation,
    )
    branch = _git(root, "branch", "--show-current").stdout.strip()
    if not branch:
        raise LEMPError("checkpoint requires a named candidate branch")
    if branch == "main" and not allow_main:
        raise LEMPError("refusing checkpoint finalization on main; use a candidate branch")

    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    ancestor = _git(root, "merge-base", "--is-ancestor", canonical_sha, head, check=False)
    if ancestor.returncode != 0:
        raise LEMPError("candidate HEAD does not descend from canonical snapshot")

    manifest = _yaml(root / "MANIFEST.yaml")
    candidate_checkpoint = manifest.get("checkpoint")
    cm = CHECKPOINT_RE.fullmatch(str(canonical_checkpoint))
    nm = CHECKPOINT_RE.fullmatch(str(candidate_checkpoint))
    if cm is None or nm is None or int(nm.group(1)) != int(cm.group(1)) + 1:
        raise LEMPError(
            f"candidate checkpoint must advance exactly one step from {canonical_checkpoint}"
        )

    validation = validate(root)
    if validation.integrity == "FAIL":
        raise LEMPError("candidate integrity failed: " + "; ".join(validation.errors))

    try:
        previous_generation = validate_against_previous(
            root,
            fetch_tags=fetch_tags,
            offline_attestation=offline_attestation,
        )
    except PreviousGenerationError as exc:
        raise LEMPError(f"previous-generation validation failed: {exc}") from exc

    paths = _checkpoint_paths(root, canonical_sha)
    unmanaged = [rel for rel in paths if not _managed_memory_path(rel)]
    if unmanaged:
        raise LEMPError("checkpoint contains unmanaged paths: " + ", ".join(unmanaged))
    for rel in paths:
        _safe(root, rel)

    payload = {
        "result": "VALIDATED" if check_only else "PENDING_COMMIT",
        "branch": branch,
        "canonical": {
            "tag": tag,
            "checkpoint": canonical_checkpoint,
            "sha": canonical_sha,
        },
        "candidate_checkpoint": candidate_checkpoint,
        "candidate_paths": paths,
        "integrity": validation.integrity,
        "previous_generation": previous_generation,
    }
    if check_only:
        return payload
    if not paths:
        raise LEMPError("checkpoint finalization requires prepared durable changes")

    _git(root, "add", "--", *paths)
    message = commit_message or f"LEMP checkpoint {candidate_checkpoint}"
    _git(root, "commit", "-m", message)
    candidate_sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    payload.update(
        {
            "result": "CANDIDATE_COMMITTED",
            "candidate_sha": candidate_sha,
            "promotion": "PENDING_CANONICAL_GATE",
        }
    )
    return payload


def format_payload(payload: dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False)
    lines = []
    if "integrity" in payload:
        lines.append(f"Integrity: {payload['integrity']}")
    canonical = payload.get("canonical")
    if isinstance(canonical, dict):
        lines.append(f"Canonical: {canonical.get('tag')} @ {canonical.get('sha')}")
    candidate = payload.get("candidate")
    if isinstance(candidate, dict):
        lines.append(f"Candidate: {candidate.get('relation')} @ {candidate.get('sha')}")
    if payload.get("missing_optional"):
        lines.append("Missing optional: " + ", ".join(payload["missing_optional"]))
    return "\n".join(lines)
