from __future__ import annotations

import re
from pathlib import PurePosixPath

ROOT_MEMORY_FILES = {
    ".gitignore",
    "BOOTSTRAP.md",
    "CONTROL_PLANE.md",
    "INDEX.md",
    "MANIFEST.yaml",
    "README.md",
    "STATE.md",
    "SPECIFICATION.md",
}

MEMORY_DIRS = {
    "applicability",
    "archive",
    "conflicts",
    "contracts",
    "decisions",
    "events",
    "invariants",
    "reports",
    "schemas",
    "sessions",
    "state",
    "topics",
}

WORKFLOW_RE = re.compile(r"^\.github/workflows/lemp-[A-Za-z0-9_.-]+\.ya?ml$")


def allowed_memory_path(value: str) -> bool:
    if value in ROOT_MEMORY_FILES:
        return True

    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False

    if WORKFLOW_RE.fullmatch(value):
        return True

    return path.parts[0] in MEMORY_DIRS
