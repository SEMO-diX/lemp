from pathlib import PurePosixPath

ROOT_MEMORY_FILES = {"MANIFEST.yaml", "STATE.md"}
MEMORY_DIRS = {
    "applicability",
    "archive",
    "conflicts",
    "contracts",
    "decisions",
    "events",
    "invariants",
    "reports",
    "sessions",
    "state",
    "topics",
}


def allowed_memory_path(value: str) -> bool:
    if value in ROOT_MEMORY_FILES:
        return True
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    return path.parts[0] in MEMORY_DIRS
