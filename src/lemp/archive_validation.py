from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def _safe(root: Path, rel: str) -> Path:
    target = (root / rel).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes repository: {rel}") from exc
    return target


def _yaml(root: Path, rel: str) -> dict[str, Any]:
    path = _safe(root, rel)
    if not path.is_file():
        raise ValueError(f"missing required file: {rel}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML mapping: {rel}")
    return data


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {path.name}")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError(f"unterminated YAML frontmatter: {path.name}")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError(f"expected YAML frontmatter mapping: {path.name}")
    return data


def validate_archive(root: Path, manifest: dict[str, Any]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    policy = manifest.get("archive_policy")
    if not isinstance(policy, dict):
        return ["MANIFEST.archive_policy must be a mapping"]

    expected = {
        "recursive_summary_only": False,
        "source_recovery_required": True,
        "immutable_preferred": True,
        "checkpointed_session_archive_required": True,
        "index": "archive/INDEX.yaml",
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            errors.append(
                f"MANIFEST.archive_policy.{key} must be {value!r}, "
                f"got {policy.get(key)!r}"
            )

    index_rel = policy.get("index", "archive/INDEX.yaml")
    if not isinstance(index_rel, str):
        errors.append("MANIFEST.archive_policy.index must be a path")
        return errors

    try:
        index = _yaml(root, index_rel)
    except Exception as exc:
        errors.append(str(exc))
        return errors

    if index.get("protocol") != manifest.get("protocol"):
        errors.append("archive index protocol does not match MANIFEST")
    if str(index.get("protocol_version")) != str(manifest.get("protocol_version")):
        errors.append("archive index protocol_version does not match MANIFEST")

    index_policy = index.get("policy")
    if not isinstance(index_policy, dict):
        errors.append("archive index policy must be a mapping")
        index_policy = {}

    allowed_types = index_policy.get("allowed_record_types") or []
    if (
        not isinstance(allowed_types, list)
        or not allowed_types
        or any(not isinstance(item, str) or not item for item in allowed_types)
    ):
        errors.append("archive allowed_record_types must be a non-empty list")
        allowed_types = []

    expected_status = index_policy.get("expected_status")
    if expected_status != "immutable-preferred":
        errors.append("archive expected_status must be 'immutable-preferred'")

    sessions_dir = _safe(root, "sessions")
    checkpointed_sessions: set[str] = set()
    if not sessions_dir.is_dir():
        errors.append("missing required directory: sessions")
    else:
        for path in sorted(sessions_dir.glob("S[0-9][0-9][0-9][0-9][0-9][0-9].md")):
            sid = path.stem
            try:
                fm = _frontmatter(path)
            except Exception as exc:
                errors.append(f"sessions/{path.name}: {exc}")
                continue
            if fm.get("id") != sid:
                errors.append(f"session id mismatch: {sid}")
                continue
            checkpoint = fm.get("checkpoint_after")
            if isinstance(checkpoint, str) and re.fullmatch(r"CP\d{6}", checkpoint):
                checkpointed_sessions.add(sid)

    records = index.get("records")
    if not isinstance(records, list):
        errors.append("archive index records must be a list")
        records = []

    indexed_sessions: set[str] = set()
    indexed_paths: set[str] = set()
    for entry in records:
        if not isinstance(entry, dict):
            errors.append(f"invalid archive index record: {entry!r}")
            continue

        session = entry.get("session")
        rel = entry.get("path")
        record_type = entry.get("record_type")
        status = entry.get("status")

        if not isinstance(session, str) or re.fullmatch(r"S\d{6}", session) is None:
            errors.append(f"invalid archive session id: {session!r}")
            continue
        if session in indexed_sessions:
            errors.append(f"duplicate archive session entry: {session}")
        indexed_sessions.add(session)

        if session not in checkpointed_sessions:
            errors.append(f"archive references unknown or non-checkpointed session: {session}")

        if not isinstance(rel, str) or not rel.startswith("archive/"):
            errors.append(f"{session}: archive path must be under archive/: {rel!r}")
            continue
        if rel in indexed_paths:
            errors.append(f"duplicate archive path entry: {rel}")
        indexed_paths.add(rel)

        path = _safe(root, rel)
        if not path.is_file():
            errors.append(f"{session}: missing archive file: {rel}")
        elif not path.stem.startswith(session):
            errors.append(f"{session}: archive filename does not match session: {rel}")

        if record_type not in allowed_types:
            errors.append(f"{session}: unsupported archive record_type {record_type!r}")
        if status != expected_status:
            errors.append(f"{session}: archive status must be {expected_status!r}")

    for session in sorted(checkpointed_sessions - indexed_sessions):
        errors.append(f"checkpointed session missing archive record: {session}")
    for session in sorted(indexed_sessions - checkpointed_sessions):
        errors.append(f"archive record has no checkpointed session: {session}")

    latest_session = manifest.get("latest_session")
    if isinstance(latest_session, str) and latest_session not in indexed_sessions:
        errors.append(f"latest session missing archive record: {latest_session}")

    return errors
