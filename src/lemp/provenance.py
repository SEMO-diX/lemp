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


def _records(
    root: Path,
    folder: str,
    prefix: str,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    directory = _safe(root, folder)
    if not directory.is_dir():
        errors.append(f"missing required directory: {folder}")
        return {}

    records: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob(f"{prefix}[0-9][0-9][0-9][0-9][0-9][0-9].md")):
        expected = path.stem
        try:
            fm = _frontmatter(path)
        except Exception as exc:
            errors.append(f"{folder}/{path.name}: {exc}")
            continue
        if fm.get("id") != expected:
            errors.append(
                f"{label} id mismatch: file={expected!r}, frontmatter={fm.get('id')!r}"
            )
            continue
        records[expected] = fm
    return records


def _cycle_errors(
    records: dict[str, dict[str, Any]],
    field: str,
    label: str,
) -> list[str]:
    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            errors.append(f"{label} cycle detected at {item_id}")
            return
        if item_id in visited:
            return
        visiting.add(item_id)
        previous = records.get(item_id, {}).get(field)
        if isinstance(previous, str) and previous in records:
            visit(previous)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in records:
        visit(item_id)
    return errors


def validate_provenance(root: Path, manifest: dict[str, Any]) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    sessions = _records(root, "sessions", "S", "session", errors)
    events = _records(root, "events", "E", "event", errors)
    decisions = _records(root, "decisions", "D", "decision", errors)

    for sid, fm in sessions.items():
        previous = fm.get("previous")
        if previous is not None:
            if not isinstance(previous, str) or re.fullmatch(r"S\d{6}", previous) is None:
                errors.append(f"{sid}: invalid previous session reference {previous!r}")
            elif previous not in sessions:
                errors.append(f"{sid}: previous references unknown session {previous}")
            elif previous == sid:
                errors.append(f"{sid}: previous session cannot reference itself")

        checkpoint = fm.get("checkpoint_after")
        if not isinstance(checkpoint, str) or re.fullmatch(r"CP\d{6}", checkpoint) is None:
            errors.append(f"{sid}: invalid checkpoint_after {checkpoint!r}")

        state_version = fm.get("state_version_after")
        if (
            not isinstance(state_version, int)
            or isinstance(state_version, bool)
            or state_version < 1
        ):
            errors.append(f"{sid}: invalid state_version_after {state_version!r}")

    errors.extend(_cycle_errors(sessions, "previous", "session previous"))

    latest_session = manifest.get("latest_session")
    if not isinstance(latest_session, str) or latest_session not in sessions:
        errors.append(f"MANIFEST latest_session is not a known session: {latest_session!r}")
    else:
        latest = sessions[latest_session]
        if latest.get("checkpoint_after") != manifest.get("checkpoint"):
            errors.append("latest session checkpoint_after does not match MANIFEST")
        if latest.get("state_version_after") != manifest.get("state_version"):
            errors.append("latest session state_version_after does not match MANIFEST")

    for eid, fm in events.items():
        source_session = fm.get("source_session")
        if not isinstance(source_session, str) or re.fullmatch(r"S\d{6}", source_session) is None:
            errors.append(f"{eid}: invalid source_session {source_session!r}")
        elif source_session not in sessions:
            errors.append(f"{eid}: source_session references unknown session {source_session}")

        supersedes = fm.get("supersedes")
        if supersedes is not None:
            if not isinstance(supersedes, str) or re.fullmatch(r"E\d{6}", supersedes) is None:
                errors.append(f"{eid}: invalid supersedes reference {supersedes!r}")
            elif supersedes not in events:
                errors.append(f"{eid}: supersedes references unknown event {supersedes}")
            elif supersedes == eid:
                errors.append(f"{eid}: supersedes cannot reference itself")

        source_event = fm.get("source_event")
        if source_event is not None:
            if not isinstance(source_event, str) or re.fullmatch(r"E\d{6}", source_event) is None:
                errors.append(f"{eid}: invalid source_event {source_event!r}")
            elif source_event not in events:
                errors.append(f"{eid}: source_event references unknown event {source_event}")

    errors.extend(_cycle_errors(events, "supersedes", "event supersession"))

    latest_event = manifest.get("latest_event")
    if not isinstance(latest_event, str) or latest_event not in events:
        errors.append(f"MANIFEST latest_event is not a known event: {latest_event!r}")

    for did, fm in decisions.items():
        source_session = fm.get("source_session")
        if not isinstance(source_session, str) or re.fullmatch(r"S\d{6}", source_session) is None:
            errors.append(f"{did}: invalid source_session {source_session!r}")
        elif source_session not in sessions:
            errors.append(f"{did}: source_session references unknown session {source_session}")

        source_event = fm.get("source_event")
        if source_event is not None:
            if not isinstance(source_event, str) or re.fullmatch(r"E\d{6}", source_event) is None:
                errors.append(f"{did}: invalid source_event {source_event!r}")
            elif source_event not in events:
                errors.append(f"{did}: source_event references unknown event {source_event}")

    latest_decision = manifest.get("latest_decision")
    if not isinstance(latest_decision, str) or latest_decision not in decisions:
        errors.append(
            f"MANIFEST latest_decision is not a known decision: {latest_decision!r}"
        )

    try:
        invariant_index = _yaml(root, "invariants/INDEX.yaml")
    except Exception as exc:
        errors.append(str(exc))
        return errors

    invariant_entries = invariant_index.get("invariants")
    if not isinstance(invariant_entries, list):
        errors.append("invariant index invariants must be a list")
        invariant_entries = []

    for entry in invariant_entries:
        if not isinstance(entry, dict):
            errors.append(f"invalid invariant index entry: {entry!r}")
            continue
        rel = entry.get("path")
        if not isinstance(rel, str):
            continue
        try:
            invariant = _yaml(root, rel)
        except Exception as exc:
            errors.append(str(exc))
            continue
        source = invariant.get("source")
        if not isinstance(source, dict):
            continue
        source_decision = source.get("decision")
        if source_decision is None:
            continue
        if (
            not isinstance(source_decision, str)
            or re.fullmatch(r"D\d{6}", source_decision) is None
        ):
            errors.append(
                f"{entry.get('id')}: invalid source decision {source_decision!r}"
            )
            continue
        if source_decision not in decisions:
            errors.append(
                f"{entry.get('id')}: source references unknown decision {source_decision}"
            )
            continue
        expected = f"decisions/{source_decision}.md"
        if source.get("path") != expected:
            errors.append(
                f"{entry.get('id')}: source decision path mismatch: "
                f"{source.get('path')!r} != {expected!r}"
            )

    return errors
